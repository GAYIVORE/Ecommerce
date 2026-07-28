# apps/core/tests.py
import datetime

from django.test import TestCase
from django.utils import timezone

from .models import RateLimitAttempt
from .utils import get_client_ip, record_attempt, clear_attempts, is_rate_limited


class RateLimitUtilsTests(TestCase):
    """Covers the sliding-window rate limiter used by login/registration throttling."""

    def test_not_limited_before_threshold(self):
        for _ in range(4):
            record_attempt('login-ip:1.2.3.4')
        self.assertFalse(is_rate_limited('login-ip:1.2.3.4', limit=5, window_minutes=15))

    def test_limited_once_threshold_reached(self):
        for _ in range(5):
            record_attempt('login-ip:1.2.3.4')
        self.assertTrue(is_rate_limited('login-ip:1.2.3.4', limit=5, window_minutes=15))

    def test_old_attempts_outside_window_dont_count(self):
        stale = RateLimitAttempt.objects.create(key='login-ip:9.9.9.9')
        # Backdate it outside the window without touching auto_now_add via update().
        RateLimitAttempt.objects.filter(pk=stale.pk).update(
            created_at=timezone.now() - datetime.timedelta(minutes=30)
        )
        for _ in range(4):
            record_attempt('login-ip:9.9.9.9')
        # 1 stale + 4 fresh = 5 raw rows, but only the 4 fresh ones are in-window.
        self.assertFalse(is_rate_limited('login-ip:9.9.9.9', limit=5, window_minutes=15))

    def test_stale_attempts_are_pruned_from_the_table(self):
        stale = RateLimitAttempt.objects.create(key='login-ip:5.5.5.5')
        RateLimitAttempt.objects.filter(pk=stale.pk).update(
            created_at=timezone.now() - datetime.timedelta(minutes=30)
        )
        is_rate_limited('login-ip:5.5.5.5', limit=5, window_minutes=15)
        self.assertFalse(RateLimitAttempt.objects.filter(pk=stale.pk).exists())

    def test_clear_attempts_resets_the_counter(self):
        for _ in range(5):
            record_attempt('login-user:jane')
        self.assertTrue(is_rate_limited('login-user:jane', limit=5, window_minutes=15))
        clear_attempts('login-user:jane')
        self.assertFalse(is_rate_limited('login-user:jane', limit=5, window_minutes=15))

    def test_keys_are_independent(self):
        for _ in range(5):
            record_attempt('login-user:jane')
        self.assertTrue(is_rate_limited('login-user:jane', limit=5, window_minutes=15))
        self.assertFalse(is_rate_limited('login-user:bob', limit=5, window_minutes=15))

    def test_get_client_ip_prefers_forwarded_for(self):
        class FakeRequest:
            META = {'HTTP_X_FORWARDED_FOR': '203.0.113.4, 10.0.0.1', 'REMOTE_ADDR': '10.0.0.1'}
        self.assertEqual(get_client_ip(FakeRequest()), '203.0.113.4')

    def test_get_client_ip_falls_back_to_remote_addr(self):
        class FakeRequest:
            META = {'REMOTE_ADDR': '10.0.0.1'}
        self.assertEqual(get_client_ip(FakeRequest()), '10.0.0.1')
