from django.urls import path
from . import views

urlpatterns = [
    path('', views.homepage, name='homepage'),
    path('cart/', views.cart_view, name='cart'),
    path('add-to-cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('add-listing/', views.add_listing, name='add_listing'),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('products/', views.product_list, name='product_list'),
]
