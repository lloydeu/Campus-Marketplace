from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.validators import MinValueValidator, MaxValueValidator


class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    icon = models.CharField(max_length=50, default='📦')
    length = models.PositiveIntegerField(default=0)
    plural = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.name

class Product(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name='products')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class CartItem(models.Model):
    SHIPPING_METHOD_CHOICES = [
        ('S', 'Standard Shipping'), 
        ('P', 'Pickup'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="cart_items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    shipping_method = models.CharField(max_length=1, choices=SHIPPING_METHOD_CHOICES, blank=True, help_text="Shipping method for this item")

    

    def line_total(self):
        return self.product.price * self.quantity

    def __str__(self):
        return f"{self.quantity} × {self.product.name}"

class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="orders")
    external_id = models.CharField(max_length=150, blank=True, null=True, unique=True)
    placed_at = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    invoice_id = models.CharField(max_length=100, blank=True, null=True)
    payment_method = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return f"Order #{self.id} by {self.user.username}"

    class Meta:
        ordering = ['-placed_at']


class OrderItem(models.Model):

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price_each = models.DecimalField(max_digits=10, decimal_places=2)
   
    def line_total(self):
        return self.price_each * self.quantity

    def __str__(self):
        return f"{self.quantity} × {self.product.name}"
    
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator

class Profile(models.Model):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
        ('N', 'Prefer not to say'),
    ]
    
    # Basic Information
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, help_text="User profile picture")
    bio = models.TextField(max_length=500, blank=True, help_text="Short bio or about me")
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True, help_text="Gender")
    date_of_birth = models.DateField(blank=True, null=True, help_text="Date of birth")
    
    # Contact Information
    phone_number = models.CharField(max_length=20, blank=True, help_text="Phone number")
    alternate_phone = models.CharField(max_length=20, blank=True, help_text="Alternate phone number")
    
    # Address Information
    address = models.TextField(blank=True, help_text="Street address")
    city = models.CharField(max_length=100, blank=True, help_text="City")
    province = models.CharField(max_length=100, blank=True, help_text="Province/State")
    postal_code = models.CharField(max_length=20, blank=True, help_text="Postal code")
    country = models.CharField(max_length=100, default='Philippines', help_text="Country")
    
    # Seller Information
    is_seller = models.BooleanField(default=False, help_text="Is this user a seller?")
    shop_name = models.CharField(max_length=200, blank=True, help_text="Shop name (if seller)")
    shop_description = models.TextField(blank=True, help_text="Shop description (if seller)")
    shop_logo = models.ImageField(upload_to='shop_logos/', blank=True, null=True, help_text="Shop logo (if seller)")
    seller_rating = models.DecimalField(
        max_digits=3, 
        decimal_places=2, 
        default=0, 
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        help_text="Average seller rating (0-5)"
    )
    shop_phone_number = models.CharField(max_length=20, blank=True, null=True, help_text="Shop contact phone number")
    shop_alternate_phone = models.CharField(max_length=20, blank=True, null=True, help_text="Shop alternate contact phone number")
    
    # Shop location fields 
    shop_address = models.TextField(blank=True, help_text="Shop street address")
    shop_city = models.CharField(max_length=100, blank=True, help_text="Shop city")
    shop_province = models.CharField(max_length=100, blank=True, help_text="Shop province/state")
    shop_postal_code = models.CharField(max_length=20, blank=True, help_text="Shop postal code")
    shop_country = models.CharField(max_length=100, default='Philippines', help_text="Shop country")
    
    total_sales = models.PositiveIntegerField(default=0, help_text="Total number of sales")
    
    # Account Settings
    email_notifications = models.BooleanField(default=True, help_text="Receive email notifications")
    newsletter_subscription = models.BooleanField(default=False, help_text="Subscribe to newsletter")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login = models.DateTimeField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.user.username}'s profile"
    
    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'
        ordering = ['-created_at']

@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    else:
        # Only save if profile exists
        if hasattr(instance, "profile"):
            instance.profile.save()

class Message(models.Model):
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_messages')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='messages', null=True, blank=True)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Message from {self.sender.username} to {self.recipient.username}"
    
    class Meta:
        ordering = ['-created_at']

class ShippingAddress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shipping_addresses')
    address_id = models.AutoField(primary_key=True)
    full_name = models.CharField(max_length=200)
    address = models.TextField(blank=True, help_text="Street address")
    city = models.CharField(max_length=100, blank=True, help_text="City")
    province = models.CharField(max_length=100, blank=True, help_text="Province/State")
    postal_code = models.CharField(max_length=20, blank=True, help_text="Postal code")
    country = models.CharField(max_length=100, default='Philippines', help_text="Country")
    phone_number = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    
    
    class Meta:
        verbose_name = 'Shipping Address'
        verbose_name_plural = 'Shipping Addresses'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.full_name}, {self.address}, {self.city}"
    
