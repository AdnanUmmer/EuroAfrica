from django.test import SimpleTestCase

from django.template import Template, Context

from .templatetags.presentation import polish_copy



class PresentationCopyTests(SimpleTestCase):

    def test_custom_and_translated_copy_is_preserved(self):

        for text in ('Owner revised heading', 'Des opportunités entre deux continents', ''):

            self.assertEqual(polish_copy(text), text)



    def test_default_copy_is_refined_without_changing_input(self):

        source = 'Connecting Africa and Europe Through Trade'

        self.assertIn('Two continents.', polish_copy(source))

        self.assertEqual(source, 'Connecting Africa and Europe Through Trade')



    def test_cms_text_remains_escaped(self):

        rendered = Template('{% load presentation %}{{ text|polish_copy }}').render(Context({'text':'<script>alert(1)</script>'}))

        self.assertNotIn('<script>', rendered)

        self.assertIn('&lt;script&gt;', rendered)



class TranslationRefinementTests(SimpleTestCase):
    def test_all_revised_copy_and_approved_aliases_are_localized(self):
        from django.utils.translation import override
        from .templatetags.presentation import COPY, ALIASES
        for language in ('ar', 'fr', 'de', 'hu', 'uk'):
            with override(language):
                for source, replacement in COPY.items():
                    self.assertNotEqual(polish_copy(source), replacement, (language, source))
                for original, replacement in ALIASES.items():
                    self.assertEqual(polish_copy(original), polish_copy(next(k for k,v in COPY.items() if v == replacement)))
