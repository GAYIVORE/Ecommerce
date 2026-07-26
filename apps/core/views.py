# apps/core/views.py

from django.shortcuts import render
from django.utils import timezone
from django.db import models
from django.db.models import F, Count, Q
from apps.products.models import Category, Product
from apps.promotions.models import Coupon
from apps.shops.models import Shop
from apps.earn.models import Service


def home(request):
    """
    Renders the homepage of the e-commerce shop, including active product categories,
    platform-wide marketing promotional discount vouchers, and the hero ad carousel
    (featured shop / product / service spotlights).
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

    # --- Hero ad carousel spotlights ---------------------------------------
    # Best-stocked verified shop with a logo/banner image, used for the "shop" slide.
    featured_shop = (
        Shop.objects.filter(status='ACTIVE', is_active=True, is_deleted=False)
        .exclude(image='')
        .annotate(
            total_products=Count(
                'products', filter=Q(products__available=True, products__is_deleted=False)
            )
        )
        .order_by('-total_products')
        .first()
    )

    # Most recently updated in-stock product with an image, used for the "product" slide.
    featured_product = (
        Product.objects.filter(available=True, is_deleted=False, stock__gt=0)
        .exclude(image='')
        .select_related('shop')
        .order_by('-updated_at')
        .first()
    )

    # Newest active service listing, used for the "services" slide.
    featured_service = (
        Service.objects.filter(is_active=True)
        .select_related('provider')
        .order_by('-created_at')
        .first()
    )

    # A handful of the newest live listings for the homepage services showcase strip.
    recent_services = (
        Service.objects.filter(is_active=True)
        .select_related('provider')
        .order_by('-created_at')[:3]
    )

    context = {
        'categories': categories,
        'coupon': active_coupon,
        'featured_shop': featured_shop,
        'featured_product': featured_product,
        'featured_service': featured_service,
        'recent_services': recent_services,
    }
    return render(request, 'core/home.html', context)