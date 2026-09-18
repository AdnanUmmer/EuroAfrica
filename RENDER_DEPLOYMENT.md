# Render deployment repair

## Root cause and evidence

`euroafrica/urls.py` already maps the empty path `/` to `trade.views.home`, which renders `trade/home.html`. There is no `trade/urls.py`; the unused `accounts/urls.py` is not included in the root URLconf. The homepage uses `get_object_or_404(HomePage, pk=1)`. Migrations through 0005 created tables and footer links, **not the required HomePage, SiteSettings or ContactPage rows**. The old build command never ran `seed_content`. A new PostgreSQL database therefore had valid schema but no homepage record, producing the application-level 404.

This was reproduced against a disposable fresh database with DEBUG=false and the actual Render hostname: migration-only GET `/` returned 404 with zero HomePage rows; migration 0006 changed it to 200 with no redirect. The reproduction uses SQLite for isolation; it does not access or change the live PostgreSQL database. The public URL could not be inspected through the available web fetcher. Live confirmation remains necessary after deployment.

Migration 0006 creates only missing required singleton records from historical defaults. Existing owner text and image references are preserved. `build.sh` also runs the existing idempotent `seed_content` command, providing both directions, 13 categories, About, the private privacy draft and Editor permissions on a new database. The request handler and page design are unchanged; no database writes were added to GET requests.

## Render settings

Set **Build Command** to:

```bash
bash build.sh
```

This executes:

```bash
python -m pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate --noinput
python manage.py seed_content
python manage.py check
```

Set **Start Command** to:

```bash
bash start.sh
```

This installs starter photos into empty image fields only when MEDIA_ROOT is configured, then starts:

```bash
gunicorn euroafrica.wsgi:application --bind "0.0.0.0:${PORT:-10000}"
```

The original `gunicorn euroafrica.wsgi` entry point was valid and was not the cause of the 404. An explicit port binding makes the Render port contract clear. The existing build command also receives the singleton repair through `migrate`; using `build.sh` additionally initializes the category content.

Required dashboard environment values (plain values, no quotes/brackets):

```dotenv
DEBUG=False
SECRET_KEY=<existing strong random secret, at least 50 characters; do not rotate unnecessarily>
DATABASE_URL=<existing working Render PostgreSQL URL>
ALLOWED_HOSTS=euroafrica-1u37.onrender.com
SITE_URL=https://euroafrica-1u37.onrender.com
CSRF_TRUSTED_ORIGINS=https://euroafrica-1u37.onrender.com
STAGING=false
INDEXABLE=false
```

Keep INDEXABLE=false until the privacy notice, public contact details and launch checklist are approved, then deliberately set it true on production. Render supplies RENDER=true and PORT automatically; do not manually set PORT. TRUST_LOCAL_PROXY is not needed on Render. Keep it false unless a separate trusted local proxy is actually configured. Existing optional SMTP and Search Console variables remain supported.

`SITE_URL` is validated as an origin. Whitespace, a trailing hostname dot and default HTTPS port are normalized. Paths, credentials, fragments, queries, localhost/loopback and insecure production origins are rejected at startup. The canonical hostname must be in ALLOWED_HOSTS. Django now reads the CSRF_TRUSTED_ORIGINS environment variable. PREPEND_WWW=false and APPEND_SLASH=true are explicit. Render's forwarded HTTPS header prevents a redirect back to the same HTTPS URL; plain HTTP still permanently redirects to the canonical HTTPS host. Secure cookies, HSTS, PostgreSQL and HTTPS enforcement remain enabled.

Do not enable HSTS_INCLUDE_SUBDOMAINS or HSTS_PRELOAD simply to silence checks. Their default false values produce Django warnings W005/W021, intentionally documented pending a domain-wide HTTPS/preload decision.

## Uploaded images: immediate deployment issue

WhiteNoise correctly serves **collected static files**, not admin uploads. Previously DEBUG=false also removed the only `/media/` route, and Render has no project Nginx configuration. The Render-only media handler now streams validated image file extensions with bounded filesystem paths, cache headers and nosniff; missing files and traversal attempts return 404. Admin uploads retain the existing Pillow validation/re-encoding. This handler suits this small informational site; object storage/CDN is preferable if traffic or horizontal scaling grows.

For reliable uploads, attach a **persistent disk** to the web service at `/var/data` and add:

```dotenv
MEDIA_ROOT=/var/data/media
```

The disk requires a paid Render service. A free service's writable filesystem is ephemeral; setting MEDIA_ROOT alone does not make it persistent. Without persistent storage, do not rely on saved admin uploads surviving deploys. Existing local media files are not in Git: copy owner uploads into the matching paths on the persistent disk if migrating an existing content database. Never clear image fields just to hide missing files.

Render disks are unavailable during build and pre-deploy, so starter-image installation is in `start.sh`, after the disk is mounted. Existing image references and files are not replaced. If a paid disk is unavailable, external object storage is a separate infrastructure requirement; it has not been silently substituted.

## Verification performed

- `manage.py check`: no issues, using explicit local test environment values. The local `.env` initially failed the existing production-secret guard; it was not changed or printed.
- `manage.py test trade --noinput`: 25 tests passed, including canonical configuration regression coverage.
- `manage.py makemigrations --check --dry-run`: no model drift.
- `scripts/check_production.py`: production-oriented deploy checks and manifest static collection passed; this existing helper explicitly opts into HSTS subdomains/preload for its isolated checks.
- A second `check --deploy` using Render-style settings with the actual default HSTS opt-ins disabled exited 0 with only W005/W021, as explained above; no warnings were silenced.
- `scripts/verify_render.py`: reproduces the original fresh-database 404 before migration 0006, verifies `/` resolves to the intended view, asserts migration-only `/` and `/contact/` return 200 with no Location header behind Render-style HTTPS, checks owner-content preservation, repeated seeding, all 13 categories, About, canonical, HTTP redirect, HSTS, missing-page 404, WhiteNoise files and media path protection.

The isolated script uses disposable SQLite and throwaway secrets. Production DATABASE_URL remains PostgreSQL. No production database credentials, Render dashboard access, real SMTP, disk mount or live redeployment were tested or changed.

## Deploy and confirm

Commit/push the repair on the linked main branch. Render redeploys automatically only if this service is connected to that repository/branch and Auto-Deploy is enabled. Otherwise choose **Manual Deploy -> Deploy latest commit**. Check logs for migration 0006, seeding and Gunicorn startup.

From a terminal after Render reports Live:

```bash
curl -I https://euroafrica-1u37.onrender.com/
curl -I https://euroafrica-1u37.onrender.com/contact/
curl -I https://euroafrica-1u37.onrender.com/africa-to-europe/
curl -I https://euroafrica-1u37.onrender.com/not-a-real-page/
```

Expected: 200, 200, 200, 404. The first HTTPS request must have no Location header. Open homepage/admin and verify actual CSS and image URLs. In the Render shell, confirm singleton records if diagnosis is still needed:

```bash
python manage.py shell -c "from trade.models import HomePage, SiteSettings, ContactPage; print({m.__name__: m.objects.filter(pk=1).exists() for m in (HomePage, SiteSettings, ContactPage)})"
python manage.py check --deploy
```

Do not run seed commands against a different database URL or publish the placeholder privacy notice. Configure the public contact email and complete the launch checks before enabling search indexing.

References: https://render.com/docs/deploy-django ; https://render.com/docs/disks ; https://render.com/docs/deploys .
