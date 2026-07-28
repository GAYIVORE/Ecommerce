import datetime
import json
import logging

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db import models  
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.contrib import messages
from django.db import IntegrityError
from django.utils import timezone

# Fixed model import typos securely
from .models import Shop
from .forms import VendorShopSettingsForm
from apps.products.models import Category, Product
# Import your OrderItem model here (adjust the app name 'orders' if yours is different)
from apps.orders.models import OrderItem, SubOrder

logger = logging.getLogger(__name__)


def shop_directory(request):
    """ Renders a public directory listing of all verified, active, non-deleted vendor shops. """
    shops = Shop.objects.filter(
        status='ACTIVE',   # Only show fully approved shops in the public directory
        is_active=True,
        is_deleted=False  
    ).annotate(
        total_products=Count(
            'products', 
            filter=models.Q(products__available=True, products__is_deleted=False)
        )
    ).order_by('-total_products')
    
    return render(request, 'shops/shop_directory.html', {'shops': shops})


@login_required
def create_shop(request):
    """ Handles the creation/application form workflow for opening a new shop. """
    if hasattr(request.user, 'shop'):
        shop = request.user.shop
        if shop.status == 'PENDING':
            messages.info(request, "Your shop application is currently pending review.")
            return redirect('/') 
        messages.warning(request, "You already own a shop!")
        return redirect('shops:vendor_dashboard')

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        image = request.FILES.get('image')

        try:
            min_delivery_days = int(request.POST.get('min_delivery_days', 2))
            max_delivery_days = int(request.POST.get('max_delivery_days', 5))
        except (TypeError, ValueError):
            min_delivery_days, max_delivery_days = 2, 5

        if min_delivery_days < 0 or max_delivery_days < 0:
            messages.error(request, "Delivery days can't be negative.")
            return render(request, 'shops/create_shop.html')
        if min_delivery_days > max_delivery_days:
            messages.error(request, "Your fastest delivery estimate can't be slower than your slowest one.")
            return render(request, 'shops/create_shop.html')

        if not name:
            messages.error(request, "Shop name is required.")
            return render(request, 'shops/create_shop.html')

        if Shop.objects.filter(name__iexact=name).exists():
            messages.error(request, f"The name '{name}' is already taken. Please choose another.")
            return render(request, 'shops/create_shop.html')

        try:
            new_shop = Shop.objects.create(
                owner=request.user,  
                name=name,
                description=description,
                phone_number=phone_number,  
                image=image,                
                status='PENDING',
                min_delivery_days=min_delivery_days,
                max_delivery_days=max_delivery_days,
            )
            messages.success(request, f"Application for '{new_shop.name}' submitted successfully and is awaiting review!")
            return redirect('/')  
        except IntegrityError:
            # The pre-check above (filter(name__iexact=name).exists()) can't fully
            # close the race where two people submit the same name at almost the
            # same instant — Shop.name is unique=True at the DB level, so this is
            # the real backstop. Give the same friendly message as the pre-check
            # instead of falling through to the generic error below.
            messages.error(request, f"The name '{name}' is already taken. Please choose another.")
        except Exception as e:
            # 🔒 Fixed: previously showed the raw exception message (f"...{e}") straight
            # to the user, which can leak internal details (DB error text, field names,
            # etc). Log the real error for admins and show a generic, safe message.
            logger.error("Shop application failed for user %s: %s", request.user.pk, e, exc_info=True)
            messages.error(request, "Something went wrong submitting your application. Please try again.")

    return render(request, 'shops/create_shop.html')


@login_required
def vendor_dashboard(request):
    """ View for managing the vendor shop layout once approved """
    if not hasattr(request.user, 'shop'):
        return redirect('shops:create_shop')
        
    shop = request.user.shop
    
    if shop.status == 'PENDING':
        return render(request, 'shops/application_pending.html', {'shop': shop})
    elif shop.status == 'SUSPENDED' or not shop.is_active or shop.is_deleted: 
        return render(request, 'shops/shop_disabled.html', {'shop': shop})
        
    # 1. Fetching shop inventory items
    products = Product.objects.filter(shop=shop, is_deleted=False).order_by('-created_at')
    
    # 2. Fetch incoming SubOrders tied to this vendor shop
    # Filters out completed/cancelled/refunded records to display actionable dispatches
    vendor_orders = SubOrder.objects.filter(
        shop=shop,
        status__in=['Pending', 'Processing', 'Shipped']
    ).select_related('parent_order', 'parent_order__user').prefetch_related('items').order_by('-created_at')
    
    # 3. Compute operational alerts (items low on stock)
    low_stock_count = products.filter(stock__lte=5).count()

    # 4. Sales analytics — mirrors VendorDashboardView so this alternate entry point
    # (linked from the homepage) renders the same chart/revenue widgets instead of
    # leaving them blank or shipping a broken inline script.
    cutoff = timezone.now() - datetime.timedelta(days=30)
    daily = (
        SubOrder.objects.filter(shop=shop, created_at__gte=cutoff)
        .annotate(day=TruncDate('created_at'))
        .values('day')
        .annotate(total=Sum('sub_total'))
        .order_by('day')
    )
    daily_map = {row['day']: float(row['total'] or 0) for row in daily}
    labels, values = [], []
    for i in range(29, -1, -1):
        day = (timezone.now() - datetime.timedelta(days=i)).date()
        labels.append(day.strftime('%b %d'))
        values.append(round(daily_map.get(day, 0), 2))

    all_orders = SubOrder.objects.filter(shop=shop)
    month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    context = {
        'shop': shop,
        'products': products,
        'vendor_orders': vendor_orders,      # Pass sub-orders context
        'low_stock_count': low_stock_count,  # Pass critical inventory alert context
        'sales_chart_labels': json.dumps(labels),
        'sales_chart_values': json.dumps(values),
        'lifetime_revenue': all_orders.aggregate(t=Sum('sub_total'))['t'] or 0,
        'month_revenue': all_orders.filter(created_at__gte=month_start).aggregate(t=Sum('sub_total'))['t'] or 0,
        'month_order_count': all_orders.filter(created_at__gte=month_start).count(),
    }
    return render(request, 'products/vendor_dashboard.html', context)

def recent_restocks_feed(request):
    """ Endpoint targeted by HTMX to pull the latest 4 in-stock items. """
    recent_restocks = Product.objects.filter(available=True, is_deleted=False, stock__gt=0).select_related('shop').order_by('-updated_at')[:4]
    return render(request, 'shops/partials/restock_feed.html', {'recent_restocks': recent_restocks})


def sectors_showcase_api(request):
    """ Renders the marketplace sectors grid asynchronously. """
    categories = (
        Category.objects
        .annotate(total_products=Count('products'))
        .order_by('-total_products')[:3]
    )
    return render(request, 'shops/partials/sectors_showcase.html', {'categories': categories})


@login_required
def shop_settings(request):
    """
    Lets a vendor edit their own storefront profile, including the delivery-window
    promise (min/max days) that customers see on every product page, at checkout,
    and on every order they place — set once here, applied automatically everywhere.
    """
    if not hasattr(request.user, 'shop'):
        return redirect('shops:create_shop')

    shop = request.user.shop

    if request.method == 'POST':
        form = VendorShopSettingsForm(request.POST, request.FILES, instance=shop)
        if form.is_valid():
            form.save()
            messages.success(request, "Shop settings updated.")
            return redirect('shops:shop_settings')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = VendorShopSettingsForm(instance=shop)

    return render(request, 'shops/shop_settings.html', {'shop': shop, 'form': form})