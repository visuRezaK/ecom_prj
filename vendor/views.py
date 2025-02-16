from unicodedata import category
from django.shortcuts import render, redirect
from django.db import models
from django.contrib.auth.decorators import login_required
from django.db.models.functions import TruncMonth
from django.contrib import messages
from django.db.models import Count, Avg
from django.contrib.auth.hashers import check_password
from django.http import JsonResponse

from plugin.paginate_queryset import paginate_queryset
from store import models as store_models
from vendor import models as vendor_models

def get_monthly_sales():
    monthly_sales = (
        store_models.OrderItem.objects
        .annotate(month=TruncMonth('date'))
        .values('month')
        .annotate(order_count = models.Count('id'))
        .order_by('month')
    )
    return monthly_sales

@login_required
def dashboard(request):
    products = store_models.Product.objects.filter(vendor=request.user)
    orders = store_models.Order.objects.filter(orderitem__product__vendor=request.user, payment_status="Paid").distinct()
    revenue = store_models.OrderItem.objects.filter(vendor=request.user).aggregate(total = models.Sum("total"))['total']
    notis = vendor_models.Notifications.objects.filter(user=request.user, seen=False)
    reviews = store_models.Review.objects.filter(product__vendor=request.user)
    rating = store_models.Review.objects.filter(product__vendor=request.user).aggregate(avg = models.Avg("rating"))['avg']
    monthly_sales = get_monthly_sales()

    context = {
        "products": products,
        "orders": orders,
        "revenue": revenue,
        "notis": notis,
        "reviews": reviews,
        "rating": rating,
        "monthly_sales": monthly_sales,
    }

    return render(request, "vendor/dashboard.html", context)    

@login_required
def products(request):
    product_list = store_models.Product.objects.filter(vendor=request.user)
    products = paginate_queryset(request, product_list, 6)
    context = {
        "products": products,
        "product_list": product_list,
    }
    return render(request, "vendor/products.html", context)

@login_required
def orders(request):
    orders_list = store_models.Order.objects.filter(orderitem__product__vendor=request.user, payment_status="Paid").distinct()
    orders = paginate_queryset(request, orders_list, 6)
    context = {
        "orders": orders,
        "orders_list": orders_list,
    }
    return render(request, "vendor/orders.html", context)

@login_required
def order_detail(request, order_id):
    order = store_models.Order.objects.get(orderitem__product__vendor=request.user, order_id=order_id, payment_status="Paid")
    context = {
        "order": order,
    }
    return render(request, "vendor/order_detail.html", context)  

@login_required
def order_item_detail(request, order_id, item_id):
    order = store_models.Order.objects.get(orderitem__product__vendor=request.user, order_id=order_id, payment_status="Paid")
    item = store_models.OrderItem.objects.get(order=order, id=item_id)
    context = {
        "order": order,
        "item": item,
    }
    return render(request, "vendor/order_item_detail.html", context)      

@login_required
def update_order_status(request, order_id):
    order = store_models.Order.objects.get(orderitem__product__vendor=request.user, order_id=order_id, payment_status="Paid")

    if request.method == "POST":
        order_status = request.POST.get("order_status")
        order.order_status = order_status
        order.save()

        messages.success(request, "Order status updated successfully")
        return redirect("vendor:order_detail", order_id=order.order_id)
    return redirect("vendor:order_detail", order_id=order.order_id)    

@login_required
def update_order_item_status(request, order_id, item_id):
    order = store_models.Order.objects.get(orderitem__product__vendor=request.user, order_id=order_id, payment_status="Paid")
    item = store_models.OrderItem.objects.get(order=order, id=item_id)

    if request.method == "POST":
        order_status = request.POST.get("order_status")
        shipping_service = request.POST.get("shipping_service")
        tracking_id = request.POST.get("tracking_id")

        item.order_status = order_status
        item.shipping_service = shipping_service
        item.tracking_id = tracking_id
        item.save()

        messages.success(request, "Item status updated successfully")
        return redirect("vendor:order_item_detail", order_id=order.order_id, item_id=item.id)
    return redirect("vendor:order_item_detail", order_id=order.order_id, item_id=item.id)

