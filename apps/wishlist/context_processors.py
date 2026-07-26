# apps/wishlist/context_processors.py

from .models import WishlistItem


def wishlist_count_processor(request):
    """
    Globally injects the authenticated user's wishlist count
    into all rendered templates.

    Runs on every page load, so this is a single COUNT query against
    WishlistItem (filtered through the wishlist -> user relation) rather
    than first fetching the Wishlist row and then counting its items —
    that used to cost two round-trips per request for every logged-in user.
    """
    if request.user.is_authenticated:
        try:
            count = WishlistItem.objects.filter(wishlist__user=request.user).count()
            return {'wishlist_count': count}
        except Exception:
            return {'wishlist_count': 0}
    return {'wishlist_count': 0}