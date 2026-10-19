"""Database-backed editorial translations with field-level English fallback."""
from django.utils.translation import get_language
from .content_fields import CONTENT_FIELDS


# Presentation compatibility for existing published direction labels. Keep stored
# editorial values/source fingerprints intact; no production data migration needed.
ARROW_FREE_LABELS = {
    'Africa → Europe': 'Africa to Europe', 'Europe → Africa': 'Europe to Africa',
    'Afrika → Europa': 'Afrika nach Europa', 'Europa → Afrika': 'Europa nach Afrika',
    'Afrique → Europe': "De l’Afrique vers l’Europe", 'Europe → Afrique': "De l’Europe vers l’Afrique",
    'Afrika → Európa': 'Afrikából Európába', 'Európa → Afrika': 'Európából Afrikába',
    'Африка → Європа': 'З Африки до Європи', 'Європа → Африка': 'З Європи до Африки',
}


def display_labels(obj, values):
    field = {'tradedirection': 'title', 'footerlink': 'label'}.get(obj._meta.model_name)
    if field in values:
        values[field] = ARROW_FREE_LABELS.get(values[field], values[field])
    return values


def translated_values(obj):
    fields = CONTENT_FIELDS.get(obj._meta.model_name, ())
    values = {name: getattr(obj, name) for name in fields}
    language = (get_language() or 'en').split('-')[0]
    if language == 'en' or not obj.pk:
        return display_labels(obj, values)
    # A model instance is request-local. Cache only translations, never source values.
    cache = obj.__dict__.setdefault('_editorial_translations', {})
    if language not in cache:
        cache[language] = list(obj.translations.filter(language=language))
    for row in cache[language]:
        if row.field in values and row.source_text == values[row.field] and row.text.strip():
            values[row.field] = row.text
    return display_labels(obj, values)
