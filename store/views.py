from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.urls import reverse
from django.http import JsonResponse
from django.db.models import Q, Avg, Sum
from django.conf import settings
from django.contrib import messages
from django.db import models
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


import requests
import stripe
from decimal import Decimal

from store import models as store_models
from customer import models as customer_models
from vendor import models as vendor_models

from plugin.service_fee import calculate_service_fee
from plugin.tax_calculation import tax_calculation
stripe.api_key = settings.STRIPE_SECRET_KEY
from customer.models import Address



def index(request):
    products = store_models.Product.objects.filter(status="Published")

    context = {
        "products": products,
        

    }
    return render(request, "store/index.html", context)

def product_detail(request, slug):
    product = store_models.Product.objects.get(status="Published", slug=slug)
    related_products = store_models.Product.objects.filter(category=product.category).exclude(id=product.id)
    product_stock_range = range(1, product.stock + 1)
    context = {
        "product": product,
        "related_products": related_products    ,
        "product_stock_range": product_stock_range,
    }
    return render(request, "store/product_detail.html", context)

def add_to_cart(request):
    # Get parameters from the request (ID, color, size, quantity, cart_id)
    id = request.GET.get("id")
    qty = request.GET.get("qty")
    color = request.GET.get("color")
    size = request.GET.get("size")
    cart_id = request.GET.get("cart_id")
    
    request.session['cart_id'] = cart_id

    # Validate required fields
    if not id or not qty or not cart_id:
        return JsonResponse({"error": "No color or size selected"}, status=400)

    # Try to fetch the product, return an error if it doesn't exist
    try:
        product = store_models.Product.objects.get(status="Published", id=id)
    except store_models.Product.DoesNotExist:
        return JsonResponse({"error": "Product not found"}, status=404)

    # Check if the item is already in the cart
    existing_cart_item = store_models.Cart.objects.filter(cart_id=cart_id, product=product).first()

    # Check if quantity that user is adding exceed item stock qty
    if int(qty) > product.stock:
        return JsonResponse({"error": "Qty exceed current stock amount"}, status=404)

    # If the item is not in the cart, create a new cart entry
    if not existing_cart_item:
        cart = store_models.Cart()
        cart.product = product
        cart.qty = qty
        cart.price = product.price
        cart.color = color
        cart.size = size
        cart.sub_total = Decimal(product.price) * Decimal(qty)
        #cart.shipping = Decimal(product.shipping) * Decimal(qty)
        cart.shipping = Decimal(product.shipping) 
        cart.total = cart.sub_total + cart.shipping
        cart.user = request.user if request.user.is_authenticated else None
        cart.cart_id = cart_id
        cart.save()

        message = "Item added to cart"
    else:
        # If the item exists in the cart, update the existing entry
        existing_cart_item.color = color
        existing_cart_item.size = size
        existing_cart_item.qty = qty
        existing_cart_item.price = product.price
        existing_cart_item.sub_total = Decimal(product.price) * Decimal(qty)
        #existing_cart_item.shipping = Decimal(product.shipping) * Decimal(qty)
        existing_cart_item.shipping = Decimal(product.shipping) 
        existing_cart_item.total = existing_cart_item.sub_total +  existing_cart_item.shipping
        existing_cart_item.user = request.user if request.user.is_authenticated else None
        existing_cart_item.cart_id = cart_id
        existing_cart_item.save()

        message = "Cart updated"

    # Count the total number of items in the cart
    total_cart_items = store_models.Cart.objects.filter(cart_id=cart_id)
    cart_sub_total = store_models.Cart.objects.filter(cart_id=cart_id).aggregate(sub_total = models.Sum("sub_total"))['sub_total']

    # Return the response with the cart update message and total cart items
    return JsonResponse({
        "message": message ,
        "total_cart_items": total_cart_items.count(),
        "cart_sub_total": "{:,.2f}".format(cart_sub_total),
        "item_sub_total": "{:,.2f}".format(existing_cart_item.sub_total) if existing_cart_item else "{:,.2f}".format(cart.sub_total) 
    })


