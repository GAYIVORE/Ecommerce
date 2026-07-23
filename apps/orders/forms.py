# apps/orders/forms.py

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
            'city': forms.TextInput(attrs={'placeholder': 'City / Town'}),
            'state': forms.TextInput(attrs={'placeholder': 'Region (e.g., Greater Accra, Ashanti)'}),
            'postal_code': forms.TextInput(attrs={'placeholder': 'Digital Address / Postal Code (optional)'}),
            'country': forms.TextInput(attrs={'placeholder': 'Country'}),
            'phone_number': forms.TextInput(attrs={'placeholder': '024 XXX XXXX'}),
        }
        labels = {
            'full_name': 'Full Name',
            'address_line1': 'Address Line 1',
            'address_line2': 'Address Line 2',
            'city': 'City / Town',
            'state': 'Region',
            'postal_code': 'Postal Code / Digital Address',
            'country': 'Country',
            'phone_number': 'Active Phone Number',
            'is_default': 'Set as my default shipping profile address',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Apply standard localized placeholder defaults
        if not self.initial.get('country'):
            self.fields['country'].initial = "Ghana"
            
        for field_name, field in self.fields.items():
            if field_name != 'is_default':
                field.widget.attrs.update({'class': 'field'})
            else:
                field.widget.attrs.update({
                    'class': 'h-4 w-4 rounded-sm border-line text-brand-500 focus:ring-brand-500 transition-colors cursor-pointer'
                })


class PaymentMethodForm(forms.Form):
    """
    ⚡ Updated: Maps form selections directly to our new multi-vendor backend payment choices.
    """
    METHOD_CHOICES = [
        ('paystack', 'Pay Now with Card or Mobile Money (via Paystack)'),
        ('cod', 'Pay on Delivery / Cash / Merchant Transfer'),
    ]
    
    method = forms.ChoiceField(
        choices=METHOD_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'sr-only'}), # Screen-reader safe hiding for custom Tailwind radio designs
        label="Select Payment Method",
        required=True,
        initial='paystack'
    )