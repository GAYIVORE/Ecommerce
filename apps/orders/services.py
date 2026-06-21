# apps/orders/services.py

import requests
from django.conf import settings
from django.urls import reverse

class PaystackPaymentService:
    """
    Handles payment initialization and verification payloads with Paystack.
    Transforms standard GHS values to their subunit form (pesewas) as required by Paystack.
    """
    def __init__(self):
        self.secret_key = settings.PAYSTACK_SECRET_KEY
        self.base_url = "https://api.paystack.co"
        self.headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json",
        }

    def initialize_transaction(self, order, request):
        """
        Generates a secure checkout payment link from Paystack.
        """
        url = f"{self.base_url}/transaction/initialize"
        
        # Convert GHS to pesewas (e.g., 10 GHS = 1000 pesewas)
        amount_in_pesewas = int(order.total_amount * 100)
        
        # Build dynamic fallback absolute redirection url
        callback_url = request.build_absolute_uri(reverse('orders:payment_callback'))

        payload = {
            "email": order.email,
            "amount": amount_in_pesewas,
            "reference": order.order_id,  # Use your database unique Order ID
            "callback_url": callback_url,
            "metadata": {
                "order_database_id": order.id,
                "custom_fields": [
                    {"display_name": "Platform", "variable_name": "platform", "value": "MultiVendor Marketplace"}
                ]
            }
        }

        response = requests.post(url, json=payload, headers=self.headers)
        if response.status_code == 200:
            return response.json().get('data') # Returns authorization_url and reference
        return None

    def verify_transaction(self, reference):
        """
        Server-to-Server double-check to confirm the transaction status.
        """
        url = f"{self.base_url}/transaction/verify/{reference}"
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('data', {}).get('status') == 'success':
                return True, result.get('data')
        return False, None