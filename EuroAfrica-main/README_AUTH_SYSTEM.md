# Premium Luxury Django Authentication System

This package gives you a premium black-and-gold authentication flow for a luxury perfume ecommerce site using Django auth, session login, Django messages, and Google OAuth via `django-allauth`.

## Files included

- `accounts/models.py`
- `accounts/forms.py`
- `accounts/views.py`
- `accounts/urls.py`
- `accounts/backends.py`
- `accounts/adapters.py`
- `accounts/context_processors.py`
- `accounts/templates/accounts/login.html`
- `accounts/templates/accounts/signup.html`
- `accounts/templates/accounts/account.html`
- `accounts/templates/accounts/password_reset.html`
- `accounts/static/accounts/css/auth.css`
- `accounts/static/accounts/js/auth.js`

## 1. Install dependencies

```bash
pip install django django-allauth
```

## 2. Add apps to `settings.py`

```python
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "accounts",
]

SITE_ID = 1

AUTHENTICATION_BACKENDS = [
    "accounts.backends.EmailBackend",
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "accounts:account"
LOGOUT_REDIRECT_URL = "accounts:login"

ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_USER_MODEL_USERNAME_FIELD = "username"
ACCOUNT_EMAIL_VERIFICATION = "optional"
ACCOUNT_LOGOUT_ON_GET = False

ACCOUNT_ADAPTER = "accounts.adapters.LuxuryAccountAdapter"
SOCIALACCOUNT_ADAPTER = "accounts.adapters.LuxurySocialAccountAdapter"

SOCIALACCOUNT_LOGIN_ON_GET = True

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = "Maison de Parfum <noreply@example.com>"
```

## 3. Add middleware and templates config

```python
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

TEMPLATES[0]["DIRS"] = [BASE_DIR / "templates"]
TEMPLATES[0]["OPTIONS"]["context_processors"] += [
    "accounts.context_processors.auth_nav",
]
```

## 4. Add URLs

Project `urls.py`:

```python
from django.contrib import admin
from django.urls import include, path
from django.contrib.auth import views as auth_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls", namespace="accounts")),
    path("accounts/", include("allauth.urls")),
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="accounts/password_reset.html"
        ),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="accounts/password_reset.html"
        ),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="accounts/password_reset.html"
        ),
        name="password_reset_complete",
    ),
]
```

## 5. Run migrations

```bash
python manage.py makemigrations accounts
python manage.py migrate
```

## 6. Configure Google OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Create a project and open `APIs & Services > Credentials`.
3. Configure the OAuth consent screen.
4. Create an `OAuth 2.0 Client ID` for a web application.
5. Add authorized redirect URIs:
   - `http://127.0.0.1:8000/accounts/google/login/callback/`
   - `http://localhost:8000/accounts/google/login/callback/`
   - Your production domain callback, for example `https://yourdomain.com/accounts/google/login/callback/`
6. In Django admin, create a `SocialApp`:
   - Provider: Google
   - Name: Google
   - Client id: your Google client ID
   - Secret key: your Google client secret
   - Sites: attach your current site
7. Optional provider config in `settings.py`:

```python
SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "online"},
    }
}
```

Google sign-in will automatically create the user on first login and use the Google profile name and email.

## 7. Protect wishlist, checkout, and buy-now routes

### Wishlist views

If you want a hard protected view:

```python
from django.contrib.auth.decorators import login_required

@login_required(login_url="accounts:login")
def wishlist(request):
    ...
```

If you want the premium modal on a heart icon click:

```html
<a href="/wishlist/"
   class="wishlist-link"
   data-auth-modal-url="{% url 'accounts:auth_modal' %}?next=/wishlist/">
   Wishlist
</a>
```

The included JavaScript will open the premium modal for guests and allow direct access for signed-in users.

### Checkout and Buy Now

Use `login_required` plus `next`, or redirect guests through:

```python
from django.contrib.auth.decorators import login_required

@login_required(login_url="accounts:login")
def checkout(request):
    ...
```

For a buy-now button in templates:

```html
{% if request.user.is_authenticated %}
    <a href="/checkout/" class="luxury-primary-btn">Buy Now</a>
{% else %}
    <a href="{% url 'accounts:login' %}?next=/checkout/" class="luxury-primary-btn">
        Buy Now
    </a>
{% endif %}
```

In views, you can also show the luxury message before redirecting:

```python
from django.contrib import messages
from django.shortcuts import redirect

def buy_now_gate(request):
    if not request.user.is_authenticated:
        messages.info(request, "Sign in required to continue purchase.")
        return redirect(f"/accounts/login/?next={request.path}")
```

## 8. Navbar greeting

Use the reusable snippet:

```django
{% include "includes/navbar_account_snippet.html" %}
```

When signed out it shows `Login`.
When signed in it shows `Hello, Name` with:

- My Account
- Orders
- Wishlist
- Logout

## 9. Notes

- Login uses email as the auth identity.
- Internally, `username = email`.
- Password validation uses Django's built-in password validators.
- Messages are styled as luxury toast notifications.
- Forms include show/hide password, remember me, divider line, loading spinner, and mobile responsiveness.
- If your existing project already has order, address, or wishlist models, update the `related_name` access inside `account_view`.
