from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import LogEarningForm, QuickCashOfferForm, ServiceForm, WithdrawForm
from .models import EarningTransaction, QuickCashOffer, Service, ServiceBooking, ServiceCategory
from .utils import get_user_balance

# =============================================================================
# DASHBOARD
# =============================================================================


@login_required
def dashboard(request):
    user = request.user
    services_count = Service.objects.filter(provider=user).count()
    bookings_received = ServiceBooking.objects.filter(service__provider=user)
    completed_bookings = bookings_received.filter(status=ServiceBooking.Status.COMPLETED)

    lifetime_earned = EarningTransaction.objects.filter(
        user=user, status=EarningTransaction.Status.COMPLETED, amount__gt=0
    ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')

    avg_earning_per_booking = completed_bookings.aggregate(
        avg=Avg('provider_earning')
    )['avg'] or Decimal('0.00')

    context = {
        'active_tab': 'dashboard',
        'services_count': services_count,
        'bookings_count': completed_bookings.count(),
        'pending_bookings_count': bookings_received.filter(
            status=ServiceBooking.Status.PENDING
        ).count(),
        'lifetime_earned': lifetime_earned,
        'balance': get_user_balance(user),
        'avg_earning_per_booking': avg_earning_per_booking,
        'recent_transactions': EarningTransaction.objects.filter(user=user)[:6],
    }
    return render(request, 'earn/dashboard.html', context)


# =============================================================================
# SERVICES MARKETPLACE
# =============================================================================


@login_required
def marketplace(request):
    services = (
        Service.objects.filter(is_active=True)
        .select_related('provider')
        .exclude(provider=request.user)
    )

    query = request.GET.get('q', '').strip()
    category = request.GET.get('category', '')
    sort = request.GET.get('sort', 'newest')

    if query:
        services = services.filter(Q(title__icontains=query) | Q(description__icontains=query))
    if category:
        services = services.filter(category=category)

    if sort == 'price_low':
        services = services.order_by('price')
    elif sort == 'price_high':
        services = services.order_by('-price')
    elif sort == 'popular':
        services = services.annotate(
            completed_bookings=Count(
                'bookings', filter=Q(bookings__status=ServiceBooking.Status.COMPLETED)
            )
        ).order_by('-completed_bookings')
    else:
        services = services.order_by('-created_at')

    paginator = Paginator(services, 12)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'active_tab': 'marketplace',
        'page_obj': page_obj,
        'categories': ServiceCategory.choices,
        'query': query,
        'selected_category': category,
        'sort': sort,
    }
    return render(request, 'earn/marketplace.html', context)


@login_required
def service_detail(request, slug):
    service = get_object_or_404(Service, slug=slug, is_active=True)
    return render(
        request, 'earn/service_detail.html', {'active_tab': 'marketplace', 'service': service}
    )


@login_required
def service_create(request):
    if request.method == 'POST':
        form = ServiceForm(request.POST)
        if form.is_valid():
            service = form.save(commit=False)
            service.provider = request.user
            service.save()
            messages.success(request, 'Your service has been published!')
            return redirect('earn:marketplace')
    else:
        form = ServiceForm()
    return render(request, 'earn/service_form.html', {'active_tab': 'marketplace', 'form': form})


@require_POST
@login_required
def book_service(request, pk):
    service = get_object_or_404(Service, pk=pk, is_active=True)
    if service.provider_id == request.user.id:
        messages.error(request, "You can't book your own service.")
        return redirect('earn:marketplace')

    ServiceBooking.objects.create(
        service=service,
        customer=request.user,
        amount=service.price,
        notes=request.POST.get('notes', ''),
    )
    messages.success(
        request, f"Booking request sent for '{service.title}'. The provider will confirm shortly."
    )
    return redirect('earn:my_bookings')


# =============================================================================
# BOOKINGS MANAGEMENT
# =============================================================================


@login_required
def my_bookings(request):
    context = {
        'active_tab': 'bookings',
        'incoming': ServiceBooking.objects.filter(service__provider=request.user).select_related(
            'service', 'customer'
        ),
        'outgoing': ServiceBooking.objects.filter(customer=request.user).select_related(
            'service', 'service__provider'
        ),
    }
    return render(request, 'earn/bookings.html', context)


@require_POST
@login_required
def booking_confirm(request, pk):
    booking = get_object_or_404(
        ServiceBooking,
        pk=pk,
        service__provider=request.user,
        status=ServiceBooking.Status.PENDING,
    )
    booking.status = ServiceBooking.Status.CONFIRMED
    booking.save(update_fields=['status', 'updated_at'])
    messages.success(request, 'Booking confirmed.')
    return redirect('earn:my_bookings')


@require_POST
@login_required
def booking_complete(request, pk):
    booking = get_object_or_404(ServiceBooking, pk=pk, service__provider=request.user)
    booking.mark_completed()
    messages.success(request, 'Booking marked completed — your earnings have been credited.')
    return redirect('earn:my_bookings')


