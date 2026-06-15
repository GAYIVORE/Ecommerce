from django import forms
from .models import ShippingAddress

class ShippingAddressForm(forms.ModelForm):
    """
    Form for users to input or select a shipping address during checkout.
    """
    class Meta:
        model = ShippingAddress
        fields = [
            'full_name', 'address_line1', 'address_line2',
            'city', 'state', 'postal_code', 'country', 'phone_number',
            'is_default'
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={'placeholder': 'Full Name'}),
            'address_line1': forms.TextInput(attrs={'placeholder': 'Street Address, P.O. Box'}),
            'address_line2': forms.TextInput(attrs={'placeholder': 'Apartment, suite, unit, etc. (optional)'}),
            'city': forms.TextInput(attrs={'placeholder': 'City'}),
            'state': forms.TextInput(attrs={'placeholder': 'State / Region (optional)'}),
            'postal_code': forms.TextInput(attrs={'placeholder': 'Postal Code (optional)'}),
            'country': forms.TextInput(attrs={'placeholder': 'Country (e.g., Ghana)'}),
            'phone_number': forms.TextInput(attrs={'placeholder': 'Phone Number'}),
        }
        labels = {
            'full_name': 'Full Name',
            'address_line1': 'Address Line 1',
            'address_line2': 'Address Line 2',
            'city': 'City',
            'state': 'State/Region',
            'postal_code': 'Postal Code',
            'country': 'Country',
            'phone_number': 'Phone Number',
            'is_default': 'Set as default address',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if field_name != 'is_default':
                field.widget.attrs.update({
                    'class': 'w-full px-3.5 py-2.5 rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-slate-900/10'
                })

class PaymentMethodForm(forms.Form):
    """
    Form for selecting between Pay Now (Paystack) and Pay on Delivery.
    """
    # These keys match the logic in your views.py 'place_order' function
    METHOD_CHOICES = [
        ('pay_now', 'Pay Now (Card / Mobile Money)'),
        ('pay_on_delivery', 'Pay on Delivery (Cash / USSD)'),
    ]
    
    method = forms.ChoiceField(
        choices=METHOD_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'hidden'}), # We use CSS/JS to style these
        label="Select Payment Method",
        required=True
    )