from django.shortcuts import render, redirect, get_object_or_404
from .models import Product, Category, CartItem, Order, OrderItem, Profile, Message, ShippingAddress
from django.http import HttpResponse
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm
from django.contrib.auth.decorators import login_required
from .forms import UserRegisterForm, ProfileForm, ProductForm
from django.contrib import messages
from django.urls import reverse_lazy
from django.contrib.auth.views import PasswordResetView, LoginView
from django.views.decorators.http import require_http_methods
from django.db.models import Q, Sum, F, ExpressionWrapper, DecimalField
from django.shortcuts import render
from django.http import JsonResponse
from campus_marketplace.services.lalamove_service import get_lalamove_quotation, create_lalamove_order
import json, requests, base64, time
from django.core.serializers import serialize
from django.views.decorators.csrf import csrf_exempt



def homepage(request):
    categories = Category.objects.all()
    latest = Product.objects.order_by('-created_at')[:6]

    for category in categories:

        category.length = len((Product.objects.all().filter(category=category)))
        if category.length > 1:
            category.plural = True

           
    return render(request, "shop/index.html", {
        "categories": categories,
        "latest": latest,
    })

def product_list(request):
    query = request.GET.get("q")
    category_slug = request.GET.get("category")
    products = Product.objects.all()
    if query:
        products = products.filter(name__icontains=query)
    if category_slug:
        products = products.filter(category__slug=category_slug)
    categories = Category.objects.all()
    return render(request, "shop/product_list.html", {
        "products": products,
        "categories": categories
    })

@login_required
def cart_view(request):
    """Display user's shopping cart"""
    cart_items = CartItem.objects.filter(user=request.user)
    total = sum(float(item.line_total()) for item in cart_items)
    return render(request, "shop/cart.html", {"cart_items": cart_items, "total": total})


def add_to_cart(request, product_id):
    if not request.user.is_authenticated:
        return redirect('login')
     
    product = get_object_or_404(Product, id=product_id)
    cart_item, created = CartItem.objects.get_or_create(user=request.user, product=product, defaults={'quantity': 1})
    if not created:
        cart_item.quantity += 1
    cart_item.save()
    messages.success(request, f"{product.name} added to cart!")
    return redirect("cart")


def product_detail(request, product_id):
    """Display detailed information about a single product"""
    # Get the product or show 404 if not found
    product = get_object_or_404(Product, id=product_id)
    
    # Get related products (same category, exclude current product)
    related_products = Product.objects.filter(
        category=product.category
    ).exclude(id=product_id)[:4]
    
    # Get seller info
    seller = product.seller
    seller_products_count = Product.objects.filter(seller=seller).count()
    
    # Check if user has this in cart
    in_cart = False
    if request.user.is_authenticated:
        in_cart = CartItem.objects.filter(
            user=request.user, 
            product=product
        ).exists()
    
    context = {
        'product': product,
        'related_products': related_products,
        'seller': seller,
        'seller_products_count': seller_products_count,
        'in_cart': in_cart,
    }
    
    return render(request, 'shop/product_detail.html', context)

@login_required(login_url='login')
def cart_view(request):
    """Display user's shopping cart"""
    cart_items = CartItem.objects.filter(user=request.user)
    user_addresses = ShippingAddress.objects.filter(user=request.user)

    addresses_json = serialize('json', user_addresses)
    
    # 2. Convert the JSON string back into a Python list of dictionaries
    #    (This helps clean up the structure, removing model/pk info)
    addresses_list = json.loads(addresses_json)
    
    # 3. Simplify the list to just the necessary fields for JavaScript
    clean_addresses = [
        item['fields'] for item in addresses_list
    ]
    
    # Calculate totals
    subtotal = sum(float(item.line_total()) for item in cart_items)
    tax = subtotal * 0.05 
    
    total = subtotal + tax 
    
    context = {
        'cart_items': cart_items,
        'cart_subtotal': f"{subtotal:.2f}",
        'tax': f"{tax:.2f}",
        'cart_total': f"{total:.2f}",
        'user_addresses': user_addresses,
        'clean_addresses': clean_addresses
    }
    return render(request, "shop/cart.html", context)


