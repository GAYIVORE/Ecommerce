# apps/products/urls.py

from django.urls import path
from . import views

app_name = 'products' # Namespace for this app's URLs

urlpatterns = [
    path('', views.product_list, name='product_list'),
    path('<slug:category_slug>/', views.product_list, name='product_list_by_category'),
    path('detail/<slug:slug>/', views.product_detail, name='product_detail'),
]
