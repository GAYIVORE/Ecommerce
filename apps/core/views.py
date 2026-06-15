from django.shortcuts import render

# apps/core/views.py

from django.shortcuts import render

def home(request):
    """
    Renders the homepage of the e-commerce shop.
    """
    return render(request, 'core/home.html', {})

