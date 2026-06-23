# apps/core/views.py

from django.shortcuts import render
from django.utils import timezone
from django.db import models
from django.db.models import F
from apps.products.models import Category
from apps.promotions.models import Coupon


def home(request):
    """
    Renders the homepage of the e-commerce shop, including active product categories
    and platform-wide marketing promotional discount vouchers.
    """
    now = timezone.now()
    categories = Category.objects.prefetch_related('products').all()
    
    # Fetch a live, active global platform coupon matching your admin status badges
    active_coupon = (
        Coupon.objects.filter(
            shop__isnull=True,            # Global coupon (not bound to a single vendor)
            active=True,                  # Must be manually toggled active
            valid_from__lte=now,          # The campaign has officially started
            valid_to__gte=now             # The campaign has not expired yet
        )
        .filter(
            # Only select if usage_limit is unrestricted, OR times_used is under the allowed ceiling
            models.Q(usage_limit__isnull=True) | models.Q(times_used__lt=F('usage_limit'))
        )
        .order_by('-created_at')          # Always render the newest promotional deal
        .first()
    )
    
    context = {
        'categories': categories,
        'coupon': active_coupon,
    }
    return render(request, 'core/home.html', context)