from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.db.models import Q, Sum, Count
from django.db.models.functions import TruncDate
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse, HttpResponse
from django.utils import timezone
import csv
import datetime
import json

from .models import Product, Category, Shop
from apps.reviews.forms import ReviewForm
from apps.reviews.models import Review
# Import SubOrder to trace vendor-specific order partitions
from apps.orders.models import SubOrder


# =============================================================================
# PUBLIC MARKETPLACE VIEWS (CUSTOMER FACING)
# =============================================================================

def search_suggest(request):
    """
    Lightweight JSON endpoint powering the search-as-you-type dropdown in the
    nav bar and product list. Deliberately small and fast: top 6 name matches
    only, no full-text ranking — this is a typeahead, not a search results page.
    """
    query = request.GET.get('q', '').strip()
    if len(query) < 2:
        return JsonResponse({'results': []})

    products = Product.objects.select_related('shop').filter(
        Q(name__icontains=query),
        available=True, is_deleted=False, shop__status='ACTIVE',
    ).order_by('-created_at')[:6]

    results = [
        {
            'name': p.name,
            'url': p.get_absolute_url(),
            'price': f"{p.price:.2f}",
            'shop': p.shop.name if p.shop else '',
            'image': p.image.url if p.image else '',
        }
        for p in products
    ]
    return JsonResponse({'results': results})


class GlobalProductListView(ListView):
    """
    Enterprise-grade marketplace feed supporting global aggregation,
    category segmentation, and fuzzy database search optimization.
    """
    model = Product
    template_name = 'products/product_list.html'
    context_object_name = 'products'
    paginate_by = 24  

    def get_queryset(self):
        # ⚡ Eager load foreign mappings via select_related to solve N+1 query traps
        queryset = Product.objects.select_related('shop', 'category').filter(
            available=True,
            is_deleted=False,
            shop__status='ACTIVE',
            shop__is_active=True,
            shop__is_deleted=False
        )
        
        # Category Isolation Routing logic
        category_slug = self.kwargs.get('category_slug')
        if category_slug:
            self.category = get_object_or_404(Category, slug=category_slug)
            queryset = queryset.filter(category=self.category)
        else:
            self.category = None

        # Text Query Parsing Search Optimization
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) | Q(description__icontains=query)
            )

        # Sort ordering
        sort = self.request.GET.get('sort')
        sort_map = {
            'price_asc': 'price',
            'price_desc': '-price',
            'newest': '-created_at',
            'name': 'name',
        }
        queryset = queryset.order_by(sort_map.get(sort, '-created_at'))
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = self.category
        context['categories'] = Category.objects.all()
        context['query'] = self.request.GET.get('q', '')
        context['current_sort'] = self.request.GET.get('sort', '')
        return context


