# apps/products/tests.py
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.shops.models import Shop
from .models import Category, Product

User = get_user_model()


class ProductCatalogTestBase(TestCase):
    def setUp(self):
        self.vendor = User.objects.create_user(username='vendor', email='vendor@example.com', password='pass12345')
        self.other_vendor = User.objects.create_user(username='vendor2', email='vendor2@example.com', password='pass12345')
        self.customer = User.objects.create_user(username='customer', email='customer@example.com', password='pass12345')

        self.shop = Shop.objects.create(owner=self.vendor, name='Gizmo Shop', status='ACTIVE', is_active=True)
        self.other_shop = Shop.objects.create(owner=self.other_vendor, name='Other Shop', status='ACTIVE', is_active=True)

        self.category = Category.objects.create(name='Gadgets', slug='gadgets')
        self.product = Product.objects.create(
            shop=self.shop, category=self.category, name='Widget', slug='widget',
            description='A fine widget', price=Decimal('50.00'), stock=10, available=True,
        )


class PublicCatalogTests(ProductCatalogTestBase):
    def test_product_list_shows_available_products(self):
        response = self.client.get(reverse('products:product_list'))
        self.assertContains(response, 'Widget')

    def test_hidden_shop_products_are_not_listed(self):
        self.shop.status = 'PENDING'
        self.shop.save()
        response = self.client.get(reverse('products:product_list'))
        self.assertNotContains(response, 'Widget')

    def test_unavailable_product_is_not_listed(self):
        self.product.available = False
        self.product.save()
        response = self.client.get(reverse('products:product_list'))
        self.assertNotContains(response, 'Widget')

    def test_soft_deleted_product_is_not_listed(self):
        self.product.is_deleted = True
        self.product.save()
        response = self.client.get(reverse('products:product_list'))
        self.assertNotContains(response, 'Widget')

    def test_search_filters_by_name(self):
        Product.objects.create(
            shop=self.shop, category=self.category, name='Gizmo', slug='gizmo',
            description='Unrelated', price=Decimal('20.00'), stock=5, available=True,
        )
        response = self.client.get(reverse('products:product_list'), {'q': 'Widget'})
        names = [p.name for p in response.context['products']]
        self.assertEqual(names, ['Widget'])

    def test_product_detail_renders(self):
        response = self.client.get(reverse('products:product_detail', args=[self.product.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Widget')

    def test_unavailable_product_detail_is_404(self):
        self.product.available = False
        self.product.save()
        response = self.client.get(reverse('products:product_detail', args=[self.product.slug]))
        self.assertEqual(response.status_code, 404)

    def test_search_suggest_returns_matches(self):
        response = self.client.get(reverse('products:search_suggest'), {'q': 'Wid'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['results']), 1)
        self.assertEqual(data['results'][0]['name'], 'Widget')

    def test_search_suggest_ignores_short_queries(self):
        response = self.client.get(reverse('products:search_suggest'), {'q': 'w'})
        self.assertEqual(response.json(), {'results': []})


class VendorProductManagementTests(ProductCatalogTestBase):
    """IDOR / ownership-scoping coverage for the vendor dashboard product CRUD views."""

    def setUp(self):
        super().setUp()
        self.shop.status = 'ACTIVE'
        self.shop.save()

    def test_non_vendor_cannot_access_dashboard(self):
        self.client.force_login(self.customer)
        response = self.client.get(reverse('products:vendor_dashboard'))
        self.assertEqual(response.status_code, 403)

    def test_vendor_dashboard_only_shows_own_products(self):
        Product.objects.create(
            shop=self.other_shop, category=self.category, name='Not Mine', slug='not-mine',
            description='x', price=Decimal('10.00'), stock=5, available=True,
        )
        self.client.force_login(self.vendor)
        response = self.client.get(reverse('products:vendor_dashboard'))
        product_names = [p.name for p in response.context['products']]
        self.assertEqual(product_names, ['Widget'])

    def test_vendor_cannot_update_another_vendors_product(self):
        foreign_product = Product.objects.create(
            shop=self.other_shop, category=self.category, name='Not Mine', slug='not-mine',
            description='x', price=Decimal('10.00'), stock=5, available=True,
        )
        self.client.force_login(self.vendor)
        response = self.client.get(reverse('products:vendor_product_update', args=[foreign_product.slug]))
        self.assertEqual(response.status_code, 404)

    def test_vendor_cannot_delete_another_vendors_product(self):
        foreign_product = Product.objects.create(
            shop=self.other_shop, category=self.category, name='Not Mine', slug='not-mine',
            description='x', price=Decimal('10.00'), stock=5, available=True,
        )
        self.client.force_login(self.vendor)
        response = self.client.post(reverse('products:vendor_product_delete', args=[foreign_product.slug]))
        self.assertEqual(response.status_code, 404)
        foreign_product.refresh_from_db()
        self.assertFalse(foreign_product.is_deleted)

    def test_vendor_can_soft_delete_own_product(self):
        self.client.force_login(self.vendor)
        self.client.post(reverse('products:vendor_product_delete', args=[self.product.slug]))
        self.product.refresh_from_db()
        self.assertTrue(self.product.is_deleted)
        self.assertFalse(self.product.available)

    def test_deleted_product_row_is_not_actually_removed(self):
        """
        🔒 Regression test: DeleteView's POST handling changed in Django 4.0 to
        route through form_valid() rather than delete(). An override that only
        touches delete() silently no-ops and the product gets hard-deleted
        instead of archived. This asserts the row still exists afterward.
        """
        self.client.force_login(self.vendor)
        self.client.post(reverse('products:vendor_product_delete', args=[self.product.slug]))
        self.assertTrue(Product.objects.filter(pk=self.product.pk).exists())

    def test_vendor_can_create_product_bound_to_own_shop(self):
        self.client.force_login(self.vendor)
        self.client.post(reverse('products:vendor_product_create'), {
            'category': self.category.id,
            'name': 'New Gadget',
            'slug': 'new-gadget',
            'description': 'Shiny',
            'price': '15.00',
            'stock': 3,
            'available': 'on',
        })
        new_product = Product.objects.get(slug='new-gadget')
        self.assertEqual(new_product.shop, self.shop)
