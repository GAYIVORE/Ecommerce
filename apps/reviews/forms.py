# apps/reviews/forms.py

from django import forms
from .models import Review

class ReviewForm(forms.ModelForm):
    """
    Form for users to submit a product review.
    """
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.RadioSelect(choices=[(i, str(i)) for i in range(1, 6)]), # Radio buttons for rating
            'comment': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Write your review here...'}),
        }
        labels = {
            'rating': 'Your Rating (1-5 Stars)',
            'comment': 'Your Comment',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Tailwind CSS classes to the comment textarea
        self.fields['comment'].widget.attrs.update({
            'class': 'form-input' # Custom class from style.css
        })
        # For radio buttons, styling is more complex and often done directly in template
        # or via custom widget rendering. We'll rely on CSS for basic styling.
