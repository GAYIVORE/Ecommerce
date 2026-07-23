import hashlib
import hmac
import json
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse

from apps.cart.models import Cart, CartItem
from apps.products.models import Product, Category
from apps.shops.models import Shop
from apps.promotions.models import Coupon
from django.utils import timezone
import datetime

from .models import Order, SubOrder, OrderItem, ShippingAddress
from .views import restore_order_stock

User = get_user_model()


def make_paystack_signature(body: bytes) -> str:
    return hmac.new(
        bytes(settings.PAYSTACK_SECRET_KEY or 'test-secret', 'utf-8'),
        msg=body,
        digestmod=hashlib.sha256,
    ).hexdigest()


class CheckoutTestBase(TestCase):
    """Shared fixtures for the checkout / payment test suite."""

    def setUp(self):
        self.buyer = User.objects.create_user(username='buyer', email='buyer@example.com', password='pass12345')
        self.vendor = User.objects.create_user(username='vendor', email='vendor@example.com', password='pass12345')

        self.shop = Shop.objects.create(owner=self.vendor, name='Test Shop', status='ACTIVE', is_active=True)
        self.category = Category.objects.create(name='Gadgets', slug='gadgets')

        self.product = Product.objects.create(
            shop=self.shop, category=self.category, name='Widget', slug='widget',
            description='A fine widget.', price=Decimal('20.00'), stock=3, available=True,
        )

        self.address = ShippingAddress.objects.create(
            user=self.buyer, full_name='Buyer Test', address_line1='1 Test St',
            city='Accra', country='Ghana', phone_number='0240000000', is_default=True,
        )

        self.client = Client()
        self.client.force_login(self.buyer)

    def add_to_cart(self, quantity=1):
        cart, _ = Cart.objects.get_or_create(user=self.buyer)
        item, created = CartItem.objects.get_or_create(cart=cart, product=self.product, defaults={'quantity': quantity})
        if not created:
            item.quantity = quantity
            item.save()
        return cart

    def prime_checkout_session(self, payment_method='cod'):
        session = self.client.session
        session['selected_shipping_address_id'] = self.address.id
        session['payment_method'] = payment_method
        session.save()


class StockReservationTests(CheckoutTestBase):
    """The core reliability fix: stock must be reserved atomically at order
    creation, for both COD and Paystack, so two buyers can never both walk
    away thinking they successfully bought the last unit."""

    def test_cod_order_decrements_stock_immediately(self):
        self.add_to_cart(quantity=2)
        self.prime_checkout_session(payment_method='cod')

        self.client.post(reverse('orders:place_order'))
        self.product.refresh_from_db()

        self.assertEqual(self.product.stock, 1)
        self.assertTrue(Order.objects.filter(user=self.buyer).exists())

    def test_paystack_order_also_reserves_stock_immediately(self):
        """Before the fix, Paystack orders didn't touch stock until the webhook
        fired — this test guards against that regression specifically."""
        self.add_to_cart(quantity=2)
        self.prime_checkout_session(payment_method='paystack')

        self.client.post(reverse('orders:place_order'))
        self.product.refresh_from_db()

        self.assertEqual(self.product.stock, 1)

    def test_cannot_oversell_the_last_unit(self):
        """Simulates two back-to-back checkouts for the same product where
        combined demand exceeds stock. The second must be rejected, not both
        silently succeed."""
        self.product.stock = 1
        self.product.save()

        self.add_to_cart(quantity=1)
        self.prime_checkout_session(payment_method='cod')
        self.client.post(reverse('orders:place_order'))

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 0)
        self.assertFalse(self.product.available)

        second_buyer = User.objects.create_user(username='buyer2', email='b2@example.com', password='pass12345')
        second_address = ShippingAddress.objects.create(
            user=second_buyer, full_name='Buyer Two', address_line1='2 Test St',
            city='Accra', country='Ghana', phone_number='0240000001', is_default=True,
        )
        cart2, _ = Cart.objects.get_or_create(user=second_buyer)
        CartItem.objects.create(cart=cart2, product=self.product, quantity=1)

        client2 = Client()
        client2.force_login(second_buyer)
        session2 = client2.session
        session2['selected_shipping_address_id'] = second_address.id
        session2['payment_method'] = 'cod'
        session2.save()

        client2.post(reverse('orders:place_order'), follow=True)

        self.assertFalse(Order.objects.filter(user=second_buyer).exists())
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 0)

    def test_restore_order_stock_reverses_reservation(self):
        self.add_to_cart(quantity=2)
        self.prime_checkout_session(payment_method='paystack')
        self.client.post(reverse('orders:place_order'))

        order = Order.objects.get(user=self.buyer)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 1)

        restore_order_stock(order)

        self.product.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(self.product.stock, 3)
        self.assertTrue(self.product.available)
        self.assertEqual(order.status, 'Cancelled')
        self.assertTrue(order.sub_orders.filter(status='Cancelled').exists())


