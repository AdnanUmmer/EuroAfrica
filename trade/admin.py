from django.contrib import admin
from django.utils.html import format_html
from django.db import models
from django.contrib.admin.widgets import AdminFileWidget
from .models import *

admin.site.site_header = 'EuroAfrica content studio'
admin.site.site_title = 'EuroAfrica admin'
admin.site.index_title = 'Your website, at a glance'

class ImagePreviewWidget(AdminFileWidget):
    def render(self, name, value, attrs=None, renderer=None):
        control = super().render(name, value, attrs, renderer)
        if value and getattr(value, 'url', None):
            return format_html('<div class="studio-upload"><a href="{}" target="_blank" rel="noopener"><img src="{}" alt="Current uploaded image"></a><div>{}<p class="help">Replacing this image creates a new URL. Existing files are kept.</p></div></div>', value.url, value.url, control)
        return format_html('<div class="studio-upload empty">{}</div>', control)

class ImageAdminMixin:
    formfield_overrides = {models.ImageField: {'widget': ImagePreviewWidget}}

class ContentAdmin(ImageAdminMixin, admin.ModelAdmin):
    readonly_fields = ['updated_at', 'image_preview', 'preview_link']
    def image_preview(self, obj):
        image = getattr(obj, 'image', None) or getattr(obj, 'hero_image', None) or getattr(obj, 'header_logo', None)
        return format_html('<img src="{}" width="180" style="max-height:120px;object-fit:contain">', image.url) if image else 'No uploaded image'
    def preview_link(self, obj):
        if obj.pk and isinstance(obj, (TradeCategory, TradeDirection, ContentPage)):
            return format_html('<a href="/preview/{}/{}/">Open private preview</a>', obj._meta.model_name, obj.pk)
        return 'Use the public homepage to review saved changes.'
    def get_fieldsets(self, request, obj=None):
        seo = ['seo_title', 'meta_description', 'social_image', 'social_image_alt']
        editorial = ['published', 'indexable', 'order', 'editorial_notes']
        all_fields = [f.name for f in self.model._meta.fields if f.editable and not f.primary_key]
        images = [x for x in all_fields if x not in seo and (x in ['header_logo', 'footer_logo', 'logo_alt', 'favicon'] or 'image' in x or x.endswith(('_alt', '_caption', '_position')))]
        groups = [('Content', {'fields': [x for x in all_fields if x not in seo + editorial + images]}), ('Images', {'fields': images, 'description': 'Upload JPEG, PNG or WebP under 6 MB. Recommended: 1600 × 1100 for banners, 1000 × 750 for cards. Describe the image in alt text. Crop focus controls which part stays visible.'}), ('Visibility & order', {'fields': [x for x in editorial if x in all_fields]}), ('SEO & sharing', {'fields': seo, 'description': 'Optional overrides. Keep every published title and description specific to its page.'}), ('Review & preview', {'fields': ['updated_at', 'preview_link']})]
        return [(label, options) for label, options in groups if options['fields']]
    def formfield_for_dbfield(self, db_field, request, **kwargs):
        field = super().formfield_for_dbfield(db_field, request, **kwargs)
        if field:
            if db_field.name == 'order': field.help_text = 'Lower numbers appear first.'
            if db_field.name == 'published': field.label = 'Publish this page'; field.help_text = 'Unchecked means draft: accessible only through a private preview.'
            if db_field.name == 'indexable': field.label = 'Allow search indexing'; field.help_text = 'Only applies to published pages when production indexing is enabled.'
            if db_field.name.endswith('_position'): field.label = db_field.verbose_name.replace('position', 'crop focus').capitalize()
        return field
    @admin.display(description='Status', ordering='published')
    def publication(self, obj):
        return format_html('<span class="status-badge {}">{}</span>', 'published' if obj.published else 'draft', 'Published' if obj.published else 'Draft')

class HomeFeatureInline(admin.StackedInline):
    model = HomeFeature
    extra = 0

class ContentSectionInline(admin.StackedInline):
    model = ContentSection
    extra = 0

