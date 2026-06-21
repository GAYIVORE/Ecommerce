# apps/orders/views.py

import json
import hashlib
import hmac
import requests
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.conf import settings

from apps.cart.cart_utils import get_or_create_user_cart
from apps.products.models import Product
from apps.promotions.models import Coupon
from apps.promotions.forms import CouponApplyForm
from .models import Order, SubOrder, OrderItem, ShippingAddress
from .forms import ShippingAddressForm, PaymentMethodForm


def get_checkout_step(request):
    return request.session.get('checkout_step', 1)


def set_checkout_step(request, step):
    request.session['checkout_step'] = step


@login_required
def checkout_shipping(request):
    """Step 1: Collect or select delivery location profile."""
    cart = get_or_create_user_cart(request)
    if not cart or not cart.items.exists():
        messages.warning(request, "Your cart is empty. Please add items before checking out.")
        return redirect('cart:cart_detail')

    set_checkout_step(request, 1)
    user_addresses = ShippingAddress.objects.filter(user=request.user)
    selected_address_id = request.session.get('selected_shipping_address_id')
    selected_address = None

    if selected_address_id:
        selected_address = user_addresses.filter(id=selected_address_id).first()

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
                messages.success(request, "New delivery address saved and selected.")
                return redirect('orders:checkout_payment')
            else:
                messages.error(request, "Please correct the errors in the new address form.")
    else:
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
    """Step 2: Core payment option distribution selector."""
    set_checkout_step(request, 2)
    cart = get_or_create_user_cart(request)
    selected_address_id = request.session.get('selected_shipping_address_id')

    if not cart or not cart.items.exists():
        messages.warning(request, "Your cart is empty.")
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
            messages.success(request, "Payment routing method preserved.")
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
    """Step 3: Verification panel showing multi-vendor distributions and voucher tools."""
    set_checkout_step(request, 3)
    cart = get_or_create_user_cart(request)
    selected_address_id = request.session.get('selected_shipping_address_id')
    payment_method = request.session.get('payment_method')

    if not cart or not cart.items.exists():
        messages.warning(request, "Your cart is empty.")
        return redirect('cart:cart_detail')
    if not selected_address_id:
        return redirect('orders:checkout_shipping')
    if not payment_method:
        return redirect('orders:checkout_payment')

    shipping_address = get_object_or_404(ShippingAddress, id=selected_address_id, user=request.user)
    
    # ⚡ Updated to integrate our custom CouponApplyForm optimization checks
    coupon_form = CouponApplyForm(request.POST or None)
    coupon_code = request.session.get('coupon_code')
    applied_coupon = None

    if coupon_code:
        applied_coupon = Coupon.objects.filter(
            code=coupon_code,
            valid_from__lte=timezone.now(),
            valid_to__gte=timezone.now(),
            active=True
        ).select_related('shop').first()
        
        if not applied_coupon or not applied_coupon.is_valid:
            del request.session['coupon_code']
            applied_coupon = None
            messages.warning(request, "Applied coupon is no longer valid.")

    if request.method == 'POST' and 'submit_coupon' in request.POST:
        if coupon_form.is_valid():
            # Extract checked coupon safely from form clean wrapper
            coupon = coupon_form.cleaned_coupon
            
            # Vendor specific check: ensure target vendor items are inside the active cart context
            if coupon.shop and not cart.items.filter(product__shop=coupon.shop).exists():
                messages.error(request, f"This coupon code only applies to products from '{coupon.shop.name}'.")
            else:
                request.session['coupon_code'] = coupon.code
                messages.success(request, f"Coupon '{coupon.code}' applied successfully!")
                return redirect('orders:checkout_review')
        else:
            messages.error(request, "Invalid, expired, or fully depleted coupon code entered.")

    # Calculate multi-vendor scoped pricing
    cart_items = cart.items.select_related('product__shop').all()
    cart_total = sum(item.quantity * item.product.price for item in cart_items)
    discount_amount = 0

    if applied_coupon:
        if applied_coupon.shop:
            # Isolate discount value strictly to the issuing vendor's matching lines
            vendor_target_total = sum(
                item.quantity * item.product.price 
                for item in cart_items if item.product.shop == applied_coupon.shop
            )
            discount_amount = (vendor_target_total * applied_coupon.discount) / 100
        else:
            # Global platform coupon application
            discount_amount = (cart_total * applied_coupon.discount) / 100

    final_total = max(0, cart_total - discount_amount)

    context = {
        'cart': cart,
        'shipping_address': shipping_address,
        'payment_method': payment_method,
        'coupon_form': coupon_form,
        'coupon_discount_percentage': applied_coupon.discount if applied_coupon else 0,
        'discount_amount': discount_amount,
        'final_total': final_total,
        'applied_coupon': applied_coupon,
        'current_step': 3,
    }
    return render(request, 'orders/checkout_review.html', context)


