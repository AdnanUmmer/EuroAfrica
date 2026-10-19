"""Publish the owner's approved September copy once; retain historical enquiries/media."""
from django.db import migrations
from django.utils import timezone

DATA = {'home': {'hero_heading': 'Connecting Africa and Europe Through Trade',
          'hero_text': 'Discover the products, industries and opportunities shaping trade between two '
                       'dynamic markets.',
          'hero_detail': 'EuroAfrica provides a clear view of the key commodities and manufactured goods '
                         'moving between Africa and Europe. From agricultural produce and strategic minerals '
                         'to machinery, pharmaceuticals and transport equipment, explore the sectors driving '
                         'commercial exchange across both continents.',
          'primary_label': 'Explore Trade Categories',
          'primary_url': '/#trade-directions',
          'secondary_label': 'Make an Enquiry',
          'secondary_url': '/contact/',
          'direction_heading': 'Two Continents. Diverse Markets. Growing Opportunities.',
          'direction_text': 'Africa and Europe are connected by established trade relationships spanning '
                            'agriculture, manufacturing, energy, infrastructure and consumer goods.\n'
                            '\n'
                            'African markets supply Europe with valuable agricultural commodities, '
                            'horticultural produce, minerals and manufactured goods, while European '
                            'industries provide African markets with machinery, transport equipment, '
                            'pharmaceuticals, refined products and foodstuffs.\n'
                            '\n'
                            'EuroAfrica brings these trade flows together in one accessible platform, '
                            'helping businesses, professionals and interested stakeholders understand what '
                            'is traded, where key products originate and the sectors creating commercial '
                            'opportunities between the two regions.',
          'about_heading': 'Understand the Trade Behind the Markets',
          'about_text': 'International trade can be complex. EuroAfrica makes the landscape easier to '
                        'understand by organising key trade categories, products and market information into '
                        'a clear and accessible resource.',
          'diversity_heading': 'Explore a Trade Relationship Built on Complementary Strengths',
          'diversity_text': 'Africa and Europe bring different strengths to international trade.\n'
                            '\n'
                            'Africa combines agricultural capacity, natural resources and expanding '
                            'manufacturing industries. Europe contributes advanced machinery, transportation '
                            'systems, pharmaceuticals, industrial products and established manufacturing '
                            'capabilities.\n'
                            '\n'
                            'Together, these complementary strengths create trade relationships across '
                            'numerous sectors and markets.\n'
                            '\n'
                            'EuroAfrica helps you explore those connections and identify the categories '
                            'shaping commerce between the two continents.',
          'contact_heading': 'Looking for More Information?',
          'contact_text': "Whether you're researching a particular product category, exploring a market or "
                          'looking for information about trade between Africa and Europe, you can contact us '
                          'with your enquiry.\n'
                          '\n'
                          "Tell us what you're interested in and provide the relevant details. Our team will "
                          'review your enquiry and respond using the contact information provided.',
          'final_heading': 'Discover the Trade Connecting Africa and Europe',
          'final_text': 'Explore key industries, understand important product categories and discover the '
                        'commercial connections between African and European markets.',
          'show_about': True,
          'show_diversity': True},
 'features': [('Explore Key Trade Categories',
               'Discover important products moving between African and European markets across agriculture, '
               'industry, healthcare, transportation and natural resources.'),
              ('Understand Product Origins',
               'Learn about the countries and regions associated with major export categories and the role '
               'they play within international supply chains.'),
              ('Discover Market Connections',
               'See how resources, agricultural products, manufactured goods and industrial technologies '
               'connect businesses and economies across both continents.'),
              ('Access Clear Information',
               'Navigate trade information without unnecessary complexity, whether you are researching a '
               'sector, exploring commercial possibilities or simply seeking a better understanding of '
               'Africa-Europe trade.')],
 'contact': {'title': 'Start Your Enquiry',
             'introduction': 'Have a question about a trade category, product or market featured on '
                             'EuroAfrica?\n'
                             '\n'
                             'Complete the enquiry form with as much relevant information as possible. This '
                             'helps us understand your request and provide a more useful response.'},
 'about': {'title': 'About EuroAfrica',
           'summary': 'EuroAfrica is an informational platform focused on trade between African and European '
                      'markets.',
           'body': 'Our purpose is to make key trade categories and market connections easier to discover '
                   'and understand. We present information across sectors including agriculture, '
                   'horticulture, minerals, textiles, machinery, transportation, pharmaceuticals, energy '
                   'products and food.\n'
                   '\n'
                   'By bringing these categories together in a structured and accessible format, EuroAfrica '
                   'provides a starting point for businesses, professionals, researchers and other '
                   'stakeholders interested in understanding the commercial links between Africa and '
                   'Europe.'},
 'about_sections': [('Our Focus',
                     'We focus on presenting trade information clearly, professionally and responsibly.\n'
                     '\n'
                     'Rather than overwhelming visitors with unnecessary complexity, EuroAfrica highlights '
                     'the products, sectors and markets that contribute to trade between the two regions.'),
                    ('Our Vision',
                     'To become a trusted and accessible source of information for understanding the '
                     'products, industries and opportunities connecting African and European markets.')],
 'directions': [{'slug': 'africa-to-europe',
                 'title': 'Africa to Europe',
                 'heading': 'Discover What Africa Brings to European Markets',
                 'summary': "Africa's diverse climates, natural resources and growing industries support a "
                            'broad range of exports to European markets.',
                 'introduction': 'From internationally recognised agricultural commodities to valuable '
                                 'minerals and manufactured products, these sectors demonstrate the depth '
                                 "and diversity of Africa's role in international trade."},
                {'slug': 'europe-to-africa',
                 'title': 'Europe to Africa',
                 'heading': 'European Products Supporting African Markets',
                 'summary': 'European exports to Africa span industrial equipment, transportation, '
                            'healthcare, energy and food.',
                 'introduction': 'These products serve businesses, governments, industries and consumers '
                                 'across African markets while supporting infrastructure development, '
                                 'manufacturing and everyday economic activity.'}],
 'categories': [{'title': 'Agricultural Commodities',
                 'slug': 'agricultural-commodities',
                 'summary': 'From African farms to international markets.',
                 'overview': 'Africa is an important source of globally traded agricultural commodities. '
                             "Cocoa from Côte d'Ivoire and Ghana, coffee from Ethiopia and Kenya, and sesame "
                             'seeds from countries including Ethiopia, Sudan and Tanzania represent some of '
                             "the continent's established agricultural exports.\n"
                             '\n'
                             'These commodities connect African producers and supply chains with food, '
                             'beverage and processing industries across international markets.',
                 'link_label': 'Explore Agricultural Commodities',
                 'direction': 'africa-to-europe',
                 'image_source': 'beverages'},
                {'title': 'Horticulture',
                 'slug': 'horticulture',
                 'summary': 'Fresh produce cultivated for demanding international markets.',
                 'overview': "Africa's varied climates and agricultural regions support the production of "
                             'fresh fruits, vegetables, avocados and flowers for export.\n'
                             '\n'
                             'Countries including Kenya, Morocco and Zimbabwe contribute to horticultural '
                             'trade, supplying products ranging from fresh produce to cut roses.',
                 'link_label': 'Explore Horticulture',
                 'direction': 'africa-to-europe',
                 'image_source': 'fresh-fruits-vegetables'},
                {'title': 'Raw Minerals & Metals',
                 'slug': 'raw-minerals-metals',
                 'summary': 'Resources supporting global industry and technology.',
                 'overview': 'Africa holds significant reserves of minerals and metals used across '
                             'manufacturing, infrastructure, energy and technology industries.\n'
                             '\n'
                             'Copper and cobalt from the Democratic Republic of Congo and Zambia, alongside '
                             'gold and platinum from South Africa and other producing regions, form part of '
                             "the continent's important mineral trade.",
                 'link_label': 'Explore Minerals & Metals',
                 'direction': 'africa-to-europe',
                 'image_source': None},
                {'title': 'Textiles & Apparel',
                 'slug': 'textiles-apparel',
                 'summary': 'African manufacturing reaching international consumers.',
                 'overview': "Africa's textile, clothing and footwear industries contribute to trade with "
                             'European markets, supported in some cases by preferential trade arrangements '
                             'such as Economic Partnership Agreements.\n'
                             '\n'
                             'The sector represents an important intersection between local manufacturing, '
                             'employment, international supply chains and access to overseas markets.',
                 'link_label': 'Explore Textiles & Apparel',
                 'direction': 'africa-to-europe',
                 'image_source': 'handicrafts-textiles'},
                {'title': 'Machinery & Appliances',
                 'slug': 'machinery-appliances',
                 'summary': 'Over €41 billion in machinery and appliances supporting industry, production '
                            'and infrastructure.',
                 'overview': 'Valued at more than €41 billion, machinery and appliances represent the '
                             'largest export category from Europe to Africa. The sector includes industrial '
                             'factory equipment, power generators and specialised machinery supporting '
                             'manufacturing, infrastructure development and productive industries across '
                             'African markets.',
                 'link_label': 'Explore Machinery & Appliances',
                 'direction': 'europe-to-africa',
                 'image_source': 'machinery-mechanical-appliances'},
                {'title': 'Transport Equipment',
                 'slug': 'transport-equipment',
                 'summary': 'Connecting people, businesses and economies.',
                 'overview': 'European transport exports to African markets include passenger vehicles, '
                             'heavy-duty trucks, commercial aircraft, railway equipment and related '
                             'transportation technologies.\n'
                             '\n'
                             'These products support passenger mobility, logistics, construction, public '
                             'transportation and commercial supply chains across the continent.',
                 'link_label': 'Explore Transport Equipment',
                 'direction': 'europe-to-africa',
                 'image_source': 'transportation-vehicles'},
                {'title': 'Chemicals & Pharmaceuticals',
                 'slug': 'chemicals-pharmaceuticals',
                 'summary': 'Supporting healthcare, agriculture and industry.',
                 'overview': 'European chemical and pharmaceutical exports serve a wide range of African '
                             'sectors.\n'
                             '\n'
                             'Products include pharmaceuticals and medical supplies as well as industrial '
                             'chemicals and synthetic fertilisers used by healthcare providers, agricultural '
                             'operations and industrial businesses.',
                 'link_label': 'Explore Chemicals & Pharmaceuticals',
                 'direction': 'europe-to-africa',
                 'image_source': 'chemicals-pharmaceuticals'},
                {'title': 'Refined Mineral Products & Fuels',
                 'slug': 'refined-mineral-products-fuels',
                 'summary': 'Energy products serving markets with diverse refining capacities.',
                 'overview': 'Refined petroleum products and fuels form another component of '
                             'Europe-to-Africa trade, particularly in markets where domestic refining '
                             'capacity does not fully meet demand.\n'
                             '\n'
                             'These products support transportation, industry, commercial activity and '
                             'broader energy requirements.',
                 'link_label': 'Explore Refined Products & Fuels',
                 'direction': 'europe-to-africa',
                 'image_source': 'refined-petroleum-minerals'},
                {'title': 'Agri-food & Foodstuffs',
                 'slug': 'agri-food-foodstuffs',
                 'summary': 'Food products connecting European producers with African consumers.',
                 'overview': 'European agricultural and food exports include wheat, dairy products and a '
                             'broad range of processed consumer foods.\n'
                             '\n'
                             'These goods form part of established food supply chains serving retail, '
                             'hospitality, food processing and consumer markets across Africa.',
                 'link_label': 'Explore Agri-food & Foodstuffs',
                 'direction': 'europe-to-africa',
                 'image_source': 'processed-foodstuffs-wheat'},
                {'title': 'Tobacco Products',
                 'slug': 'tobacco-products',
                 'summary': 'A regulated category within international trade.',
                 'overview': 'Tobacco products are also traded from European producers into certain African '
                             'markets. As a regulated product category, their importation, distribution and '
                             'sale are subject to the applicable laws, duties and public-health requirements '
                             'of individual markets.',
                 'link_label': 'Explore Trade Information',
                 'direction': 'europe-to-africa',
                 'image_source': None}],
 'legacy': {'cut-flowers': 'horticulture',
            'fresh-fruits-vegetables': 'horticulture',
            'beverages': 'agricultural-commodities',
            'nuts': 'agricultural-commodities',
            'fish': 'agricultural-commodities',
            'handicrafts-textiles': 'textiles-apparel',
            'natural-cosmetics': '@africa-to-europe',
            'machinery-mechanical-appliances': 'machinery-appliances',
            'electrical-equipment-technology': 'machinery-appliances',
            'transportation-vehicles': 'transport-equipment',
            'refined-petroleum-minerals': 'refined-mineral-products-fuels',
            'processed-foodstuffs-wheat': 'agri-food-foodstuffs'}}


