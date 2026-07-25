# apps/core/management/commands/seed_demo_data.py
"""
Seeds the database with realistic demo data (shops, categories, products)
so the storefront isn't an empty shell on first run.

Usage:
    python manage.py seed_demo_data
    python manage.py seed_demo_data --flush   # wipe demo data first
"""
import random
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils.text import slugify

from apps.users.models import User
from apps.shops.models import Shop
from apps.products.models import Category, Product

CATEGORIES = [
    ("Electronics", "Phones, laptops, gadgets & accessories"),
    ("Fashion", "Clothing, shoes & everyday style"),
    ("Home & Living", "Furniture, decor & kitchenware"),
    ("Beauty", "Skincare, cosmetics & personal care"),
    ("Groceries", "Pantry staples & fresh essentials"),
]

SHOPS = [
    ("Osu Tech Hub", "Electronics", [
        ("Wireless Earbuds Pro", "Noise-cancelling wireless earbuds with 30hr battery life.", 249.99, 40),
        ("USB-C Fast Charger 65W", "Compact GaN charger, fits any bag pocket.", 129.50, 65),
        ("4K Action Camera", "Waterproof action camera with stabilization.", 899.00, 12),
        ("Bluetooth Mechanical Keyboard", "Hot-swappable switches, RGB backlight.", 420.00, 18),
    ]),
    ("Accra Fashion House", "Fashion", [
        ("Ankara Print Shirt", "Handmade tailored shirt in bold Ankara print.", 180.00, 30),
        ("Leather Sandals", "Genuine leather, hand-stitched sole.", 150.00, 22),
        ("Denim Jacket", "Classic fit, stonewashed denim.", 260.00, 15),
        ("Kente Trim Tote Bag", "Canvas tote with woven Kente accent.", 95.00, 50),
    ]),
    ("Homey Interiors", "Home & Living", [
        ("Ceramic Dinner Set (16pc)", "Chip-resistant stoneware, dishwasher safe.", 340.00, 20),
        ("Woven Storage Basket", "Handwoven natural fiber basket, large.", 85.00, 34),
        ("Scented Soy Candle", "50-hour burn, sandalwood & amber.", 60.00, 70),
        ("Bamboo Cutting Board Set", "3-piece set, antimicrobial bamboo.", 110.00, 28),
    ]),
    ("Glow Beauty Bar", "Beauty", [
        ("Shea Butter Body Cream", "100% raw shea butter, unscented.", 55.00, 90),
        ("Vitamin C Serum", "Brightening serum with hyaluronic acid.", 145.00, 40),
        ("Bamboo Bristle Brush Set", "5-piece makeup brush set.", 90.00, 45),
        ("Argan Oil Hair Mask", "Deep conditioning treatment, 250ml.", 75.00, 38),
    ]),
    ("Fresh Market Co", "Groceries", [
        ("Organic Rice (5kg)", "Locally grown long-grain rice.", 65.00, 120),
        ("Cold-Pressed Palm Oil (1L)", "Traditionally processed, no additives.", 40.00, 100),
        ("Roasted Groundnuts (500g)", "Lightly salted, freshly roasted.", 22.00, 150),
        ("Dried Hibiscus (Sobolo) 300g", "For brewing sobolo/hibiscus tea.", 18.00, 200),
    ]),
]


class Command(BaseCommand):
    help = "Seed demo shops, categories, and products for local preview."

    def add_arguments(self, parser):
        parser.add_argument('--flush', action='store_true', help='Delete existing demo data first.')

    @transaction.atomic
    def handle(self, *args, **options):
        if options['flush']:
            Product.objects.filter(shop__owner__username__startswith='demo_vendor_').delete()
            Shop.objects.filter(owner__username__startswith='demo_vendor_').delete()
            User.objects.filter(username__startswith='demo_vendor_').delete()
            self.stdout.write(self.style.WARNING('Flushed existing demo data.'))

        categories = {}
        for name, desc in CATEGORIES:
            cat, _ = Category.objects.get_or_create(
                name=name,
                defaults={'slug': slugify(name), 'description': desc},
            )
            categories[name] = cat

        created_products = 0
        for idx, (shop_name, cat_name, products) in enumerate(SHOPS, start=1):
            username = f"demo_vendor_{idx}"
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': f"{username}@example.com",
                    'role': User.Roles.VENDOR,
                    'is_active': True,
                },
            )
            if created:
                user.set_password('DemoVendor123!')
                user.save()

            shop, _ = Shop.objects.get_or_create(
                owner=user,
                defaults={
                    'name': shop_name,
                    'slug': slugify(shop_name),
                    'description': f"{shop_name} — verified vendor on E Shop specializing in {cat_name.lower()}.",
                    'status': 'ACTIVE',
                    'is_active': True,
                },
            )
            if shop.status != 'ACTIVE':
                shop.status = 'ACTIVE'
                shop.is_active = True
                shop.save()

            for name, desc, price, stock in products:
                slug = slugify(name)
                if Product.objects.filter(slug=slug).exists():
                    continue
                Product.objects.create(
                    shop=shop,
                    category=categories[cat_name],
                    name=name,
                    slug=slug,
                    description=desc,
                    price=Decimal(str(price)),
                    stock=stock,
                    available=True,
                )
                created_products += 1

        self.stdout.write(self.style.SUCCESS(
            f"Seed complete: {len(categories)} categories, {len(SHOPS)} shops, "
            f"{created_products} new products."
        ))
        self.stdout.write(self.style.NOTICE(
            "Demo vendor logins: demo_vendor_1..5 / password 'DemoVendor123!'"
        ))
