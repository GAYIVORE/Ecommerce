# apps/promotions/urls.py

from django.urls import path
from . import views

app_name = 'promotions' # ADDED: Define the app_name for the namespace

urlpatterns = [
    # No direct views for promotions app itself, only logic within orders app for now.
    # We can add specific promotion-related views here later if needed, e.g.,
    # path('apply/', views.apply_coupon, name='apply_coupon'), # If you had a dedicated apply view
]
