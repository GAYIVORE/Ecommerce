from django.apps import AppConfig

class PaymentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    
    # 🌟 FIX: Prepend 'apps.' so Django knows its true location
    name = 'apps.payments'