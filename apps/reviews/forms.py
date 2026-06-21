# apps/reviews/forms.py

from django import forms
from .models import Review


class ReviewForm(forms.ModelForm):
    """
    Form for customers to submit star ratings and performance feedback on products.
    """
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            # Use a clean list of strings to facilitate radio-to-star design transforms in HTML templates
            'rating': forms.RadioSelect(choices=[(i, f"{i} Star{'s' if i > 1 else ''}") for i in range(1, 6)]),
            'comment': forms.Textarea(attrs={
                'rows': 4, 
                'placeholder': 'Share your experience with this product...'
            }),
        }
        labels = {
            'rating': 'Product Rating',
            'comment': 'Written Review',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Apply pristine modern Tailwind configurations to input controls
        self.fields['comment'].widget.attrs.update({
            'class': 'w-full px-4 py-3 text-sm font-medium text-slate-900 bg-white border border-slate-200 rounded-xl focus:outline-none focus:border-amber-500 focus:ring-4 focus:ring-amber-500/10 transition-all placeholder:text-slate-400'
        })
        
        # Add helper attributes to make custom interactive star wrappers easier to build with CSS/JS
        self.fields['rating'].widget.attrs.update({
            'class': 'space-y-2 focus:ring-amber-500 text-amber-500'
        })


class VendorReplyForm(forms.ModelForm):
    """
    ⚡ Added: Dedicated form for verified merchant dashboard response actions.
    """
    class Meta:
        model = Review
        fields = ['vendor_reply']
        widgets = {
            'vendor_reply': forms.Textarea(attrs={
                'rows': 3, 
                'placeholder': 'Write your public response to this customer...'
            }),
        }
        labels = {
            'vendor_reply': 'Merchant Official Response',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['vendor_reply'].widget.attrs.update({
            'class': 'w-full px-4 py-2.5 text-sm font-medium text-slate-900 bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:border-indigo-500 focus:ring-4 focus:ring-indigo-500/10 transition-all placeholder:text-slate-400'
        })