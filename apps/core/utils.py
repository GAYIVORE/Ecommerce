# apps/core/utils.py
"""
Shared, dependency-free rate-limiting helpers.

Backed by the RateLimitAttempt model (see apps/core/models.py) rather than
Django's cache framework, because the default cache is per-process/in-memory:
fine on a single long-running server, but useless on serverless platforms
(e.g. Vercel) where each invocation can land on a different, cold instance
with no shared memory. A DB-backed counter works correctly everywhere the
app already needs a database anyway.
"""
import datetime

from django.utils import timezone

from .models import RateLimitAttempt


def get_client_ip(request):
    """
    Best-effort real client IP behind a reverse proxy. Vercel (and most
    proxies) forward the original client address via X-Forwarded-For; we take
    the first hop, which is the original client. Falls back to REMOTE_ADDR
    for local/direct requests.
    """
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', 'unknown')


def record_attempt(key):
    """Log one rate-limited event (e.g. a failed login) under `key`."""
    RateLimitAttempt.objects.create(key=key)


def clear_attempts(key):
    """Wipe the attempt history for `key` — call this on a successful login."""
    RateLimitAttempt.objects.filter(key=key).delete()


def is_rate_limited(key, limit, window_minutes):
    """
    Returns True if `key` has accumulated `limit` or more attempts within the
    last `window_minutes`. Also opportunistically deletes attempts for this
    key older than the window, so the table stays small instead of growing
    forever (no separate cleanup cron job needed).
    """
    cutoff = timezone.now() - datetime.timedelta(minutes=window_minutes)
    RateLimitAttempt.objects.filter(key=key, created_at__lt=cutoff).delete()
    return RateLimitAttempt.objects.filter(key=key, created_at__gte=cutoff).count() >= limit