class WebhookTests(CheckoutTestBase):
    """Guards the Paystack webhook: idempotency, signature checks, and that a
    failed charge releases the stock that place_order() had reserved."""

    def _place_paystack_order(self, quantity=1):
        self.add_to_cart(quantity=quantity)
        self.prime_checkout_session(payment_method='paystack')
        self.client.post(reverse('orders:place_order'))
        return Order.objects.get(user=self.buyer)

    def _post_webhook(self, payload: dict):
        body = json.dumps(payload).encode('utf-8')
        signature = make_paystack_signature(body)
        return self.client.post(
            reverse('orders:paystack_webhook'),
            data=body,
            content_type='application/json',
            HTTP_X_PAYSTACK_SIGNATURE=signature,
        )

    def test_webhook_rejects_bad_signature(self):
        body = json.dumps({'event': 'charge.success', 'data': {}}).encode('utf-8')
        response = self.client.post(
            reverse('orders:paystack_webhook'),
            data=body,
            content_type='application/json',
            HTTP_X_PAYSTACK_SIGNATURE='not-the-real-signature',
        )
        self.assertEqual(response.status_code, 400)

    def test_webhook_marks_order_paid_and_does_not_double_decrement_stock(self):
        order = self._place_paystack_order(quantity=2)
        self.product.refresh_from_db()
        stock_after_reservation = self.product.stock
        self.assertEqual(stock_after_reservation, 1)

        payload = {
            'event': 'charge.success',
            'data': {'reference': f'PRE-ORD-{order.id}-ABC123', 'id': 999888},
        }
        response = self._post_webhook(payload)
        self.assertEqual(response.status_code, 200)

        order.refresh_from_db()
        self.product.refresh_from_db()
        self.assertTrue(order.payment_status)
        self.assertEqual(order.status, 'Processing')
        self.assertEqual(self.product.stock, stock_after_reservation)

    def test_webhook_is_idempotent_on_replay(self):
        order = self._place_paystack_order(quantity=1)
        payload = {
            'event': 'charge.success',
            'data': {'reference': f'PRE-ORD-{order.id}-ABC123', 'id': 999888},
        }
        self._post_webhook(payload)
        self.product.refresh_from_db()
        stock_after_first = self.product.stock

        self._post_webhook(payload)
        self.product.refresh_from_db()

        self.assertEqual(self.product.stock, stock_after_first)

    def test_webhook_charge_failed_restores_stock(self):
        order = self._place_paystack_order(quantity=2)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 1)

        payload = {
            'event': 'charge.failed',
            'data': {'reference': f'PRE-ORD-{order.id}-XYZ999', 'id': 111222},
        }
        response = self._post_webhook(payload)
        self.assertEqual(response.status_code, 200)

        order.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(order.status, 'Cancelled')
        self.assertFalse(order.payment_status)
        self.assertEqual(self.product.stock, 3)


class CouponApplicationTests(CheckoutTestBase):

    def test_shop_scoped_coupon_discounts_only_that_shops_items(self):
        coupon = Coupon.objects.create(
            code='SAVE10', shop=self.shop, discount=10, active=True,
            valid_from=timezone.now() - datetime.timedelta(days=1),
            valid_to=timezone.now() + datetime.timedelta(days=1),
        )
        self.add_to_cart(quantity=1)
        self.prime_checkout_session(payment_method='cod')

        session = self.client.session
        session['coupon_code'] = coupon.code
        session.save()

        self.client.post(reverse('orders:place_order'))

        order = Order.objects.get(user=self.buyer)
        self.assertEqual(order.total_amount, Decimal('18.00'))


class ExpireStaleOrdersCommandTests(CheckoutTestBase):

    def test_stale_unpaid_paystack_order_is_expired_and_stock_restored(self):
        from django.core.management import call_command

        self.add_to_cart(quantity=2)
        self.prime_checkout_session(payment_method='paystack')
        self.client.post(reverse('orders:place_order'))

        order = Order.objects.get(user=self.buyer)
        # order_date uses auto_now_add=True, so a normal .save() would silently
        # re-stamp it to "now" — .update() bypasses that pre_save behavior.
        Order.objects.filter(pk=order.pk).update(order_date=timezone.now() - datetime.timedelta(hours=5))

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 1)

        call_command('expire_stale_orders', hours=2)

        order.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(order.status, 'Cancelled')
        self.assertEqual(self.product.stock, 3)

    def test_recent_unpaid_order_is_not_expired(self):
        from django.core.management import call_command

        self.add_to_cart(quantity=1)
        self.prime_checkout_session(payment_method='paystack')
        self.client.post(reverse('orders:place_order'))
        order = Order.objects.get(user=self.buyer)

        call_command('expire_stale_orders', hours=2)

        order.refresh_from_db()
        self.assertNotEqual(order.status, 'Cancelled')
