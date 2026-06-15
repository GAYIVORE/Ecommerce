# apps/core/urls.py

from django.urls import path
from . import views

app_name = 'core' # Namespace for this app's URLs

urlpatterns = [
    path('', views.home, name='home'), # The root path for this app
]
