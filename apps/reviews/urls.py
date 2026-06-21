# apps/reviews/urls.py

from django.urls import path
from . import views

app_name = 'reviews'

urlpatterns = [
    # 🛒 Customer Action: Submit a product evaluation & star rating
    path('add/<slug:product_slug>/', views.add_review, name='add_review'),
    
    # 🏪 Vendor Action: Post an official merchant dashboard response reply
    path('reply/<int:review_id>/', views.add_vendor_reply, name='add_vendor_reply'),
]