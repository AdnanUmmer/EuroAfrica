from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.core.exceptions import ValidationError
from .validators import validate_image, validate_destination

IMAGE_POSITIONS = [('center', 'Centre'), ('top', 'Top'), ('bottom', 'Bottom'), ('left', 'Left'), ('right', 'Right')]

def image_field():
    return models.ImageField(upload_to='content/%Y/%m/', blank=True, validators=[validate_image], help_text='JPEG, PNG or WebP; maximum 6 MB. Use a landscape image. Uploaded images are resized for the web.')

class SEO(models.Model):
    seo_title = models.CharField(max_length=180, blank=True, help_text='Optional override; otherwise the page title and EuroAfrica are used.')
    meta_description = models.CharField(max_length=300, blank=True)
    social_image = image_field()
    social_image_alt = models.CharField(max_length=240, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        abstract = True

class Singleton(models.Model):
    class Meta:
        abstract = True
    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

class SiteSettings(Singleton, SEO):
    class Meta:
        verbose_name_plural = 'Brand, footer & SEO settings'
    site_name = models.CharField(max_length=100, default='EuroAfrica')
    tagline = models.CharField(max_length=180, default='Bridging Markets • Creating Opportunities')
    header_logo = image_field()
    footer_logo = image_field()
    logo_alt = models.CharField(max_length=200, default='EuroAfrica')
    favicon = image_field()
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=60, blank=True)
    address = models.TextField(blank=True)
    linkedin = models.URLField(blank=True)
    instagram = models.URLField(blank=True)
    footer_copy = models.CharField(max_length=300, default='An introduction to the products and sectors connecting African and European markets.')
    legal_copy = models.CharField(max_length=240, blank=True, default='Bridging continents. Connecting perspectives.')
    def __str__(self): return 'Brand, contact details & default SEO'

class HomePage(Singleton, SEO):
    hero_heading = models.CharField(max_length=180, default='Connecting Africa and Europe Through Trade')
    hero_text = models.TextField(default='Explore the products and sectors connecting African and European markets—from fresh produce and specialty goods to machinery, technology, and industrial supplies.')
    hero_image = image_field()
    hero_alt = models.CharField(max_length=240, blank=True)
    hero_caption = models.CharField(max_length=300, blank=True)
    hero_position = models.CharField(max_length=10, choices=IMAGE_POSITIONS, default='center')
    primary_label = models.CharField(max_length=80, default='Explore Trade Categories')
    primary_url = models.CharField(max_length=200, default='/#trade-directions', validators=[validate_destination])
    secondary_label = models.CharField(max_length=80, default='Contact Us')
    secondary_url = models.CharField(max_length=200, default='/contact/', validators=[validate_destination])
    direction_heading = models.CharField(max_length=180, default='Two continents. A world of possibilities.')
    direction_text = models.TextField(default='Discover the categories connecting markets in both directions.')
    about_heading = models.CharField(max_length=180, default='A shared perspective on trade')
    about_text = models.TextField(default='EuroAfrica brings together an introduction to the products and sectors linking Africa and Europe. Explore each trade direction to understand the breadth of categories represented here.')
    diversity_heading = models.CharField(max_length=180, default='From the everyday to the exceptional')
    diversity_text = models.TextField(default='Fresh flowers and food. Handcrafted textiles and personal care. Machinery and industrial technology. Explore a diverse range of categories, each with its own materials, applications and considerations.')
    diversity_image = image_field()
    diversity_alt = models.CharField(max_length=240, blank=True)
    diversity_caption = models.CharField(max_length=300, blank=True)
    diversity_position = models.CharField(max_length=10, choices=IMAGE_POSITIONS, default='center')
    show_about = models.BooleanField(default=True)
    show_diversity = models.BooleanField(default=True)
    contact_heading = models.CharField(max_length=180, default='Let’s start a conversation')
    contact_text = models.TextField(default='Interested in a category? Share your question with EuroAfrica.')
    def __str__(self): return 'Homepage'

class Published(SEO):
    title = models.CharField(max_length=180)
    slug = models.SlugField(max_length=180)
    summary = models.TextField()
    published = models.BooleanField(default=False)
    indexable = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    image = image_field()
    image_alt = models.CharField(max_length=240, blank=True)
    image_caption = models.CharField(max_length=300, blank=True)
    image_position = models.CharField(max_length=10, choices=IMAGE_POSITIONS, default='center')
    class Meta:
        abstract = True
        ordering = ['order', 'title']
    def __str__(self): return self.title

class TradeDirection(Published):
    seed_key = models.CharField(max_length=180, unique=True, null=True, blank=True, editable=False)
    slug = models.SlugField(unique=True)
    introduction = models.TextField()
    def clean(self):
        if self.slug in ('admin', 'preview', 'contact', 'about', 'privacy', 'static', 'media', 'pages'):
            raise ValidationError({'slug': 'This URL is reserved. Choose a different slug.'})
        history = URLHistory.objects.filter(path=f'/{self.slug}/').first()
        if history and (history.kind != 'TradeDirection' or history.object_id != self.pk):
            raise ValidationError({'slug': 'This URL belongs to a previous page. Choose a new slug.'})
    def get_absolute_url(self): return reverse('direction', args=[self.slug])

