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