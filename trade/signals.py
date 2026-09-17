from io import BytesIO
from pathlib import Path
from uuid import uuid4
from PIL import Image, ImageOps
from django.core.files.base import ContentFile
from django.db.models.signals import pre_save, post_save, post_delete, post_migrate
from django.db.models import ImageField
from django.dispatch import receiver
from django.utils import timezone
from .models import TradeCategory, TradeDirection, URLHistory, CategoryProduct, CategorySection, CategoryImage, FooterLink, SiteSettings

@receiver(pre_save)
def prepare_content(sender, instance, **kwargs):
    if sender._meta.app_label != 'trade': return
    for field in sender._meta.fields:
        if not isinstance(field, ImageField): continue
        value = getattr(instance, field.name)
        if value and not value._committed:
            from .validators import validate_image
            validate_image(value)
            im = ImageOps.exif_transpose(Image.open(value))
            im.thumbnail((1600, 1600))
            buffer = BytesIO()
            im.convert('RGBA' if 'A' in im.getbands() else 'RGB').save(buffer, 'WEBP', quality=85)
            value.save(f'{uuid4().hex}.webp', ContentFile(buffer.getvalue()), save=False)
            if im.width > 960:
                for width in (480, 960):
                    scaled = im.copy()
                    scaled.thumbnail((width, 1600))
                    variant = BytesIO()
                    scaled.convert('RGBA' if 'A' in scaled.getbands() else 'RGB').save(variant, 'WEBP', quality=82)
                    value.storage.save(value.name[:-5] + f'-{width}.webp', ContentFile(variant.getvalue()))
    if sender not in (TradeCategory, TradeDirection) or not instance.pk: return
    old = sender.objects.filter(pk=instance.pk).first()
    if not old: return
    if old.get_absolute_url() != instance.get_absolute_url():
        if old.published:
            URLHistory.objects.update_or_create(path=old.get_absolute_url(), defaults={'kind': sender.__name__, 'object_id': instance.pk})
        if sender == TradeDirection:
            for category in old.categories.filter(published=True):
                URLHistory.objects.update_or_create(path=category.get_absolute_url(), defaults={'kind': 'TradeCategory', 'object_id': category.pk})

@receiver(post_save)
@receiver(post_delete)
def touch_parent(sender, instance, **kwargs):
    if sender == FooterLink:
        SiteSettings.objects.update(updated_at=timezone.now())
    if sender in (CategoryProduct, CategorySection, CategoryImage):
        TradeCategory.objects.filter(pk=instance.category_id).update(updated_at=timezone.now())
    if sender == TradeCategory:
        TradeDirection.objects.filter(pk=instance.direction_id).update(updated_at=timezone.now())

@receiver(post_migrate)
def add_footer_permissions(sender, **kwargs):
    if sender.name != 'trade': return
    from django.contrib.auth.models import Group, Permission
    group = Group.objects.filter(name='Editor').first()
    if group:
        group.permissions.add(*Permission.objects.filter(content_type__app_label='trade', content_type__model='footerlink'))
