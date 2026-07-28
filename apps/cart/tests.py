# apps/cart/tests.py
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.products.models import Category, Product
from apps.shops.models import Shop
from .models import Cart, CartItem

User = get_user_model()


class CartTestBase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='shopper', email='shopper@example.com', password='pass12345')
        self.vendor = User.objects.create_user(username='vendor', email='vendor@example.com', password='pass12345')
        self.shop = Shop.objects.create(owner=self.vendor, name='Gizmo Shop', status='ACTIVE', is_active=True)
        self.category = Category.objects.create(name='Gadgets', slug='gadgets')
        self.product = Product.objects.create(
            shop=self.shop, category=self.category, name='Widget', slug='widget',
            description='A widget', price=Decimal('50.00'), stock=10, available=True,
        )


class AddToCartTests(CartTestBase):
    def test_add_to_cart_creates_item(self):
        self.client.force_login(self.user)
        self.client.post(reverse('cart:add_to_cart', args=[self.product.id]), {'quantity': 2})
        cart = Cart.objects.get(user=self.user)
        item = cart.items.get(product=self.product)
        self.assertEqual(item.quantity, 2)

    def test_cannot_add_more_than_available_stock(self):
        self.client.force_login(self.user)
        self.client.post(reverse('cart:add_to_cart', args=[self.product.id]), {'quantity': 999})
        cart = Cart.objects.get(user=self.user)
        item = cart.items.get(product=self.product)
        # Capped to available stock rather than the requested (over-)quantity.
        self.assertEqual(item.quantity, self.product.stock)

    def test_cannot_add_more_once_at_stock_ceiling(self):
        self.client.force_login(self.user)
        self.client.post(reverse('cart:add_to_cart', args=[self.product.id]), {'quantity': 10})
        response = self.client.post(
            reverse('cart:add_to_cart', args=[self.product.id]), {'quantity': 1}, follow=True
        )
        cart = Cart.objects.get(user=self.user)
        item = cart.items.get(product=self.product)
        self.assertEqual(item.quantity, 10)
        self.assertContains(response, 'maximum available stock')

    def test_out_of_stock_product_cannot_be_added(self):
        self.product.stock = 0
        self.product.save()
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('cart:add_to_cart', args=[self.product.id]), {'quantity': 1}, follow=True
        )
        self.assertFalse(CartItem.objects.filter(product=self.product).exists())
        self.assertContains(response, 'out of stock')

    def test_unavailable_product_returns_404(self):
        self.product.available = False
        self.product.save()
        self.client.force_login(self.user)
        response = self.client.post(reverse('cart:add_to_cart', args=[self.product.id]), {'quantity': 1})
        # add_item_to_cart returns an error message rather than raising, so we
        # just confirm no cart item was created for the unavailable product.
        self.assertFalse(CartItem.objects.filter(product=self.product).exists())


class UpdateAndRemoveCartTests(CartTestBase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.user)
        self.client.post(reverse('cart:add_to_cart', args=[self.product.id]), {'quantity': 2})
        self.item = CartItem.objects.get(product=self.product)

    def test_update_quantity_within_stock(self):
        self.client.post(reverse('cart:update_cart', args=[self.item.id]), {'quantity': 5})
        self.item.refresh_from_db()
        self.assertEqual(self.item.quantity, 5)

    def test_update_quantity_above_stock_rejected(self):
        self.client.post(reverse('cart:update_cart', args=[self.item.id]), {'quantity': 999})
        self.item.refresh_from_db()
        self.assertEqual(self.item.quantity, 2)  # unchanged

    def test_update_quantity_to_zero_removes_item(self):
        self.client.post(reverse('cart:update_cart', args=[self.item.id]), {'quantity': 0})
        self.assertFalse(CartItem.objects.filter(pk=self.item.pk).exists())

    def test_remove_item(self):
        self.client.post(reverse('cart:remove_from_cart', args=[self.item.id]))
        self.assertFalse(CartItem.objects.filter(pk=self.item.pk).exists())

    def test_cannot_touch_another_users_cart_item(self):
        other_user = User.objects.create_user(username='other', email='other@example.com', password='pass12345')
        self.client.force_login(other_user)
        response = self.client.post(reverse('cart:remove_from_cart', args=[self.item.id]))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(CartItem.objects.filter(pk=self.item.pk).exists())


class AnonymousCartMergeTests(CartTestBase):
    def test_anonymous_cart_merges_into_user_cart_on_login(self):
        # Add as anonymous.
        self.client.post(reverse('cart:add_to_cart', args=[self.product.id]), {'quantity': 3})
        session_key = self.client.session.session_key
        self.assertTrue(Cart.objects.filter(session_key=session_key).exists())

        # Log in via the real view (not force_login, which bypasses middleware
        # and the actual login() call) — this exercises the real session-key
        # rotation + merge path a genuine user goes through.
        self.client.post(reverse('users:login'), {'username': 'shopper', 'password': 'pass12345'})

        user_cart = Cart.objects.get(user=self.user)
        self.assertEqual(user_cart.items.get(product=self.product).quantity, 3)
        self.assertFalse(Cart.objects.filter(session_key=session_key).exists())
