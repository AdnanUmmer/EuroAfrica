from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from trade import views

urlpatterns = [path('admin/', admin.site.urls), path('', views.home, name='home'), path('contact/', views.contact, name='contact'), path('contact/thanks/', views.thanks, name='thanks'), path('about/', views.page, {'slug': 'about'}, name='about'), path('privacy/', views.page, {'slug': 'privacy'}, name='privacy'), path('preview/<str:kind>/<int:pk>/', views.preview, name='preview'), path('sitemap.xml', views.sitemap), path('robots.txt', views.robots), path('<slug:direction_slug>/<slug:slug>/', views.category, name='category'), path('<slug:slug>/', views.direction, name='direction')]
if settings.DEBUG: urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
elif settings.SERVE_MEDIA:
    from trade.media import image
    urlpatterns += [path('media/<path:path>', image, name='uploaded_image')]