def add_to_cart(request, product_id):
    """Add product to cart"""
    if not request.user.is_authenticated:
        return redirect('login')
    
    product = get_object_or_404(Product, id=product_id)
    
    # Check if product already in cart
    cart_item, created = CartItem.objects.get_or_create(
        user=request.user,
        product=product,
        defaults={'quantity': 1, 'shipping_method': 'P'}  # Default to Standard Shipping
    )
    
    # If already in cart, increase quantity
    if not created:
        cart_item.quantity += 1
        cart_item.save()
    
    messages.success(request, f"{product.name} added to cart!")
    return redirect("cart")


@login_required(login_url='login')
def update_cart(request, item_id):
    """Update cart item quantity"""
    item = get_object_or_404(CartItem, id=item_id, user=request.user)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        quantity = int(request.POST.get('quantity', 1))
        
        if action == 'increase':
            item.quantity += 1
        elif action == 'decrease' and item.quantity > 1:
            item.quantity -= 1
        else:
            item.quantity = max(1, quantity)  # Ensure minimum 1
        
        item.save()
        messages.success(request, 'Cart updated!')
    
    return redirect('cart')


@login_required(login_url='login')
def remove_from_cart(request, item_id):
    """Remove item from cart"""
    item = get_object_or_404(CartItem, id=item_id, user=request.user)
    product_name = item.product.name
    item.delete()
    messages.success(request, f'{product_name} removed from cart!')
    return redirect('cart')


@login_required(login_url='login')
def checkout(request):
    """Checkout page - create order from cart"""
    cart_items = CartItem.objects.filter(user=request.user)
    
    # Check if cart is empty
    if not cart_items.exists():
        messages.warning(request, 'Your cart is empty!')
        return redirect('cart')
    
    if request.method == 'POST':
        # Calculate totals
        total_amount = sum(float(item.line_total()) for item in cart_items)
        tax = total_amount * 0.05
        shipping = 50.00
        final_total = total_amount + tax + shipping
        
        # Create order
        order = Order.objects.create(
            user=request.user,
            total=final_total,
            status='pending'
        )
        
        # Create order items and update product stock
        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price_each=item.product.price
            )
            
            # Update product stock
            product = item.product
            product.stock -= item.quantity
            product.save()
            
            # Update seller total sales
            seller_profile = product.seller.profile
            seller_profile.total_sales += item.quantity
            seller_profile.save()
        
        # Clear cart
        cart_items.delete()
        
        messages.success(request, 'Order placed successfully!')
        return render(request, 'shop/checkout_success.html', {'order': order})
    
    # GET request - show checkout page
    cart_items = CartItem.objects.filter(user=request.user)
    
    subtotal = sum(float(item.line_total()) for item in cart_items)
    tax = subtotal * 0.05
    shipping = 50.00
    total = subtotal + tax + shipping
    
    context = {
        'cart_items': cart_items,
        'subtotal': f"{subtotal:.2f}",
        'tax': f"{tax:.2f}",
        'shipping': f"{shipping:.2f}",
        'total': f"{total:.2f}",
    }
    
    return render(request, 'shop/checkout.html', context)

@login_required
def add_listing(request):
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.seller = request.user
            product.save()
            return redirect("homepage")
    else:
        form = ProductForm()
    return render(request, "shop/add_listing.html", {"form": form})

def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, 'Account created successfully! Please log in.')
            return redirect('login')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserRegisterForm()
    
    return render(request, 'shop/register.html', {'form': form})

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect

class CustomLoginView(LoginView):
   
    template_name = 'shop/login.html'
    redirect_authenticated_user = True
    
    def form_valid(self, form):
        user = form.get_user()
        login(self.request, user)
        
        # Remember Me: Set session to expire in 30 days
        if self.request.POST.get('remember_me'):
            self.request.session.set_expiry(30 * 24 * 60 * 60)  # 30 days
        else:
            self.request.session.set_expiry(0)  # Browser session
        
        return super().form_valid(form)

class CustomPasswordResetView(PasswordResetView):
    """Handle password reset request"""
    form_class = PasswordResetForm
    template_name = 'shop/forgot_password.html'
    email_template_name = 'shop/password_reset_email.txt'
    success_url = reverse_lazy('password_reset_done')


def logout_view(request):
    logout(request)
    return redirect("homepage")

@login_required
def profile_view(request):
        profile, created = Profile.objects.get_or_create(user=request.user)
        return render(request, "shop/profile.html", {"profile": profile})

