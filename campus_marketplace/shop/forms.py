from django import forms
from .models import Product
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Profile

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'description', 'price', 'stock', 'image', 'category']

from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from django import forms

User = get_user_model() 

class UserRegisterForm(UserCreationForm):
    # 1. Custom Fields: Override the default optional fields to make them required
    first_name = forms.CharField(
        max_length=150, 
        required=True, 
        label='First Name',
        widget=forms.TextInput(attrs={'placeholder': 'Enter your first name'})
    )
    last_name = forms.CharField(
        max_length=150, 
        required=True, 
        label='Last Name',
        widget=forms.TextInput(attrs={'placeholder': 'Enter your last name'})
    )
    # Ensure email is still required
    email = forms.EmailField(required=True) 

    class Meta:
        model = User
        # 2. Field List: Explicitly list all desired fields, including the new required ones.
        # Note: Password fields are automatically included by UserCreationForm logic.
        fields = ['username', 'email', 'first_name', 'last_name']

    def save(self, commit=True):
        # 3. Save Method: Use the parent's save method, which handles User creation
        user = super().save(commit=False)
        
        # 4. Set Names: Ensure the names from the form are set on the User object
        user.first_name = self.cleaned_data.get('first_name')
        user.last_name = self.cleaned_data.get('last_name')
        user.email = self.cleaned_data.get('email') # Re-set just in case
        
        if commit:
            user.save()
        
        return user

class ProfileForm(forms.ModelForm):
    GENDER_CHOICES = [
        ('', 'Select Gender'),
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
        ('N', 'Prefer not to say'),
    ]
    
    gender = forms.ChoiceField(choices=GENDER_CHOICES, required=False, widget=forms.Select(attrs={'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500'}))
    
    class Meta:
        model = Profile
        fields = ['avatar', 'bio', 'gender', 'date_of_birth', 'phone_number', 'alternate_phone', 'address', 'city', 'province', 'postal_code', 'country']
        widgets = {
            'avatar': forms.FileInput(attrs={'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500', 'accept': 'image/*'}),
            'bio': forms.Textarea(attrs={'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500', 'rows': 4}),
            'date_of_birth': forms.DateInput(attrs={'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500', 'type': 'date'}),
            'phone_number': forms.TextInput(attrs={'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500', 'placeholder': '+63 9XX XXX XXXX'}),
            'alternate_phone': forms.TextInput(attrs={'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500', 'placeholder': '+63 9XX XXX XXXX'}),
            'address': forms.Textarea(attrs={'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500', 'rows': 3}),
            'city': forms.TextInput(attrs={'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500'}),
            'province': forms.TextInput(attrs={'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500'}),
            'postal_code': forms.TextInput(attrs={'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500'}),
            'country': forms.TextInput(attrs={'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500'}),
        }

class CartForm(forms.Form):
    quantity = forms.IntegerField(min_value=1, widget=forms.NumberInput(attrs={'class': 'w-16 px-2 py-1 border border-gray-300 rounded text-center focus:outline-none focus:ring-2 focus:ring-red-500'}))
    shipping_method = forms.ChoiceField(choices=[('S', 'Standard Shipping'), ('P', 'Pick-up')], widget=forms.Select(attrs={'class': 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500'}))