@require_POST
@login_required
def booking_cancel(request, pk):
    booking = get_object_or_404(ServiceBooking, pk=pk)
    if request.user.id not in (booking.customer_id, booking.service.provider_id):
        messages.error(request, 'You are not allowed to cancel this booking.')
        return redirect('earn:my_bookings')

    if booking.status in (ServiceBooking.Status.PENDING, ServiceBooking.Status.CONFIRMED):
        booking.status = ServiceBooking.Status.CANCELLED
        booking.save(update_fields=['status', 'updated_at'])
        messages.info(request, 'Booking cancelled.')
    return redirect('earn:my_bookings')


@require_POST
@login_required
def booking_review(request, pk):
    booking = get_object_or_404(
        ServiceBooking, pk=pk, customer=request.user, status=ServiceBooking.Status.COMPLETED
    )
    rating = request.POST.get('rating')
    if rating:
        booking.rating = int(rating)
        booking.review_comment = request.POST.get('review_comment', '')
        booking.save(update_fields=['rating', 'review_comment', 'updated_at'])
        messages.success(request, 'Thanks for your review!')
    return redirect('earn:my_bookings')


# =============================================================================
# QUICK CASH
# =============================================================================


@login_required
def quickcash(request):
    offers = QuickCashOffer.objects.filter(is_active=True).select_related('submitted_by')
    return render(request, 'earn/quickcash.html', {'active_tab': 'quickcash', 'offers': offers})


@login_required
def add_offer(request):
    if request.method == 'POST':
        form = QuickCashOfferForm(request.POST)
        if form.is_valid():
            offer = form.save(commit=False)
            offer.submitted_by = request.user
            offer.save()
            messages.success(request, 'Your link has been added to Quick Cash offers.')
            return redirect('earn:quickcash')
    else:
        form = QuickCashOfferForm()
    return render(request, 'earn/offer_form.html', {'active_tab': 'quickcash', 'form': form})


@require_POST
@login_required
def delete_offer(request, pk):
    offer = get_object_or_404(QuickCashOffer, pk=pk, submitted_by=request.user)
    offer.delete()
    messages.info(request, 'Offer removed.')
    return redirect('earn:quickcash')


# =============================================================================
# EARNINGS
# =============================================================================


@login_required
def earnings(request):
    user = request.user
    now = timezone.now()
    thirty_days_ago = now - timezone.timedelta(days=30)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    completed_credits = EarningTransaction.objects.filter(
        user=user, status=EarningTransaction.Status.COMPLETED, amount__gt=0
    )
    lifetime_earned = completed_credits.aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')

    this_month_qs = completed_credits.filter(created_at__gte=month_start)
    this_month = this_month_qs.aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')

    last_30_qs = completed_credits.filter(created_at__gte=thirty_days_ago)
    avg_per_day = (
        last_30_qs.aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
    ) / Decimal('30')

    # Build a day-by-day totals series for the trend chart.
    daily_totals = {}
    for i in range(30):
        day = (now - timezone.timedelta(days=29 - i)).date()
        daily_totals[day.isoformat()] = 0.0
    for tx in last_30_qs:
        day_key = timezone.localtime(tx.created_at).date().isoformat()
        if day_key in daily_totals:
            daily_totals[day_key] += float(tx.amount)

    context = {
        'active_tab': 'earnings',
        'lifetime_earned': lifetime_earned,
        'balance': get_user_balance(user),
        'this_month': this_month,
        'this_month_count': this_month_qs.count(),
        'avg_per_day': round(avg_per_day, 2),
        'transactions': EarningTransaction.objects.filter(user=user)[:25],
        'chart_labels': list(daily_totals.keys()),
        'chart_values': list(daily_totals.values()),
    }
    return render(request, 'earn/earnings.html', context)


@login_required
def log_earning(request):
    if request.method == 'POST':
        form = LogEarningForm(request.POST)
        if form.is_valid():
            EarningTransaction.objects.create(
                user=request.user,
                amount=form.cleaned_data['amount'],
                transaction_type=EarningTransaction.Type.QUICK_CASH,
                description=form.cleaned_data['description'],
                status=EarningTransaction.Status.COMPLETED,
            )
            messages.success(request, 'Earning logged!')
            return redirect('earn:earnings')
    else:
        form = LogEarningForm()
    return render(request, 'earn/log_earning.html', {'active_tab': 'earnings', 'form': form})


@login_required
def withdraw(request):
    balance = get_user_balance(request.user)
    if request.method == 'POST':
        form = WithdrawForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            if amount > balance:
                messages.error(request, "You can't withdraw more than your available balance.")
            else:
                EarningTransaction.objects.create(
                    user=request.user,
                    amount=-amount,
                    transaction_type=EarningTransaction.Type.WITHDRAWAL,
                    description='Withdrawal to Mobile Money',
                    status=EarningTransaction.Status.PENDING,
                )
                messages.success(
                    request, f'Withdrawal request of ₵{amount} submitted. Payout via MoMo within 24 hours.'
                )
                return redirect('earn:earnings')
    else:
        form = WithdrawForm()
    return render(
        request, 'earn/withdraw.html', {'active_tab': 'earnings', 'form': form, 'balance': balance}
    )
