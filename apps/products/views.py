# apps/products/views.py

from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.db.models import Q
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.http import Http404

from .models import Product, Category, Shop
from apps.reviews.forms import ReviewForm
from apps.reviews.models import Review


# =============================================================================
# PUBLIC MARKETPLACE VIEWS (CUSTOMER FACING)
# =============================================================================

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
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = self.category
        context['categories'] = Category.objects.all()
        context['query'] = self.request.GET.get('q', '')
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
        # 🌟 STRATEGY SHIFT: Directly look up products owned by the user's shop 
        # via the relationship span filter 'shop__owner' (This is bulletproof!)
        return Product.objects.filter(
            shop__owner=self.request.user, 
            is_deleted=False
        ).select_related('category').order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Safely fetch the shop instance just for the top layout title text
        if hasattr(self.request.user, 'shop'):
            context['shop'] = self.request.user.shop
        else:
            context['shop'] = Shop.objects.filter(owner=self.request.user).first()
            
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
        # FIXED: Accessing singular relation wrapper securely
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
        # Security Boundary: Restricts alteration strictly to items owned by the user's shop
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