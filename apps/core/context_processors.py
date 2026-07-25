# apps/core/context_processors.py
from django.conf import settings


def google_oauth_processor(request):
    """
    Exposes whether Google OAuth is actually configured (real client id/secret
    present) so templates can safely hide the "Sign in with Google" button
    instead of crashing with allauth.socialaccount.models.SocialApp.DoesNotExist
    when no SocialApp has been configured for this environment.
    """
    return {
        'google_oauth_enabled': bool(getattr(settings, 'GOOGLE_OAUTH_ENABLED', False)),
    }
