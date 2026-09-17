from django.core.exceptions import ValidationError
from PIL import Image

def validate_image(value):
    if value.size > 6 * 1024 * 1024:
        raise ValidationError('Choose an image smaller than 6 MB.')
    try:
        image = Image.open(value)
        if image.format not in ('JPEG', 'PNG', 'WEBP') or image.width * image.height > 40000000:
            raise ValidationError('Use a JPEG, PNG or WebP image up to 40 megapixels.')
        image.verify()
    except (OSError, Image.DecompressionBombError):
        raise ValidationError('The image could not be verified.')
    finally:
        value.seek(0)

def validate_destination(value):
    if not value.startswith('/') or value.startswith('//') or '\\' in value:
        raise ValidationError('Use a local path beginning with one slash, such as /contact/.')
