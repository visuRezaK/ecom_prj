from django.urls import path
from vendor import views

app_name = "vendor"

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("products/", views.products, name="products"),

    # Orders
    path("orders/", views.orders, name="orders"),
    path("order_detail/<int:order_id>/", views.order_detail, name="order_detail"),
    path("order_item_detail/<int:order_id>/<int:item_id>/", views.order_item_detail, name="order_item_detail"),
    path("update_order_status/<int:order_id>/", views.update_order_status, name="update_order_status"),
    path("update_order_item_status/<int:order_id>/<int:item_id>/", views.update_order_item_status, name="update_order_item_status"),

    # Coupons
    path("coupons/", views.coupons, name="coupons"),
    path("update_coupon/<int:id>/", views.update_coupon, name="update_coupon"),
    path("create_coupon/", views.create_coupon, name="create_coupon"),
    path("delete_coupon/<int:id>/", views.delete_coupon, name="delete_coupon"),

    # Reviews
    path("reviews/", views.reviews, name="reviews"),
    path("update_reply/<int:id>/", views.update_reply, name="update_reply"),

    # Notis
    path("notis/", views.notis, name="notis"),
    path("mark_noti_seen/<int:id>/", views.mark_noti_seen, name="mark_noti_seen"),

    # Settings
    path("profile/", views.profile, name="profile"),
    path("change_password/", views.change_password, name="change_password"),

    # Product management
    path("create_product/", views.create_product, name="create_product"),
    path("update_product/<int:id>/", views.update_product, name="update_product"),
    path("delete_variants/<int:product_id>/<int:variant_id>/", views.delete_variants, name="delete_variants"),
    path("delete_variants_items/<int:variant_id>/<int:item_id>/", views.delete_variants_items, name="delete_variants_items"),
    path("delete_product_image/<int:product_id>/<int:image_id>/", views.delete_product_image, name="delete_product_image"),
    path("delete_product/<int:product_id>/", views.delete_product, name="delete_product"),
    
   
    
]