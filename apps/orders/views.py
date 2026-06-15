# apps/orders/views.py

from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.views.decorators.http import require_POST
from django.utils import timezone

from apps.cart.cart_utils import get_or_create_user_cart
from apps.products.models import Product
from apps.promotions.models import Coupon
from apps.promotions.forms import CouponApplyForm
from .models import Order, OrderItem, ShippingAddress
from .forms import ShippingAddressForm, PaymentMethodForm
import requests
from django.conf import settings

# Helper to get current checkout step
def get_checkout_step(request):
    return request.session.get('checkout_step', 1)

# Helper to set current checkout step
def set_checkout_step(request, step):
    request.session['checkout_step'] = step

@login_required
def checkout_shipping(request):
    """
    Step 1: Collect or select shipping address (now referred to as Delivery).
    """
    cart = get_or_create_user_cart(request)
    if not cart or not cart.items.exists():
        messages.warning(request, "Your cart is empty. Please add items before checking out.")
        return redirect('cart:cart_detail')

    set_checkout_step(request, 1)

    user_addresses = ShippingAddress.objects.filter(user=request.user)
    selected_address_id = request.session.get('selected_shipping_address_id')
    selected_address = None

    if selected_address_id:
        selected_address = get_object_or_404(user_addresses, id=selected_address_id)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'select_existing_address':
            address_id = request.POST.get('address_id')
            selected_address = get_object_or_404(user_addresses, id=address_id)
            request.session['selected_shipping_address_id'] = selected_address.id
            messages.success(request, "Delivery address selected.")
            return redirect('orders:checkout_payment')

        elif action == 'add_new_address':
            form = ShippingAddressForm(request.POST)
            if form.is_valid():
                new_address = form.save(commit=False)
                new_address.user = request.user
                new_address.save()
                request.session['selected_shipping_address_id'] = new_address.id
                messages.success(request, "New delivery address added and selected.")
                return redirect('orders:checkout_payment')
            else:
                messages.error(request, "Please correct the errors in the new address form.")
        elif action == 'use_guest_info':
            messages.error(request, "Guest checkout is not yet supported. Please log in.")
            return redirect('users:login')

    else: # GET request
        form = ShippingAddressForm()

    context = {
        'cart': cart,
        'user_addresses': user_addresses,
        'selected_address': selected_address,
        'form': form,
        'current_step': 1,
    }
    return render(request, 'orders/checkout_shipping.html', context)

@login_required
def checkout_payment(request):
    """
    Step 2: Select payment method and review order.
    """
    set_checkout_step(request, 2)
    cart = get_or_create_user_cart(request)
    selected_address_id = request.session.get('selected_shipping_address_id')

    if not cart or not cart.items.exists():
        messages.warning(request, "Your cart is empty. Please add items before checking out.")
        return redirect('cart:cart_detail')
    if not selected_address_id:
        messages.warning(request, "Please select a delivery address first.")
        return redirect('orders:checkout_shipping')

    shipping_address = get_object_or_404(ShippingAddress, id=selected_address_id, user=request.user)

    if request.method == 'POST':
        form = PaymentMethodForm(request.POST)
        if form.is_valid():
            payment_method = form.cleaned_data['method']
            request.session['payment_method'] = payment_method
            messages.success(request, f"Payment method '{payment_method}' selected.")
            return redirect('orders:checkout_review')
        else:
            messages.error(request, "Please select a valid payment method.")
    else:
        form = PaymentMethodForm()

    context = {
        'cart': cart,
        'shipping_address': shipping_address,
        'form': form,
        'current_step': 2,
    }
    return render(request, 'orders/checkout_payment.html', context)

