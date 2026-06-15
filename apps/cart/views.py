# apps/cart/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.contrib import messages
from apps.products.models import Product
from .models import CartItem
from .cart_utils import get_or_create_user_cart # Import our utility function

def cart_detail(request):
    """
    Displays the contents of the user's shopping cart.
    """
    cart = get_or_create_user_cart(request)
    return render(request, 'cart/cart_detail.html', {'cart': cart})

@require_POST # Ensure this view only accepts POST requests
def add_to_cart(request, product_id):
    """
    Adds a product to the cart.
    """
    product = get_object_or_404(Product, id=product_id, available=True)
    quantity = int(request.POST.get('quantity', 1))

    if quantity <= 0:
        messages.error(request, "Quantity must be at least 1.")
        return redirect('products:product_detail', slug=product.slug)

    if product.stock < quantity:
        messages.error(request, f"Not enough stock for {product.name}. Available: {product.stock}")
        return redirect('products:product_detail', slug=product.slug)

    cart = get_or_create_user_cart(request)

    try:
        cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
        if not created:
            # If item already exists, update quantity
            if cart_item.quantity + quantity > product.stock:
                messages.error(request, f"Cannot add more. Exceeds available stock for {product.name}.")
                return redirect('products:product_detail', slug=product.slug)
            cart_item.quantity += quantity
            cart_item.save()
            messages.success(request, f"Updated quantity of {product.name} in your cart.")
        else:
            messages.success(request, f"{product.name} added to your cart.")
    except Exception as e:
        messages.error(request, f"Error adding to cart: {e}")
        return redirect('products:product_detail', slug=product.slug)

    return redirect('cart:cart_detail') # Redirect to cart detail page

@require_POST
def remove_from_cart(request, item_id):
    """
    Removes a specific item from the cart.
    """
    cart = get_or_create_user_cart(request)
    cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
    product_name = cart_item.product.name # Store name before deleting
    cart_item.delete()
    messages.info(request, f"{product_name} removed from your cart.")
    return redirect('cart:cart_detail')

@require_POST
def update_cart(request, item_id):
    """
    Updates the quantity of a specific item in the cart.
    """
    cart = get_or_create_user_cart(request)
    cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
    new_quantity = int(request.POST.get('quantity', cart_item.quantity))

    if new_quantity <= 0:
        cart_item.delete() # Remove item if quantity is 0 or less
        messages.info(request, f"{cart_item.product.name} removed from your cart.")
    elif new_quantity > cart_item.product.stock:
        messages.error(request, f"Cannot update quantity. Only {cart_item.product.stock} of {cart_item.product.name} available.")
    else:
        cart_item.quantity = new_quantity
        cart_item.save()
        messages.success(request, f"Quantity of {cart_item.product.name} updated to {new_quantity}.")

    return redirect('cart:cart_detail')
