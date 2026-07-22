# apps/earn/urls.py

from django.urls import path

from . import views

app_name = 'earn'  # Namespace for this app's URLs

urlpatterns = [
    path('', views.dashboard, name='dashboard'),

    # Services marketplace
    path('marketplace/', views.marketplace, name='marketplace'),
    path('marketplace/post/', views.service_create, name='service_create'),
    path('marketplace/<slug:slug>/', views.service_detail, name='service_detail'),
    path('marketplace/<int:pk>/book/', views.book_service, name='book_service'),

    # Bookings
    path('bookings/', views.my_bookings, name='my_bookings'),
    path('bookings/<int:pk>/confirm/', views.booking_confirm, name='booking_confirm'),
    path('bookings/<int:pk>/complete/', views.booking_complete, name='booking_complete'),
    path('bookings/<int:pk>/cancel/', views.booking_cancel, name='booking_cancel'),
    path('bookings/<int:pk>/review/', views.booking_review, name='booking_review'),

    # Quick cash
    path('quickcash/', views.quickcash, name='quickcash'),
    path('quickcash/add/', views.add_offer, name='add_offer'),
    path('quickcash/<int:pk>/delete/', views.delete_offer, name='delete_offer'),

    # Earnings
    path('earnings/', views.earnings, name='earnings'),
    path('earnings/log/', views.log_earning, name='log_earning'),
    path('earnings/withdraw/', views.withdraw, name='withdraw'),
]
