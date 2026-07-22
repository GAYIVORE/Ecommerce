# apps/earn/models.py
"""
The Earn module lets any user of the shop moonlight as a service provider
or affiliate earner, alongside the regular product marketplace:

- Service / ServiceBooking: peer-to-peer local services (cleaning, delivery,
  tutoring, tech repair...) that other users can discover and book.
- QuickCashOffer: a directory of affiliate/gig opportunities, either curated
  by the platform (submitted_by is null) or contributed by users.
- EarningTransaction: a single ledger of every credit/debit for a user
  (completed bookings, manually logged quick-cash income, withdrawals),
  which is the source of truth for their balance.
"""
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.text import slugify

# Platform commission taken on every completed service booking.
COMMISSION_RATE = Decimal('0.10')


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class ServiceCategory(models.TextChoices):
    CLEANING = 'cleaning', 'Cleaning'
    DELIVERY = 'delivery', 'Delivery & Logistics'
    TUTORING = 'tutoring', 'Education & Tutoring'
    TECH = 'tech', 'Tech & Repairs'
    OTHER = 'other', 'Other Services'


class Service(TimeStampedModel):
    """A service listing posted by a user who wants to earn by offering it."""

    provider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='earn_services',
    )
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, unique=True, blank=True)
    category = models.CharField(
        max_length=20, choices=ServiceCategory.choices, default=ServiceCategory.OTHER
    )
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True)
    contact_phone = models.CharField(
        max_length=30, help_text='WhatsApp / contact number shown to customers'
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)[:250] or 'service'
            candidate = base_slug
            i = 1
            while Service.objects.filter(slug=candidate).exclude(pk=self.pk).exists():
                i += 1
                candidate = f'{base_slug}-{i}'
            self.slug = candidate
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('earn:service_detail', kwargs={'slug': self.slug})

    @property
    def commission_amount(self):
        return (self.price * COMMISSION_RATE).quantize(Decimal('0.01'))

    @property
    def provider_take_home(self):
        return self.price - self.commission_amount

    @property
    def bookings_count(self):
        return self.bookings.filter(status=ServiceBooking.Status.COMPLETED).count()

    @property
    def average_rating(self):
        agg = self.bookings.filter(rating__isnull=False).aggregate(models.Avg('rating'))
        value = agg['rating__avg']
        return round(value, 1) if value is not None else None


class ServiceBooking(TimeStampedModel):
    """A customer's request to book a Service from another user."""

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        CONFIRMED = 'CONFIRMED', 'Confirmed'
        COMPLETED = 'COMPLETED', 'Completed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='bookings')
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='earn_bookings_made',
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    amount = models.DecimalField(
        max_digits=10, decimal_places=2, help_text='Snapshot of the service price at booking time'
    )
    platform_fee = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    provider_earning = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    notes = models.TextField(blank=True)
    rating = models.PositiveSmallIntegerField(blank=True, null=True)
    review_comment = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Booking #{self.pk} - {self.service.title}'

    def mark_completed(self):
        """Complete the booking and credit the provider's ledger with their cut."""
        if self.status == self.Status.COMPLETED:
            return
        self.status = self.Status.COMPLETED
        self.platform_fee = (self.amount * COMMISSION_RATE).quantize(Decimal('0.01'))
        self.provider_earning = self.amount - self.platform_fee
        self.save(update_fields=['status', 'platform_fee', 'provider_earning', 'updated_at'])

        EarningTransaction.objects.create(
            user=self.service.provider,
            amount=self.provider_earning,
            transaction_type=EarningTransaction.Type.SERVICE_BOOKING,
            description=f"Booking completed: {self.service.title}",
            status=EarningTransaction.Status.COMPLETED,
            related_booking=self,
        )


class QuickCashOffer(TimeStampedModel):
    """A directory entry for an external gig / affiliate earning opportunity."""

    class OfferType(models.TextChoices):
        AFFILIATE = 'affiliate', 'Affiliate'
        SURVEY = 'survey', 'Survey'
        LOCAL = 'local', 'Local Gig'

    title = models.CharField(max_length=255)
    description = models.CharField(max_length=500, blank=True)
    earning_range = models.CharField(
        max_length=100, blank=True, help_text='e.g. ₵80 – ₵650'
    )
    link = models.URLField(blank=True)
    offer_type = models.CharField(
        max_length=20, choices=OfferType.choices, default=OfferType.AFFILIATE
    )
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='earn_offers',
        blank=True,
        null=True,
        help_text='Blank means this is an official EarnAccra partner offer',
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class EarningTransaction(TimeStampedModel):
    """Single ledger entry: the source of truth for a user's Earn balance."""

    class Type(models.TextChoices):
        SERVICE_BOOKING = 'SERVICE', 'Service Booking'
        QUICK_CASH = 'QUICK', 'Quick Cash'
        MANUAL = 'MANUAL', 'Manually Logged'
        WITHDRAWAL = 'WITHDRAWAL', 'Withdrawal'

    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        COMPLETED = 'COMPLETED', 'Completed'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='earn_transactions'
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text='Positive for earnings/credits, negative for withdrawals',
    )
    transaction_type = models.CharField(max_length=20, choices=Type.choices, default=Type.MANUAL)
    description = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.COMPLETED)
    related_booking = models.ForeignKey(
        ServiceBooking,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='transactions',
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user} {self.amount} ({self.transaction_type})'