@login_required(login_url='login')
def edit_profile(request):
    profile = request.user.profile
    
    if request.method == 'POST':
        user_form = UserRegisterForm(request.POST, instance=request.user)
        profile_form = ProfileForm(request.POST, request.FILES, instance=profile)
        
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        user_form = UserRegisterForm(instance=request.user)
        profile_form = ProfileForm(instance=profile)
    
    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'profile': profile,
    }
    return render(request, 'shop/edit_profile.html', context)


@login_required(login_url='login')
@require_http_methods(["GET", "POST"])
def become_seller(request):
    """Allow user to become a seller"""
    profile = request.user.profile
    
    # If already a seller
    if profile.is_seller:
        messages.info(request, 'You are already a seller!')
        return redirect('profile')
    
    if request.method == 'POST':
        shop_name = request.POST.get('shop_name')
        shop_description = request.POST.get('shop_description')
        
        # Validation
        if not shop_name or len(shop_name.strip()) < 3:
            messages.error(request, 'Shop name must be at least 3 characters long.')
            return render(request, 'shop/become_seller.html', {'profile': profile})
        
        if not shop_description or len(shop_description.strip()) < 10:
            messages.error(request, 'Shop description must be at least 10 characters long.')
            return render(request, 'shop/become_seller.html', {'profile': profile})
        
        # Update profile
        profile.is_seller = True
        profile.shop_name = shop_name
        profile.shop_description = shop_description
        profile.save()
        
        messages.success(request, f'Welcome! {shop_name} is now active. You can start selling!')
        return redirect('profile')
    
    return render(request, 'shop/become_seller.html', {'profile': profile})

@login_required(login_url='login')
def seller_dashboard(request):
    """Main seller dashboard with statistics"""
    profile = request.user.profile
    
    # Check if user is a seller
    if not profile.is_seller:
        messages.error(request, 'You must be a seller to access this page.')
        return redirect('profile')
    
    # Get seller's products
    products = Product.objects.filter(seller=request.user)
    
    # Get seller's orders (from products they sold)
    orders = Order.objects.filter(
        items__product__seller=request.user
    ).distinct()
    
    # Calculate statistics
    total_products = products.count()
    total_sales = profile.total_sales
    average_rating = profile.seller_rating
    
    # Calculate total revenue
    order_items = OrderItem.objects.filter(product__seller=request.user)
    total_revenue = sum(float(item.line_total()) for item in order_items) if order_items else 0
    
    # Get recent orders
    recent_orders = orders.order_by('-placed_at')[:5]
    
    # Get low stock products
    low_stock_products = products.filter(stock__lte=5)
    
    context = {
        'profile': profile,
        'products': products,
        'orders': orders,
        'total_products': total_products,
        'total_sales': total_sales,
        'average_rating': average_rating,
        'total_revenue': f"{total_revenue:.2f}",
        'recent_orders': recent_orders,
        'low_stock_products': low_stock_products,
        'low_stock_count': low_stock_products.count(),
    }
    
    return render(request, 'shop/seller_dashboard.html', context)


@login_required(login_url='login')
def seller_products(request):
    """View all seller's products"""
    profile = request.user.profile
    
    if not profile.is_seller:
        messages.error(request, 'You must be a seller to access this page.')
        return redirect('profile')
    
    # Get filter parameters
    search_query = request.GET.get('q', '')
    sort_by = request.GET.get('sort', '-created_at')
    
    # Get seller's products
    products = Product.objects.filter(seller=request.user)
    
    # Search filter
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) | 
            Q(description__icontains=search_query)
        )
    
    # Sort
    products = products.order_by(sort_by)
    
    context = {
        'products': products,
        'search_query': search_query,
        'sort_by': sort_by,
        'profile': profile,
    }
    
    return render(request, 'shop/seller_products.html', context)


@login_required(login_url='login')
def seller_orders(request):
    """View all orders for seller's products"""
    profile = request.user.profile
    
    if not profile.is_seller:
        messages.error(request, 'You must be a seller to access this page.')
        return redirect('profile')
    
    # Get orders containing seller's products
    orders = Order.objects.filter(
        items__product__seller=request.user
    ).distinct().order_by('-placed_at')
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        orders = orders.filter(status=status_filter)
    
    context = {
        'orders': orders,
        'profile': profile,
        'status_filter': status_filter,
    }
    
    return render(request, 'shop/seller_orders.html', context)