def install(apps, schema_editor, overwrite=True):
    db = schema_editor.connection.alias
    def model(name): return apps.get_model('trade', name).objects.using(db)
    now = timezone.now()
    def singleton(name, values):
        obj, created = model(name).get_or_create(pk=1, defaults=values)
        if overwrite and not created: model(name).filter(pk=1).update(**values, updated_at=now)
        return obj
    singleton('SiteSettings', {'footer_copy': 'An informational platform focused on trade between African and European markets.'})
    new_home = not model('HomePage').filter(pk=1).exists()
    home = singleton('HomePage', DATA['home'])
    singleton('ContactPage', DATA['contact'])
    if overwrite: model('HomeFeature').filter(homepage_id=home.pk).delete()
    if overwrite or new_home:
        for order, (heading, text) in enumerate(DATA['features']):
            model('HomeFeature').create(homepage_id=home.pk, heading=heading, text=text, order=order)
    about, created = model('ContentPage').get_or_create(slug='about', defaults=dict(DATA['about'],published=True))
    if overwrite:
        model('ContentPage').filter(pk=about.pk).update(**DATA['about'],published=True,updated_at=now,seo_title='',meta_description='')
        model('ContentSection').filter(page_id=about.pk).delete()
    if created or (overwrite and not model('ContentSection').filter(page_id=about.pk).exists()):
        for order,(heading,text) in enumerate(DATA['about_sections']):model('ContentSection').create(page_id=about.pk,heading=heading,text=text,order=order)
    directions = {}
    for order, item in enumerate(DATA['directions']):
        values=dict(item,seed_key=item['slug'],published=True,indexable=True,order=order)
        obj = model('TradeDirection').filter(seed_key=item['slug']).first() or model('TradeDirection').filter(slug=item['slug']).first()
        if obj is None: obj=model('TradeDirection').create(**values)
        elif overwrite:
            # Preserve edited direction slugs, so existing links do not break.
            values.pop('slug');model('TradeDirection').filter(pk=obj.pk).update(**values,updated_at=now,seo_title='',meta_description='')
        directions[item['slug']]=obj
    categories = {}
    for order,item in enumerate(DATA['categories']):
        values={k:v for k,v in item.items() if k not in ('direction','image_source')}
        values.update(seed_key=item['slug'],direction_id=directions[item['direction']].pk,published=True,indexable=True,order=order,featured=order in (0,1,4,6))
        obj=model('TradeCategory').filter(seed_key=item['slug']).first() or model('TradeCategory').filter(slug=item['slug'],direction_id=values['direction_id']).first()
        if obj is None: obj=model('TradeCategory').create(**values)
        elif overwrite:
            values.pop('slug');model('TradeCategory').filter(pk=obj.pk).update(**values,updated_at=now,seo_title='',meta_description='')
        if overwrite:
            model('CategorySection').filter(category_id=obj.pk).delete()
            model('CategoryProduct').filter(category_id=obj.pk).delete()
        if item['image_source'] and not obj.image:
            previous=model('TradeCategory').filter(seed_key=item['image_source']).exclude(pk=obj.pk).first()
            if previous and previous.image:
                model('TradeCategory').filter(pk=obj.pk).update(image=previous.image.name,image_alt=previous.image_alt,image_caption=previous.image_caption)
        categories[item['slug']]=obj
    if overwrite:
        # Retain old categories and enquiry foreign keys, but remove superseded copy from public pages.
        for old_key,target in DATA['legacy'].items():
            for old in model('TradeCategory').filter(seed_key=old_key):
                direction=model('TradeDirection').get(pk=old.direction_id)
                destination=directions[target[1:]] if target.startswith('@') else categories[target]
                kind='TradeDirection' if target.startswith('@') else 'TradeCategory'
                model('URLHistory').filter(kind='TradeCategory',object_id=old.pk).update(kind=kind,object_id=destination.pk)
                model('URLHistory').update_or_create(path=f'/{direction.slug}/{old.slug}/',defaults={'kind':kind,'object_id':destination.pk})
                model('TradeCategory').filter(pk=old.pk).update(published=False,indexable=False,featured=False,updated_at=now)


class Migration(migrations.Migration):
    dependencies = [('trade','0010_approved_content_fields')]
    operations = [migrations.RunPython(install, migrations.RunPython.noop)]
