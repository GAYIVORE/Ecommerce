from django.apps import AppConfig

class ShopsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    
    # 🌟 CRITICAL FIX: Match this exactly to its real directory structure path
    name = 'apps.shops'