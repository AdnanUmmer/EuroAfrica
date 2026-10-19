from urllib.parse import quote

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordResetView
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import (
    LuxuryAuthenticationForm,
    NewsletterPreferencesForm,
    ProfileForm,
    SignupForm,
)


User = get_user_model()


def _get_safe_redirect(request, default="accounts:account"):
    redirect_to = request.POST.get("next") or request.GET.get("next")
    if redirect_to and url_has_allowed_host_and_scheme(
        redirect_to,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect_to
    return reverse(default)


def _google_login_url(next_url):
    return f"{reverse('socialaccount_login', args=['google'])}?process=login&next={quote(next_url, safe='/?:=&')}"


def login_view(request):
    if request.user.is_authenticated:
        return redirect("accounts:account")

    form = LuxuryAuthenticationForm(request, data=request.POST or None)
    next_url = _get_safe_redirect(request)

    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        login(request, user)

        if not form.cleaned_data.get("remember_me"):
            request.session.set_expiry(0)

        messages.success(request, "Welcome back.")
        return redirect(next_url)

    if request.method == "POST" and not form.is_valid():
        email = (request.POST.get("username") or "").strip().lower()
        if email and not User.objects.filter(email__iexact=email).exists():
            messages.error(request, "Email not found.")
        else:
            messages.error(request, "Incorrect credentials.")

    return render(
        request,
        "accounts/login.html",
        {
            "form": form,
            "next": next_url,
            "google_login_url": _google_login_url(next_url),
        },
    )


def signup_view(request):
    if request.user.is_authenticated:
        return redirect("accounts:account")

    form = SignupForm(request.POST or None)
    next_url = _get_safe_redirect(request)

    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        messages.success(request, "Account created successfully.")
        return redirect(next_url)

    return render(
        request,
        "accounts/signup.html",
        {
            "form": form,
            "next": next_url,
            "google_login_url": _google_login_url(next_url),
        },
    )


@login_required
def account_view(request):
    profile = request.user.profile
    profile_form = ProfileForm(
        request.POST if request.POST.get("form_name") == "profile" else None,
        instance=profile,
        user=request.user,
    )
    newsletter_form = NewsletterPreferencesForm(
        request.POST if request.POST.get("form_name") == "newsletter" else None,
        instance=profile,
    )

    if request.method == "POST" and request.POST.get("form_name") == "profile" and profile_form.is_valid():
        profile_form.save()
        messages.success(request, "Your profile has been updated.")
        return redirect("accounts:account")

    if request.method == "POST" and request.POST.get("form_name") == "newsletter" and newsletter_form.is_valid():
        newsletter_form.save()
        messages.success(request, "Your newsletter preferences have been updated.")
        return redirect("accounts:account")

    recent_orders = request.user.orders.all()[:3] if hasattr(request.user, "orders") else []
    wishlist_items = request.user.wishlist_items.all()[:4] if hasattr(request.user, "wishlist_items") else []
    addresses = request.user.addresses.all()[:2] if hasattr(request.user, "addresses") else []

    return render(
        request,
        "accounts/account.html",
        {
            "profile_form": profile_form,
            "newsletter_form": newsletter_form,
            "recent_orders": recent_orders,
            "wishlist_items": wishlist_items,
            "addresses": addresses,
        },
    )


@require_POST
def logout_view(request):
    logout(request)
    messages.success(request, "You have been signed out.")
    return redirect("accounts:login")


class LuxuryPasswordResetView(PasswordResetView):
    template_name = "accounts/password_reset.html"
    email_template_name = "accounts/emails/password_reset_email.txt"
    subject_template_name = "accounts/emails/password_reset_subject.txt"
    success_url = reverse_lazy("accounts:login")

    def form_valid(self, form):
        messages.success(
            self.request,
            "If an account exists for that email, a reset link has been sent.",
        )
        return super().form_valid(form)


def auth_required_modal(request):
    next_url = request.GET.get("next") or reverse("accounts:login")
    payload = {
        "title": "Please sign in to save favourites.",
        "message": "Unlock your private fragrance shortlist and keep your favourites within reach.",
        "login_url": f"{reverse('accounts:login')}?next={next_url}",
        "signup_url": f"{reverse('accounts:signup')}?next={next_url}",
    }
    return JsonResponse(payload)


def protected_purchase_redirect(request):
    messages.info(request, "Sign in required to continue purchase.")
    next_url = request.GET.get("next") or "/checkout/"
    return redirect(f"{reverse('accounts:login')}?next={next_url}")
