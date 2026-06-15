# apps/orders/urls.py

from django.urls import path
from . import views

app_name = 'orders' # Namespace for this app's URLs

urlpatterns = [
    path('checkout/shipping/', views.checkout_shipping, name='checkout_shipping'),
    path('checkout/payment/', views.checkout_payment, name='checkout_payment'),
    path('checkout/review/', views.checkout_review, name='checkout_review'),
    path('checkout/place-order/', views.place_order, name='place_order'),
    path('confirmation/<int:order_id>/', views.order_confirmation, name='order_confirmation'),
    path('history/', views.order_history, name='order_history'),
    path('addresses/', views.address_list, name='address_list'),
    path('process-payment/<int:order_id>/', views.process_payment, name='process_payment'),

    # --- Address Book URLs ---
    path('addresses/add/', views.add_address, name='add_address'), # Ensure this line is exactly as shown
    path('addresses/edit/<int:address_id>/', views.edit_address, name='edit_address'),
    path('addresses/delete/<int:address_id>/', views.delete_address, name='delete_address'),
    path('addresses/set-default/<int:address_id>/', views.set_default_address, name='set_default_address'),


]
