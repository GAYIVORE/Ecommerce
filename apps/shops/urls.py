from django.urls import path
from . import views

app_name = 'shops' 

urlpatterns = [
    path('', views.shop_directory, name='shop_directory'),
    path('dashboard/', views.vendor_dashboard, name='vendor_dashboard'),
    path('dashboard/settings/', views.shop_settings, name='shop_settings'),
    # Add this line below:
    path('apply/', views.create_shop, name='create_shop'), 
    path('live-restocks/', views.recent_restocks_feed, name='recent_restocks_api'),
    path('sectors-showcase/', views.sectors_showcase_api, name='sectors_showcase_api'),
]