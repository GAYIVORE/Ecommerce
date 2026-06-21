# apps/vendors/urls.py

from django.urls import path
from . import views

app_name = 'vendors'

urlpatterns = [
    # ... your existing vendor dashboard path profiles ...
    path('onboard/', views.onboard_vendor_shop, name='onboard_vendor_shop'),
]