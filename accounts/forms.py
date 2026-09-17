from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import UserProfile

User = get_user_model()


class LuxuryAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label="Email Address",
        widget=forms.EmailInput(
            attrs={
                "class": "lux-input",
                "placeholder": "name@example.com",
                "autocomplete": "email",
            }
        ),
    )
    password = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "lux-input lux-input-password",
                "placeholder": "Enter your password",
                "autocomplete": "current-password",
            }
        ),
    )
    remember_me = forms.BooleanField(required=False)

    error_messages = {
        "invalid_login": "Incorrect credentials.",
        "inactive": "Your account is currently unavailable.",
    }


class SignupForm(forms.Form):
    full_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "class": "lux-input",
                "placeholder": "Your full name",
                "autocomplete": "name",
            }
        ),
    )
    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={
                "class": "lux-input",
                "placeholder": "name@example.com",
                "autocomplete": "email",
            }
        )
    )
    phone_number = forms.CharField(
        max_length=25,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "lux-input",
                "placeholder": "+91 98765 43210",
                "autocomplete": "tel",
            }
        ),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "lux-input lux-input-password",
                "placeholder": "Create a password",
                "autocomplete": "new-password",
            }
        )
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "lux-input lux-input-password",
                "placeholder": "Confirm your password",
                "autocomplete": "new-password",
            }
        )
    )
    receive_offers = forms.BooleanField(required=False)
    agree_terms = forms.BooleanField(required=True)

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with this email already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password:
            validate_password(password)

        if password and confirm_password and password != confirm_password:
            self.add_error("confirm_password", "Passwords do not match.")

        if not cleaned_data.get("agree_terms"):
            self.add_error("agree_terms", "You must accept the Terms & Privacy Policy.")

        return cleaned_data

    def save(self):
        full_name = self.cleaned_data["full_name"].strip()
        name_parts = full_name.split(maxsplit=1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""
        email = self.cleaned_data["email"]

        user = User.objects.create_user(
            username=email,
            email=email,
            first_name=first_name,
            last_name=last_name,
            password=self.cleaned_data["password"],
        )

        profile = user.profile
        profile.phone_number = self.cleaned_data.get("phone_number", "").strip()
        profile.receive_offers = self.cleaned_data.get("receive_offers", False)
        profile.save()
        return user


class ProfileForm(forms.ModelForm):
    first_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={"class": "lux-input"}),
    )
    last_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={"class": "lux-input"}),
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"class": "lux-input", "readonly": "readonly"})
    )

    class Meta:
        model = UserProfile
        fields = ("phone_number", "receive_offers")
        widgets = {
            "phone_number": forms.TextInput(attrs={"class": "lux-input"}),
            "receive_offers": forms.CheckboxInput(attrs={"class": "lux-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user")
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields["first_name"].initial = user.first_name
        self.fields["last_name"].initial = user.last_name
        self.fields["email"].initial = user.email

    def save(self, commit=True):
        profile = super().save(commit=False)
        self.user.first_name = self.cleaned_data["first_name"].strip()
        self.user.last_name = self.cleaned_data["last_name"].strip()
        if commit:
            self.user.save(update_fields=["first_name", "last_name"])
            profile.user = self.user
            profile.save()
        return profile


class NewsletterPreferencesForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ("receive_offers",)
        widgets = {
            "receive_offers": forms.CheckboxInput(attrs={"class": "lux-check-input"}),
        }
