# apps/products/views.py

from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from .models import Product, Category
from apps.reviews.forms import ReviewForm # ADDED: Import ReviewForm
from apps.reviews.models import Review   # ADDED: Import Review model

def product_list(request, category_slug=None):
    """
    Displays a list of products, optionally filtered by category or search query.
    """
    category = None
    categories = Category.objects.all()
    products = Product.objects.filter(available=True)

    query = request.GET.get('q') # Get the search query from the URL parameter 'q'

    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=category)

    if query:
        # Filter products where name or description contains the query (case-insensitive)
        products = products.filter(Q(name__icontains=query) | Q(description__icontains=query))

    context = {
        'category': category,
        'categories': categories,
        'products': products,
        'query': query, # Pass the search query to the template
    }
    return render(request, 'products/product_list.html', context)

def product_detail(request, slug):
    """
    Displays the details of a single product.
    Includes reviews and a review submission form.
    """
    product = get_object_or_404(Product, slug=slug, available=True)

    # Initialize the review form
    review_form = ReviewForm()
    user_review = None

    if request.user.is_authenticated:
        # Check if the logged-in user has already reviewed this product
        user_review = Review.objects.filter(product=product, user=request.user).first()
        if user_review:
            review_form = ReviewForm(instance=user_review) # Pre-populate form for editing

    context = {
        'product': product,
        'review_form': review_form, # Pass the review form to the template
        'user_review': user_review, # Pass the user's existing review (or None)
    }
    return render(request, 'products/product_detail.html', context)
