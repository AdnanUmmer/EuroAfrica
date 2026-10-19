from django import template
register = template.Library()

@register.simple_tag
def image_available(image):
    try:
        return bool(image and image.storage.exists(image.name))
    except OSError:
        return False

@register.simple_tag
def image_srcset(image):
    if not image_available(image) or not image.name.endswith('.webp'): return ''
    try:
        if not image.width or image.width <= 960: return ''
        variants = [f'{image.storage.url(image.name[:-5] + f"-{width}.webp")} {width}w'
                    for width in (480, 960) if image.storage.exists(image.name[:-5] + f'-{width}.webp')]
        return ', '.join(variants + [f'{image.url} {image.width}w'])
    except (OSError, ValueError):
        return ''
