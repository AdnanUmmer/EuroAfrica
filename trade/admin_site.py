from django.contrib.admin import AdminSite
from django.urls import path, reverse
from django.template.response import TemplateResponse

class EuroAfricaAdminSite(AdminSite):
    site_header = 'EuroAfrica content studio'
    site_title = 'EuroAfrica studio'
    index_title = 'Your website, at a glance'
    index_template = 'admin/studio_dashboard.html'

    def each_context(self, request):
        from .models import HomePage, ContactPage, SiteSettings
        context = super().each_context(request)
        tasks = []
        entries = [
            ('Dashboard', None, reverse('admin:index')),
            ('Homepage', 'homepage', HomePage),
            ('About & content pages', 'contentpage', None),
            ('Trade directions', 'tradedirection', None),
            ('Categories', 'tradecategory', None),
            ('Products', 'categoryproduct', None),
            ('Images', 'tradecategory', reverse('admin:studio_images')),
            ('Enquiries', 'enquiry', None),
            ('Contact page', 'contactpage', ContactPage),
            ('Footer links', 'footerlink', None),
            ('Brand, footer & SEO', 'sitesettings', SiteSettings),
        ]
        for label, model, target in entries:
            if model and not (request.user.has_perm(f'trade.view_{model}') or request.user.has_perm(f'trade.change_{model}')): continue
            if isinstance(target, str): url = target
            elif target:
                obj = target.objects.first()
                url = reverse(f'admin:trade_{model}_change', args=[obj.pk]) if obj else reverse(f'admin:trade_{model}_changelist')
            else: url = reverse(f'admin:trade_{model}_changelist')
            tasks.append({'label': label, 'url': url, 'active': request.path == url or (model and not isinstance(target, str) and f'/trade/{model}/' in request.path)})
        context['studio_tasks'] = tasks
        return context

    def index(self, request, extra_context=None):
        from .models import TradeCategory, Enquiry, HomePage
        info = dict(extra_context or {})
        if request.user.has_perm('trade.view_tradecategory'):
            info['category_stats'] = {'published': TradeCategory.objects.filter(published=True, direction__published=True).count(), 'drafts': TradeCategory.objects.filter(published=False).count()}
        if request.user.has_perm('trade.view_enquiry'):
            info['new_enquiries'] = Enquiry.objects.filter(status='new').count()
            info['recent_enquiries'] = Enquiry.objects.select_related('category')[:5]
        info['homepage'] = HomePage.objects.first() if request.user.has_perm('trade.change_homepage') else None
        return super().index(request, info)

    def get_urls(self):
        return [path('images/', self.admin_view(self.images), name='studio_images')] + super().get_urls()

    def images(self, request):
        from django.core.exceptions import PermissionDenied
        from django.db.models import ImageField
        from .models import HomePage, SiteSettings, TradeDirection, TradeCategory, ContentPage, CategoryProduct, CategoryImage
        models = [HomePage, SiteSettings, TradeDirection, TradeCategory, ContentPage, CategoryProduct, CategoryImage]
        allowed = [model for model in models if request.user.has_perm(f'trade.view_{model._meta.model_name}')]
        if not allowed: raise PermissionDenied
        items = []
        for model in allowed:
            for obj in model.objects.all():
                for field in model._meta.fields:
                    if isinstance(field, ImageField):
                        value = getattr(obj, field.name)
                        if value:
                            items.append({'url': value.url, 'label': str(obj), 'field': field.verbose_name, 'edit': reverse(f'admin:trade_{model._meta.model_name}_change', args=[obj.pk])})
        return TemplateResponse(request, 'admin/studio_images.html', {**self.each_context(request), 'title': 'Website images', 'items': items})
