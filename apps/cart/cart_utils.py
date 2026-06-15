# apps/cart/cart_utils.py

from .models import Cart
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
    # Ensure a session key exists for anonymous users
    if not session_key:
        return None # Or raise an error, depending on desired behavior

    # Clean up old anonymous carts if their sessions no longer exist
    # This is a simple cleanup, for production, consider a periodic task
    try:
        Session.objects.get(session_key=session_key)
    except Session.DoesNotExist:
        # If session doesn't exist, invalidate the old cart and create a new one
        Cart.objects.filter(session_key=session_key).delete()
        session_key = None # Force creation of a new session and cart

    if not session_key: # If session key was invalid or not provided
        return None

    cart, created = Cart.objects.get_or_create(session_key=session_key)
    return cart

def get_or_create_user_cart(request):
    """
    Retrieves or creates a cart for the current request.
    Handles both authenticated and anonymous users.
    Merges anonymous cart into user cart upon login.
    """
    if request.user.is_authenticated:
        user_cart = _get_or_create_cart_for_user(request.user)
        # Check for an anonymous cart and merge if exists
        if request.session.session_key:
            anonymous_cart = Cart.objects.filter(session_key=request.session.session_key).first()
            if anonymous_cart and anonymous_cart.pk != user_cart.pk: # Ensure it's not the same cart
                with transaction.atomic():
                    for item in anonymous_cart.items.all():
                        # Try to find existing item in user's cart
                        existing_item = user_cart.items.filter(product=item.product).first()
                        if existing_item:
                            existing_item.quantity += item.quantity
                            existing_item.save()
                        else:
                            # Assign the item to the user's cart
                            item.cart = user_cart
                            item.save()
                    anonymous_cart.delete() # Delete the old anonymous cart
                # Clear the session key for the anonymous cart to prevent re-merging
                if 'session_key' in request.session:
                    del request.session['session_key']
        return user_cart
    else:
        # For anonymous users, ensure a session key exists
        if not request.session.session_key:
            request.session.create() # Create a new session if one doesn't exist
        return _get_or_create_cart_for_session(request.session.session_key)


def add_item_to_cart():
    return None