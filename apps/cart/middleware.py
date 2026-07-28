# apps/cart/middleware.py


class CaptureAnonymousSessionKeyMiddleware:
    """
    🛠️ Fixes a real bug: guest carts were silently getting lost on login.

    Session-key rotation (`request.session.cycle_key()`) happens automatically
    the moment `django.contrib.auth.login()` runs, as a security measure
    against session fixation — that's correct and must stay. But it means
    that by the time the `user_logged_in` signal fires (which
    apps/cart/signals.py listens to, to merge a guest's cart into their new
    account), the *old* anonymous session key has already been rotated away
    and deleted from the session store. `request.session.session_key` inside
    the signal handler is the brand-new post-login key, not the one the
    guest's Cart row was actually saved under — so the anonymous cart was
    never found, and its items silently vanished the moment someone logged in.

    This middleware records the session key as it was at the very start of
    the request (before any view has a chance to call login()), so the merge
    logic in apps.cart.cart_utils can use the correct pre-rotation key —
    regardless of which view or auth backend triggers the login (our own
    login view, django-allauth email/password, Google OAuth, the Django
    admin login, etc).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request._pre_login_session_key = getattr(request.session, 'session_key', None)
        return self.get_response(request)
