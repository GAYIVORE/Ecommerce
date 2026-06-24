from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db import models  
from django.db.models import Count
from django.contrib import messages

# Fixed model import typos securely
from .models import Shop
from apps.products.models import Category, Product
# Import your OrderItem model here (adjust the app name 'orders' if yours is different)
from apps.orders.models import OrderItem, SubOrder


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
                status='PENDING'            
            )
            messages.success(request, f"Application for '{new_shop.name}' submitted successfully and is awaiting review!")
            return redirect('/')  
        except Exception as e:
            messages.error(request, f"Error submitting application: {e}")

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
        status__in=['Pending', 'Processing']
    ).select_related('parent_order', 'parent_order__user').prefetch_related('items').order_by('-created_at')
    
    # 3. Compute operational alerts (items low on stock)
    low_stock_count = products.filter(stock__lte=5).count()
        
    context = {
        'shop': shop,
        'products': products,
        'vendor_orders': vendor_orders,      # Pass sub-orders context
        'low_stock_count': low_stock_count,  # Pass critical inventory alert context
    }
    return render(request, 'products/vendor_dashboard.html', context)

def recent_restocks_feed(request):
    """ Endpoint targeted by HTMX to pull the latest 4 in-stock items. """
    recent_restocks = Product.objects.filter(available=True, is_deleted=False, stock__gt=0).order_by('-updated_at')[:4]
    return render(request, 'shops/partials/restock_feed.html', {'recent_restocks': recent_restocks})


def sectors_showcase_api(request):
    """ Renders the marketplace sectors grid asynchronously. """
    categories = (
        Category.objects
        .annotate(total_products=Count('products'))
        .order_by('-total_products')[:3]
    )
    return render(request, 'shops/partials/sectors_showcase.html', {'categories': categories})