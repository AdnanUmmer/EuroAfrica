"""Download the individually reviewed free Unsplash photographs. No database writes."""
import html
import json
import re
from io import BytesIO
from pathlib import Path
from urllib.request import Request, urlopen
from PIL import Image, ImageOps

ASSETS = [
    ('trade', 'an-aerial-view-of-a-cargo-ship-in-the-ocean-0A7YwYhZhWw', 'Bent Van Aeken', 'Aerial view of a container ship at sea'),
    ('cut-flowers', 'red-roses-yPMJliKzyc4', 'Sidney Pearce', 'Red roses with layered petals'),
    ('fresh-fruits-vegetables', 'avocado-on-green-surface-0FS1bxTios8', 'Louis Hansel', 'Sliced avocado on a green surface'),
    ('beverages', 'coffee-beans-JS-QXqSGVE8', 'Alex Jones', 'Roasted coffee beans in processing equipment'),
    ('nuts', 'a-close-up-of-shelled-macadamia-nuts-in-a-container-ZxHmPAAWpfo', 'Madeline Liu', 'Shelled macadamia nuts in a container'),
    ('fish', 'raw-fish-fillets-on-ice-at-a-market-stall-GIpcS2IXsdc', 'Geoffrey Moffett', 'Fish fillets displayed on ice'),
    ('handicrafts-textiles', 'woven-baskets-and-hats-displayed-on-a-textured-surface-lA3cILAjlcc', 'Anes mchayaa', 'Woven baskets and hats on a textured surface'),
    ('natural-cosmetics', 'handmade-soaps-and-natural-beauty-products-displayed-on-wooden-shelves-aDx3Kb7QdPI', 'Kawê Rodrigues', 'Soaps and personal-care products on wooden shelves'),
    ('machinery-mechanical-appliances', 'industrial-machinery-with-pipes-and-valves-sIfOwIa8Lq0', 'Dave Meckler', 'Industrial machinery with pipes and valves'),
    ('chemicals-pharmaceuticals', 'pile-of-blister-packs-of-colorful-medicine-tablets-m1Hq4ibP9rc', 'Volodymyr Hryshchenko', 'Tablets in blister packaging'),
    ('electrical-equipment-technology', 'blue-circuit-board-jXd2FSvcRr8', 'Umberto', 'Electronic components on a printed circuit board'),
    ('transportation-vehicles', 'assortment-of-assorted-vehicle-lights-in-bins-uNKJQv_aRog', 'Diego Romeo', 'Vehicle lights organized in storage bins'),
    ('refined-petroleum-minerals', 'oil-refinery-by-a-river-at-dusk-EbISsANu3Iw', 'Anthony Maw', 'Distillation structures at a refinery at dusk'),
    ('processed-foodstuffs-wheat', 'wheat-grain-in-focus-photography-during-sunset-yOQntxCp0r0', 'Ann Savchenko', 'Wheat heads in evening light'),
]

IMAGE_IDS = ['1724597500306-a4cbb7d1324e', '1518709779341-56cf4535e94b', '1579254646899-04ad03b05cdc', '1414808549009-35951c724e9f', '1761095596792-2735f03c7418', '1773739685848-a46fb41ae4f0', '1756374190688-a75e7bfd2c64', '1781451481507-a136c5488f79', '1773517458853-1afbaee86901', '1577401132921-cb39bb0adcff', '1562408590-e32931084e23', '1777213003360-0419fd2fbfdf', '1743723180480-243b89c5ebaa', '1531603845872-e4a07041f521']

def get(url):
    return urlopen(Request(url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=45).read()

def main():
    folder = Path('assets/stock'); folder.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((folder / 'manifest.json').read_text()) if (folder / 'manifest.json').exists() else []
    for (key, slug, author, alt), image_id in zip(ASSETS, IMAGE_IDS):
        if any(item['key'] == key for item in manifest): continue
        source = 'https://unsplash.com/photos/' + slug
        try:
            url = 'https://images.unsplash.com/photo-' + image_id
            url += '?auto=format&fit=max&w=1600&q=85'
            im = ImageOps.exif_transpose(Image.open(BytesIO(get(url))))
            im.thumbnail((1600, 1600))
            im.convert('RGB').save(folder / f'{key}.webp', 'WEBP', quality=83)
            manifest.append(dict(key=key, file=f'{key}.webp', source=source, author=author, alt=alt, image_url=url, license='Unsplash License', license_url='https://unsplash.com/license', attribution='Not required; credited in asset register', retrieved='2026-09-17', context='Illustrative stock photograph; no EuroAfrica ownership, location, supplier or origin claim.'))
            (folder / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
            print(key, im.size, 'downloaded', flush=True)
        except Exception as error:
            print(key, type(error).__name__, str(error), flush=True)
    print(f'{len(manifest)}/{len(ASSETS)} downloaded')

if __name__ == '__main__': main()
