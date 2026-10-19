# Approved content and enquiry release

The supplied copy replaces the homepage, both trade-direction introductions, ten category pages, About and Contact. The machinery figure (€41 billion) is retained exactly as supplied; no source or year has been invented. Four Africa-to-Europe and six Europe-to-Africa categories are published. All copy remains server-rendered and editable in admin.

## Content migration

- `0010_approved_content_fields` adds homepage detail/final CTA fields, direction heading, category CTA label, ordered HomeFeature and ContentSection models, and enquiry interest/market fields.
- `0011_approved_website_content` is a one-time approved-copy release. It replaces the relevant editorial text, clears superseded category product/section copy, archives old category records and creates permanent redirects. Existing enquiries, their category references, statuses and image files are retained. Existing image selections remain; suitable images are reused for new categories.
- Back up the production database before migrating. This content release has no automatic editorial rollback; restore from the backup if needed. Subsequent `seed_content` runs preserve later owner edits.
- Raw Minerals & Metals and Tobacco Products use the existing illustration fallback because no suitable approved photograph was supplied. Images remain editable in admin.

## Enquiries, admin and protection

Fields: full name*, company/organisation, business email*, phone, trade direction*, product/category* (including General/not yet sure), country/market, enquiry*, and consent*. Cross-direction category selections are rejected with a useful validation message.

Existing CSRF, honeypot, signed minimum/maximum submission timing, database rate limits, duplicate/replay protection, server validation and Turnstile remain active. Duplicate detection now includes the newly collected enquiry context. Turnstile server-side verification is unchanged and checks success, hostname and action; production rejects missing/invalid configuration or failed verification. Tokens, raw IPs and browser fingerprints are not stored.

Admin displays/searches the new fields and retains status filtering/actions. Legitimate enquiries save before notification delivery. Notifications use configured sender/recipient with the validated visitor address as Reply-To. SMTP failure preserves the enquiry; rejected spam receives no email. Existing confirmation and double-submit prevention remain.

## Configuration and Cloudflare

**Rotate the Turnstile secret:** a real-looking secret was already present in tracked `.env.example`. It has been removed from the working file, but remains exposed in earlier Git history. Rotate it in Cloudflare and update Render; do not reuse it. No credentials were changed remotely.

Use the existing Cloudflare Turnstile widget in **Managed** mode. Authorize the exact hostname serving the site (without scheme or path). Add the eventual custom hostname when switching domains. Put its site key and newly rotated secret in Render environment variables. Do not create a second widget or enable test keys in production. The frontend submits action `enquiry`; backend verifies it against the configured SITE_URL hostname.

Required production variables (angle-bracket values are instructions, not literal values):

```dotenv
DEBUG=False
SECRET_KEY=<existing strong private Django secret>
DATABASE_URL=<existing Render PostgreSQL connection URL>
SITE_URL=https://<current production hostname>
ALLOWED_HOSTS=<current production hostname>
CSRF_TRUSTED_ORIGINS=https://<current production hostname>
TURNSTILE_SITE_KEY=<existing widget public site key>
TURNSTILE_SECRET_KEY=<newly rotated widget secret>
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=<SMTP provider hostname>
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
EMAIL_HOST_USER=<SMTP login>
EMAIL_HOST_PASSWORD=<SMTP password>
DEFAULT_FROM_EMAIL=<verified sender address>
CONTACT_NOTIFICATION_EMAIL=<recipient inbox>
STAGING=False
```

Preserve existing working SMTP port/TLS settings if your provider or Render plan requires different ones. Confirm outbound SMTP availability for your plan. Domain and `INDEXABLE` were not changed by this release; keep indexing disabled until the intended launch. Do not configure `/var/data` without a persistent disk. Public contact details and the approved privacy notice must be completed in admin before collecting live enquiries.

## Deployment commands

With the intended production environment configured and a backup taken:

```sh
python -m pip install -r requirements.txt
python manage.py migrate --noinput
python manage.py seed_content
python manage.py link_stock_images
python manage.py collectstatic --noinput
python manage.py check
python manage.py makemigrations --check --dry-run
```

Render already supports these through `bash build.sh`; keep `bash start.sh` as the start command. Startup only starts Gunicorn and requires no persistent disk. Push the reviewed changes to the linked deployment branch. Render redeploys automatically only if Auto-Deploy is enabled; otherwise choose Deploy latest commit. If the service uses a custom build command, ensure it includes migrate/seed/link steps above. No DNS or database credential changes are required.

At launch, set the final domain consistently, review/publish the privacy notice, set a verified public email, enable production indexing, then run `python manage.py launch_check`. Submit `/sitemap.xml` to Search Console and verify canonical URLs, robots directives and indexing. Send one real enquiry and confirm its admin record and inbox notification.

## Verified results and limits

- 72 Django tests passed, covering approved content, migration preservation/redirects, enquiry validation, consent, honeypot, timing, rate limiting, Turnstile rejection/success simulations, replay/duplicates, SMTP failure and admin permissions/actions.
- Django check: zero issues. Migration drift: none. collectstatic: 132 files present.
- Render verification script passed with production settings on disposable SQLite: homepage/contact 200 behind HTTPS proxy, canonical one-hop HTTP redirects, trailing-dot normalization, WhiteNoise, media, admin recovery and migration preservation.
- Rendered SEO audit: 15 pages and 15 canonical sitemap entries, zero errors, with indexing enabled only inside the audit process.
- Browser checks: homepage, Contact and machinery category at 320, 768 and 1440px; one H1 each and no horizontal overflow. Mobile hero, tablet Contact and desktop hero visually reviewed.
- Production-media audit: 13 referenced images plus emitted responsive variants returned 200.
- `git diff --check` passed. `.env.example` now contains empty Turnstile values; no new credentials were added.

Tests used isolated local databases and simulated external verification/email. Live PostgreSQL, real Turnstile, SMTP delivery and field Core Web Vitals have not been certified by these checks. Production credentials, DNS and production database were not modified. Privacy publication, secret rotation and a live enquiry smoke test remain launch requirements.

## Changed files

`.env.example`; `APPROVED_CONTENT_RELEASE.md`; `assets/stock/bindings.json`; `scripts/verify_render.py`; `trade/approved_content.json`; `trade/models.py`; `trade/admin.py`; `trade/forms.py`; `trade/views.py`; `trade/antispam.py`; `trade/signals.py`; `trade/management/commands/seed_content.py`; `trade/migrations/0010_approved_content_fields.py`; `trade/migrations/0011_approved_website_content.py`; `trade/static/trade/site.css`; templates `trade/templates/trade/{home,direction,category,cards,page,contact}.html`; `trade/test_helpers.py`; `trade/tests.py`; `trade/test_readiness.py`; `trade/test_seo_readiness.py`; `trade/test_approved_content.py`.
