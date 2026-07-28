# apps/promotions/tests.py
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.shops.models import Shop
from .forms import CouponApplyForm
from .models import Coupon

User = get_user_model()


class CouponModelTests(TestCase):
    def setUp(self):
        self.now = timezone.now()

    def _make_coupon(self, **overrides):
        defaults = dict(
            code='SAVE10',
            valid_from=self.now - timedelta(days=1),
            valid_to=self.now + timedelta(days=1),
            discount=10,
            active=True,
        )
        defaults.update(overrides)
        return Coupon.objects.create(**defaults)

    def test_active_coupon_within_window_is_valid(self):
        coupon = self._make_coupon()
        self.assertTrue(coupon.is_valid)

    def test_inactive_coupon_is_invalid(self):
        coupon = self._make_coupon(active=False)
        self.assertFalse(coupon.is_valid)

    def test_not_yet_started_coupon_is_invalid(self):
        coupon = self._make_coupon(
            valid_from=self.now + timedelta(days=1), valid_to=self.now + timedelta(days=2)
        )
        self.assertFalse(coupon.is_valid)

    def test_expired_coupon_is_invalid(self):
        coupon = self._make_coupon(
            valid_from=self.now - timedelta(days=5), valid_to=self.now - timedelta(days=1)
        )
        self.assertFalse(coupon.is_valid)

    def test_coupon_under_usage_limit_is_valid(self):
        coupon = self._make_coupon(usage_limit=5, times_used=4)
        self.assertTrue(coupon.is_valid)

    def test_coupon_at_usage_limit_is_invalid(self):
        coupon = self._make_coupon(usage_limit=5, times_used=5)
        self.assertFalse(coupon.is_valid)

    def test_coupon_with_no_usage_limit_never_caps_out(self):
        coupon = self._make_coupon(usage_limit=None, times_used=10_000)
        self.assertTrue(coupon.is_valid)


class CouponApplyFormTests(TestCase):
    def setUp(self):
        self.now = timezone.now()
        self.vendor = User.objects.create_user(username='vendor', email='vendor@example.com', password='pass12345')
        self.shop = Shop.objects.create(owner=self.vendor, name='Gizmo Shop', status='ACTIVE', is_active=True)

    def test_blank_code_is_rejected(self):
        form = CouponApplyForm(data={'code': '  '})
        self.assertFalse(form.is_valid())

    def test_nonexistent_code_is_rejected(self):
        form = CouponApplyForm(data={'code': 'DOESNOTEXIST'})
        self.assertFalse(form.is_valid())
        self.assertIn('invalid or has expired', form.errors['code'][0])

    def test_valid_code_is_accepted_and_attaches_coupon(self):
        Coupon.objects.create(
            code='SAVE20', valid_from=self.now - timedelta(days=1), valid_to=self.now + timedelta(days=1),
            discount=20, active=True,
        )
        form = CouponApplyForm(data={'code': 'save20'})  # case-insensitive lookup
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_coupon.code, 'SAVE20')

    def test_expired_code_is_rejected(self):
        Coupon.objects.create(
            code='OLD10', valid_from=self.now - timedelta(days=10), valid_to=self.now - timedelta(days=1),
            discount=10, active=True,
        )
        form = CouponApplyForm(data={'code': 'OLD10'})
        self.assertFalse(form.is_valid())

    def test_depleted_code_is_rejected(self):
        Coupon.objects.create(
            code='DEPLETED', valid_from=self.now - timedelta(days=1), valid_to=self.now + timedelta(days=1),
            discount=15, active=True, usage_limit=3, times_used=3,
        )
        form = CouponApplyForm(data={'code': 'DEPLETED'})
        self.assertFalse(form.is_valid())
        self.assertIn('run out of redemptions', form.errors['code'][0])

    def test_inactive_code_is_rejected(self):
        Coupon.objects.create(
            code='PAUSED', valid_from=self.now - timedelta(days=1), valid_to=self.now + timedelta(days=1),
            discount=15, active=False,
        )
        form = CouponApplyForm(data={'code': 'PAUSED'})
        self.assertFalse(form.is_valid())