def cart(request):
    if "cart_id" in request.session:
        cart_id = request.session["cart_id"]

    else:
        cart_id = None
    items = store_models.Cart.objects.filter(Q(cart_id=cart_id) | Q(user=request.user) if request.user.is_authenticated else Q(cart_id=cart_id))
    cart_sub_total = store_models.Cart.objects.filter(Q(cart_id=cart_id) | Q(user=request.user) if request.user.is_authenticated else Q(cart_id=cart_id)).aggregate(sub_total = Sum("sub_total"))['sub_total']
    cart_shipping_total = items.aggregate(shipping=Sum("shipping"))['shipping'] or 0

    if request.user.is_authenticated:
        address = Address.objects.filter(user=request.user).first()
        country = address.country if address else "default_country"
    else:
        country = "default_country"  # Replace with a default country if needed

    cart_tax_total = tax_calculation(country, cart_sub_total)

    try:
        addresses = Address.objects.filter(user=request.user)        
    except:
        addresses = None

    if not items:
        messages.warning(request, "No items in cart")
        return redirect("store:index")
    context = {
        "items": items,
        "cart_sub_total": cart_sub_total,
        "cart_shipping_total": cart_shipping_total,
        "cart_tax_total": cart_tax_total,
        
        "addresses": addresses,
    }        

    return render(request, "store/cart.html", context)

def delete_cart_item(request):
    id = request.GET.get("id")
    item_id = request.GET.get("item_id")
    cart_id = request.GET.get("cart_id")

    if not id and not item_id and not cart_id:
        return JsonResponse({"error": "item or Product Id not found"}, status=400)
    
    try:
        product = store_models.Product.objects.get(status="Published", id=id)
    except store_models.Product.DoesNotExist:
        return JsonResponse({"error": "Product not found"}, status=404)
    item = store_models.Cart.objects.get(product=product, id=item_id)         
    item.delete()

    total_cart_items = store_models.Cart.objects.filter(Q(cart_id=cart_id) | Q(user=request.user))
    cart_sub_total = store_models.Cart.objects.filter(Q(cart_id=cart_id) | Q(user=request.user)).aggregate(sub_total = Sum("sub_total"))['sub_total']


    return JsonResponse({
        "message": "Item deleted",
        "total_cart_items": total_cart_items.count(),
        "cart_sub_total": "{:,.2f}".format(cart_sub_total) if cart_sub_total else 0.00
    })

def create_order(request):
    if request.method == "POST":
        address_id = request.POST.get("address")

        if not address_id:
            messages.warning(request, "Please select an address to continue")
            return redirect("store:cart")
        
        address = customer_models.Address.objects.filter(user=request.user, id=address_id).first()

        if 'cart_id' in request.session:
            cart_id = request.session['cart_id']
        else:
            cart_id = None

        items = store_models.Cart.objects.filter(cart_id=cart_id)
        cart_sub_total = store_models.Cart.objects.filter(cart_id=cart_id).aggregate(sub_total = models.Sum("sub_total"))['sub_total']    
        cart_shipping_total = store_models.Cart.objects.filter(cart_id=cart_id).aggregate(shipping =models.Sum("shipping"))["shipping"]

        order = store_models.Order()
        order.sub_total = cart_sub_total
        order.customer = request.user
        order.address = address
        order.shipping = cart_shipping_total   
        order.tax = tax_calculation(address.country, cart_sub_total)
        order.total = order.sub_total + order.shipping + Decimal(order.tax)
        order.service_fee = calculate_service_fee(order.total)
        order.total += order.service_fee
        order.initial_total = order.total
        order.save()


        for i in items:
            store_models.OrderItem.objects.create(
                order=order,
                product=i.product,
                qty=i.qty,
                color=i.color,
                size=i.size,
                price=i.price,
                sub_total=i.sub_total,
                shipping=i.shipping,
                tax=tax_calculation(address.country, i.sub_total),
                total=i.total,
                initial_total=i.total,
                vendor=i.product.vendor,
            )   

            order.vendors.add(i.product.vendor)


    return redirect("store:checkout", order.order_id)

def checkout(request, order_id):
    order = store_models.Order.objects.get(order_id=order_id)
    context = {
        "order": order,
        "paypal_client_id": settings.PAYPAL_CLIENT_ID,
        "stripe_public_key": settings.STRIPE_PUBLIC_KEY,
    }
    return render(request, "store/checkout.html", context )


