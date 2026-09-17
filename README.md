# EuroAfrica

Server-rendered Django 5.2 LTS corporate website. Two trade directions, thirteen editable categories, category product examples, editorial sections, galleries, contact enquiries, and a content-focused Django admin. No storefront or public account system is installed. The pre-existing `accounts/`, `templates/`, and `README_AUTH_SYSTEM.md` files are preserved but are not loaded by this project.

## Local setup (Windows PowerShell, Python 3.12+)

```powershell
cd "C:\Users\10adn\OneDrive\Documents\New project"
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_content
.\.venv\Scripts\python.exe manage.py install_stock_images
.\.venv\Scripts\python.exe manage.py createsuperuser
.\.venv\Scripts\python.exe manage.py runserver
```

If `python` is not installed on PATH, install Python 3.12+ or use its absolute executable path for the first command. A working `.venv` has already been created in this workspace; use its Python directly to run the existing installation. Do not replace an existing `.env` when repeating setup.

Open http://127.0.0.1:8000/ and http://127.0.0.1:8000/admin/. The local database is SQLite unless DATABASE_URL is supplied. The seed command uses stable internal identifiers and is repeatable without overwriting owner edits, including changed slugs.

## Checks

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test trade
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py collectstatic --noinput
.\.venv\Scripts\python.exe manage.py launch_check
```

`launch_check` intentionally fails in the default local configuration. Indexing is disabled until explicitly enabled. See [DEPLOYMENT.md](DEPLOYMENT.md), [OWNER_GUIDE.md](OWNER_GUIDE.md), and [VERIFICATION.md](VERIFICATION.md).

## Architecture

- `euroafrica/`: environment configuration, URL routing, WSGI.
- `trade/models.py`: CMS, enquiries, permanent redirect history and shared rate-limit counters.
- `trade/admin.py`: content editing, inlines, search, filters and previews.
- `trade/views.py`: HTML pages, contact handling, XML sitemap and robots.
- `trade/templates/`: semantic templates; plain text content is auto-escaped.
- `trade/static/trade/`: local CSS, actual extracted logo and intentional illustration placeholder.
- `trade/management/commands/`: initial content, launch checks and anti-spam counter maintenance.

No JavaScript is needed for public navigation, content or form submission. The mobile menu uses native HTML `details`/`summary`. System Georgia and Arial avoid external font requests. Content uploads are validated and re-encoded as WebP, capped at 1600px, with 480px/960px variants for larger uploads. Media filenames are randomized. Draft text and previews require permission; uploaded images are public website assets, so do not upload confidential material.

## Assets and content status

The logo was extracted from the **first page** of the supplied Euroafrica logo2.pdf, removing the presentation watermark form and cropping out the swatches. The original blue/gold gradients are preserved. `logo.png` is a transparent web asset, not a redrawn logo.

The original local vector illustration is a schematic connection graphic, not a geographic reference map or a photograph of company operations. The schematic remains a fallback for optional empty image fields. Replace any installed photograph through its owning admin page. Fourteen individually reviewed photographs are now bundled locally under the Unsplash License; sources, authors and rights are recorded in `assets/stock/README.md` and `manifest.json`. The installer fills only empty image fields and preserves existing uploads. All stock images are illustrative, not company-operation claims. Privacy starts as an unpublished owner-review draft. Company identity, public contact details and actual supply/service capabilities require owner verification.

Django 5.2 LTS was selected using the official support information: https://www.djangoproject.com/download/. Installed version during verification: 5.2.17. Dependency ranges allow patch updates; validate updates in staging and keep a deployment-specific lock with `pip freeze` after testing.

## Content studio upgrade

The shared floating notch navigation appears on every public template. The navy footer, images, captions, crop focus, legal line and navigation links are editable through the branded content studio. Public pages use a consistent editorial layout; the admin retains Django permissions, CSRF and validation with task-based navigation, real counts, preview widgets and responsive forms.

For production-mode verification without changing local settings:

```powershell
.\.venv\Scripts\python.exe scripts/check_production.py
.\.venv\Scripts\python.exe scripts/smoke_production.py
```

The second script uses an isolated SQLite database; actual PostgreSQL and Linux/proxy validation remain deployment steps. See `VERIFICATION.md` for measured results and limitations.
