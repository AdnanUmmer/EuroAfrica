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

Startup performs no image installation, database changes or media-directory creation. It only starts:

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

No persistent disk is required to start the application. Remove MEDIA_ROOT=/var/data/media when no disk is mounted. Stock-image installation is a manual optional command (`python manage.py install_stock_images`), to run only after writable durable storage is configured. It is never run by start.sh. Existing image references and files are not replaced. Uploads on the free filesystem remain ephemeral.

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

## Startup and trailing-dot follow-up (18 September 2026)

The startup failure was caused by the old start.sh running install_stock_images whenever MEDIA_ROOT was set, then exiting on PermissionError because of set -e. A configured path is not proof that a disk exists. That command has been removed entirely from startup, including when MEDIA_ROOT is mistakenly still set.

The old SiteMiddleware compared raw request.get_host() against a configured netloc and built its Location directly from SITE_URL. A dotted, unnormalized SITE_URL in the older code could therefore produce the malformed permanent redirect; Django considers a trailing-dot Host valid for ALLOWED_HOSTS. The current settings normalization already strips a configured dot. This follow-up also normalizes both sides of middleware comparison (case, DNS trailing dot, default port) and revalidates the canonical redirect destination, with USE_X_FORWARDED_HOST=False explicitly set. SecurityMiddleware continues using SECURE_SSL_HOST derived from normalized SITE_URL and Render's forwarded HTTPS protocol. HTTPS protections remain enabled.

Live header inspection during this repair found HTTPS returning 200 without Location and HTTP returning one 301 to the correct HTTPS URL followed by 200. Directly requesting the dotted hostname returned a Render-edge 404 with x-render-routing: no-server; that request never reached Django. No live response adding a dot was observed. The exact historical deployed revision/environment or cached redirect responsible cannot be established from those current responses; a stale browser 301 is a possibility, not a verified cause. After redeployment, test with curl or a fresh browser session instead of assuming an old browser redirect is a new server response.

Keep SITE_URL=https://euroafrica-1u37.onrender.com, ALLOWED_HOSTS=euroafrica-1u37.onrender.com and CSRF_TRUSTED_ORIGINS=https://euroafrica-1u37.onrender.com, with no trailing hostname dot. Remove MEDIA_ROOT while there is no mounted disk. Keep build command bash build.sh and start command bash start.sh. RENDER=true is supplied by Render; no forwarded-host environment setting is required.

Verification: 33 Django tests pass, including HTTPS 200/no-self-redirect, dotted host/default port, dotted SITE_URL, one-hop HTTP redirect without .com./, ignored X-Forwarded-Host and invalid-host rejection. Fresh subprocesses load the production WSGI application with MEDIA_ROOT absent and with /var/data/media while directory creation is forced to fail; both succeed without startup management commands. start.sh is also checked to contain only the expected set/exec commands. This Windows environment has no Bash/Gunicorn runtime, so actual Linux Gunicorn process launch remains a Render deployment check. The existing verification script additionally checks the full Django redirect chain with an intentionally dotted SITE_URL.