@login_required
def checkout_review(request):
    """
    Step 3: Final review of the order before placing.
    Handles coupon application.
    """
    set_checkout_step(request, 3)
    cart = get_or_create_user_cart(request)
    selected_address_id = request.session.get('selected_shipping_address_id')
    payment_method = request.session.get('payment_method')

    if not cart or not cart.items.exists():
        messages.warning(request, "Your cart is empty. Please add items before checking out.")
        return redirect('cart:cart_detail')
    if not selected_address_id:
        messages.warning(request, "Please select a delivery address first.")
        return redirect('orders:checkout_shipping')
    if not payment_method:
        messages.warning(request, "Please select a payment method first.")
        return redirect('orders:checkout_payment')

    shipping_address = get_object_or_404(ShippingAddress, id=selected_address_id, user=request.user)

    coupon_form = CouponApplyForm(request.POST or None) # Initialize form
    coupon_discount_percentage = 0
    coupon_code = request.session.get('coupon_code')
    applied_coupon = None

    if coupon_code:
        try:
            applied_coupon = Coupon.objects.get(
                code=coupon_code,
                valid_from__lte=timezone.now(),
                valid_to__gte=timezone.now(),
                active=True
            )
            coupon_discount_percentage = applied_coupon.discount
        except Coupon.DoesNotExist:
            messages.warning(request, "Applied coupon is no longer valid or does not exist.")
            if 'coupon_code' in request.session:
                del request.session['coupon_code']
            coupon_code = None # Clear invalid coupon

    # Handle coupon application POST request
    if request.method == 'POST' and 'submit_coupon' in request.POST:
        print(f"DEBUG: 'submit_coupon' found in POST. Form data: {request.POST}") # DEBUG PRINT
        if coupon_form.is_valid():
            print("DEBUG: Coupon form is valid.") # DEBUG PRINT
            code = coupon_form.cleaned_data['code']
            try:
                coupon = Coupon.objects.get(
                    code=code,
                    valid_from__lte=timezone.now(),
                    valid_to__gte=timezone.now(),
                    active=True
                )
                request.session['coupon_code'] = coupon.code
                messages.success(request, f"Coupon '{coupon.code}' applied successfully! You get {coupon.discount}% off.")
                print(f"DEBUG: Coupon '{coupon.code}' applied. Redirecting.") # DEBUG PRINT
                return redirect('orders:checkout_review')
            except Coupon.DoesNotExist:
                messages.error(request, "Invalid or expired coupon code.")
                if 'coupon_code' in request.session:
                    del request.session['coupon_code']
                print("DEBUG: Coupon DoesNotExist. No redirect.") # DEBUG PRINT
        else:
            print(f"DEBUG: Coupon form is NOT valid. Errors: {coupon_form.errors}") # DEBUG PRINT
            messages.error(request, "Please enter a valid coupon code.")
        print("DEBUG: Falling through to render template after POST (no redirect).") # DEBUG PRINT
        # If form is invalid or coupon lookup fails, render the page again
        # The messages will be displayed by the base template
        # The context needs to be re-evaluated to reflect current state after failed attempt
        # (e.g., if coupon_code was cleared)
        cart_total = cart.get_total_price
        discount_amount = (cart_total * coupon_discount_percentage) / 100
        final_total = cart_total - discount_amount
        context = {
            'cart': cart,
            'shipping_address': shipping_address,
            'payment_method': payment_method,
            'coupon_form': coupon_form, # Pass the coupon form (now with errors)
            'coupon_discount_percentage': coupon_discount_percentage,
            'discount_amount': discount_amount,
            'final_total': final_total,
            'applied_coupon': applied_coupon, # This might be None if coupon was invalid
            'current_step': 3,
        }
        return render(request, 'orders/checkout_review.html', context)


    # Calculate total with discount for GET request or if coupon POST didn't redirect
    cart_total = cart.get_total_price
    discount_amount = (cart_total * coupon_discount_percentage) / 100
    final_total = cart_total - discount_amount

    context = {
        'cart': cart,
        'shipping_address': shipping_address,
        'payment_method': payment_method,
        'coupon_form': coupon_form, # Pass the coupon form
        'coupon_discount_percentage': coupon_discount_percentage,
        'discount_amount': discount_amount,
        'final_total': final_total,
        'applied_coupon': applied_coupon,
        'current_step': 3,
    }
    return render(request, 'orders/checkout_review.html', context)

