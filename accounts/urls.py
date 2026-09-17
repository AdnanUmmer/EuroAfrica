from django.urls import path

from .views import (
    LuxuryPasswordResetView,
    account_view,
    auth_required_modal,
    login_view,
    logout_view,
    protected_purchase_redirect,
    signup_view,
)

app_name = "accounts"

urlpatterns = [
    path("login/", login_view, name="login"),
    path("signup/", signup_view, name="signup"),
    path("logout/", logout_view, name="logout"),
    path("account/", account_view, name="account"),
    path("forgot-password/", LuxuryPasswordResetView.as_view(), name="password_reset"),
    path("auth-modal/", auth_required_modal, name="auth_modal"),
    path("protected-purchase/", protected_purchase_redirect, name="protected_purchase"),
]

