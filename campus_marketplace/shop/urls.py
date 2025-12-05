from django.conf import settings
from django.urls import include, path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.homepage, name='homepage'),
    path('cart/', views.cart_view, name='cart'),
    path('add-to-cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    path('cart/', views.cart_view, name='cart'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/<int:item_id>/', views.update_cart, name='update_cart'),
    path('cart/remove/<int:item_id>/', views.remove_item, name='remove_item'),
    path('checkout/', views.checkout, name='checkout'),

    path('add-listing/', views.add_listing, name='add_listing'),
    path('register/', views.register, name='register'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('products/', views.product_list, name='product_list'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
 # Password Reset
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='shop/forgot_password.html'
    ), name='password_reset'),
    
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='shop/password_reset_done.html'
    ), name='password_reset_done'),
    
    path('password-reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='shop/password_reset_confirm.html'
    ), name='password_reset_confirm'),
    
    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='shop/password_reset_complete.html'
    ), name='password_reset_complete'),

    path('become-seller/', views.become_seller, name='become_seller'),
    path('seller-dashboard/', views.seller_dashboard, name='seller_dashboard'),
    
    # Seller products
    path('seller/products/', views.seller_products, name='seller_products'),
    path('seller/product/<int:product_id>/edit/', views.edit_product, name='edit_product'),
    path('seller/product/<int:product_id>/delete/', views.delete_product, name='delete_product'),
    
    # Seller orders
    path('seller/orders/', views.seller_orders, name='seller_orders'),
    path('seller/order/<int:order_id>/update-status/', views.update_order_status, name='update_order_status'),
    
    # Seller analytics
    path('seller/analytics/', views.seller_analytics, name='seller_analytics'),
    
    # Seller settings
    path('seller/settings/', views.seller_profile_settings, name='seller_profile_settings'),
    
    # Messaging
    path('product/<int:product_id>/contact-seller/', views.contact_seller, name='contact_seller'),
    path('messages/', views.messages_inbox, name='messages_inbox'),
    path('message/<int:message_id>/', views.message_detail, name='message_detail'),
    path('message/<int:message_id>/reply/', views.reply_message, name='reply_message'),
    path('message/<int:message_id>/delete/', views.delete_message, name='delete_message'),
    path('api/get-shipping-quote/', views.get_shipping_quote, name='get_shipping_quote'),
    path('api/save-shipping-address/', views.save_address, name='save_address'),
    path('delete-address/<int:address_id>/', views.delete_address, name='delete_address'),
    path('checkout/pay/', views.create_xendit_invoice, name='create_payment_intent'), # Renamed view function
    path('payment/status/', views.payment_status, name='payment_status'),
    path('payment/webhook/', views.webhook_listener, name='webhook_listener'),
   
]

if settings.DEBUG:
    urlpatterns += [
        path("__reload__/", include("django_browser_reload.urls")),
    ]
