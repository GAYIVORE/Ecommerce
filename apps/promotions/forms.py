# apps/promotions/forms.py

from django import forms

class CouponApplyForm(forms.Form):
    """
    Form for users to apply a coupon code.
    """
    code = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter coupon code',
            'class': 'form-input inline-block w-full md:w-auto'
        }),
        label="Coupon Code"
    )