@login_required(login_url='login')
def edit_product(request, product_id):
    """Edit seller's product"""
    product = get_object_or_404(Product, id=product_id)
    
    # Check ownership
    if product.seller != request.user:
        messages.error(request, 'You can only edit your own products!')
        return redirect('seller_products')
    
    if request.method == 'POST':
        from .forms import ProductForm
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, f'{product.name} updated successfully!')
            return redirect('seller_products')
    else:
        from .forms import ProductForm
        form = ProductForm(instance=product)
    
    context = {
        'form': form,
        'product': product,
    }
    
    return render(request, 'shop/edit_product.html', context)


@login_required(login_url='login')
def delete_product(request, product_id):
    """Delete seller's product"""
    product = get_object_or_404(Product, id=product_id)
    
    # Check ownership
    if product.seller != request.user:
        messages.error(request, 'You can only delete your own products!')
        return redirect('seller_products')
    
    if request.method == 'POST':
        product_name = product.name
        product.delete()
        messages.success(request, f'{product_name} has been deleted!')
        return redirect('seller_products')
    
    context = {
        'product': product,
    }
    
    return render(request, 'shop/confirm_delete_product.html', context)


@login_required(login_url='login')
def update_order_status(request, order_id):
    """Update order status"""
    order = get_object_or_404(Order, id=order_id)
    
    # Check if seller has products in this order
    has_product = order.items.filter(product__seller=request.user).exists()
    if not has_product:
        messages.error(request, 'You cannot update this order!')
        return redirect('seller_orders')
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        
        # Validate status
        valid_statuses = ['pending', 'confirmed', 'shipped', 'delivered', 'cancelled']
        if new_status in valid_statuses:
            order.status = new_status
            order.save()
            messages.success(request, f'Order status updated to {new_status}!')
        else:
            messages.error(request, 'Invalid status!')
    
    return redirect('seller_orders')


@login_required(login_url='login')
def seller_analytics(request):
    """Seller analytics and reports"""
    profile = request.user.profile
    
    if not profile.is_seller:
        messages.error(request, 'You must be a seller to access this page.')
        return redirect('profile')
    
    # Get time period filter
    time_period = request.GET.get('period', '30')  # 7, 30, 90 days
    
    from datetime import datetime, timedelta
    
    # Calculate date range
    if time_period == '7':
        start_date = datetime.now() - timedelta(days=7)
    elif time_period == '90':
        start_date = datetime.now() - timedelta(days=90)
    else:
        start_date = datetime.now() - timedelta(days=30)
    
    # Get seller's orders in time period
    orders = Order.objects.filter(
        items__product__seller=request.user,
        placed_at__gte=start_date
    ).distinct()
    
    # Calculate metrics
    total_orders = orders.count()
    total_revenue = sum(float(o.total) for o in orders) if orders else 0
    
    # Orders by status
    pending_orders = orders.filter(status='pending').count()
    shipped_orders = orders.filter(status='shipped').count()
    delivered_orders = orders.filter(status='delivered').count()
    
    # Top products
    top_products = OrderItem.objects.filter(
        product__seller=request.user,
        order__placed_at__gte=start_date
    ).values('product__name').annotate(
        total_sold=Sum('quantity'),
        revenue=Sum('price_each')
    ).order_by('-total_sold')[:5]
    
    context = {
        'profile': profile,
        'time_period': time_period,
        'total_orders': total_orders,
        'total_revenue': f"{total_revenue:.2f}",
        'pending_orders': pending_orders,
        'shipped_orders': shipped_orders,
        'delivered_orders': delivered_orders,
        'top_products': top_products,
    }
    
    return render(request, 'shop/seller_analytics.html', context)


@login_required(login_url='login')
def seller_profile_settings(request):
    """Edit seller profile and shop settings"""
    profile = request.user.profile
    
    if not profile.is_seller:
        messages.error(request, 'You must be a seller to access this page.')
        return redirect('profile')
    
    if request.method == 'POST':
        from .forms import ProfileForm
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Shop settings updated successfully!')
            return redirect('seller_dashboard')
    else:
        from .forms import ProfileForm
        form = ProfileForm(instance=profile)
    
    context = {
        'form': form,
        'profile': profile,
    }
    
    return render(request, 'shop/seller_profile_settings.html', context)