@login_required
@transaction.atomic
def place_order(request):
    """
    ⚡ Engine Core: Implements Parent-Child Order Splitting logic alongside
    vendor coupon scopes and secure automated inventory calculation metrics.
    """
    if request.method != 'POST':
        return redirect('cart:cart_detail')

    cart = get_or_create_user_cart(request)
    selected_address_id = request.session.get('selected_shipping_address_id')
    payment_method = request.session.get('payment_method')
    coupon_code = request.session.get('coupon_code')

    if not cart or not cart.items.exists():
        messages.error(request, "Your cart is empty.")
        return redirect('cart:cart_detail')
        
    if not selected_address_id or not payment_method:
        messages.error(request, "Missing information. Restart checkout pipeline.")
        return redirect('orders:checkout_shipping')

    shipping_address = get_object_or_404(ShippingAddress, id=selected_address_id, user=request.user)
    applied_coupon = None

    if coupon_code:
        applied_coupon = Coupon.objects.filter(
            code=coupon_code, valid_from__lte=timezone.now(), valid_to__gte=timezone.now(), active=True
        ).select_related('shop').first()

    cart_items = cart.items.select_related('product__shop').all()
    cart_total = sum(item.quantity * item.product.price for item in cart_items)
    global_discount_amount = 0

    # Early validation check: pre-verify inventory availability prior to building database records
    for cart_item in cart_items:
        if cart_item.product.stock < cart_item.quantity or not cart_item.product.available:
            messages.error(request, f"Sorry, '{cart_item.product.name}' is sold out or unavailable. Adjust quantity.")
            return redirect('cart:cart_detail')

    if applied_coupon:
        if applied_coupon.shop:
            vendor_target_total = sum(
                item.quantity * item.product.price 
                for item in cart_items if item.product.shop == applied_coupon.shop
            )
            global_discount_amount = (vendor_target_total * applied_coupon.discount) / 100
        else:
            global_discount_amount = (cart_total * applied_coupon.discount) / 100

    final_total = max(0, cart_total - global_discount_amount)

    # Use atomic transactions block to protect database mutations
    with transaction.atomic():
        # 1. Instantiate Parent Container Record
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
            coupon_applied=coupon_code if applied_coupon else None,
            discount_percentage=applied_coupon.discount if applied_coupon else 0,
            payment_method=payment_method,
            status='Pending',
            payment_status=True if payment_method == 'cod' else False,
        )

        # 2. Extract and Group items by Shop to generate SubOrders dynamically
        shop_item_map = {}
        for item in cart_items:
            shop = item.product.shop
            shop_item_map.setdefault(shop, []).append(item)

        for shop, items in shop_item_map.items():
            vendor_raw_subtotal = sum(i.quantity * i.product.price for i in items)
            
            vendor_proportional_discount = 0
            if applied_coupon:
                if applied_coupon.shop == shop or applied_coupon.shop is None:
                    vendor_proportional_discount = (vendor_raw_subtotal * applied_coupon.discount) / 100

            vendor_final_subtotal = max(0, vendor_raw_subtotal - vendor_proportional_discount)

            # Create localized child partition container row
            sub_order = SubOrder.objects.create(
                parent_order=order,
                shop=shop,
                status='Pending' if payment_method == 'paystack' else 'Processing',
                sub_total=vendor_final_subtotal,
                shipping_cost=0.00
            )

            # Write matching line item structures
            for cart_item in items:
                OrderItem.objects.create(
                    order=order,
                    sub_order=sub_order,
                    product=cart_item.product,
                    product_name=cart_item.product.name,
                    product_price=cart_item.product.price,
                    quantity=cart_item.quantity
                )
                
                # 🌟 SEPARATE LOGIC CHANNELS: Process structural stock deduction immediately ONLY for Cash On Delivery (COD)
                if payment_method == 'cod':
                    product = cart_item.product
                    product.stock -= cart_item.quantity
                    if product.stock <= 0:
                        product.stock = 0
                        product.available = False
                    product.save()

        # Update coupon limit calculations immediately if choosing COD
        if payment_method == 'cod' and applied_coupon:
            Coupon.objects.filter(id=applied_coupon.id).update(times_used=models.F('times_used') + 1)

    # 3. Clean operational parameters out from state caches
    cart.items.all().delete()
    for session_key in ['selected_shipping_address_id', 'payment_method', 'coupon_code', 'checkout_step']:
        request.session.pop(session_key, None)

    # --- GATEWAY DISTRIBUTION ROUTING (PAYSTACK SPLIT ENGINE) ---
    if payment_method == 'paystack':
        paystack_url = "https://api.paystack.co/transaction/initialize"
        headers = {
            "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json",
        }
        
        generated_sub_orders = order.sub_orders.select_related('shop').all()
        subaccounts_payload = []
        
        for sub_order in generated_sub_orders:
            if sub_order.shop.paystack_subaccount_code:
                commission_rate = 0.05  # 5% Marketplace Platform Fee Commission
                total_vendor_pesewas = int(sub_order.sub_total * 100)
                
                commission_pesewas = int(total_vendor_pesewas * commission_rate)
                vendor_share_pesewas = total_vendor_pesewas - commission_pesewas
                
                subaccounts_payload.append({
                    "subaccount": sub_order.shop.paystack_subaccount_code,
                    "share": vendor_share_pesewas
                })
        
        payload = {
            "amount": int(order.total_amount * 100), # Explicit Pesewas integer conversions
            "email": request.user.email,
            "reference": f"PRE-ORD-{order.id}",
            "currency": "GHS",
            "callback_url": request.build_absolute_uri(f"/orders/order-confirmation/{order.id}/")
        }
        
        if subaccounts_payload:
            payload["split"] = {
                "type": "flat",
                "bearer_type": "account", # Your master account bears the transactional gate fee
                "subaccounts": subaccounts_payload
            }

        try:
            response = requests.post(paystack_url, json=payload, headers=headers, timeout=10)
            if response.status_code == 200:
                return redirect(response.json()['data']['authorization_url'])
            else:
                messages.error(request, f"Gateway configuration error: {response.json().get('message')}")
                return redirect('cart:cart_detail')
        except requests.RequestException:
            messages.error(request, "Gateway connection dropped. Complete payment via your history dashboard.")
            return redirect('orders:order_confirmation', order_id=order.id)
            
    messages.success(request, f"Order #{order.id} verified successfully using Cash on Delivery!")
    return redirect('orders:order_confirmation', order_id=order.id)