class TradeCategory(Published):
    seed_key = models.CharField(max_length=180, unique=True, null=True, blank=True, editable=False)
    direction = models.ForeignKey(TradeDirection, on_delete=models.PROTECT, related_name='categories')
    overview = models.TextField()
    hero_image = image_field()
    hero_alt = models.CharField(max_length=240, blank=True)
    hero_caption = models.CharField(max_length=300, blank=True)
    hero_position = models.CharField(max_length=10, choices=IMAGE_POSITIONS, default='center')
    featured = models.BooleanField(default=False)
    editorial_notes = models.TextField(blank=True, help_text='Internal only. Never displayed on the public site.')
    class Meta(Published.Meta):
        constraints = [models.UniqueConstraint(fields=['direction', 'slug'], name='category_direction_slug')]
        verbose_name_plural = 'Trade categories'
    def get_absolute_url(self): return reverse('category', args=[self.direction.slug, self.slug])
    def clean(self):
        if self.direction_id and self.slug:
            history = URLHistory.objects.filter(path=self.get_absolute_url()).first()
            if history and (history.kind != 'TradeCategory' or history.object_id != self.pk):
                raise ValidationError({'slug': 'This URL belongs to a previous category. Choose a new slug.'})

class CategoryProduct(models.Model):
    category = models.ForeignKey(TradeCategory, on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    image = image_field()
    image_alt = models.CharField(max_length=240, blank=True)
    image_caption = models.CharField(max_length=300, blank=True)
    image_position = models.CharField(max_length=10, choices=IMAGE_POSITIONS, default='center')
    order = models.PositiveIntegerField(default=0)
    class Meta: ordering = ['order', 'pk']
    def __str__(self): return self.name

class CategorySection(models.Model):
    category = models.ForeignKey(TradeCategory, on_delete=models.CASCADE, related_name='sections')
    heading = models.CharField(max_length=180)
    text = models.TextField()
    order = models.PositiveIntegerField(default=0)
    class Meta: ordering = ['order', 'pk']

class CategoryImage(models.Model):
    category = models.ForeignKey(TradeCategory, on_delete=models.CASCADE, related_name='gallery')
    image = image_field()
    image_alt = models.CharField(max_length=240)
    caption = models.CharField(max_length=240, blank=True)
    image_position = models.CharField(max_length=10, choices=IMAGE_POSITIONS, default='center')
    order = models.PositiveIntegerField(default=0)
    class Meta: ordering = ['order', 'pk']
    def __str__(self): return f'{self.category.title} — {self.image_alt}'

class FooterLink(models.Model):
    label = models.CharField(max_length=80)
    destination = models.CharField(max_length=250, validators=[validate_destination], help_text='A local website path, for example /contact/. Unpublished page links are hidden automatically.')
    group = models.CharField(max_length=20, choices=[('explore', 'Explore'), ('trade', 'Trade directions'), ('legal', 'Legal')], default='explore')
    order = models.PositiveIntegerField(default=0)
    visible = models.BooleanField(default=True)
    class Meta: ordering = ['group', 'order', 'pk']
    def __str__(self): return self.label

class ContentPage(Published):
    slug = models.SlugField(unique=True, choices=[('about', 'About'), ('privacy', 'Privacy')])
    body = models.TextField(help_text='Plain text; separate paragraphs with blank lines.')
    def get_absolute_url(self): return reverse(self.slug)

class ContactPage(Singleton, SEO):
    title = models.CharField(max_length=180, default='A conversation starts here')
    introduction = models.TextField(default='Tell us which trade category interests you and what you would like to know. Please avoid including sensitive personal information.')
    confirmation = models.TextField(default='Thank you. Your enquiry has been saved for the EuroAfrica team.')
    def get_absolute_url(self): return reverse('contact')
    def __str__(self): return 'Contact page'

class Enquiry(models.Model):
    name = models.CharField(max_length=120)
    email = models.EmailField()
    company = models.CharField(max_length=180, blank=True)
    phone = models.CharField(max_length=60, blank=True)
    category = models.ForeignKey(TradeCategory, null=True, blank=True, on_delete=models.SET_NULL)
    message = models.TextField(max_length=5000)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[('new', 'New'), ('in_progress', 'In progress'), ('resolved', 'Resolved')], default='new')
    staff_notes = models.TextField(blank=True)
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Enquiries'
    def __str__(self): return f'{self.name} — {self.created_at:%Y-%m-%d}'

class URLHistory(models.Model):
    path = models.CharField(max_length=500, unique=True)
    kind = models.CharField(max_length=30)
    object_id = models.PositiveBigIntegerField()

class SubmissionWindow(models.Model):
    key = models.CharField(max_length=64, unique=True)
    attempts = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)


class StockImageInitialization(models.Model):
    """Record first default-image setup so later deliberate clears stay cleared."""
    key = models.CharField(max_length=150, primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)
