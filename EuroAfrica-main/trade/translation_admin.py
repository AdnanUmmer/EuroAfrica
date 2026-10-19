"""Translation editing without changing existing source-content admin forms."""
from django import forms
from django.contrib import admin
from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.utils.html import format_html
from django.urls import reverse
from .models import ContentTranslation
from .content_fields import CONTENT_FIELDS


class TranslationLinkMixin:
    @admin.display(description='Translations')
    def translations_link(self, obj):
        if not obj or not obj.pk:
            return 'Save this content first to add translations.'
        ct = ContentType.objects.get_for_model(obj)
        target = f'{obj._meta.model_name}:{obj.pk}'
        return format_html('<a href="{}?content_type__id__exact={}&object_id__exact={}">Edit translations</a> · <a href="{}?target={}">Add a translation</a>',
            reverse('admin:trade_contenttranslation_changelist'), ct.pk, obj.pk,
            reverse('admin:trade_contenttranslation_add'), target)


class TranslationForm(forms.ModelForm):
    target = forms.ChoiceField(label='Content record')
    field = forms.ChoiceField(label='Content field')

    class Meta:
        model = ContentTranslation
        fields = ['target', 'language', 'field', 'text']
        widgets = {'text': forms.Textarea(attrs={'rows':12, 'dir':'auto'})}

    def __init__(self, *args, request_user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.targets = {}
        choices = []
        for name in CONTENT_FIELDS:
            if request_user and not request_user.has_perm(f'trade.change_{name}'):
                continue
            model = apps.get_model('trade', name)
            for obj in model.objects.all():
                key = f'{name}:{obj.pk}'
                self.targets[key] = obj
                choices.append((key, f'{model._meta.verbose_name}: {obj}'))
        self.fields['target'].choices = [('', 'Choose content')] + choices
        if self.instance.pk:
            self.initial['target'] = f'{self.instance.content_type.model}:{self.instance.object_id}'
        key = self.data.get('target') if self.is_bound else self.initial.get('target')
        obj = self.targets.get(key)
        names = CONTENT_FIELDS[obj._meta.model_name] if obj else sorted({f for fs in CONTENT_FIELDS.values() for f in fs})
        self.fields['field'].choices = [(name, name.replace('_',' ').capitalize()) for name in names]
        if obj:
            field = self.data.get('field') if self.is_bound else self.initial.get('field')
            if field in names:
                self.fields['text'].help_text = 'English source: ' + getattr(obj, field)

    def clean(self):
        data = super().clean()
        obj = self.targets.get(data.get('target'))
        if obj:
            self.instance.content_type = ContentType.objects.get_for_model(obj)
            self.instance.object_id = obj.pk
            field = data.get('field')
            if field in CONTENT_FIELDS[obj._meta.model_name]:
                self.instance.source_text = getattr(obj, field)
                duplicate = ContentTranslation.objects.filter(content_type=self.instance.content_type, object_id=obj.pk, language=data.get('language'), field=field).exclude(pk=self.instance.pk)
                if duplicate.exists():
                    raise forms.ValidationError('This translation already exists. Edit the existing record.')
        return data


@admin.register(ContentTranslation)
class ContentTranslationAdmin(admin.ModelAdmin):
    form = TranslationForm
    fields = ['target', 'language', 'field', 'text', 'source_text', 'updated_at']
    readonly_fields = ['source_text', 'updated_at']
    list_display = ['content_type', 'object_id', 'language', 'field', 'needs_review', 'updated_at']
    list_filter = ['language', 'content_type', 'field']
    search_fields = ['text', 'source_text']
    list_select_related = ['content_type']

    @admin.display(boolean=True, description='Source changed')
    def needs_review(self, obj):
        return not obj.content_object or getattr(obj.content_object, obj.field, None) != obj.source_text

    def get_form(self, request, obj=None, **kwargs):
        base = super().get_form(request, obj, **kwargs)
        class RequestForm(base):
            def __init__(self, *args, **kw):
                super().__init__(*args, request_user=request.user, **kw)
        return RequestForm

    def get_queryset(self, request):
        allowed = [name for name in CONTENT_FIELDS if request.user.has_perm(f'trade.change_{name}')]
        return super().get_queryset(request).filter(content_type__app_label='trade', content_type__model__in=allowed)
