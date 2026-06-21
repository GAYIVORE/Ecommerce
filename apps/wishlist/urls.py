# apps/wishlist/urls.py

from django.urls import path
from . import views

app_name = 'wishlist'

urlpatterns = [
    # Displays the clean grid layout of saved items
    path('', views.wishlist_detail, name='wishlist_detail'),
    
    # Secure POST actions for mutation workflows
    path('add/<int:product_id>/', views.add_to_wishlist, name='add_to_wishlist'),
    path('remove/<int:item_id>/', views.remove_from_wishlist, name='remove_from_wishlist'),
    path('move-to-cart/<int:item_id>/', views.move_to_cart, name='move_to_cart'),
]