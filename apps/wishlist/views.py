# apps/wishlist/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.utils import IntegrityError # For handling unique_together constraint
from django.views.decorators.http import require_POST

from apps.products.models import Product
from .models import Wishlist, WishlistItem

@login_required
def wishlist_detail(request):
    """
    Displays the user's wishlist.
    """
    wishlist, created = Wishlist.objects.get_or_create(user=request.user)
    return render(request, 'wishlist/wishlist_detail.html', {'wishlist': wishlist})

@login_required
@require_POST
def add_to_wishlist(request, product_id):
    """
    Adds a product to the user's wishlist.
    """
    product = get_object_or_404(Product, id=product_id)
    wishlist, created = Wishlist.objects.get_or_create(user=request.user)

    try:
        WishlistItem.objects.create(wishlist=wishlist, product=product)
        messages.success(request, f"{product.name} has been added to your wishlist!")
    except IntegrityError:
        messages.info(request, f"{product.name} is already in your wishlist.")
    except Exception as e:
        messages.error(request, f"An error occurred while adding to wishlist: {e}")

    # Redirect back to the product detail page or product list
    return redirect(request.META.get('HTTP_REFERER', 'products:product_list'))

@login_required
@require_POST
def remove_from_wishlist(request, item_id):
    """
    Removes a product from the user's wishlist.
    """
    wishlist_item = get_object_or_404(WishlistItem, id=item_id, wishlist__user=request.user)
    product_name = wishlist_item.product.name # Get name before deleting
    wishlist_item.delete()
    messages.info(request, f"{product_name} has been removed from your wishlist.")
    return redirect('wishlist:wishlist_detail')

@login_required
@require_POST
def move_to_cart(request, item_id):
    """
    Moves a product from the wishlist to the shopping cart.
    """
    from apps.cart.cart_utils import add_item_to_cart # Import here to avoid circular dependency

    wishlist_item = get_object_or_404(WishlistItem, id=item_id, wishlist__user=request.user)
    product = wishlist_item.product

    if product.stock > 0 and product.available:
        try:
            # Add to cart (quantity 1 by default)
            add_item_to_cart(request, product, 1)
            wishlist_item.delete() # Remove from wishlist after moving to cart
            messages.success(request, f"{product.name} has been moved to your cart!")
        except Exception as e:
            messages.error(request, f"Could not move {product.name} to cart: {e}")
    else:
        messages.warning(request, f"{product.name} is out of stock or unavailable and cannot be moved to cart.")

    return redirect('wishlist:wishlist_detail')
