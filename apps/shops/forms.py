# apps/shops/forms.py
from django import forms
from .models import Shop

class ShopForm(forms.ModelForm):
    class Meta:
        model = Shop
        # 🌟 Added 'phone_number' to the list below
        fields = '__all__'
        
    # Optional styling trick: clean placeholder or explicit styling for the input
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'phone_number' in self.fields:
            self.fields['phone_number'].widget.attrs.update({
                'placeholder': 'e.g., +233 24 000 0000'
            })


class VendorShopSettingsForm(forms.ModelForm):
    """
    Self-service settings a vendor is trusted to edit themselves. Deliberately
    excludes 'status', 'is_active', 'is_deleted', 'owner', and the Paystack
    subaccount code — those stay admin-only so a vendor can't self-approve
    their own shop or redirect payouts.
    """
    class Meta:
        model = Shop
        fields = ['name', 'description', 'phone_number', 'image', 'min_delivery_days', 'max_delivery_days']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'field'}),
            'description': forms.Textarea(attrs={'class': 'field', 'rows': 4}),
            'phone_number': forms.TextInput(attrs={'class': 'field'}),
            'min_delivery_days': forms.NumberInput(attrs={'class': 'field'}),
            'max_delivery_days': forms.NumberInput(attrs={'class': 'field'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['phone_number'].widget.attrs.update({'placeholder': 'e.g., +233 24 000 0000'})
        self.fields['min_delivery_days'].widget.attrs.update({'min': 0})
        self.fields['max_delivery_days'].widget.attrs.update({'min': 0})

    def clean(self):
        cleaned_data = super().clean()
        lo = cleaned_data.get('min_delivery_days')
        hi = cleaned_data.get('max_delivery_days')
        if lo is not None and hi is not None and lo > hi:
            self.add_error('max_delivery_days', "Slowest delivery estimate can't be faster than the fastest one.")
        return cleaned_data