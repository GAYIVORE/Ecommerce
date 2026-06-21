# apps/users/urls.py

from django.urls import path
from . import views

app_name = 'users'  # Namespace for clean reverse routing: e.g., 'users:login'

urlpatterns = [
    # Core Authentication Routes
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    
    # Secure POST-driven logout pathway to mitigate link prefetch session termination
    path('logout/', views.user_logout, name='logout'),
    
    # Profile & Account Verification Panel Elements
    path('profile/', views.profile, name='profile'),
    path('activate/<str:uidb64>/<str:token>/', views.activate, name='activate'),
]