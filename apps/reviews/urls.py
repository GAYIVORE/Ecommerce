# apps/reviews/urls.py

from django.urls import path
from . import views

app_name = 'reviews' # Namespace for this app's URLs

urlpatterns = [
    path('add/<slug:product_slug>/', views.add_review, name='add_review'),
    # You might add edit/delete review URLs later if needed
]
