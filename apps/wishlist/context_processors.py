# apps/wishlist/context_processors.py

def wishlist_count_processor(request):
    """
    Globally injects the authenticated user's wishlist count 
    into all rendered templates.
    """
    if request.user.is_authenticated:
        try:
            # Safely count the related items on the user's wishlist
            count = request.user.wishlist.items.count()
            return {'wishlist_count': count}
        except Exception:
            return {'wishlist_count': 0}
    return {'wishlist_count': 0}