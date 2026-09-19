"""One-time enrichment of unchanged starter copy; owner revisions stay intact."""
from django.db import migrations
from django.utils import timezone

ROWS = [('cut-flowers',
  'Cut flowers bring together distinct shapes, stem structures and colour palettes for floral arrangements. Roses '
  'offer a recognisable focal flower; summer flowers introduce variety; alstroemeria adds clusters of patterned '
  'blooms.\n'
  '\n'
  'When discussing this category, identify the flower type, preferred colour and intended use. Variety, handling '
  'and timing are useful topics for a detailed enquiry.',
  'Planning a flower enquiry',
  'Begin with the flower and the role it will play in an arrangement. A rose used as a focal bloom calls for a '
  'different brief from a mixed selection of summer flowers. For alstroemeria, describe the preferred colours and '
  'presentation rather than assuming a standard assortment.\n'
  '\n'
  'Include the intended delivery period, destination and approximate number of stems or bunches. Ask how the '
  'flowers would be packed and handled, and which product details can be confirmed. The category listing alone '
  'does not establish a harvest schedule, stem grade or shipment arrangement.'),
 ('fresh-fruits-vegetables',
  'Avocados, mangoes and passion fruit sit alongside green beans and peas in this category. The examples '
  'represent different textures, preparation methods and uses, from fresh consumption to ingredients in cooking.\n'
  '\n'
  'A useful produce enquiry names the item and its intended application. Ripeness, presentation and handling '
  'requirements vary by product and should be discussed individually.',
  'Describing the produce you need',
  'An enquiry about mangoes or avocados should distinguish fruit for immediate consumption from fruit intended '
  'for further preparation. Passion fruit, green beans and peas also need separate product descriptions; a mixed '
  'produce request is clearer when each item is listed individually.\n'
  '\n'
  'Describe the destination, intended use, approximate quantity and preferred pack format. Ask about the '
  'available variety, condition and handling information for each item. These questions establish a practical '
  'discussion without assuming a season, origin, certification or confirmed availability.'),
 ('beverages',
  'Tea and coffee offer distinct ways to explore the beverage category. Premium black tea and specialty purple '
  'tea are presented alongside Kenyan coffee, retaining the specific origin named in the supplied category '
  'information.\n'
  '\n'
  'These examples do not describe the origin of every African beverage. Enquiries can distinguish between tea and '
  'coffee and specify the desired format or intended use without assuming a particular grade or certification.',
  'Tea and coffee: useful distinctions',
  'For tea, start by identifying whether your interest is black tea or purple tea and whether the discussion '
  'concerns loose tea, packaged tea or an ingredient. For Kenyan coffee, specify whether you are asking about '
  'beans or another preparation and how the coffee would be used.\n'
  '\n'
  'Flavour preferences, pack size and intended audience help make an enquiry specific. Request the product '
  'information needed to compare options rather than treating terms such as premium or specialty as a verified '
  'grade. Origin and processing details should be established for the individual product.'),
 ('nuts',
  'Macadamia nuts are valued in a range of food preparations, from simple snack formats to baking and '
  'confectionery. This category focuses on macadamias rather than implying a broader range of nuts.\n'
  '\n'
  'For an enquiry, it helps to specify the intended preparation and whether the discussion concerns whole nuts or '
  'an ingredient format. Processing, packaging and allergen information need to be established for the particular '
  'product.',
  'Preparing a macadamia enquiry',
  'A macadamia brief can distinguish a finished snack from an ingredient used in a recipe or manufacturing '
  'process. Describe whether whole nuts or smaller pieces would suit the application, and whether the intended '
  'preparation calls for an unseasoned or otherwise specified format.\n'
  '\n'
  'Include the quantity, packaging preference and destination. Ask for ingredient, allergen and handling '
  'information relevant to the item under discussion. This page introduces macadamias only; additional nut '
  'varieties, processing options and particular quality grades are not confirmed by the category listing.'),
 ('fish',
  'This category includes Nile perch as a named example, together with other fish fillets. Species and '
  'presentation are important distinctions; the general reference to fillets does not identify additional species '
  'or their origins.\n'
  '\n'
  'A category enquiry should name the fish where known and describe the required presentation. Handling, '
  'traceability and applicable requirements should be clarified before any specific trade discussion.',
  'Making a fish-fillet brief precise',
  'State whether your enquiry concerns Nile perch or another identified fish species. If the species is not yet '
  'known, say so rather than relying on the broad label fish fillets. Describe the desired cut, portion size and '
  'intended use to distinguish otherwise different requests.\n'
  '\n'
  'Ask about product presentation, handling information and traceability documents for the particular item. '
  'Quantity, destination and intended timing provide useful context for a response. The overview does not '
  'establish catch origin, processing conditions or the availability of a particular shipment.'),
 ('handicrafts-textiles',
  'Handicrafts and textiles bring together decorative and practical objects. Traditional jewellery, woven '
  'baskets, leather goods and fabrics such as kikoys each have distinct materials, construction methods and '
  'uses.\n'
  '\n'
  'This overview does not attribute items to a particular maker or community. Enquiries can describe the object, '
  'material and intended use, with provenance and production details left for verification.',
  'Materials, dimensions and provenance',
  'A woven basket, a piece of jewellery, a leather item and a kikoy fabric each need a different description. '
  'Specify the material where known, intended use, dimensions and any colour or pattern preferences. Reference '
  'photographs can be discussed after initial contact rather than assuming a catalogue item is available.\n'
  '\n'
  'Ask about the maker, production method and provenance when those details matter to your enquiry. A broad '
  'category name does not identify a particular community or certify how an item was made. Keep questions about '
  'quantities and presentation separate from claims that still require verification.'),
 ('natural-cosmetics',
  'Essential oils, soaps and shea-based body creams represent different product formats within personal care. '
  'Ingredient composition, fragrance and intended use help distinguish one item from another.\n'
  '\n'
  'The category name is descriptive and does not establish organic certification, safety approval or therapeutic '
  'benefits. Specific ingredient lists, labelling and market requirements need to be checked for individual '
  'products.',
  'Product format and intended use',
  'An essential oil enquiry should identify the named oil and intended application; a soap or shea-based body '
  'cream enquiry should describe the finished product format. Fragrance preferences, packaging and intended '
  'audience may help distinguish the request without making assumptions about the formulation.\n'
  '\n'
  'Ask for the specific ingredient list and relevant product documentation before drawing conclusions about '
  'suitability. Natural is a category description here, not proof of certification or a health benefit. This '
  'overview does not provide medical advice or establish that a formulation is approved for a particular market.'),
 ('machinery-mechanical-appliances',
  'This category covers boilers and specialized factory machinery used in manufacturing and processing. The '
  'intended process is central to understanding a machine: equipment for one application may differ substantially '
  'from equipment for another.\n'
  '\n'
  'Useful enquiry details include the process, operating environment and technical specification. This overview '
  'does not confirm equipment availability, installation services or a particular manufacturer.',
  'Writing a machinery specification',
  'Identify the process before naming a preferred machine. For a boiler or manufacturing appliance, describe the '
  'application, desired capacity and operating environment using the information you already have. If the '
  'specification is incomplete, separate confirmed requirements from questions that need further discussion.\n'
  '\n'
  'Include any known power, space or compatibility constraints and the destination of use. Ask which technical '
  'documentation would be needed to evaluate a particular machine. Installation, servicing, training and '
  'spare-parts support should be discussed separately; none is implied by a category overview.'),
 ('chemicals-pharmaceuticals',
  'Medicines and vaccines have different purposes and requirements from industrial chemical compounds or '
  'agricultural fertilizers. They are grouped here as supplied examples, while retaining those important '
  'distinctions.\n'
  '\n'
  'A specific enquiry should clearly identify the product type and intended application. This informational '
  'overview makes no claim of authorization to supply regulated products or of regulatory approval in any market.',
  'Separate briefs for distinct product types',
  'Begin by identifying whether the request concerns a medicine, vaccine, chemical compound or agricultural '
  'fertilizer. These are separate applications, so a general request for chemicals is unlikely to contain enough '
  'information for a useful response. Use an exact product name or specification where one is known.\n'
  '\n'
  'State the intended use and destination, and ask what documentation would be necessary before any detailed '
  'discussion. Do not infer an authorization, registration or handling capability from inclusion on this website. '
  'Product-specific requirements need assessment by the appropriate qualified parties.'),
 ('electrical-equipment-technology',
  'Electrical equipment and technology span industrial control, communications and medical applications. The '
  'examples in this category are industrial electronics, telecommunications equipment and high-tech medical '
  'apparatus.\n'
  '\n'
  'Technical compatibility, intended use and the operating setting are useful starting points for an enquiry. No '
  'particular brand, certification, support service or medical-device authorization is implied.',
  'Compatibility before comparison',
  'Industrial electronics, telecommunications equipment and medical apparatus should be described by their '
  'function and operating context. Include known model identifiers, interfaces or system requirements when the '
  'enquiry concerns compatibility with existing equipment. Clearly mark any specification that is still '
  'uncertain.\n'
  '\n'
  'A useful brief also explains the destination and intended application. Ask about technical documentation and '
  'distinguish product questions from questions about installation or support. This category does not establish a '
  'brand relationship, device approval or after-sales service commitment.'),
 ('transportation-vehicles',
  'Transportation encompasses complete motor vehicles as well as components and specialist aircraft equipment. '
  'These items serve different applications and should be identified separately in a detailed discussion.\n'
  '\n'
  'For spare parts, precise part identification and compatibility are useful enquiry details. The category '
  'overview does not confirm a vehicle inventory, aircraft capability or maintenance service.',
  'Identifying vehicles and components',
  'For a motor vehicle, describe the vehicle type and intended application. For an automotive spare part, include '
  'the part identifier and relevant vehicle information where available. Aircraft equipment should be identified '
  'separately so it is not confused with general automotive components.\n'
  '\n'
  'Clarify whether the discussion concerns a complete item or a replacement component and provide the destination '
  'of use. Ask what compatibility and product records would be needed to assess the request. No inventory, '
  'maintenance service or technical authorization is established by these informational examples.'),
 ('refined-petroleum-minerals',
  'The supplied category heading is broad; its named examples are specialized oils and distillation products. '
  'This page keeps the focus on those examples without introducing unconfirmed mineral types or additional '
  'petroleum products.\n'
  '\n'
  'The intended application and relevant specification help distinguish materials within the category. Product '
  'composition, handling information and suitability require individual verification.',
  'Use the material specification',
  'Specialized oils and distillation products are more clearly described by their intended application and known '
  'specification than by a broad industrial label. Include the product name or reference where available, and '
  'distinguish a confirmed requirement from a material you are still investigating.\n'
  '\n'
  'Quantity, packaging and destination are useful discussion points. Ask about composition and handling '
  'documentation for the individual material. Although the category heading also mentions minerals, the supplied '
  'examples do not identify particular mineral products; additional supply capabilities should not be inferred.'),
 ('processed-foodstuffs-wheat',
  'Wheat and other cereals form one part of this category, alongside dairy items and European beverages and '
  'spirits. The range includes ingredients and finished food or beverage formats with different storage and '
  'presentation needs.\n'
  '\n'
  'Enquiries should identify the product and intended use. Labelling, ingredients and any market-specific '
  'requirements need to be considered for each item; this overview does not confirm specific brands or '
  'availability.',
  'Ingredients and finished products',
  'Separate a request for wheat or other cereals from a request for dairy items or European beverages and '
  'spirits. Explain whether the item would be used as an ingredient or supplied in a finished presentation, and '
  'name the product rather than relying only on its broad food category.\n'
  '\n'
  'Describe the intended use, destination and pack format. Ask about ingredient information, labelling and '
  'handling for the specific item. Any brand, origin, certification or availability question remains to be '
  'confirmed individually; this overview is an introduction to the listed product types.')]


def enrich(apps, schema_editor):
    Category = apps.get_model('trade', 'TradeCategory')
    Section = apps.get_model('trade', 'CategorySection')
    Direction = apps.get_model('trade', 'TradeDirection')
    db = schema_editor.connection.alias
    for key, original, heading, text in ROWS:
        category = Category.objects.using(db).filter(seed_key=key, overview=original).first()
        if category and not Section.objects.using(db).filter(category_id=category.pk).exists():
            Section.objects.using(db).create(category_id=category.pk, heading=heading, text=text, order=10)
            now = timezone.now()
            Category.objects.using(db).filter(pk=category.pk).update(updated_at=now)
            Direction.objects.using(db).filter(pk=category.direction_id).update(updated_at=now)


class Migration(migrations.Migration):
    dependencies = [('trade', '0008_enquiry_protection')]
    operations = [migrations.RunPython(enrich, migrations.RunPython.noop)]
