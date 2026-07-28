# apps/wishlist/tests.py
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.cart.models import Cart
from apps.products.models import Category, Product
from apps.shops.models import Shop
from .models import Wishlist, WishlistItem

User = get_user_model()


class WishlistTestBase(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user(username='customer', email='c@example.com', password='pass12345')
        self.vendor = User.objects.create_user(username='vendor', email='v@example.com', password='pass12345')
        self.shop = Shop.objects.create(owner=self.vendor, name='Gizmo Shop', status='ACTIVE', is_active=True)
        self.category = Category.objects.create(name='Gadgets', slug='gadgets')
        self.product = Product.objects.create(
            shop=self.shop, category=self.category, name='Widget', slug='widget',
            description='A widget', price=Decimal('50.00'), stock=10, available=True,
        )


class AddToWishlistTests(WishlistTestBase):
    def test_add_creates_wishlist_item(self):
        self.client.force_login(self.customer)
        self.client.post(reverse('wishlist:add_to_wishlist', args=[self.product.id]))
        wishlist = Wishlist.objects.get(user=self.customer)
        self.assertTrue(wishlist.items.filter(product=self.product).exists())

    def test_adding_same_product_twice_does_not_duplicate(self):
        self.client.force_login(self.customer)
        self.client.post(reverse('wishlist:add_to_wishlist', args=[self.product.id]))
        self.client.post(reverse('wishlist:add_to_wishlist', args=[self.product.id]))
        wishlist = Wishlist.objects.get(user=self.customer)
        self.assertEqual(wishlist.items.filter(product=self.product).count(), 1)

    def test_vendor_cannot_wishlist_own_product(self):
        """
        🔒 Regression test: WishlistItem.clean() previously read Shop.user /
        Shop.vendor (neither exists — the real field is Shop.owner), so this
        rule silently never fired and vendors could wishlist their own
        listings. Confirms the fix actually blocks it now.
        """
        self.client.force_login(self.vendor)
        response = self.client.post(
            reverse('wishlist:add_to_wishlist', args=[self.product.id]), follow=True
        )
        self.assertFalse(WishlistItem.objects.filter(product=self.product).exists())
        self.assertContains(response, "cannot add your own shop")

    def test_other_vendor_can_wishlist_a_product_they_dont_own(self):
        other_vendor = User.objects.create_user(username='vendor2', email='v2@example.com', password='pass12345')
        Shop.objects.create(owner=other_vendor, name='Other Shop', status='ACTIVE', is_active=True)
        self.client.force_login(other_vendor)
        self.client.post(reverse('wishlist:add_to_wishlist', args=[self.product.id]))
        self.assertTrue(WishlistItem.objects.filter(product=self.product, wishlist__user=other_vendor).exists())


class RemoveAndMoveWishlistTests(WishlistTestBase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.customer)
        self.client.post(reverse('wishlist:add_to_wishlist', args=[self.product.id]))
        self.item = WishlistItem.objects.get(product=self.product, wishlist__user=self.customer)

    def test_remove_item(self):
        self.client.post(reverse('wishlist:remove_from_wishlist', args=[self.item.id]))
        self.assertFalse(WishlistItem.objects.filter(pk=self.item.pk).exists())

    def test_cannot_remove_another_users_wishlist_item(self):
        other = User.objects.create_user(username='other', email='o@example.com', password='pass12345')
        self.client.force_login(other)
        response = self.client.post(reverse('wishlist:remove_from_wishlist', args=[self.item.id]))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(WishlistItem.objects.filter(pk=self.item.pk).exists())

    def test_move_to_cart_transfers_item_and_removes_from_wishlist(self):
        self.client.post(reverse('wishlist:move_to_cart', args=[self.item.id]))
        self.assertFalse(WishlistItem.objects.filter(pk=self.item.pk).exists())
        cart = Cart.objects.get(user=self.customer)
        self.assertTrue(cart.items.filter(product=self.product).exists())

    def test_move_to_cart_blocked_when_out_of_stock(self):
        self.product.stock = 0
        self.product.save()
        self.client.post(reverse('wishlist:move_to_cart', args=[self.item.id]))
        # Stays on the wishlist since the transfer was refused.
        self.assertTrue(WishlistItem.objects.filter(pk=self.item.pk).exists())
        self.assertFalse(Cart.objects.filter(user=self.customer, items__product=self.product).exists())