class SingletonAdmin(ContentAdmin):
    def get_inlines(self, request, obj=None):
        return [HomeFeatureInline] if self.model == HomePage else []

    def has_add_permission(self, request): return not self.model.objects.exists() and super().has_add_permission(request)
    def has_delete_permission(self, request, obj=None): return False

class ProductInline(ImageAdminMixin, admin.StackedInline):
    model = CategoryProduct
    extra = 0
class SectionInline(admin.StackedInline):
    model = CategorySection
    extra = 0
class ImageInline(ImageAdminMixin, admin.StackedInline):
    model = CategoryImage
    extra = 0

@admin.register(TradeCategory)
class CategoryAdmin(ContentAdmin):
    list_display = ['title', 'direction', 'publication', 'indexable', 'featured', 'order']
    list_select_related = ['direction']
    list_filter = ['direction', 'published', 'featured']
    search_fields = ['title', 'summary']
    prepopulated_fields = {'slug': ['title']}
    inlines = [ProductInline, SectionInline, ImageInline]
    list_editable = ['order', 'featured']

@admin.register(TradeDirection, ContentPage)
class PageAdmin(ContentAdmin):
    def get_inlines(self, request, obj=None):
        return [ContentSectionInline] if self.model == ContentPage else []
    list_display = ['title', 'publication', 'indexable', 'order']
    search_fields = ['title']
    list_filter = ['published']

admin.site.register([SiteSettings, HomePage, ContactPage], SingletonAdmin)

@admin.register(Enquiry)
class EnquiryAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'company', 'interest', 'category', 'market', 'status', 'created_at']
    list_filter = ['status', 'interest', 'category']
    search_fields = ['name', 'email', 'company', 'market', 'message']
    readonly_fields = ['name', 'email', 'company', 'phone', 'interest', 'category', 'market', 'message', 'privacy_consent_at', 'created_at']
    fields = ['name', 'email', 'company', 'phone', 'interest', 'category', 'market', 'message', 'privacy_consent_at', 'created_at', 'status', 'staff_notes']
    date_hierarchy = 'created_at'
    list_select_related = ['category']
    actions = ['mark_read', 'mark_replied', 'mark_spam', 'archive']

    def set_status(self, request, queryset, value):
        count = queryset.update(status=value)
        self.message_user(request, f'{count} selected enquiries updated.')

    @admin.action(description='Mark selected enquiries as read', permissions=['change'])
    def mark_read(self, request, queryset): self.set_status(request, queryset, 'read')

    @admin.action(description='Mark selected enquiries as replied', permissions=['change'])
    def mark_replied(self, request, queryset): self.set_status(request, queryset, 'replied')

    @admin.action(description='Mark selected enquiries as spam', permissions=['change'])
    def mark_spam(self, request, queryset): self.set_status(request, queryset, 'spam')

    @admin.action(description='Archive selected enquiries', permissions=['change'])
    def archive(self, request, queryset): self.set_status(request, queryset, 'archived')

    def has_add_permission(self, request): return False

@admin.register(CategoryProduct)
class ProductAdmin(ImageAdminMixin, admin.ModelAdmin):
    list_display = ['name', 'category', 'order']
    list_editable = ['order']
    list_filter = ['category__direction', 'category']
    search_fields = ['name', 'category__title']
    list_select_related = ['category']
    fieldsets = [('Content', {'fields': ['category', 'name', 'description', 'order']}), ('Image', {'fields': ['image', 'image_alt', 'image_caption', 'image_position']})]

@admin.register(CategoryImage)
class GalleryAdmin(ImageAdminMixin, admin.ModelAdmin):
    list_display = ['category', 'image_alt', 'order']
    list_editable = ['order']
    list_filter = ['category']
    search_fields = ['image_alt', 'caption', 'category__title']
    list_select_related = ['category']

@admin.register(FooterLink)
class FooterLinkAdmin(admin.ModelAdmin):
    list_display = ['label', 'destination', 'group', 'order', 'visible']
    list_editable = ['order', 'visible']
    list_filter = ['group', 'visible']
    search_fields = ['label', 'destination']
