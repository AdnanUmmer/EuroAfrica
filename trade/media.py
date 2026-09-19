"""Bounded image delivery from repository media or a configured upload volume."""
from pathlib import Path
from django.conf import settings
from django.http import FileResponse, Http404
from django.views.decorators.http import require_safe


@require_safe
def image(request, path):
    try:
        root = Path(settings.MEDIA_ROOT).resolve()
        target = (root / path).resolve()
    except (OSError, ValueError):
        raise Http404 from None
    types = {'.webp': 'image/webp', '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg'}
    if not target.is_relative_to(root) or target.suffix.lower() not in types:
        raise Http404
    try:
        stream = target.open('rb')
    except (OSError, ValueError):
        raise Http404 from None
    response = FileResponse(stream, content_type=types[target.suffix.lower()])
    response['Cache-Control'] = 'private, no-store' if settings.STAGING else 'public, max-age=604800'
    response['X-Content-Type-Options'] = 'nosniff'
    return response