class ProductDetailView(DetailView):
    """
    Detailed product showcase integrating active user review instances 
    and multi-vendor identification layers.
    """
    model = Product
    template_name = 'products/product_detail.html'
    context_object_name = 'product'

    def get_queryset(self):
        return Product.objects.select_related('shop', 'category').filter(
            available=True, 
            is_deleted=False
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.get_object()
        
        review_form = ReviewForm()
        user_review = None

        if self.request.user.is_authenticated:
            user_review = Review.objects.filter(product=product, user=self.request.user).first()
            if user_review:
                review_form = ReviewForm(instance=user_review)

        context['review_form'] = review_form
        context['user_review'] = user_review

        related_products = Product.objects.select_related('shop', 'category').filter(
            category=product.category, available=True, is_deleted=False, stock__gt=0
        ).exclude(pk=product.pk)[:8]

        if related_products.count() < 4:
            # Not enough in the same category — top up with more from the same shop
            more = Product.objects.select_related('shop', 'category').filter(
                shop=product.shop, available=True, is_deleted=False, stock__gt=0
            ).exclude(pk=product.pk).exclude(pk__in=[p.pk for p in related_products])[:8]
            related_products = list(related_products) + list(more)

        context['related_products'] = related_products[:4]
        return context


class ShopStorefrontView(ListView):
    """
    Renders an isolated digital storefront displaying the inventory 
    of a single, explicitly queried merchant.
    """
    template_name = 'products/shop_storefront.html'
    context_object_name = 'products'
    paginate_by = 24

    def get_queryset(self):
        self.shop = get_object_or_404(
            Shop.objects.select_related('owner'), 
            slug=self.kwargs.get('shop_slug'), 
            status='ACTIVE',
            is_active=True, 
            is_deleted=False
        )
        return Product.objects.filter(shop=self.shop, available=True, is_deleted=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['shop'] = self.shop
        
        # ✅ Fetch only categories that have active products inside THIS vendor's shop
        context['categories'] = Category.objects.filter(
            products__shop=self.shop,
            products__available=True,
            products__is_deleted=False
        ).distinct()
        
        return context

# =============================================================================
# PRIVATE VENDOR DASHBOARD VIEWS (MERCHANT WORKSPACE)
# =============================================================================

class VendorRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Custom Security Guardrail: Confirms user authentication and verifies
    the active profile owns an explicitly registered merchant shop.
    """
    def test_func(self):
        user = self.request.user
        return hasattr(user, 'shop') and user.shop.status == 'ACTIVE' and user.shop.is_active and not user.shop.is_deleted


class VendorDashboardView(VendorRequiredMixin, ListView):
    template_name = 'products/vendor_dashboard.html'
    context_object_name = 'products'
    paginate_by = 15

    def get_queryset(self):
        return Product.objects.filter(
            shop__owner=self.request.user, 
            is_deleted=False
        ).select_related('category').order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Pull or locate target shop profile 
        if hasattr(self.request.user, 'shop'):
            shop = self.request.user.shop
        else:
            shop = Shop.objects.filter(owner=self.request.user).first()
        
        context['shop'] = shop
        
        # 📊 Injected Dashboard Metrics to satisfy your dashboard template requirements
        if shop:
            # 1. Only orders actually awaiting vendor action, most recent first, capped —
            # the full history lives in the CSV export, not this table.
            context['vendor_orders'] = SubOrder.objects.filter(
                shop=shop, status__in=['Pending', 'Processing']
            ).select_related('parent_order').order_by('-created_at')[:15]
            
            # 2. Derive low stock counts dynamically (e.g., threshold <= 5 units)
            context['low_stock_count'] = Product.objects.filter(
                shop=shop, 
                is_deleted=False, 
                stock__lte=5
            ).count()

            # 3. Sales analytics — last 30 days revenue trend + lifetime/monthly totals
            cutoff = timezone.now() - datetime.timedelta(days=30)
            daily = (
                SubOrder.objects.filter(shop=shop, created_at__gte=cutoff)
                .annotate(day=TruncDate('created_at'))
                .values('day')
                .annotate(total=Sum('sub_total'))
                .order_by('day')
            )
            daily_map = {row['day']: float(row['total'] or 0) for row in daily}
            labels, values = [], []
            for i in range(29, -1, -1):
                day = (timezone.now() - datetime.timedelta(days=i)).date()
                labels.append(day.strftime('%b %d'))
                values.append(round(daily_map.get(day, 0), 2))
            context['sales_chart_labels'] = json.dumps(labels)
            context['sales_chart_values'] = json.dumps(values)

            all_orders = SubOrder.objects.filter(shop=shop)
            context['lifetime_revenue'] = all_orders.aggregate(t=Sum('sub_total'))['t'] or 0
            context['month_revenue'] = all_orders.filter(
                created_at__gte=timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            ).aggregate(t=Sum('sub_total'))['t'] or 0
            context['month_order_count'] = all_orders.filter(
                created_at__gte=timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            ).count()
        else:
            context['vendor_orders'] = SubOrder.objects.none()
            context['low_stock_count'] = 0
            context['sales_chart_labels'] = json.dumps([])
            context['sales_chart_values'] = json.dumps([])
            context['lifetime_revenue'] = 0
            context['month_revenue'] = 0
            context['month_order_count'] = 0
            
        return context

class VendorProductCreateView(VendorRequiredMixin, CreateView):
    """
    Secure inventory intake. Silently binds new products to the 
    merchant's shop without changing form fields.
    """
    model = Product
    fields = ['category', 'name', 'slug', 'description', 'price', 'stock', 'available', 'image']
    template_name = 'products/vendor_product_form.html'
    success_url = reverse_lazy('products:vendor_dashboard')

    def form_valid(self, form):
        if hasattr(self.request.user, 'shop'):
            user_shop = self.request.user.shop
            form.instance.shop = user_shop
            messages.success(self.request, f'Product "{form.instance.name}" listed successfully!')
            return super().form_valid(form)
        else:
            form.add_error(None, "You do not have an active shop to create products.")
            return self.form_invalid(form)


class VendorProductUpdateView(VendorRequiredMixin, UpdateView):
    """
    Allows a merchant to securely update their own specific product specifications.
    """
    model = Product
    fields = ['category', 'name', 'slug', 'price', 'stock', 'available', 'image', 'description']
    template_name = 'products/vendor_product_form.html'
    success_url = reverse_lazy('products:vendor_dashboard')

    def get_queryset(self):
        return Product.objects.filter(shop__owner=self.request.user, is_deleted=False)

    def form_valid(self, form):
        messages.success(self.request, f'Product "{form.instance.name}" details updated.')
        return super().form_valid(form)


class VendorProductDeleteView(VendorRequiredMixin, DeleteView):
    """
    Enterprise Safe Delete Action. Overrides hard table elimination 
    with a safe structural soft-deletion toggle.
    """
    model = Product
    template_name = 'products/vendor_product_confirm_delete.html'
    success_url = reverse_lazy('products:vendor_dashboard')

    def get_queryset(self):
         return Product.objects.filter(shop__owner=self.request.user, is_deleted=False)

    def delete(self, request, *map_args, **map_kwargs):
        self.object = self.get_object()
        self.object.is_deleted = True
        self.object.available = False
        self.object.save()
        messages.warning(request, f'Product "{self.object.name}" removed from marketplace listings.')
        return redirect(self.get_success_url())


# apps/products/views.py

class VendorInventoryBaseView(VendorRequiredMixin, ListView):
    """
    Dedicated view for isolating the Inventory Tracking Base away from the overview metrics dashboard.
    Supports catalog analytics, full data descriptions, and stock level warnings.
    """
    model = Product
    template_name = 'products/inventory_base.html'  # Points to your standalone template
    context_object_name = 'products'
    paginate_by = 25  # Keeps catalog data lists easy to read per page execution

    def get_queryset(self):
        # Grabs inventory tracking items belonging explicitly to this shop owner
        return Product.objects.filter(
            shop__owner=self.request.user, 
            is_deleted=False
        ).select_related('category').order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Safely determine the merchant shop profile
        if hasattr(self.request.user, 'shop'):
            shop = self.request.user.shop
        else:
            shop = Shop.objects.filter(owner=self.request.user).first()
        
        context['shop'] = shop
        
        # Inject dynamic operational alert stock totals 
        if shop:
            context['low_stock_count'] = Product.objects.filter(
                shop=shop, 
                is_deleted=False, 
                stock__lte=5
            ).count()
        else:
            context['low_stock_count'] = 0
            
        return context

# =============================================================================
# ORDER MANAGEMENT & STATUS TRANSITIONS
# =============================================================================

@login_required
@require_POST
@login_required
@require_POST
def bulk_update_order_status(request):
    """
    Lets a vendor mark several pending/processing sub-orders as Shipped in one
    action from the dashboard table, instead of one submit per row.
    """
    if not hasattr(request.user, 'shop'):
        messages.error(request, "Unauthorized vendor management profile context.")
        return redirect('core:home')

    shop = request.user.shop
    sub_order_ids = request.POST.getlist('sub_order_ids')

    if not sub_order_ids:
        messages.warning(request, "No orders were selected.")
        return redirect('products:vendor_dashboard')

    # Scope strictly to this vendor's own sub-orders — a vendor can never touch
    # another shop's orders even if IDs were tampered with in the request.
    updated = SubOrder.objects.filter(
        id__in=sub_order_ids, shop=shop, status__in=['Pending', 'Processing']
    ).update(status='Shipped')

    if updated:
        messages.success(request, f"{updated} order{'s' if updated != 1 else ''} marked as shipped.")
    else:
        messages.warning(request, "Selected orders were already processed or don't belong to your shop.")

    return redirect('products:vendor_dashboard')


@login_required
def export_orders_csv(request):
    """CSV export of every order this vendor's shop has ever received."""
    if not hasattr(request.user, 'shop'):
        raise Http404()

    shop = request.user.shop
    sub_orders = SubOrder.objects.filter(shop=shop).select_related('parent_order').order_by('-created_at')

    response = HttpResponse(content_type='text/csv')
    filename = f"{shop.slug}-orders-{timezone.now().strftime('%Y-%m-%d')}.csv"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow(['SubOrder ID', 'Order Date', 'Customer', 'Items', 'Subtotal (GHS)', 'Status', 'Payment Method', 'Paid'])

    for sub_order in sub_orders:
        order = sub_order.parent_order
        item_summary = "; ".join(
            f"{item.product_name} x{item.quantity}" for item in sub_order.items.all()
        )
        writer.writerow([
            sub_order.id,
            sub_order.created_at.strftime('%Y-%m-%d %H:%M'),
            order.shipping_full_name,
            item_summary,
            sub_order.sub_total,
            sub_order.status,
            order.payment_method,
            'Yes' if order.payment_status else 'No',
        ])

    return response


@login_required
def export_products_csv(request):
    """CSV export of this vendor's full product catalog, for offline inventory review."""
    if not hasattr(request.user, 'shop'):
        raise Http404()

    shop = request.user.shop
    products = Product.objects.filter(shop=shop, is_deleted=False).select_related('category').order_by('name')

    response = HttpResponse(content_type='text/csv')
    filename = f"{shop.slug}-products-{timezone.now().strftime('%Y-%m-%d')}.csv"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow(['Product ID', 'Name', 'Category', 'Price (GHS)', 'Stock', 'Available', 'Created'])

    for product in products:
        writer.writerow([
            product.id,
            product.name,
            product.category.name if product.category else '',
            product.price,
            product.stock,
            'Yes' if product.available else 'No',
            product.created_at.strftime('%Y-%m-%d'),
        ])

    return response


def update_order_status(request, sub_order_id):
    """
    Fulfillment Engine: Shifts specific vendor SubOrder slices to 'Shipped' status.
    Ensures severe access separation boundaries remain unbreached.
    """
    if not hasattr(request.user, 'shop'):
        messages.error(request, "Unauthorized vendor management profile context.")
        return redirect('core:home')
        
    shop = request.user.shop
    
    # Isolation Query: Vendor can only retrieve a SubOrder belonging to their specific Shop ID
    sub_order = get_object_or_404(SubOrder, id=sub_order_id, shop=shop)
    
    if sub_order.status in ['Pending', 'Processing']:
        sub_order.status = 'Shipped'
        sub_order.save()
        messages.success(request, f"SubOrder #{sub_order.id} updated to Shipped status.")
    else:
        messages.warning(request, f"SubOrder #{sub_order.id} is already processed as {sub_order.status}.")
        
    return redirect('products:vendor_dashboard')


