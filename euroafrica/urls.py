from django.contrib import admin
from django.urls import path
from django.conf import settings
from trade import views
from trade.recovery import StaffPasswordResetView
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy

urlpatterns = [path('admin/', admin.site.urls), path('', views.home, name='home'), path('contact/', views.contact, name='contact'), path('contact/thanks/', views.thanks, name='thanks'), path('about/', views.page, {'slug': 'about'}, name='about'), path('privacy/', views.page, {'slug': 'privacy'}, name='privacy'), path('preview/<str:kind>/<int:pk>/', views.preview, name='preview'), path('sitemap.xml', views.sitemap), path('robots.txt', views.robots), path('<slug:direction_slug>/<slug:slug>/', views.category, name='category'), path('<slug:slug>/', views.direction, name='direction')]
urlpatterns = [
    path('admin/password_reset/', StaffPasswordResetView.as_view(), name='admin_password_reset'),
    path('admin/password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='admin_password_reset_done'),
    path('admin/reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(success_url=reverse_lazy('admin_password_reset_complete')), name='admin_password_reset_confirm'),
    path('admin/reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='admin_password_reset_complete'),
] + urlpatterns
if settings.DEBUG or settings.SERVE_MEDIA:
    from trade.media import image
    urlpatterns += [path('media/<path:path>', image, name='uploaded_image')]

