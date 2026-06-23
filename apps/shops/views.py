from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db import models  
from django.db.models import Count
from django.contrib import messages
from .models import Shop

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
    # Guard clause: If the user already has a shop record
    if hasattr(request.user, 'shop'):
        shop = request.user.shop
        if shop.status == 'PENDING':
            messages.info(request, "Your shop application is currently pending review.")
            return redirect('/')  # Redirect to home or account page
        messages.warning(request, "You already own a shop!")
        return redirect('shops:vendor_dashboard')

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        # 🌟 1. Extract the new phone number field
        phone_number = request.POST.get('phone_number', '').strip()
        # 🌟 2. Extract the file payload for the image banner/logo
        image = request.FILES.get('image')

        if not name:
            messages.error(request, "Shop name is required.")
            return render(request, 'shops/create_shop.html')

        # Prevent duplicate unique name conflicts explicitly
        if Shop.objects.filter(name__iexact=name).exists():
            messages.error(request, f"The name '{name}' is already taken. Please choose another.")
            return render(request, 'shops/create_shop.html')

        try:
            # Create the shop with a default 'PENDING' approval state
            new_shop = Shop.objects.create(
                owner=request.user,  # Uses the correct 'owner' FK field
                name=name,
                description=description,
                phone_number=phone_number,  # 🌟 3. Save phone number to DB
                image=image,                # 🌟 4. Save image upload to Cloudinary/Storage
                status='PENDING'            # Submits to the admin verification pool
            )
            # Note: Your model's save() method runs slugify() inside .create() automatically!
            
            messages.success(request, f"Application for '{new_shop.name}' submitted successfully and is awaiting review!")
            return redirect('/')  
        except Exception as e:
            messages.error(request, f"Error submitting application: {e}")

    return render(request, 'shops/create_shop.html')


# Make sure to add this import at the very top of your apps/shops/views.py file!
from apps.products.models import Product

@login_required
def vendor_dashboard(request):
    """ View for managing the vendor shop layout once approved """
    if not hasattr(request.user, 'shop'):
        return redirect('shops:create_shop')
        
    shop = request.user.shop
    
    # Direct pending applications or suspended users away from the live workspace
    if shop.status == 'PENDING':
        return render(request, 'shops/application_pending.html', {'shop': shop})
    elif shop.status == 'SUSPENDED' or not shop.is_active or shop.is_deleted: 
        return render(request, 'shops/shop_disabled.html', {'shop': shop})
        
    # 🌟 FETCH THE PRODUCTS LINKED TO THIS ACTIVE SHOP
    products = Product.objects.filter(shop=shop, is_deleted=False).order_by('-created_at')
        
    # 🌟 INCLUDE THE PRODUCTS IN YOUR CONTEXT DICTIONARY
    context = {
        'shop': shop,
        'products': products,
    }
        
    return render(request, 'products/vendor_dashboard.html', context)

def recent_restocks_feed(request):
    """
    Endpoint targeted by HTMX to pull the latest 4 in-stock items.
    """
    recent_restocks = Product.objects.filter(stock__gt=0).order_by('-updated_at')[:4]
    
    # Updated template path format based on your directory layout
    return render(request, 'shops/partials/restock_feed.html', {'recent_restocks': recent_restocks})