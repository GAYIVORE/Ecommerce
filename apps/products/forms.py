from django import forms
from .models import Product

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['category', 'name', 'description', 'price', 'stock', 'available', 'image']
        
        # We use a color-coded style: Gray border, blue focus ring, error red border
        input_classes = {
            'class': 'w-full p-2 border border-gray-300 rounded-md transition duration-200 '
                     'focus:border-blue-500 focus:ring-2 focus:ring-blue-200 outline-none'
        }
        
        widgets = {
            'category': forms.Select(attrs=input_classes),
            'name': forms.TextInput(attrs=input_classes),
            'description': forms.Textarea(attrs={'class': input_classes['class'], 'rows': 4}),
            'price': forms.NumberInput(attrs=input_classes),
            'stock': forms.NumberInput(attrs=input_classes),
            'available': forms.CheckboxInput(attrs={'class': 'h-5 w-5 text-blue-600 rounded focus:ring-blue-500'}),
            'image': forms.FileInput(attrs={'class': 'w-full p-2 border border-gray-300 rounded-md bg-gray-50 text-gray-700'}),
        }