@login_required(login_url='login')
def contact_seller(request, product_id):
    """Contact seller about a product"""
    product = get_object_or_404(Product, id=product_id)
    seller = product.seller
    
    # Prevent user from messaging themselves
    if request.user == seller:
        messages.error(request, 'You cannot message yourself!')
        return redirect('product_detail', product_id=product_id)
    
    if request.method == 'POST':
        subject = request.POST.get('subject')
        message_text = request.POST.get('message')
        
        # Validation
        if not subject or len(subject.strip()) < 3:
            messages.error(request, 'Subject must be at least 3 characters.')
            return render(request, 'shop/contact_seller.html', {'product': product, 'seller': seller})
        
        if not message_text or len(message_text.strip()) < 10:
            messages.error(request, 'Message must be at least 10 characters.')
            return render(request, 'shop/contact_seller.html', {'product': product, 'seller': seller})
        
        # Create message
        Message.objects.create(
            sender=request.user,
            recipient=seller,
            product=product,
            subject=subject,
            message=message_text
        )
        
        messages.success(request, f'Message sent to {seller.username}!')
        return redirect('product_detail', product_id=product_id)
    
    context = {
        'product': product,
        'seller': seller,
    }
    return render(request, 'shop/contact_seller.html', context)


@login_required(login_url='login')
def messages_inbox(request):
    """View all received messages"""
    messages_list = Message.objects.filter(recipient=request.user).order_by('-created_at')
    
    # Filter by read/unread
    filter_type = request.GET.get('filter', 'all')
    if filter_type == 'unread':
        messages_list = messages_list.filter(is_read=False)
    elif filter_type == 'read':
        messages_list = messages_list.filter(is_read=True)
    
    # Mark all as read when viewing
    unread_messages = Message.objects.filter(recipient=request.user, is_read=False)
    unread_messages.update(is_read=True)
    
    unread_count = Message.objects.filter(recipient=request.user, is_read=False).count()
    
    context = {
        'messages': messages_list,
        'filter_type': filter_type,
        'unread_count': unread_count,
    }
    
    return render(request, 'shop/messages_inbox.html', context)


@login_required(login_url='login')
def message_detail(request, message_id):
    """View single message"""
    message = get_object_or_404(Message, id=message_id)
    
    # Check if user is recipient
    if message.recipient != request.user:
        messages.error(request, 'You cannot view this message!')
        return redirect('messages_inbox')
    
    # Mark as read
    if not message.is_read:
        message.is_read = True
        message.save()
    
    context = {
        'message': message,
    }
    
    return render(request, 'shop/message_detail.html', context)


@login_required(login_url='login')
def reply_message(request, message_id):
    """Reply to a message"""
    original_message = get_object_or_404(Message, id=message_id)
    
    # Check if user is recipient
    if original_message.recipient != request.user:
        messages.error(request, 'You cannot reply to this message!')
        return redirect('messages_inbox')
    
    if request.method == 'POST':
        reply_text = request.POST.get('message')
        
        if not reply_text or len(reply_text.strip()) < 5:
            messages.error(request, 'Reply must be at least 5 characters.')
            return render(request, 'shop/reply_message.html', {'original_message': original_message})
        
        # Create reply message
        Message.objects.create(
            sender=request.user,
            recipient=original_message.sender,
            product=original_message.product,
            subject=f"Re: {original_message.subject}",
            message=reply_text
        )
        
        messages.success(request, 'Reply sent!')
        return redirect('messages_inbox')
    
    context = {
        'original_message': original_message,
    }
    
    return render(request, 'shop/reply_message.html', context)


@login_required(login_url='login')
def delete_message(request, message_id):
    """Delete a message"""
    message = get_object_or_404(Message, id=message_id)
    
    # Check if user is recipient
    if message.recipient != request.user:
        messages.error(request, 'You cannot delete this message!')
        return redirect('messages_inbox')
    
    if request.method == 'POST':
        message.delete()
        messages.success(request, 'Message deleted!')
        return redirect('messages_inbox')
    
    context = {
        'message': message,
    }
    
    return render(request, 'shop/confirm_delete_message.html', context)



