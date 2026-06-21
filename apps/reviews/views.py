# apps/reviews/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.utils import IntegrityError
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.products.models import Product
from .forms import ReviewForm, VendorReplyForm
from .models import Review


@login_required
def add_review(request, product_slug):
    """
    Handles adding or updating a customer review for a specific product.
    Automatically handles existing records using model instance updates.
    """
    product = get_object_or_404(Product, slug=product_slug)

    # Check if user has already reviewed this product
    existing_review = Review.objects.filter(product=product, user=request.user).first()

    if request.method == 'POST':
        form = ReviewForm(request.POST, instance=existing_review)
        if form.is_valid():
            try:
                review = form.save(commit=False)
                review.product = product
                review.user = request.user
                # Note: review.shop is automatically mapped by the model's save() override
                review.save()
                
                if existing_review:
                    messages.success(request, "Your review has been updated successfully!")
                else:
                    messages.success(request, "Your review has been submitted successfully!")
                return redirect('products:product_detail', slug=product.slug)
            except IntegrityError:
                messages.error(request, "You have already reviewed this product. You can update your existing review.")
                return redirect('products:product_detail', slug=product.slug)
        else:
            messages.error(request, "Please correct the errors in your review.")
    else:
        form = ReviewForm(instance=existing_review)

    context = {
        'product': product,
        'form': form,
        'existing_review': existing_review,
    }
    return render(request, 'reviews/add_review.html', context)


@login_required
@require_POST
def add_vendor_reply(request, review_id):
    """
    ⚡ Added: Secure Merchant Response Controller.
    Allows verified shop owners to respond directly to customer reviews.
    """
    review = get_object_or_404(Review, id=review_id)
    
    # 🔒 Security Guard: Verify the logged-in user is the explicit owner of the shop selling the item
    if review.product.shop.owner != request.user:
        messages.error(request, "Access denied. You do not have permissions to manage this shop profile.")
        return redirect('products:product_detail', slug=review.product.slug)

    form = VendorReplyForm(request.POST, instance=review)
    if form.is_valid():
        reply = form.save(commit=False)
        reply.vendor_replied_at = timezone.now()
        reply.save()
        messages.success(request, "Your official merchant response has been published.")
    else:
        messages.error(request, "Unable to publish response. Check form inputs.")

    return redirect('products:product_detail', slug=review.product.slug)