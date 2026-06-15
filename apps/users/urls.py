# apps/users/urls.py

from django.urls import path
from . import views
from django.contrib.auth import views as auth_views # Import Django's built-in auth views if needed later

app_name = 'users' # Namespace for this app's URLs

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    # Use POST for logout for security reasons (prevents accidental logout via image/link prefetch)
    path('logout/', views.user_logout, name='logout'),
    path('profile/', views.profile, name='profile'),
]