def get_shipping_quote(request):
    if request.method == 'POST':
        try:
            import json
            from django.http import JsonResponse
            import requests # Assuming this is available

            # Assuming you get the order details from the frontend
            data = json.loads(request.body)
            
            # This is where we call the Lalamove Python function
            # ASSUMPTION: get_lalamove_quotation returns the raw Lalamove JSON response
            quote_response = get_lalamove_quotation(data) 
            

            quote_data = quote_response.get('data', {}) 
            price_breakdown = quote_data.get('priceBreakdown', {})
            print("Lalamove Quote Data:", price_breakdown)  # Debugging line
            
            return JsonResponse({
                "success": True,
           
                "fee": price_breakdown.get('total'), 
                "currency": price_breakdown.get('currency'),
                "quoteId": quote_data.get('quotationId')
            })
        except requests.exceptions.HTTPError as e:
            # Handle HTTP errors from the Lalamove API call
            return JsonResponse({"success": False, "error": str(e.response.text)}, status=e.response.status_code)
        except KeyError as e:
            # Handle the specific KeyError if a field is missing (e.g., if Lalamove returns an error response)
            return JsonResponse({"success": False, "error": f"Missing key in Lalamove response: {e}"}, status=500)
        except Exception as e:
            # Catch general exceptions (e.g., JSON decoding)
            return JsonResponse({"success": False, "error": str(e)}, status=400)
            
    return JsonResponse({"error": "Invalid request method"}, status=405)


