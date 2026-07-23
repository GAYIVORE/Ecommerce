from decimal import Decimal

from django import forms

from .models import QuickCashOffer, Service

INPUT_CLASSES = (
    'w-full px-5 py-3.5 bg-ink-900 border border-white/10 focus:border-jade-500 '
    'focus:outline-none rounded-2xl text-sm text-white placeholder-white/30 transition-colors'
)


class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = ['title', 'category', 'price', 'description', 'contact_phone']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': INPUT_CLASSES, 'placeholder': 'e.g. Premium Home Cleaning Service'
            }),
            'category': forms.Select(attrs={'class': INPUT_CLASSES}),
            'price': forms.NumberInput(attrs={'class': INPUT_CLASSES, 'placeholder': '180'}),
            'description': forms.Textarea(attrs={
                'class': INPUT_CLASSES, 'rows': 3,
                'placeholder': 'Describe what you offer and your experience...',
            }),
            'contact_phone': forms.TextInput(attrs={
                'class': INPUT_CLASSES, 'placeholder': '+233 24 555 1234'
            }),
        }


class QuickCashOfferForm(forms.ModelForm):
    class Meta:
        model = QuickCashOffer
        fields = ['title', 'description', 'earning_range', 'link', 'offer_type']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': INPUT_CLASSES, 'placeholder': 'e.g. My Affiliate Store'
            }),
            'description': forms.TextInput(attrs={
                'class': INPUT_CLASSES, 'placeholder': 'Short description of the opportunity'
            }),
            'earning_range': forms.TextInput(attrs={
                'class': INPUT_CLASSES, 'placeholder': 'e.g. ₵80 – ₵650'
            }),
            'link': forms.URLInput(attrs={
                'class': INPUT_CLASSES, 'placeholder': 'https://...'
            }),
            'offer_type': forms.Select(attrs={'class': INPUT_CLASSES}),
        }


class LogEarningForm(forms.Form):
    amount = forms.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal('0.01'),
        widget=forms.NumberInput(attrs={'class': INPUT_CLASSES, 'placeholder': '50.00'}),
    )
    description = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': INPUT_CLASSES, 'placeholder': 'e.g. Sagapoll survey payout'
        }),
    )


class WithdrawForm(forms.Form):
    amount = forms.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal('1.00'),
        widget=forms.NumberInput(attrs={'class': INPUT_CLASSES, 'placeholder': '100.00'}),
    )
