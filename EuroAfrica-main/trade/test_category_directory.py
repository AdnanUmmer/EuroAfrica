from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils.translation import override
from .models import TradeCategory

@override_settings(SECURE_SSL_REDIRECT=False)
class CategoryDirectoryTests(TestCase):
    def test_directory_contains_all_visible_categories(self):
        response = self.client.get(reverse('categories'))
        self.assertEqual(response.status_code, 200)
        visible = TradeCategory.objects.filter(published=True, direction__published=True)
        self.assertEqual(list(response.context['categories']), list(visible.select_related('direction')))
        for category in visible:
            self.assertContains(response, category.get_absolute_url())
        self.assertNotContains(response, '<figcaption')

    def test_hidden_categories_and_directions_stay_hidden(self):
        category = TradeCategory.objects.filter(published=True).first()
        category.published = False
        category.save()
        self.assertNotContains(self.client.get(reverse('categories')), category.get_absolute_url())
        direction = category.direction
        direction.published = False
        direction.save()
        response = self.client.get(reverse('categories'))
        self.assertFalse(response.context['categories'].filter(direction=direction).exists())

    def test_directory_language_and_rtl(self):
        for language in ('en', 'ar', 'fr', 'de', 'hu', 'uk'):
            self.client.cookies['django_language'] = language
            response = self.client.get(reverse('categories'))
            self.assertContains(response, 'lang="' + language + '"')
            self.assertContains(response, 'dir="' + ('rtl' if language == 'ar' else 'ltr') + '"')
            if language != 'en':
                self.assertNotContains(response, '>All categories<')
                self.assertNotContains(response, '>Categories<')
