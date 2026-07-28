# apps/vendors/tests.py
from unittest.mock import patch, Mock

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.shops.models import Shop

User = get_user_model()


def _mock_paystack_response(status_code=201, status=True, subaccount_code='ACCT_test123', message='Failed'):
    mock_response = Mock()
    mock_response.status_code = status_code
    mock_response.json.return_value = (
        {'status': True, 'data': {'subaccount_code': subaccount_code}} if status
        else {'status': False, 'message': message}
    )
    return mock_response


class VendorAccessControlTests(TestCase):
    def setUp(self):
        self.non_vendor = User.objects.create_user(username='plain', email='p@example.com', password='pass12345')
        self.vendor_user = User.objects.create_user(
            username='vend', email='vend@example.com', password='pass12345', role='VENDOR'
        )

    def test_non_vendor_role_is_denied(self):
        self.client.force_login(self.non_vendor)
        response = self.client.get(reverse('vendors:onboard_vendor_shop'))
        self.assertEqual(response.status_code, 403)

    def test_anonymous_is_redirected_to_login(self):
        response = self.client.get(reverse('vendors:onboard_vendor_shop'))
        self.assertEqual(response.status_code, 302)

    def test_approved_vendor_role_can_access_onboarding_form(self):
        self.client.force_login(self.vendor_user)
        response = self.client.get(reverse('vendors:onboard_vendor_shop'))
        self.assertEqual(response.status_code, 200)


class VendorOnboardingTests(TestCase):
    def setUp(self):
        self.vendor_user = User.objects.create_user(
            username='vend', email='vend@example.com', password='pass12345', role='VENDOR'
        )
        self.client.force_login(self.vendor_user)
        self.post_data = {
            'business_name': 'Makola Digital', 'settlement_bank': 'MTN', 'account_number': '0244123456',
        }

    @patch('apps.vendors.views.requests.post')
    def test_successful_onboarding_creates_shop_with_subaccount(self, mock_post):
        mock_post.return_value = _mock_paystack_response()
        self.client.post(reverse('vendors:onboard_vendor_shop'), self.post_data)
        shop = Shop.objects.get(owner=self.vendor_user)
        self.assertEqual(shop.name, 'Makola Digital')
        self.assertEqual(shop.paystack_subaccount_code, 'ACCT_test123')

    @patch('apps.vendors.views.requests.post')
    def test_paystack_rejection_does_not_create_subaccount_code(self, mock_post):
        mock_post.return_value = _mock_paystack_response(status_code=400, status=False, message='Invalid account')
        self.client.post(reverse('vendors:onboard_vendor_shop'), self.post_data, follow=True)
        self.assertFalse(Shop.objects.filter(owner=self.vendor_user).exists())

    @patch('apps.vendors.views.requests.post')
    def test_network_failure_is_handled_gracefully(self, mock_post):
        import requests
        mock_post.side_effect = requests.RequestException('timeout')
        response = self.client.post(reverse('vendors:onboard_vendor_shop'), self.post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Shop.objects.filter(owner=self.vendor_user).exists())

    @patch('apps.vendors.views.requests.post')
    def test_duplicate_shop_name_is_handled_without_500(self, mock_post):
        """
        🔒 Regression test: a Paystack success for a business_name that
        collides with an existing Shop.name (globally unique) used to bubble
        up an unhandled IntegrityError. Confirms it's now caught with a
        friendly message instead of a 500.
        """
        other_owner = User.objects.create_user(username='other', email='o@example.com', password='pass12345')
        Shop.objects.create(owner=other_owner, name='Makola Digital', status='ACTIVE', is_active=True)

        mock_post.return_value = _mock_paystack_response()
        response = self.client.post(reverse('vendors:onboard_vendor_shop'), self.post_data)
        self.assertEqual(response.status_code, 200)  # re-rendered form, not a 500
        self.assertContains(response, 'already')
        self.assertFalse(Shop.objects.filter(owner=self.vendor_user).exists())

    @patch('apps.vendors.views.requests.post')
    def test_already_onboarded_vendor_is_redirected(self, mock_post):
        Shop.objects.create(
            owner=self.vendor_user, name='Existing', status='ACTIVE', is_active=True,
            paystack_subaccount_code='ACCT_already',
        )
        response = self.client.get(reverse('vendors:onboard_vendor_shop'), follow=True)
        self.assertRedirects(response, reverse('shops:vendor_dashboard'))
        mock_post.assert_not_called()

    @patch('apps.vendors.views.requests.post')
    def test_updating_an_existing_shop_without_subaccount_reuses_the_row(self, mock_post):
        """Vendor applied via shops:create_shop first (PENDING, no subaccount yet),
        then completes payout onboarding — should update, not duplicate, the Shop row."""
        shop = Shop.objects.create(owner=self.vendor_user, name='Old Name', status='PENDING', is_active=True)
        mock_post.return_value = _mock_paystack_response()
        self.client.post(reverse('vendors:onboard_vendor_shop'), self.post_data)
        self.assertEqual(Shop.objects.filter(owner=self.vendor_user).count(), 1)
        shop.refresh_from_db()
        self.assertEqual(shop.name, 'Makola Digital')
        self.assertEqual(shop.paystack_subaccount_code, 'ACCT_test123')
