# apps/cart/urls.py

from django.urls import path
from . import views

app_name = 'cart'

urlpatterns = [
    path('', views.cart_detail, name='cart_detail'),
    # ⚡ Updated this line below from views.add_to_cart to views.add_to_cart_view
    path('add/<int:product_id>/', views.add_to_cart_view, name='add_to_cart'),
    path('remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('update/<int:item_id>/', views.update_cart, name='update_cart'),
]