# apps/cart/signals.py

from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from apps.cart.cart_utils import get_or_create_user_cart

@receiver(user_logged_in)
def merge_anonymous_cart_on_login(sender, request, user, **kwargs):
    """
    Listens to Django's built-in login event.
    Automatically grabs any guest items floating in the session 
    and welds them safely into the user's permanent database cart.
    """
    get_or_create_user_cart(request)