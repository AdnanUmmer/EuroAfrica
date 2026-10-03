"""Database-backed editorial translations with field-level English fallback."""
from django.utils.translation import get_language
from .content_fields import CONTENT_FIELDS


def translated_values(obj):
    fields = CONTENT_FIELDS.get(obj._meta.model_name, ())
    values = {name: getattr(obj, name) for name in fields}
    language = (get_language() or 'en').split('-')[0]
    if language == 'en' or not obj.pk:
        return values
    # A model instance is request-local. Cache only translations, never source values.
    cache = obj.__dict__.setdefault('_editorial_translations', {})
    if language not in cache:
        cache[language] = list(obj.translations.filter(language=language))
    for row in cache[language]:
        if row.field in values and row.source_text == values[row.field] and row.text.strip():
            values[row.field] = row.text
    return values
