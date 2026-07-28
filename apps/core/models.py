from django.db import models


class RateLimitAttempt(models.Model):
    """
    Generic sliding-window rate-limit / lockout tracker.

    Each row is one "attempt" (e.g. a failed login, a registration submission)
    recorded against an arbitrary string key. Callers decide what the key means
    (e.g. "login-ip:203.0.113.4" or "login-user:jane") and how large a
    window/threshold counts as abuse — this model just stores timestamps
    cheaply, so it works the same on SQLite locally and Postgres in production
    (including serverless deployments, where an in-memory cache wouldn't be
    shared across function instances).
    """
    key = models.CharField(max_length=200, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Rate Limit Attempt"
        verbose_name_plural = "Rate Limit Attempts"
        indexes = [
            models.Index(fields=['key', 'created_at']),
        ]

    def __str__(self):
        return f"{self.key} @ {self.created_at:%Y-%m-%d %H:%M:%S}"