@login_required
def process_payment(request, order_id):
    """
    Fallback loop allowing outstanding unpaid parent invoices to trigger gateway handshakes,
    fully supporting dynamic vendor subaccount payment splits.
    """
    order = get_or_create_user_cart = get_object_or_404(Order, id=order_id, user=request.user)
    if order.payment_status or order.payment_method == 'cod':
        messages.info(request, "This invoice is already paid or set to Cash on Delivery.")
        return redirect('orders:order_history')

    paystack_url = "https://api.paystack.co/transaction/initialize"
    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }
    
    # Re-fetch SubOrders to build vendor share splits for payment recovery
    generated_sub_orders = order.sub_orders.select_related('shop').all()
    subaccounts_payload = []
    
    for sub_order in generated_sub_orders:
        if sub_order.shop.paystack_subaccount_code:
            commission_rate = 0.05  # 5% platform fee matching primary engine split rules
            total_vendor_pesewas = int(sub_order.sub_total * 100)
            
            commission_pesewas = int(total_vendor_pesewas * commission_rate)
            vendor_share_pesewas = total_vendor_pesewas - commission_pesewas
            
            subaccounts_payload.append({
                "subaccount": sub_order.shop.paystack_subaccount_code,
                "share": vendor_share_pesewas
            })

    # Reference includes retry tracker string token parameters
    payload = {
        "amount": int(order.total_amount * 100),
        "email": request.user.email,
        "reference": f"RETRY-ORD-{order.id}",
        "currency": "GHS",
        "callback_url": request.build_absolute_uri(f"/orders/order-confirmation/{order.id}/")
    }
    
    if subaccounts_payload:
        payload["split"] = {
            "type": "flat",
            "bearer_type": "account",
            "subaccounts": subaccounts_payload
        }

    try:
        response = requests.post(paystack_url, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            return redirect(response.json()['data']['authorization_url'])
        else:
            messages.error(request, f"Gateway error: {response.json().get('message')}")
    except requests.RequestException:
        messages.error(request, "Gateway pipeline connection dropped. Try again shortly.")
        
    return redirect('orders:order_history')


@csrf_exempt
def paystack_webhook(request):
    """
    🔒 Secure Automated Webhook: Intercepts Paystack fulfillment events safely.
    Handles atomic multi-vendor status elevation, product inventory subtractions, 
    and dynamic 'Sold Out' availability state triggers.
    """
    if request.method != 'POST':
        return HttpResponse(status=405)

    signature = request.META.get('HTTP_X_PAYSTACK_SIGNATURE')
    if not signature:
        return HttpResponseBadRequest("Missing security token.")

    # 🔧 FIX: Paystack uses SHA256 encoding for signing webhook payloads
    computed_signature = hmac.new(
        bytes(settings.PAYSTACK_SECRET_KEY, 'utf-8'),
        msg=request.body,
        digestmod=hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(computed_signature, signature):
        return HttpResponseBadRequest("Signature verification mismatch.")

    try:
        payload = json.loads(request.body)
        if payload.get('event') == 'charge.success':
            data = payload.get('data', {})
            reference = data.get('reference', '')
            transaction_id = data.get('id')

            # Parse out the base primary database model integer ID token
            order_id = reference.split('-')[-1]
            
            # Open up safe transaction block to run inventory reductions securely
            with transaction.atomic():
                # Lock rows using select_for_update to handle simultaneous concurrent webhooks
                order = Order.objects.select_for_update().get(id=order_id)

                if not order.payment_status:
                    # 1. Update Core Parent Order Status
                    order.payment_status = True
                    order.transaction_id = str(transaction_id)
                    order.status = 'Processing'
                    order.save()
                    
                    # 2. Sync Status Changes to child SubOrders
                    order.sub_orders.all().update(status='Processing')
                    
                    # 3. Secure Stock Subtraction Loops & Real-time Sold Out Checks
                    order_items = order.items.select_related('product').all()
                    for item in order_items:
                        product = item.product
                        product.stock -= item.quantity
                        
                        # Check if product hits zero balance thresholds
                        if product.stock <= 0:
                            product.stock = 0
                            product.available = False  # 🌟 Automatically labels product as 'Sold Out'
                            
                        product.save()

                    # 4. Asynchronous tracking coupon counter execution
                    if order.coupon_applied:
                        Coupon.objects.filter(code=order.coupon_applied).update(
                            times_used=models.F('times_used') + 1
                        )
                        
    except (ValueError, Order.DoesNotExist) as e:
        # Always return 200 OK block to Paystack for handled/not-found issues 
        # so they cease firing duplicate retries at your Vercel logs
        return HttpResponse(status=200)

    return HttpResponse(status=200)

@login_required
def order_confirmation(request, order_id):
    """Validates the transaction status on final redirect landings."""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    reference = f"PRE-ORD-{order.id}"
    
    if order.payment_method == 'paystack' and not order.payment_status:
        url = f"https://api.paystack.co/transaction/verify/{reference}"
        headers = {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"}
        try:
            res = requests.get(url, headers=headers, timeout=5)
            if res.status_code == 200 and res.json().get('data', {}).get('status') == 'success':
                order.payment_status = True
                order.transaction_id = str(res.json()['data']['id'])
                order.status = 'Processing'
                order.save()
                
                if order.coupon_applied:
                    Coupon.objects.filter(code=order.coupon_applied).update(times_used=models.F('times_used') + 1)
        except requests.RequestException:
            pass

    return render(request, 'orders/order_confirmation.html', {'order': order})


@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user).prefetch_related('sub_orders__shop').order_by('-order_date')
    return render(request, 'orders/order_history.html', {'orders': orders})


# --- Address Book Management Actions ---

@login_required
def address_list(request):
    addresses = ShippingAddress.objects.filter(user=request.user).order_by('-is_default', '-id')
    return render(request, 'orders/address_list.html', {'addresses': addresses})


@login_required
def add_address(request):
    if request.method == 'POST':
        form = ShippingAddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            address.save()
            messages.success(request, "Address profile stored.")
            return redirect('orders:address_list')
        else:
            messages.error(request, "Invalid address input profiles.")
    else:
        form = ShippingAddressForm()
    return render(request, 'orders/address_form.html', {'form': form, 'form_title': 'Add New Delivery Address'})


@login_required
def edit_address(request, address_id):
    address = get_object_or_404(ShippingAddress, id=address_id, user=request.user)
    if request.method == 'POST':
        form = ShippingAddressForm(request.POST, instance=address)
        if form.is_valid():
            form.save()
            messages.success(request, "Address configuration altered.")
            return redirect('orders:address_list')
    else:
        form = ShippingAddressForm(instance=address)
    return render(request, 'orders/address_form.html', {'form': form, 'form_title': 'Edit Delivery Address'})


@login_required
@require_POST
def delete_address(request, address_id):
    address = get_object_or_404(ShippingAddress, id=address_id, user=request.user)
    address.delete()
    messages.info(request, "Address profile removed cleanly.")
    return redirect('orders:address_list')


@login_required
@require_POST
def set_default_address(request, address_id):
    address = get_object_or_404(ShippingAddress, id=address_id, user=request.user)
    address.is_default = True
    address.save()
    messages.success(request, "Default profile address configuration shifted.")
    return redirect('orders:address_list')