@login_required
def coupons(request):
    coupons_list = store_models.Coupon.objects.filter(vendor=request.user)
    coupons = paginate_queryset(request, coupons_list, 3)
    context = {
        "coupons": coupons,
        "coupons_list": coupons_list,
    }
    return render(request, "vendor/coupons.html", context)

@login_required
def update_coupon(request, id):
    coupon = store_models.Coupon.objects.get(vendor=request.user, id=id)

    if request.method == "POST":
       code = request.POST.get("coupon_code")
       coupon.code = code
       coupon.save()

    messages.success(request, "Coupon updated successfully")
    return redirect("vendor:coupons")
    

@login_required
def delete_coupon(request, id):
    coupon = store_models.Coupon.objects.get(vendor=request.user, id=id)
    coupon.delete()
    messages.success(request, "Coupon deleted successfully")
    return redirect("vendor:coupons")

@login_required
def create_coupon(request):
    if request.method == "POST":
        code = request.POST.get("coupon_code")
        discount = request.POST.get("coupon_discount")
        coupon = store_models.Coupon.objects.create(vendor=request.user, code=code, discount=discount)
        coupon.save()

    messages.success(request, "Coupon created successfully")
    return redirect("vendor:coupons")
    
@login_required
def reviews(request):
    reviews_list = store_models.Review.objects.filter(product__vendor=request.user)
    
    rating = request.GET.get("rating")
    date = request.GET.get("date")

    if rating:
        reviews_list = reviews_list.filter(rating=rating)

    if date:
        reviews_list = reviews_list.order_by(date)

    reviews = paginate_queryset(request, reviews_list, 3)

    context = {
        "reviews": reviews,
        "reviews_list": reviews_list,
    }
    return render(request, "vendor/reviews.html", context)    

@login_required
def update_reply(request, id):
    review = store_models.Review.objects.get(product__vendor=request.user, id=id)

    if request.method == "POST":
        reply = request.POST.get("reply")
        review.reply = reply
        review.save()

    messages.success(request, "Reply added successfully")
    return redirect("vendor:reviews")

@login_required
def notis(request):
    notis_list = vendor_models.Notifications.objects.filter(user=request.user, seen=False).order_by('-date')
    notis = paginate_queryset(request, notis_list, 3)
    context = {
        "notis": notis,
        "notis_list": notis_list,
    }
    return render(request, "vendor/notis.html", context)

@login_required
def mark_noti_seen(request, id):
    noti = vendor_models.Notifications.objects.get(user=request.user, id=id)
    noti.seen = True
    noti.save()
    messages.success(request, "Notification marked as seen")
    return redirect("vendor:notis")

@login_required
def profile(request):
    profile = request.user.profile

    if request.method == "POST":
        image = request.FILES.get("image")
        full_name = request.POST.get("full_name")
        mobile = request.POST.get("mobile")

        if image != None:
            profile.image = image

        profile.full_name = full_name
        profile.mobile = mobile

        request.user.save()
        profile.save()

        messages.success(request, "Profile updated successfully")    
        return redirect("vendor:profile")
    context = { 
        "profile": profile
    }
    return render(request, "vendor/profile.html", context)

@login_required
def change_password(request):
    if request.method == "POST":
        old_password = request.POST.get("old_password")
        new_password = request.POST.get("new_password")
        confirm_new_password = request.POST.get("confirm_new_password")

        if confirm_new_password != new_password:
            messages.error(request, "Confirmed Password and New password do not match")
            return redirect("vendor:change_password")
        
        if check_password(old_password, request.user.password):
            request.user.set_password(new_password)
            request.user.save()
            messages.success(request, "Password changed successfully")
            return redirect("vendor:profile")
        else:
            messages.error(request, "Old password is incorrect")
            return redirect("vendor:change_password")
    return render(request, "vendor/change_password.html")