def coupon_apply(request, order_id):
    try:    
        order = store_models.Order.objects.get(order_id=order_id)
        order_items = store_models.OrderItem.objects.filter(order=order)
    except store_models.Order.DoesNotExist:
        return redirect("store:cart")

    if request.method == "POST":
        coupon_code = request.POST.get("coupon_code")

        if not coupon_code:
            messages.error(request, "No coupon entered")        
            return redirect("store:checkout", order.order_id)
        
        try:
            coupon = store_models.Coupon.objects.get(code=coupon_code)
        except store_models.Coupon.DoesNotExist:
            messages.error(request, "Coupon does not exist")
            return redirect("store:checkout", order.order_id)

        if coupon in order.coupons.all():
            messages.error(request, "Coupon already activated")
            return redirect("store:checkout", order.order_id)
        
        else:
            total_discount = 0

            for item in order_items:
                if coupon.vendor == item.product.vendor and coupon not in item.coupon.all():
                    item_discount = item.total * coupon.discount / 100
                    total_discount += item_discount

                    item.coupon.add(coupon)
                    item.total -= item_discount
                    item.saved += item_discount
                    item.save()

            if total_discount > 0:
                order.coupons.add(coupon)
                order.total -= total_discount
                order.sub_total -= total_discount
                order.saved += total_discount
                order.save()

        messages.success(request, "Coupon activated")            
        return redirect("store:checkout", order.order_id)
def clear_cart_items(request):
    try:
        cart_id = request.session['cart_id']
        store_models.Cart.objects.filter(cart_id=cart_id).delete()
    except:
        pass
    return           


def get_paypal_access_token():
    token_url = 'https://api.sandbox.paypal.com/v1/oauth2/token'
    data = {'grant_type': 'client_credentials'}
    auth = (settings.PAYPAL_CLIENT_ID, settings.PAYPAL_SECRET_ID)
    response = requests.post(token_url, data=data, auth=auth)

    if response.status_code == 200:
        return response.json()['access_token']
    else:
        raise Exception(f'failed to get access token from Paypal. Status code: {response.status_code}')
    
def paypal_payment_verify(request, order_id):
    order = store_models.Order.objects.get(order_id=order_id) 

    transaction_id = request.GET.get("transaction_id")
    paypal_api_url = f'https://api-m.sandbox.paypal.com/v2/checkout/orders/{transaction_id}'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {get_paypal_access_token()}',
    }   
    response = requests.get(paypal_api_url, headers=headers)

    if response.status_code == 200:
        paypal_order_data = response.json()
        paypal_payment_status = paypal_order_data['status']
        payment_method = "PayPal"
        if paypal_payment_status == "COMPLETED":
            if order.payment_status == "Processing": 
                order.payment_status = "Paid"
                payment_method = request.GET.get("payment_method")
                order.payment_method = payment_method
                order.save() 
                clear_cart_items(request)
                return redirect(f"/payment_status/{order.order_id}/?payment_status=paid")    
    else:
        return redirect(f"/payment_status/{order.order_id}/?payment_status=failed")

def payment_status(request, order_id):
    order = store_models.Order.objects.get(order_id=order_id)
    payment_status = request.GET.get("payment_status")
    context = {
        "order": order,
        "payment_status": payment_status
    }
    return render(request, "store/payment_status.html", context )   


@csrf_exempt
def stripe_payment(request, order_id):
    order = store_models.Order.objects.get(order_id=order_id)
    stripe.api_key = settings.STRIPE_SECRET_KEY


    checkout_session = stripe.checkout.Session.create(
        customer_email = order.address.email,
        payment_method_types = ['card'],
        line_items = [
            {
                'price_data': {
                    'currency': 'USD',
                    'product_data': {
                        'name': order.address.full_name
                    },
                    'unit_amount': int(order.total * 100)
                },
                'quantity': 1

            }
        ],
        mode = 'payment',
        success_url = request.build_absolute_uri(reverse("store:stripe_payment_verify", args=[order.order_id])) + "?session_id={CHECKOUT_SESSION_ID}" + "&payment_method=Stripe",
        cancel_url = request.build_absolute_uri(reverse("store:stripe_payment_verify", args=[order.order_id]))
    )
    print("checkout session", checkout_session)
    return JsonResponse({"sessionId": checkout_session.id})

