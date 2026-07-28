# apps/reviews/tests.py
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.products.models import Category, Product
from apps.shops.models import Shop
from .models import Review

User = get_user_model()


class ReviewTestBase(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user(username='customer', email='c@example.com', password='pass12345')
        self.other_customer = User.objects.create_user(username='other', email='o@example.com', password='pass12345')
        self.vendor = User.objects.create_user(username='vendor', email='v@example.com', password='pass12345')
        self.other_vendor = User.objects.create_user(username='vendor2', email='v2@example.com', password='pass12345')

        self.shop = Shop.objects.create(owner=self.vendor, name='Gizmo Shop', status='ACTIVE', is_active=True)
        self.other_shop = Shop.objects.create(owner=self.other_vendor, name='Other Shop', status='ACTIVE', is_active=True)

        self.category = Category.objects.create(name='Gadgets', slug='gadgets')
        self.product = Product.objects.create(
            shop=self.shop, category=self.category, name='Widget', slug='widget',
            description='A widget', price=Decimal('50.00'), stock=10, available=True,
        )


class AddReviewTests(ReviewTestBase):
    def test_requires_login(self):
        response = self.client.post(reverse('reviews:add_review', args=[self.product.slug]), {
            'rating': 5, 'comment': 'Great!',
        })
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Review.objects.filter(product=self.product).exists())

    def test_creates_review_with_denormalized_shop(self):
        self.client.force_login(self.customer)
        self.client.post(reverse('reviews:add_review', args=[self.product.slug]), {
            'rating': 5, 'comment': 'Great product!',
        })
        review = Review.objects.get(product=self.product, user=self.customer)
        self.assertEqual(review.rating, 5)
        self.assertEqual(review.shop, self.shop)

    def test_second_submission_updates_existing_review_instead_of_duplicating(self):
        self.client.force_login(self.customer)
        self.client.post(reverse('reviews:add_review', args=[self.product.slug]), {
            'rating': 2, 'comment': 'Meh.',
        })
        self.client.post(reverse('reviews:add_review', args=[self.product.slug]), {
            'rating': 5, 'comment': 'Actually great after using it more.',
        })
        self.assertEqual(Review.objects.filter(product=self.product, user=self.customer).count(), 1)
        review = Review.objects.get(product=self.product, user=self.customer)
        self.assertEqual(review.rating, 5)

    def test_rating_out_of_range_is_rejected(self):
        self.client.force_login(self.customer)
        self.client.post(reverse('reviews:add_review', args=[self.product.slug]), {
            'rating': 9, 'comment': 'Broken rating',
        })
        self.assertFalse(Review.objects.filter(product=self.product, user=self.customer).exists())

    def test_two_different_customers_can_both_review_same_product(self):
        self.client.force_login(self.customer)
        self.client.post(reverse('reviews:add_review', args=[self.product.slug]), {'rating': 4, 'comment': 'Nice'})
        self.client.force_login(self.other_customer)
        self.client.post(reverse('reviews:add_review', args=[self.product.slug]), {'rating': 3, 'comment': 'OK'})
        self.assertEqual(Review.objects.filter(product=self.product).count(), 2)


class VendorReplyTests(ReviewTestBase):
    def setUp(self):
        super().setUp()
        self.review = Review.objects.create(
            product=self.product, user=self.customer, rating=4, comment='Pretty good'
        )

    def test_shop_owner_can_reply(self):
        self.client.force_login(self.vendor)
        self.client.post(reverse('reviews:add_vendor_reply', args=[self.review.id]), {
            'vendor_reply': 'Thanks for the feedback!'
        })
        self.review.refresh_from_db()
        self.assertEqual(self.review.vendor_reply, 'Thanks for the feedback!')
        self.assertIsNotNone(self.review.vendor_replied_at)

    def test_unrelated_vendor_cannot_reply(self):
        """IDOR check: a vendor who doesn't own the product's shop must be blocked."""
        self.client.force_login(self.other_vendor)
        self.client.post(reverse('reviews:add_vendor_reply', args=[self.review.id]), {
            'vendor_reply': 'Sneaky reply'
        })
        self.review.refresh_from_db()
        self.assertEqual(self.review.vendor_reply, '')

    def test_customer_cannot_reply_as_vendor(self):
        self.client.force_login(self.other_customer)
        self.client.post(reverse('reviews:add_vendor_reply', args=[self.review.id]), {
            'vendor_reply': 'Not a vendor'
        })
        self.review.refresh_from_db()
        self.assertEqual(self.review.vendor_reply, '')

    def test_reply_form_only_updates_vendor_reply_field(self):
        """
        Regression guard: VendorReplyForm.Meta.fields must stay scoped to
        ['vendor_reply'] only — if it ever widened to include rating/comment,
        a "vendor reply" POST could silently rewrite the customer's own review.
        """
        self.client.force_login(self.vendor)
        self.client.post(reverse('reviews:add_vendor_reply', args=[self.review.id]), {
            'vendor_reply': 'Reply text',
            'rating': 1,
            'comment': 'Hijacked comment',
        })
        self.review.refresh_from_db()
        self.assertEqual(self.review.rating, 4)
        self.assertEqual(self.review.comment, 'Pretty good')
