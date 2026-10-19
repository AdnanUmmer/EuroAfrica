from pathlib import Path
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

def validate_pdf(value):
    if value.size > 25 * 1024 * 1024:
        raise ValidationError('Choose a PDF smaller than 25 MB.')
    if Path(value.name).suffix.lower() != '.pdf':
        raise ValidationError('Upload a PDF document.')
    try:
        header = value.read(1024)
    except OSError:
        raise ValidationError('The PDF could not be read.') from None
    finally:
        value.seek(0)
    if b'%PDF-' not in header:
        raise ValidationError('The uploaded file is not a valid PDF document.')

def validate_destination(value):
    if not value.startswith('/') or value.startswith('//') or '\\' in value:
        raise ValidationError('Use a local path beginning with one slash, such as /contact/.')
