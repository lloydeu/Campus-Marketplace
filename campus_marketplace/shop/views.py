from django.shortcuts import render, redirect, get_object_or_404
from .models import Product, Category, CartItem, Order, OrderItem, Profile
from django.http import HttpResponse
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from .forms import UserRegisterForm, ProfileForm, ProductForm
from django.contrib import messages



def homepage(request):
    categories = Category.objects.all()
    latest = Product.objects.order_by('-created_at')[:6]
    return render(request, "shop/index.html", {
        "categories": categories,
        "latest": latest
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
    cart_items = CartItem.objects.filter(user=request.user)
    total = sum(item.line_total() for item in cart_items)
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

@login_required
def checkout(request):
    cart_items = CartItem.objects.filter(user=request.user)
    if request.method == "POST":
        order = Order.objects.create(user=request.user, total=sum(item.line_total() for item in cart_items))
        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price_each=item.product.price
            )
        cart_items.delete()  # clear cart
        return render(request, "shop/checkout_success.html", {"order": order})
    return render(request, "shop/checkout.html", {"cart_items": cart_items})

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
    if request.method == "POST":
        form = UserRegisterForm(request.POST)
        profile_form = ProfileForm(request.POST)
        if form.is_valid() and profile_form.is_valid():
            user = form.save()
            profile = profile_form.save(commit=False)
            profile.user = user
            profile.save()
            login(request, user)
            return redirect("homepage")
    else:
        form = UserRegisterForm()
        profile_form = ProfileForm()
    return render(request, "shop/register.html", {"form": form, "profile_form": profile_form})

def login_view(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect("homepage")
    else:
        form = AuthenticationForm()
    return render(request, "shop/login.html", {"form": form})

def logout_view(request):
    logout(request)
    return redirect("homepage")

@login_required
def profile_view(request):
        profile, created = Profile.objects.get_or_create(user=request.user)
        return render(request, "shop/profile.html", {"profile": profile})