# Replace your existing place_order view inside apps/orders/views.py with this:



@login_required
@transaction.atomic
def place_order(request, applied_coupon=None):
    if request.method == 'POST':
        cart = get_or_create_user_cart(request)
        selected_address_id = request.session.get('selected_shipping_address_id')
        payment_method = request.session.get('payment_method') # 'pay_now' or 'pay_on_delivery'
        coupon_code = request.session.get('coupon_code')
        coupon_discount_percentage = 0

        if not cart or not cart.items.exists():
            messages.error(request, "Your cart is empty. Cannot place an empty order.")
            return redirect('cart:cart_detail')
        if not selected_address_id or not payment_method:
            messages.error(request, "Missing delivery or payment information. Please restart checkout.")
            return redirect('orders:checkout_shipping')

        shipping_address = get_object_or_404(ShippingAddress, id=selected_address_id, user=request.user)

        if coupon_code:
            try:
                coupon = Coupon.objects.get(
                    code=coupon_code,
                    valid_from__lte=timezone.now(),
                    valid_to__gte=timezone.now(),
                    active=True
                )
                coupon_discount_percentage = coupon.discount
            except Coupon.DoesNotExist:
                messages.warning(request, "The coupon applied earlier is no longer valid.")
                coupon_code = None

        cart_total = cart.get_total_price() if callable(cart.get_total_price) else cart.get_total_price
        discount_amount = (cart_total * coupon_discount_percentage) / 100
        final_total = cart_total - discount_amount

        # 1. Create the Order (Default to Unpaid for BOTH flows initially)
        order = Order.objects.create(
            user=request.user,
            shipping_address=shipping_address,
            shipping_full_name=shipping_address.full_name,
            shipping_address_line1=shipping_address.address_line1,
            shipping_address_line2=shipping_address.address_line2,
            shipping_city=shipping_address.city,
            shipping_state=shipping_address.state,
            shipping_postal_code=shipping_address.postal_code,
            shipping_country=shipping_address.country,
            shipping_phone_number=shipping_address.phone_number,
            total_amount=final_total,
            original_total_amount=cart_total,
            coupon_applied=coupon_code,
            discount_percentage=coupon_discount_percentage,
            payment_method=payment_method,
            status='Pending',
            payment_status=False, # Verified via Paystack callback/webhook later
        )

        # 2. Add Items & Deduct Stock
        for cart_item in cart.items.all():
            if cart_item.product.stock < cart_item.quantity:
                raise ValueError(f"Insufficient stock for {cart_item.product.name}.")

            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                product_name=cart_item.product.name,
                product_price=cart_item.product.price,
                quantity=cart_item.quantity
            )
            cart_item.product.stock -= cart_item.quantity
            cart_item.product.save()

        # 3. Clear Cart & Session Properties
        cart.items.all().delete()
        
        if 'selected_shipping_address_id' in request.session:
            del request.session['selected_shipping_address_id']
        if 'payment_method' in request.session:
            del request.session['payment_method']
        if 'coupon_code' in request.session:
            del request.session['coupon_code']
        if 'checkout_step' in request.session:
            del request.session['checkout_step']

        # --- ROUTING LOGIC BASED ON USER CHOICE ---

        # WAY 1: Pay Before Delivery (On-the-spot app redirect)
        if payment_method == 'pay_now':
            paystack_url = "https://api.paystack.co/transaction/initialize"
            headers = {
                "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
                "Content-Type": "application/json",
            }
            payload = {
                "amount": int(order.total_amount * 100), # Amount in Pesewas
                "email": request.user.email,
                "reference": f"PRE-ORD-{order.id}", # Prefix helps webhook distinguish type
                "currency": "GHS",
                "callback_url": request.build_absolute_uri(f"/orders/confirmation/{order.id}/")
            }
            try:
                response = requests.post(paystack_url, json=payload, headers=headers)
                if response.status_code == 200:
                    return redirect(response.json()['data']['authorization_url'])
            except requests.RequestException:
                messages.error(request, "Communication with Paystack failed. Please try paying from history.")

        # WAY 2: Pay on Delivery (Go straight to confirmation screen)
        messages.success(request, f"Your order #{order.id} has been reserved successfully for Pay on Delivery!")
        return redirect('orders:order_confirmation', order_id=order.id)

    messages.error(request, "Invalid request method.")
    return redirect('cart:cart_detail')


