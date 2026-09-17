from django import template
register = template.Library()

@register.simple_tag
def image_srcset(image):
    if not image or not image.name.endswith('.webp'): return ''
    base = image.url[:-5]
    return f'{base}-480.webp 480w, {base}-960.webp 960w, {image.url} {image.width}w' if image.width > 960 else ''
