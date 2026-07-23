# apps/cart/cart_utils.py

from .models import Cart, CartItem
from apps.products.models import Product
from django.contrib.sessions.models import Session
from django.db import transaction

def _get_or_create_cart_for_user(user):
    """
    Gets or creates a cart for an authenticated user.
    """
    cart, created = Cart.objects.get_or_create(user=user)
    return cart

def _get_or_create_cart_for_session(session_key):
    """
    Gets or creates a cart for an anonymous session.
    Ensures the session exists.
    """
    if not session_key:
        return None

    # Clean up old anonymous carts if their sessions no longer exist
    try:
        Session.objects.get(session_key=session_key)
    except Session.DoesNotExist:
        Cart.objects.filter(session_key=session_key).delete()
        return None

    cart, created = Cart.objects.get_or_create(session_key=session_key)
    return cart

def get_or_create_user_cart(request):
    """
    Retrieves or creates a cart for the current request.
    Handles both authenticated and anonymous users.
    Merges anonymous cart into user cart upon login.
    """
    user = getattr(request, 'user', None)
    if user is not None and user.is_authenticated:
        user_cart = _get_or_create_cart_for_user(request.user)
        
        # Check for an anonymous cart and merge if it exists
        if request.session.session_key:
            anonymous_cart = Cart.objects.filter(session_key=request.session.session_key).first()
            if anonymous_cart and anonymous_cart.pk != user_cart.pk:
                with transaction.atomic():
                    # Optimization: Eager load products during the merge loop
                    anonymous_items = anonymous_cart.items.select_related('product').all()
                    
                    for item in anonymous_items:
                        existing_item = user_cart.items.filter(product=item.product).first()
                        if existing_item:
                            # Caps the merged quantity to whatever stock the vendor actually has
                            potential_qty = existing_item.quantity + item.quantity
                            existing_item.quantity = min(potential_qty, item.product.stock)
                            existing_item.save()
                        else:
                            # Re-bind the item container straight to the user's cart
                            item.cart = user_cart
                            # Cap quantity at current stock level just in case
                            item.quantity = min(item.quantity, item.product.stock)
                            item.save()
                            
                    anonymous_cart.delete() # Safely wipe the empty shell anchor
        return user_cart
    else:
        if not request.session.session_key:
            request.session.create() 
        return _get_or_create_cart_for_session(request.session.session_key)


def add_item_to_cart(request, product_id, quantity=1):
    """
    Safely adds a vendor product to the current session's cart.
    Validates inventory levels and handles multi-vendor quantity modification boundaries.
    
    Returns:
        tuple: (CartItem object or None, error_message string or None)
    """
    # 1. Ensure the product exists and is active/visible
    try:
        product = Product.objects.select_related('shop').get(
            id=product_id, 
            available=True, 
            is_deleted=False, 
            shop__is_active=True, 
            shop__is_deleted=False
        )
    except Product.DoesNotExist:
        return None, "This product is currently unavailable."

    # 2. Prevent adding completely out of stock items
    if product.stock <= 0:
        return None, f"Sorry, '{product.name}' is completely out of stock."

    # 3. Retrieve or build the appropriate cart container
    cart = get_or_create_user_cart(request)
    if not cart:
        return None, "An error occurred while accessing your shopping cart."

    # 4. Handle CartItem manipulation with explicit stock ceilings
    with transaction.atomic():
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': 0}
        )
        
        # Calculate new requested quantity target
        new_quantity = cart_item.quantity + int(quantity)
        
        # Guardrail: Check if target exceeds vendor's stock
        if new_quantity > product.stock:
            if created:
                # If they asked for more than available on first click, give them max stock
                cart_item.quantity = product.stock
                cart_item.save()
                return cart_item, f"Only {product.stock} units of '{product.name}' are available. Added max quantity to cart."
            else:
                return cart_item, f"Cannot add more units. You already have the maximum available stock ({product.stock}) in your cart."
        
        # If within normal bounds, update cleanly
        cart_item.quantity = new_quantity
        cart_item.save()
        return cart_item, None