# apps/orders/views.py

@login_required
def process_payment(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    if order.payment_status:
        messages.info(request, "This order is already paid.")
        return redirect('orders:order_history')

    # Initialize Paystack
    paystack_url = "https://api.paystack.co/transaction/initialize"
    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "amount": int(order.total_amount * 100),
        "email": request.user.email,
        "reference": f"RETRY-ORD-{order.id}", # Use a different prefix for retries
        "currency": "GHS",
        "callback_url": request.build_absolute_uri(f"/orders/confirmation/{order.id}/")
    }
    
    response = requests.post(paystack_url, json=payload, headers=headers)
    if response.status_code == 200:
        return redirect(response.json()['data']['authorization_url'])
    else:
        messages.error(request, "Could not connect to payment gateway. Please try again.")
        return redirect('orders:order_history')


from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def paystack_webhook(request):
    """
    Paystack calls this when a payment is successful.
    """
    if request.method == 'POST':
        # 1. Verify the signature (Important for security)
        # 2. Extract reference from payload
        # 3. Find the Order (e.g., ORD-123)
        # 4. Update: order.payment_status = True, order.status = 'Processing'
        # 5. order.save()
        return HttpResponse(status=200)

@login_required
def order_confirmation(request, order_id):
    """
    Displays the order confirmation page after a successful order.
    """
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'orders/order_confirmation.html', {'order': order})

@login_required
def order_history(request):
    """
    Displays a list of all orders for the logged-in user.
    """
    orders = Order.objects.filter(user=request.user).order_by('-order_date')
    return render(request, 'orders/order_history.html', {'orders': orders})

# --- Address Book Views ---

@login_required
def address_list(request):
    """
    Displays a list of all shipping addresses for the logged-in user.
    """
    addresses = ShippingAddress.objects.filter(user=request.user).order_by('-is_default', '-id')
    return render(request, 'orders/address_list.html', {'addresses': addresses})

@login_required
def add_address(request):
    """
    Handles adding a new shipping address.
    """
    if request.method == 'POST':
        form = ShippingAddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            address.save()
            messages.success(request, "Address added successfully!")
            return redirect('orders:address_list')
        else:
            messages.error(request, "Please correct the errors in the form.")
    else:
        form = ShippingAddressForm()
    return render(request, 'orders/address_form.html', {'form': form, 'form_title': 'Add New Delivery Address'})

@login_required
def edit_address(request, address_id):
    """
    Handles editing an existing shipping address.
    """
    address = get_object_or_404(ShippingAddress, id=address_id, user=request.user)
    if request.method == 'POST':
        form = ShippingAddressForm(request.POST, instance=address)
        if form.is_valid():
            form.save()
            messages.success(request, "Address updated successfully!")
            return redirect('orders:address_list')
        else:
            messages.error(request, "Please correct the errors in the form.")
    else:
        form = ShippingAddressForm(instance=address)
    return render(request, 'orders/address_form.html', {'form': form, 'form_title': 'Edit Delivery Address'})

@login_required
@require_POST # Ensure this view only accepts POST requests
def delete_address(request, address_id):
    """
    Deletes a shipping address.
    """
    address = get_object_or_404(ShippingAddress, id=address_id, user=request.user)
    address.delete()
    messages.info(request, "Address deleted successfully!")
    return redirect('orders:address_list')

@login_required
@require_POST
def set_default_address(request, address_id):
    """
    Sets a specific address as the default for the user.
    """
    address = get_object_or_404(ShippingAddress, id=address_id, user=request.user)
    address.is_default = True
    address.save()
    messages.success(request, "Default address updated.")
    return redirect('orders:address_list')
