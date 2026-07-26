# apps/core/context_processors.py
from django.core.cache import cache


def google_oauth_processor(request):
    """
    Exposes whether Google OAuth is actually configured so templates can
    safely hide the "Continue with Google" button instead of crashing with
    allauth.socialaccount.models.SocialApp.DoesNotExist when no SocialApp
    has been configured for this environment.

    Google OAuth is configured via the admin panel (a SocialApp row at
    /admin/socialaccount/socialapp/), not via env vars, so this checks the
    database directly rather than a settings flag. The result is cached
    briefly since this runs on every request across every page.
    """
    enabled = cache.get('google_oauth_enabled')
    if enabled is None:
        from allauth.socialaccount.models import SocialApp
        enabled = SocialApp.objects.filter(provider='google').exists()
        cache.set('google_oauth_enabled', enabled, 300)  # 5 minutes
    return {
        'google_oauth_enabled': enabled,
    }