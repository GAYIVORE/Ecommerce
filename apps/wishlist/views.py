# apps/wishlist/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.utils import IntegrityError
from django.core.exceptions import ValidationError
from django.views.decorators.http import require_POST

from apps.products.models import Product
from .models import Wishlist, WishlistItem


@login_required
def wishlist_detail(request):
    """
    Displays the user's wishlist, optimized with prefetched product data 
    to prevent performance bottlenecks.
    """
    wishlist, created = Wishlist.objects.get_or_create(user=request.user)
    
    # Optimize query rendering: Pre-fetch items and related products/images in 1 single pass
    wishlist_items = (
        wishlist.items.select_related('product')
        .prefetch_related('product__images')
        .all()
    )
    
    context = {
        'wishlist': wishlist,
        'wishlist_items': wishlist_items,
    }
    return render(request, 'wishlist/wishlist_detail.html', context)


@login_required
@require_POST
def add_to_wishlist(request, product_id):
    """
    Adds a product to the user's wishlist with comprehensive defensive validation checks.
    """
    product = get_object_or_404(Product, id=product_id)
    wishlist, created = Wishlist.objects.get_or_create(user=request.user)

    try:
        WishlistItem.objects.create(wishlist=wishlist, product=product)
        messages.success(request, f"{product.name} has been added to your wishlist!")
    except IntegrityError:
        messages.info(request, f"{product.name} is already in your wishlist.")
    except ValidationError as e:
        # Handles your model's custom defensive rules (e.g. self-vendor check) safely
        messages.warning(request, e.message if hasattr(e, 'message') else str(e))
    except Exception as e:
        messages.error(request, f"An error occurred while adding to wishlist: {e}")

    return redirect(request.META.get('HTTP_REFERER', 'products:product_list'))


@login_required
@require_POST
def remove_from_wishlist(request, item_id):
    """
    Removes an item from the user's wishlist.
    """
    wishlist_item = get_object_or_404(WishlistItem, id=item_id, wishlist__user=request.user)
    product_name = wishlist_item.product.name
    wishlist_item.delete()
    
    messages.info(request, f"{product_name} has been removed from your wishlist.")
    return redirect('wishlist:wishlist_detail')


@login_required
@require_POST
def move_to_cart(request, item_id):
    """
    Safely transitions a product from the saved wishlist table into the active session cart.
    """
    # Lazy import inside view controller to prevent circular application dependencies
    from apps.cart.cart_utils import add_item_to_cart 

    wishlist_item = get_object_or_404(
        WishlistItem.objects.select_related('product'), 
        id=item_id, 
        wishlist__user=request.user
    )
    product = wishlist_item.product

    # Check inventory and active listing visibility parameters
    if product.stock > 0 and product.available:
        try:
            add_item_to_cart(request, product, quantity=1)
            wishlist_item.delete()  # Drop from wishlist container on successful cart transfer
            messages.success(request, f"{product.name} has been moved to your cart!")
        except Exception as e:
            messages.error(request, f"Could not move {product.name} to cart: {e}")
    else:
        messages.warning(
            request, 
            f"{product.name} is currently out of stock or unavailable and cannot be moved to cart."
        )

    return redirect('wishlist:wishlist_detail')