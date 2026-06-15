# apps/reviews/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.utils import IntegrityError # For handling unique_together constraint
from apps.products.models import Product
from .forms import ReviewForm
from .models import Review

@login_required
def add_review(request, product_slug):
    """
    Handles adding a new review for a specific product.
    """
    product = get_object_or_404(Product, slug=product_slug)

    # Check if user has already reviewed this product
    existing_review = Review.objects.filter(product=product, user=request.user).first()

    if request.method == 'POST':
        form = ReviewForm(request.POST, instance=existing_review) # Use instance for update if exists
        if form.is_valid():
            try:
                review = form.save(commit=False)
                review.product = product
                review.user = request.user
                review.save()
                if existing_review:
                    messages.success(request, "Your review has been updated successfully!")
                else:
                    messages.success(request, "Your review has been submitted successfully!")
                return redirect('products:product_detail', slug=product.slug)
            except IntegrityError:
                messages.error(request, "You have already reviewed this product. You can edit your existing review.")
                return redirect('products:product_detail', slug=product.slug)
            except Exception as e:
                messages.error(request, f"An error occurred: {e}")
                return redirect('products:product_detail', slug=product.slug)
        else:
            messages.error(request, "Please correct the errors in your review.")
    else:
        form = ReviewForm(instance=existing_review) # Pre-populate form if editing

    context = {
        'product': product,
        'form': form,
        'existing_review': existing_review,
    }
    return render(request, 'reviews/add_review.html', context) # This template will be simple, or we might embed it directly