def stripe_payment_verify(request, order_id):
    order = store_models.Order.objects.get(order_id=order_id)
    

    session_id = request.GET.get("session_id")
    session = stripe.checkout.Session.retrieve(session_id)
    payment_method = "Stripe"
    if session.payment_status == "paid":
        if order.payment_status == "Processing":
            order.payment_status = "Paid"
            payment_method = request.GET.get("payment_method")
            order.payment_method = payment_method
            order.save()
            clear_cart_items(request)

            # Send Email to Customer
            customer_models.Notifications.objects.create(type="New Order", user=request.user)
            customer_merge_data = {
                'order': order,
                'order_items': order.order_items(),
            }
            subject = f"New Order!"
            text_body = render_to_string("email/order/customer/customer_new_order.txt", customer_merge_data)
            html_body = render_to_string("email/order/customer/customer_new_order.html", customer_merge_data)

            msg = EmailMultiAlternatives(
                subject=subject, from_email=settings.FROM_EMAIL,
                to=[order.address.email], body=text_body
            )

            msg.attach_alternative(html_body, "text/html")
            msg.send()

            
            # Send Order Emails to Vendors:
            for item in order.order_items():
                vendor_merge_data = {
                    'item': item,
                }

                subject = f"New Sale!"
                text_body = render_to_string("email/order/vendor/vendor_new_order.txt", vendor_merge_data)
                html_body = render_to_string("email/order/vendor/vendor_new_order.html", vendor_merge_data)
            try:
                msg = EmailMultiAlternatives(
                    subject=subject, from_email=settings.FROM_EMAIL,
                    to=[item.vendor.email], body=text_body
                )

                msg.attach_alternative(html_body, "text/html")
                msg.send()
                print(f"Email Sent to {item.vendor.email}")
            except Exception as e:
                print(f"Error sending email to {item.vendor.email}: {e}")
               # vendor_models.Notifications.objects.create(type="New Order", user=item.vendor, order=item)
            # Send InApp Notification

            # Send Email to Vendor

            return redirect(f"/payment_status/{order.order_id}/?payment_status=paid")
    return redirect(f"/payment_status/{order.order_id}/?payment_status=failed")










# def add_to_cart(request):
#     # Get parameters from the request (ID, color, size, quantity, cart_id) 
#     id = request.GET.get("id")
#     qty = request.GET.get("qty")
#     color = request.GET.get("color")
#     size = request.GET.get("size")
#     cart_id = request.GET.get("cart_id")

#     request.session['cart_id'] = cart_id

#     # Validate required fields
#     if not id or not qty or not cart_id:
#         return JsonResponse({"error": "No color or size selected"}, status=400)

#     try:
#         product = store_models.Product.objects.get(status="published", id=id)
#     except store_models.Product.DoesNotExist:
#         return JsonResponse({"error": "Product not found"}, status=404)
    
#     # Check if the item is already in the cart
#     existing_cart_item = store_models.Cart.objects.filter(cart_id=cart_id, product=product).first()
    
#     # Check if quantity that user is adding exceed item stock qty
#     if int(qty) > product.stock:
#         return JsonResponse({"error": "Qty exceed current stock amount"}, status=404)    
      
#     # If the item is not in the cart, create a new cart entry
#     if not existing_cart_item:
#         cart = store_models.Cart()
#         cart.product = product
#         cart.qty = qty
#         cart.price = product.price
#         cart.color = color
#         cart.size = size
#         cart.sub_total = Decimal(product.price) * Decimal(qty)
#         cart.shipping = Decimal(product.shipping) * Decimal(qty)
#         cart.total = cart.sub_total + cart.shipping
#         cart.user = request.user if request.user.is_authenticated else None
#         cart.cart_id = cart_id
#         cart.save()

#         message = "Item added to cart"
#     else:
#         # If the item exists in the cart, update the existing entry
#         #existing_cart_item.product = product
#         existing_cart_item.qty = qty
#         existing_cart_item.price = product.price
#         existing_cart_item.color = color
#         existing_cart_item.size = size
#         existing_cart_item.sub_total = Decimal(product.price) * Decimal(qty)
#         existing_cart_item.shipping = Decimal(product.shipping) * Decimal(qty)
#         existing_cart_item.total = existing_cart_item.sub_total + existing_cart_item.shipping
#         existing_cart_item.user = request.user if request.user.is_authenticated else None
#         existing_cart_item.cart_id = cart_id
#         existing_cart_item.save() 

#         message = "Cart updated"  

#     total_cart_items = store_models.Cart.objects.filter(cart_id=cart_id)
#     cart_sub_total = store_models.Cart.objects.filter(Q(cart_id=cart_id) | Q(cart_id=cart_id)).aggregate(sub_total=Sum("sub_total")['sub_total'])

#     return JsonResponse({
#         "message": message,
#         "total_cart_items": total_cart_items.count(),
#         "cart_sub_total": "{:,.2f}".format(cart_sub_total),
#         "item_sub_total": "{:,.2f}".format(existing_cart_item.sub_total) if existing_cart_item else "{:,.2f}".format(cart.sub_total)
#     })