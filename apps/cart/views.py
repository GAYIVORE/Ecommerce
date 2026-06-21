# apps/cart/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.contrib import messages
from apps.products.models import Product
from .models import CartItem, Cart
from .cart_utils import get_or_create_user_cart, add_item_to_cart  # ⚡ Imported add utility

def cart_detail(request):
    """
    Displays the contents of the user's shopping cart.
    Optimized with deep prefetching to handle multi-vendor templates efficiently.
    """
    cart = get_or_create_user_cart(request)
    
    # ⚡ Performance Optimization: Eager load items, products, and their parent shops 
    # to kill N+1 query traps when grouping items by vendor on the frontend.
    if cart:
        optimized_items = cart.items.select_related('product__shop', 'product__category')
        # Use a small trick to cache the optimized queryset into the object mapping
        cart.cached_items = optimized_items
        
    return render(request, 'cart/cart_detail.html', {'cart': cart})


@require_POST
def add_to_cart_view(request, product_id):
    """
    Adds a product to the cart using our localized, stock-safe business utility.
    """
    quantity = int(request.POST.get('quantity', 1))
    
    if quantity <= 0:
        messages.error(request, "Quantity must be at least 1.")
        # Fallback to referrer or home if slug data path is unknown
        return redirect(request.META.get('HTTP_REFERER', 'products:product_list'))

    # ⚡ Outsource structural validation and database checks to cart_utils
    cart_item, error_message = add_item_to_cart(request, product_id, quantity=quantity)

    if error_message:
        messages.error(request, error_message)
        if cart_item:
            # If the item exists but they tried to add past stock capacity, take them to the cart
            return redirect('cart:cart_detail')
        return redirect(request.META.get('HTTP_REFERER', 'products:product_list'))

    messages.success(request, f"'{cart_item.product.name}' added to your cart successfully.")
    return redirect('cart:cart_detail')


@require_POST
def remove_from_cart(request, item_id):
    """
    Removes a specific item from the cart.
    """
    cart = get_or_create_user_cart(request)
    cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
    product_name = cart_item.product.name 
    cart_item.delete()
    messages.info(request, f"'{product_name}' removed from your cart.")
    return redirect('cart:cart_detail')


@require_POST
def update_cart(request, item_id):
    """
    Updates the quantity of a specific item in the cart with explicit multi-vendor stock checks.
    """
    cart = get_or_create_user_cart(request)
    cart_item = get_object_or_404(CartItem.objects.select_related('product'), id=item_id, cart=cart)
    new_quantity = int(request.POST.get('quantity', cart_item.quantity))

    if new_quantity <= 0:
        cart_item.delete() 
        messages.info(request, f"'{cart_item.product.name}' removed from your cart.")
    elif new_quantity > cart_item.product.stock:
        messages.error(request, f"Cannot update quantity. Only {cart_item.product.stock} units of '{cart_item.product.name}' are available.")
    else:
        cart_item.quantity = new_quantity
        cart_item.save()
        messages.success(request, f"Quantity of '{cart_item.product.name}' updated to {new_quantity}.")

    return redirect('cart:cart_detail')