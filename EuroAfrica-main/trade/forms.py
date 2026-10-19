from django.utils.translation import gettext_lazy as _
from django import forms
from .models import Enquiry, TradeCategory
from .antispam import GENERIC_ERROR, timing_token, valid_timing


class EnquiryForm(forms.ModelForm):
    website = forms.CharField(required=False, max_length=200, widget=forms.TextInput(attrs={'tabindex': '-1', 'autocomplete': 'off'}))
    form_token = forms.CharField(max_length=512, widget=forms.HiddenInput)
    category = forms.ChoiceField(label=_('Product / category'))
    privacy_consent = forms.BooleanField(label=_('I agree to my details being used to respond to this enquiry.'), required=True)

    class Meta:
        model = Enquiry
        fields = ['name', 'email', 'company', 'phone', 'interest', 'category', 'market', 'message']
        labels = {'name': _('Full name'), 'phone': _('Phone number'), 'interest': _("I’m interested in"), 'market': _('Country / market of interest'), 'message': _('Your enquiry'), 'email': _('Business email'), 'company': _('Company / organisation')}
        widgets = {
            'message': forms.Textarea(attrs={'rows': 6, 'maxlength': 5000}),
            'name': forms.TextInput(attrs={'autocomplete': 'name'}),
            'email': forms.EmailInput(attrs={'autocomplete': 'email'}),
            'company': forms.TextInput(attrs={'autocomplete': 'organization'}),
            'phone': forms.TextInput(attrs={'autocomplete': 'tel', 'type': 'tel'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.categories = TradeCategory.objects.filter(published=True, direction__published=True)
        self.fields['category'].choices = [('', _('Choose a product or category')), ('general', _('General / not yet sure'))] + [(str(c.pk), c.translated['title']) for c in self.categories]
        self.fields['interest'].choices = [('', '---------'), ('general', _('General Enquiry')), ('africa-to-europe', _('Africa → Europe Trade')), ('europe-to-africa', _('Europe → Africa Trade'))]
        self.fields['form_token'].initial = timing_token()
        self.fields['message'].help_text = _('Describe the product or topic and what you would like to know. Maximum 5,000 characters.')
        for name in ('email', 'phone'):
            self.fields[name].widget.attrs['dir'] = 'ltr'
        self.order_fields(['name', 'company', 'email', 'phone', 'interest', 'category', 'market', 'message', 'privacy_consent', 'website', 'form_token'])

    def clean_category(self):
        value = self.cleaned_data['category']
        if value == 'general':
            return None
        try:
            return self.categories.get(pk=value)
        except TradeCategory.DoesNotExist:
            raise forms.ValidationError(_('Choose an available enquiry type.')) from None

    def clean(self):
        data = super().clean()
        if data.get('website') or not valid_timing(data.get('form_token', '')):
            raise forms.ValidationError(GENERIC_ERROR)
        for field in ('name', 'email', 'company', 'phone', 'market'):
            value = data.get(field, '')
            if '\r' in value or '\n' in value:
                self.add_error(field, _('Enter this value on one line.'))
        category = data.get('category')
        interest = data.get('interest')
        if category and interest and interest != 'general' and category.direction.seed_key != interest:
            self.add_error('category', _('Choose a category in the selected trade direction, or select General Enquiry.'))
        return data
