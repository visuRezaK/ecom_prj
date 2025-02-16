from django.contrib import admin
from store import models as store_models

class GalleryInline(admin.TabularInline):
    model = store_models.Gallery

class VariantInline(admin.TabularInline):
    model = store_models.Variant

class VariantItemInline(admin.TabularInline):
    model = store_models.VariantItem    

class CategoryAdmin(admin.ModelAdmin):
    list_display = ['title', 'image']
    list_editable = ['image']
    prepopulated_fields = {'slug': ('title',)}

class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'regular_price', 'stock', 'status', 'featured', 'vendor', 'date']
    search_fields = ['name', 'category__title'] 
    list_filter = ['status', 'featured', 'category']
    inlines = [GalleryInline, VariantInline]
    prepopulated_fields = {'slug': ('name',)}


class VariantAdmin(admin.ModelAdmin):
    list_display = ['product', 'name']
    search_fields = ['product__name', 'name'] 
    inlines = [VariantItemInline]

class VariantItemAdmin(admin.ModelAdmin):
    list_display = ['variant', 'title', 'content']
    search_fields = ['variant__name', 'title'] 

class GalleryAdmin(admin.ModelAdmin):
    list_display = ['product', 'gallery_id']
    search_fields = ['product__name', 'gallery_id'] 

class CartAdmin(admin.ModelAdmin):
    list_display = ['cart_id', 'product', 'user', 'qty', 'price', 'total', 'date']
    search_fields = ['cart_id', 'product__name', 'user__username'] 
    list_filter = ['date', 'product']
    


class CouponAdmin(admin.ModelAdmin):
    list_display = ['code', 'vendor', 'discount']
    search_fields = ['code', 'vendor__username'] 
    
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_id', 'customer', 'total', 'payment_status', 'order_status', 'payment_method', 'date']
    list_editable = ['payment_status', 'order_status', 'payment_method']
    search_fields = ['order_id', 'customer__username'] 
    list_filter = ['payment_status', 'order_status']
    

class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['item_id', 'order', 'product', 'qty', 'price', 'total']
    search_fields = ['item_id', 'order__order_id', 'product__name'] 
    list_filter = ['order__date']
    
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['user', 'product', 'rating', 'active', 'date']
    search_fields = ['user__username', 'product__name'] 
    list_filter = ['active', 'rating']

admin.site.register(store_models.Category, CategoryAdmin)            
admin.site.register(store_models.Product, ProductAdmin)            
admin.site.register(store_models.Variant, VariantAdmin)            
admin.site.register(store_models.VariantItem, VariantItemAdmin)            
admin.site.register(store_models.Gallery, GalleryAdmin)                     
admin.site.register(store_models.Cart, CartAdmin)            
admin.site.register(store_models.Coupon, CouponAdmin)            
admin.site.register(store_models.Order, OrderAdmin)            
admin.site.register(store_models.OrderItem, OrderItemAdmin)            
admin.site.register(store_models.Review, ReviewAdmin)            
