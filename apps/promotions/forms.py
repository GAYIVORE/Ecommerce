# apps/promotions/forms.py

from django import forms
from django.utils import timezone
from .models import Coupon


class CouponApplyForm(forms.Form):
    """
    Form for customers to submit promotional coupon codes on the checkout review page.
    """
    code = forms.CharField(
        max_length=50,
        label="Promo Code",
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter coupon code',
            'class': 'field'
        })
    )

    def clean_code(self):
        """
        🛡️ Early-Stage Validation: Sanitizes data and verifies basic 
        validity parameters before passing it downstream.
        """
        code = self.cleaned_data.get('code', '').strip()
        if not code:
            raise forms.ValidationError("Please provide a coupon code.")

        # Query database directly using optimized indexes
        coupon = Coupon.objects.filter(
            code__iexact=code,
            valid_from__lte=timezone.now(),
            valid_to__gte=timezone.now(),
            active=True
        ).first()

        if not coupon:
            raise forms.ValidationError("This coupon code is invalid or has expired.")

        # Guard against fully depleted promotional campaigns
        if coupon.usage_limit is not None and coupon.times_used >= coupon.usage_limit:
            raise forms.ValidationError("This coupon code has run out of redemptions.")

        # Attach the coupon object directly to the cleaned data map for easy view access
        self.cleaned_coupon = coupon
        return code