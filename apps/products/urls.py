# apps/products/urls.py

from django.urls import path
from . import views
from apps.shops.views import shop_directory

app_name = 'products'  # Namespace for this app's URLs

urlpatterns = [
    # -------------------------------------------------------------------------
    # Public Marketplace Routes (Customers)
    # -------------------------------------------------------------------------
    # Global feeds and entry points
    path('', views.GlobalProductListView.as_view(), name='product_list'),
    path('category/<slug:category_slug>/', views.GlobalProductListView.as_view(), name='product_list_by_category'),
    path('detail/<slug:slug>/', views.ProductDetailView.as_view(), name='product_detail'),
    
    # Public Vendor Storefront Profile Catalog
    path('shops/', shop_directory, name='shop_list'), 
    path('shops/<slug:shop_slug>/', views.ShopStorefrontView.as_view(), name='shop_storefront'),

    # -------------------------------------------------------------------------
    # Private Vendor Management Workspace Routes (Merchants)
    # -------------------------------------------------------------------------
    # Core Vendor Dashboard landing engine
    path('dashboard/', views.VendorDashboardView.as_view(), name='vendor_dashboard'),
    path('sub-order/<int:sub_order_id>/ship/', views.update_order_status, name='update_order_status'),

    path('dashboard/inventory/', views.VendorInventoryBaseView.as_view(), name='vendor_inventory_base'),
    # Inventory Lifecycle Management Actions
    path('dashboard/products/create/', views.VendorProductCreateView.as_view(), name='vendor_product_create'),
    path('dashboard/products/<slug:slug>/update/', views.VendorProductUpdateView.as_view(), name='vendor_product_update'),
    path('dashboard/products/<slug:slug>/delete/', views.VendorProductDeleteView.as_view(), name='vendor_product_delete'),
]