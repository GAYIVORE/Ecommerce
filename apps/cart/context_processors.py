# apps/cart/context_processors.py
from .models import Cart


def cart_count_processor(request):
    """
    Globally injects the current cart's total item quantity into every
    rendered template, for the nav bar badge. Read-only: never creates a
    cart, so anonymous browsing doesn't spawn empty Cart rows.
    """
    try:
        if request.user.is_authenticated:
            cart = getattr(request.user, 'cart', None)
        else:
            session_key = request.session.session_key
            cart = Cart.objects.filter(session_key=session_key).first() if session_key else None

        return {'cart_item_count': cart.get_total_quantity if cart else 0}
    except Exception:
        return {'cart_item_count': 0}