@login_required(login_url='login')
def save_shipping_address(request):
    """Save user's shipping address"""
    if request.method == 'POST':
        try:
            import json
            data = json.loads(request.body)
            
            if ShippingAddress.objects.filter(
                user=request.user,
                address=data.get('address'),
                city=data.get('city'),
                province=data.get('province'),
                postal_code=data.get('postal_code')
            ).exists():
                return JsonResponse({
                    'success': False,
                    'error': 'This address already exists.'
                }, status=400)
            
            new_address = ShippingAddress.objects.create(
                
                user=request.user,
                full_name=data.get('full_name'),
                address=data.get('address'),
                city=data.get('city'),
                province=data.get('province'),
                postal_code=data.get('postal_code'),
                phone_number=data.get('phone_number')
                )
            
            return JsonResponse({
                'success': True,
                'message': 'Address saved successfully'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)

@login_required(login_url='login')
def delete_address(request, address_id):
    """Remove item from cart"""
    address = get_object_or_404(ShippingAddress, address_id=address_id, user=request.user)
    address.delete()
    messages.success(request, 'Address removed successfully!')
    return redirect('cart')

def get_xendit_auth_header():
    import base64
    from django.conf import settings

    auth_string = f"{settings.XENDIT_SECRET_KEY}:"
    encoded_auth = base64.b64encode(auth_string.encode()).decode()
    return f"Basic {encoded_auth}"
    
# --- New Helper Function for Base URL ---
def get_base_url(request):
    """Constructs the base URL (e.g., http://127.0.0.1:8000)"""
    return request.build_absolute_uri('/').strip('/')


@login_required(login_url='login')
def create_xendit_invoice(request):
    """
    Creates a Xendit Invoice (Payment Link) and redirects the user.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid method'}, status=405)

    try:
        data = json.loads(request.body)
        shipping_method = data.get('shipping_method')
        final_total = float(data.get('final_total', 0)) # Client-side total

    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'success': False, 'error': 'Invalid request data'}, status=400)


    # 1. SECURITY: Re-calculate total from the database
    user_cart_items = CartItem.objects.filter(user=request.user)
    if not user_cart_items.exists():
        return JsonResponse({'success': False, 'error': 'Cart is empty'}, status=400)

    cart_summary = user_cart_items.annotate(
        item_price=ExpressionWrapper(
            F('quantity') * F('product__price'), 
            output_field=DecimalField()
        )
    ).aggregate(cart_subtotal=Sum('item_price'))
    
    subtotal = cart_summary.get('cart_subtotal') or 0
    tax = subtotal * 0.05
    shipping_cost = 0 # You must retrieve the actual Lalamove cost here!
    if shipping_method == 'lalamove':
        # Retrieve the cost from session or calculate based on address/cart items
        # For testing, you must replace 50.00 with your actual retrieved shipping cost
        shipping_cost = 50.00
    
    server_calculated_total = subtotal + tax + shipping_cost
    
    # 2. Prepare Xendit Invoice Data
    order_id = f"ORDER-{request.user.id}-{int(time.time())}"
    
    # Xendit Sandbox Invoice Creation URL
    XENDIT_INVOICE_URL = "https://api.xendit.co/v2/invoices" 
    
    invoice_data = {
        "external_id": order_id, # Your unique order ID
        "amount": round(server_calculated_total, 2),
        "currency": "PHP",
        "description": f"TUP Marketplace Order #{order_id}",
        "payer_email": request.user.email,
        "customer": {
            "given_names": request.user.first_name,
            "surname": request.user.last_name,
            "email": request.user.email,
        },
        "success_redirect_url": get_base_url(request) + reverse_lazy('payment_status') + f"?order_id={order_id}",
        "failure_redirect_url": get_base_url(request) + reverse_lazy('payment_status') + f"?order_id={order_id}&status=failed",
        "callback_url": get_base_url(request) + reverse_lazy('webhook_listener'), # Secure, server-to-server confirmation
    }
    
    # 3. Call Xendit API
    try:
        response = requests.post(
            XENDIT_INVOICE_URL,
            headers={
                "Authorization": get_xendit_auth_header(),
                "Content-Type": "application/json"
            },
            data=json.dumps(invoice_data)
        )
        response.raise_for_status() # Raise exception for bad status codes
        
        payment_info = response.json()
        
        # IMPORTANT: Create your PENDING Order object here, using 'order_id' as the reference
        # Order.objects.create(reference_number=order_id, user=request.user, status='PENDING', ...)

        return JsonResponse({
            'success': True,
            'redirect_url': payment_info['invoice_url'] # Xendit's hosted payment page URL
        })

    except requests.exceptions.RequestException as e:
        print(f"Xendit API Error: {e.response.text if e.response is not None else str(e)}")
        return JsonResponse({'success': False, 'error': 'Payment gateway initialization failed.'}, status=500)

@csrf_exempt
def webhook_listener(request):
    """
    Receives secure payment confirmation from Xendit.
    """
    if request.method != 'POST':
        return HttpResponse(status=405) # Only accept POST

    try:
        # 1. SECURITY: Verify Xendit Callback Token (CRITICAL)
        # Check Xendit documentation for the exact header name; often 'X-Callback-Token'.
        xendit_token = request.headers.get('X-Callback-Token')
        if xendit_token != 'YOUR_WEBHOOK_VERIFICATION_TOKEN': # Replace with your token from Xendit settings
             return HttpResponse('Forbidden: Invalid Callback Token', status=403)
             
        # 2. Parse Data
        data = json.loads(request.body)
        
        external_id = data.get('external_id') # Your unique order ID
        status = data.get('status') # e.g., 'PAID', 'EXPIRED'

        # 3. Retrieve and Update Order
        # order = get_object_or_404(Order, reference_number=external_id)
        
        # Placeholder logic: Find your order and update its status
        if status == 'PAID':
            # if order.status != 'PAID':
                # order.status = 'PAID'
                # order.xendit_invoice_id = data.get('id') # Save the Xendit Invoice ID
                # order.save()
                
                # Clear the user's cart and perform inventory updates (CRITICAL)
                # CartItem.objects.filter(user=order.user).delete()
                
                # print(f"Order {external_id} paid successfully.")
                pass

        elif status in ['EXPIRED', 'FAILED', 'CANCELLED']:
            # order.status = status
            # order.save()
            # print(f"Order {external_id} failed with status: {status}.")
            pass
            
        # Xendit expects a 200 OK response to confirm successful receipt
        return HttpResponse('Webhook received', status=200)

    except Exception as e:
        # Log unexpected errors
        print(f"Error processing Xendit webhook: {e}")
        return HttpResponse('Internal Server Error', status=500)

@login_required(login_url='login')
def payment_status(request):
    """
    Handles user return from the Xendit payment gateway (redirect_url).
    The actual order confirmation happens in the webhook, but this shows a quick status.
    """
    order_id = request.GET.get('order_id')
    status_param = request.GET.get('status', 'success') # Default to success if not specified
    
    if status_param == 'failed':
        message = "Your payment failed or was cancelled. Please check your details and try again."
        is_success = False
    else:
        # Xendit sends the user back even if payment is pending (e.g., waiting for bank transfer)
        message = f"Thank you! We have received your payment request for Order #{order_id}. Your order status will be confirmed shortly via email once Xendit securely notifies us of the final payment success. You can check your order history for updates."
        is_success = True

    context = {
        'order_id': order_id,
        'message': message,
        'is_success': is_success
    }
    
    # Render a dedicated payment status HTML page
    return render(request, 'shop/payment_status.html', context)



        