@login_required
def create_product(request):
    categories = store_models.Category.objects.all()

    if request.method == "POST":
        image = request.FILES.get("image")
        name = request.POST.get("name")
        category_id = request.POST.get("category_id")
        price = request.POST.get("price")
        regular_price = request.POST.get("regular_price")
        shipping = request.POST.get("shipping")
        stock = request.POST.get("stock")
        description = request.POST.get("description")
        
        category = store_models.Category.objects.get(id=category_id)
        product = store_models.Product.objects.create(vendor=request.user, image=image, name=name, category_id=category_id, price=price, regular_price=regular_price, shipping=shipping, stock=stock, description=description)
        product.save()

        
        return redirect("vendor:update_product", product.id)
    context = {
        "categories": categories
    }
    return render(request, "vendor/create_product.html", context)

@login_required
def update_product(request, id):
    product = store_models.Product.objects.get(vendor=request.user, id=id)
    categories = store_models.Category.objects.all()

    if request.method == "POST":
        image = request.FILES.get("image")
        name = request.POST.get("name")
        category_id = request.POST.get("category_id")
        price = request.POST.get("price")
        regular_price = request.POST.get("regular_price")
        shipping = request.POST.get("shipping")
        stock = request.POST.get("stock")
        description = request.POST.get("description")
        category = store_models.Category.objects.get(id=category_id)

        product.name = name
        product.category = category
        product.price = price
        product.regular_price = regular_price
        product.shipping = shipping
        product.stock = stock
        product.description = description
        
        if image:
            product.image = image

        product.save()    

        variant_ids = request.POST.getlist("variant_id[]")
        variant_title = request.POST.getlist("variant_title[]")

        if variant_ids and variant_title:
            for i, variant_id in enumerate(variant_ids):
                variant_name = variant_title[i]
                if variant_id:
                    variant = store_models.Variant.objects.filter(id=variant_id).first()
                    if variant:
                        variant.name = variant_name
                        variant.save()
                else:
                    variant = store_models.Variant.objects.create(product=product, name=variant_name)

                item_ids = request.POST.getlist(f"item_id_{i}[]")       
                item_titles = request.POST.getlist(f"item_title_{i}[]")
                item_descriptions = request.POST.getlist(f"item_description_{i}[]")
                
                if item_ids and item_titles and item_descriptions:
                    for j in range(len(item_ids)):
                        item_id = item_ids[j]
                        item_title = item_titles[j]
                        item_description = item_descriptions[j]
                        if item_id:
                            variant_item = store_models.VariantItem.objects.filter(id=item_id).first()
                            if variant_item:
                                variant_item.title = item_title
                                variant_item.content = item_description
                                variant_item.save()
                        else:
                            store_models.VariantItem.objects.create(
                                variant=variant, 
                                title=item_title, 
                                content=item_description
                            )    

        for file_key, image_file in request.FILES.items():
            if file_key.startswith("image_"):
                store_models.Gallery.objects.create(product=product, image=image_file)

        messages.success(request, "Product updated successfully")
        return redirect("vendor:update_product", product.id)                

    context = { 
        "product": product,
        "categories": categories,
        "variants": store_models.Variant.objects.filter(product=product),
        "gallery_images": store_models.Gallery.objects.filter(product=product),
    }    

    return render(request, "vendor/update_product.html", context)

def delete_variants(request, product_id, variant_id):
    product = store_models.Product.objects.get(id=product_id)
    variants = store_models.Variant.objects.get(id=variant_id, product__vendor=request.user, product=product)
    variants.delete()
    return JsonResponse({"message": "Variant deleted successfully"})
   
def delete_variants_items(request, variant_id, item_id):
    variants = store_models.Variant.objects.get(id=variant_id)
    item = store_models.VariantItem.objects.get(id=item_id, variant=variants)
    item.delete()
    return JsonResponse({"message": "Variant Item deleted successfully"})   

def delete_product_image(request, product_id, image_id):
    product = store_models.Product.objects.get(id=product_id)
    image = store_models.Gallery.objects.get(id=image_id, product=product)
    image.delete()
    return JsonResponse({"message": "Product Image deleted successfully"})

@login_required
def delete_product(request, product_id):
    product = store_models.Product.objects.get(id=product_id, vendor=request.user)
    product.delete()
    messages.success(request, "Product deleted successfully")
    return redirect("vendor:products")
