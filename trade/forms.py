from django import forms
from .models import Enquiry, TradeCategory

class EnquiryForm(forms.ModelForm):
    website = forms.CharField(required=False, widget=forms.HiddenInput)
    class Meta:
        model = Enquiry
        fields = ['name', 'email', 'company', 'phone', 'category', 'message']
        widgets = {'message': forms.Textarea(attrs={'rows': 6}), 'name': forms.TextInput(attrs={'autocomplete': 'name'}), 'email': forms.EmailInput(attrs={'autocomplete': 'email'})}
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = TradeCategory.objects.filter(published=True, direction__published=True)
        self.fields['category'].empty_label = 'General enquiry'
    def clean_website(self):
        if self.cleaned_data['website']: raise forms.ValidationError('Unable to submit this enquiry.')
        return ''
