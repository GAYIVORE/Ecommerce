# apps/vendors/forms.py

from django import forms

class VendorOnboardingForm(forms.Form):
    # Paystack precise system bank codes for Ghana networks
    GHANA_FINANCIAL_PROVIDERS = [
        ('MTN', 'MTN Mobile Money'),
        ('VOD', 'Telecel Cash (Vodafone)'),
        ('ATL', 'AT Money (AirtelTigo)'),
    ]

    business_name = forms.CharField(
        max_length=150,
        label="Official Shop Name",
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-slate-200 rounded-xl focus:ring-4 focus:ring-amber-500/10 focus:border-amber-500 transition-all outline-none',
            'placeholder': 'e.g. Makola Digital Electronics'
        })
    )
    
    settlement_bank = forms.ChoiceField(
        choices=GHANA_FINANCIAL_PROVIDERS,
        label="Payout Wallet Provider",
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 border border-slate-200 rounded-xl focus:ring-4 focus:ring-amber-500/10 focus:border-amber-500 transition-all outline-none bg-white'
        })
    )
    
    account_number = forms.CharField(
        max_length=15,
        label="Mobile Money Number",
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 border border-slate-200 rounded-xl focus:ring-4 focus:ring-amber-500/10 focus:border-amber-500 transition-all outline-none',
            'placeholder': 'e.g. 0244123456'
        })
    )