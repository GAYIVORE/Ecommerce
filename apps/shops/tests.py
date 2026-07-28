# apps/shops/tests.py
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Shop

User = get_user_model()


class ShopDirectoryTests(TestCase):
    def setUp(self):
        self.vendor = User.objects.create_user(username='vendor', email='v@example.com', password='pass12345')

    def test_active_shop_is_listed(self):
        Shop.objects.create(owner=self.vendor, name='Gizmo Shop', status='ACTIVE', is_active=True)
        response = self.client.get(reverse('shops:shop_directory'))
        self.assertContains(response, 'Gizmo Shop')

    def test_pending_shop_is_not_listed(self):
        Shop.objects.create(owner=self.vendor, name='Pending Shop', status='PENDING', is_active=True)
        response = self.client.get(reverse('shops:shop_directory'))
        self.assertNotContains(response, 'Pending Shop')

    def test_deleted_shop_is_not_listed(self):
        Shop.objects.create(owner=self.vendor, name='Gone Shop', status='ACTIVE', is_active=True, is_deleted=True)
        response = self.client.get(reverse('shops:shop_directory'))
        self.assertNotContains(response, 'Gone Shop')


class CreateShopTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='applicant', email='a@example.com', password='pass12345')
        self.client.force_login(self.user)

    def test_valid_application_creates_pending_shop(self):
        self.client.post(reverse('shops:create_shop'), {
            'name': 'New Shop', 'description': 'desc', 'phone_number': '0240000000',
            'min_delivery_days': 1, 'max_delivery_days': 3,
        })
        shop = Shop.objects.get(owner=self.user)
        self.assertEqual(shop.status, 'PENDING')

    def test_duplicate_name_is_rejected_with_friendly_message(self):
        other = User.objects.create_user(username='other', email='o@example.com', password='pass12345')
        Shop.objects.create(owner=other, name='Taken Name', status='ACTIVE', is_active=True)

        response = self.client.post(reverse('shops:create_shop'), {
            'name': 'Taken Name', 'description': 'desc', 'phone_number': '0240000000',
            'min_delivery_days': 1, 'max_delivery_days': 3,
        }, follow=True)
        self.assertFalse(Shop.objects.filter(owner=self.user).exists())
        self.assertContains(response, 'already taken')

    def test_delivery_window_validated(self):
        self.client.post(reverse('shops:create_shop'), {
            'name': 'Bad Window Shop', 'description': 'desc', 'phone_number': '0240000000',
            'min_delivery_days': 5, 'max_delivery_days': 1,
        })
        self.assertFalse(Shop.objects.filter(owner=self.user).exists())

    def test_user_with_shop_already_cannot_reapply(self):
        Shop.objects.create(owner=self.user, name='Existing Shop', status='ACTIVE', is_active=True)
        response = self.client.get(reverse('shops:create_shop'), follow=True)
        self.assertRedirects(response, reverse('shops:vendor_dashboard'))


class VendorDashboardAccessTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='u', email='u@example.com', password='pass12345')
        self.client.force_login(self.user)

    def test_no_shop_redirects_to_create_shop(self):
        response = self.client.get(reverse('shops:vendor_dashboard'))
        self.assertRedirects(response, reverse('shops:create_shop'))

    def test_pending_shop_shows_pending_page(self):
        Shop.objects.create(owner=self.user, name='Pending Shop', status='PENDING', is_active=True)
        response = self.client.get(reverse('shops:vendor_dashboard'))
        self.assertTemplateUsed(response, 'shops/application_pending.html')

    def test_suspended_shop_shows_disabled_page(self):
        Shop.objects.create(owner=self.user, name='Suspended Shop', status='SUSPENDED', is_active=True)
        response = self.client.get(reverse('shops:vendor_dashboard'))
        self.assertTemplateUsed(response, 'shops/shop_disabled.html')

    def test_active_shop_shows_dashboard(self):
        Shop.objects.create(owner=self.user, name='Active Shop', status='ACTIVE', is_active=True)
        response = self.client.get(reverse('shops:vendor_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Active Shop')


class ShopSettingsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='u', email='u@example.com', password='pass12345')
        self.shop = Shop.objects.create(
            owner=self.user, name='My Shop', status='ACTIVE', is_active=True,
            min_delivery_days=1, max_delivery_days=3,
        )
        self.client.force_login(self.user)

    def test_vendor_can_update_own_settings(self):
        self.client.post(reverse('shops:shop_settings'), {
            'name': 'Renamed Shop', 'description': 'new desc', 'phone_number': '0201234567',
            'min_delivery_days': 2, 'max_delivery_days': 4,
        })
        self.shop.refresh_from_db()
        self.assertEqual(self.shop.name, 'Renamed Shop')

    def test_cannot_self_approve_via_settings_form(self):
        """
        🔒 VendorShopSettingsForm deliberately excludes status/is_active/owner/
        paystack fields — confirms a vendor can't smuggle self-approval through
        this endpoint even by adding extra POST fields.
        """
        self.client.post(reverse('shops:shop_settings'), {
            'name': 'My Shop', 'description': 'x', 'phone_number': '0201234567',
            'min_delivery_days': 1, 'max_delivery_days': 3,
            'status': 'ACTIVE', 'is_active': 'on', 'owner': self.user.pk,
            'paystack_subaccount_code': 'ACCT_HACKED',
        })
        self.shop.refresh_from_db()
        self.assertNotEqual(self.shop.paystack_subaccount_code, 'ACCT_HACKED')

    def test_invalid_delivery_window_rejected(self):
        self.client.post(reverse('shops:shop_settings'), {
            'name': 'My Shop', 'description': 'x', 'phone_number': '0201234567',
            'min_delivery_days': 10, 'max_delivery_days': 2,
        })
        self.shop.refresh_from_db()
        self.assertEqual(self.shop.min_delivery_days, 1)  # unchanged
