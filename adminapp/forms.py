from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
import uuid

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True, help_text="Required. Enter a valid email address.")
    display_name = forms.CharField(max_length=150, required=True, help_text="Required. This will be your visible username.")

    class Meta:
        model = User
        fields = ("display_name", "email", "password1", "password2")

    def clean_email(self):
        email = self.cleaned_data.get("email").strip()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("This email address is already registered.")
        return email

    def clean_display_name(self):
        display_name = self.cleaned_data.get("display_name").strip()
        if not display_name:
            raise forms.ValidationError("Display name is required.")
        return display_name

    def save(self, commit=True):
        # Generate a unique username based on UUID
        user = super().save(commit=False)
        user.username = f"user_{uuid.uuid4().hex[:20]}"  # Unique username
        if commit:
            user.save()
            # Create Profile with display_name
            from .models import Profile
            Profile.objects.create(user=user, display_name=self.cleaned_data['display_name'])
        return user