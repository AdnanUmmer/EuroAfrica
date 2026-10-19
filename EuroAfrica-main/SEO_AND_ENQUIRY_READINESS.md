# SEO and enquiry readiness — 19 September 2026

## Scope and results

Implemented in the working tree; no domain, DNS, production environment, production database, account or password was changed. Indexing remains opt-in for the real launch. These changes have not been pushed or deployed during this task.

The final suite passes **68 tests**. The rendered SEO audit passes for **18 public pages and 18 canonical sitemap URLs** with simulated indexing enabled only inside the audit process. This is a technical foundation, not a ranking guarantee or a Lighthouse score.

## A. Existing issues

The enquiry form already used CSRF, Django validation, a ten-per-hour database counter and a hidden-input honeypot. It lacked server-side Turnstile, signed timing, duplicate/replay handling and explicit consent. A bot able to submit a valid-looking form could therefore cause repeated notifications. Rate limiting primarily used the proxy socket address on Render. Emails used configured recipients but lacked Reply-To. Admin had the original New/In progress/Resolved statuses and no status actions.

SEO already had server-rendered pages, descriptive paths, editable metadata, canonicals, breadcrumbs, structured data and a publication-aware sitemap. Improvements were needed for category-specific title context, useful additional content, sharing defaults, image sizing hints, parent-dependent sitemap dates and a reusable rendered audit. Search indexing is intentionally still disabled pending your real hosting launch.

## B. Implemented enquiry flow

1. Django CSRF remains enabled. No csrf_exempt was added.
2. A cheap per-address limit runs first to bound malformed POSTs and remote verification costs: 10 attempts per fixed ten-minute window. Rate-limited responses are 429 with Retry-After.
3. Django validates lengths, email, required name/message, an enquiry type selected from published categories or General enquiry, and consent. International names remain valid. Existing optional phone/company fields remain.
4. A visually offscreen text honeypot has tabindex=-1, autocomplete=off and an aria-hidden container. It is not a hidden input. Filled values reject the enquiry without mail.
5. A Django-signed form token contains a timestamp and random nonce. It rejects submissions under two seconds, tampering and forms older than two hours. Errors retain entered fields and issue a fresh token.
6. An additional keyed-email counter allows five attempts per fixed hour.
7. Keyed digests of normalized email/message and the signed form token prevent duplicate enquiries and replay for two hours. An already accepted duplicate returns the generic success page without another email. Expired rows can be removed safely.
8. Server-side HTTPS POST to Cloudflare Siteverify checks success, hostname against SITE_URL and action=enquiry. Tokens longer than 2048 characters, missing/invalid/expired/replayed tokens, malformed responses and network failures cannot save or send. The remote request has a five-second timeout. Logs contain static diagnostic categories, not secrets, tokens or message contents.
9. Unique receipt keys and PostgreSQL row locks recheck duplicates in the same transaction as saving the enquiry and consent timestamp. A database failure rolls back both. SMTP runs after this transaction.
10. The response redirects to the noindex thank-you page. Browser JavaScript prevents double-click submission; server checks remain authoritative.

No Redis or extra Python dependency was introduced. No visitor acknowledgement or spam-detected emails are sent.

### Proxy and privacy boundaries

Outside Render the limiter ignores forwarded headers and uses REMOTE_ADDR. On Render it reads only the rightmost valid X-Forwarded-For hop, rather than accepting a spoofable left prefix. This is deliberately conservative: another intermediary can cause a shared proxy bucket. Validate this topology on the real deployment before changing the policy; the short limit is temporary, not a permanent block. A separate email limit and Turnstile remain active. No raw IP, user-agent history, browser fingerprint or Turnstile token is stored in the database. The Siteverify request omits optional remoteip.

Run the existing cleanup command hourly through your deployment scheduler, or regularly from Render Shell:

```bash
python manage.py clear_rate_windows
```

It removes old counters and expired receipt digests, not enquiries. Limits expire even before cleanup; physical retention depends on running cleanup. Review the privacy notice to describe Cloudflare verification, submitted data, consent records, processors and the owner's retention policy before public launch. The existing draft is not automatically published.

## C. SEO changes

- Category title defaults now include the trade direction; directions identify trade categories, and Contact has a descriptive enquiry title. Admin overrides win.
- Fallback descriptions normalize whitespace and avoid cutting words mid-sentence; explicit editorial descriptions remain unchanged.
- Open Graph and Twitter sharing metadata use a page-specific social image, hero/category image, site default or actual logo fallback. Missing files are skipped. Available image dimensions and alt fields are included.
- Organization/WebSite/BreadcrumbList markup remains limited to known site information. No Product, rating or review markup was introduced.
- Card sizes attributes now reflect the card grid rather than requesting half-screen images on desktop. Hero fetchpriority, explicit dimensions, lazy loading, system fonts and WhiteNoise caching remain.
- Sitemap lastmod includes changes to the direction/navigation context. It does not use request time as a fake modification date.
- Submitted/error form representations are noindex. Private previews, admin and thank-you responses remain blocked.
- Thirteen distinct editorial sections describe useful enquiry details for the supplied categories. They add context without claiming inventory, certification, regulatory approval or unconfirmed services.
- A read-only audit checks rendered titles/descriptions for duplicates, one H1, canonical URLs, structured data, image dimensions/alt attributes, crawlable links and exact sitemap membership. launch_check also runs it.

```bash
python manage.py audit_seo --simulate-indexing --json
```

This flag changes settings only within that command, not Render or .env. At real launch run the audit without the flag. Existing owner-revised categories are deliberately left for editorial review instead of having copy replaced.

## D. Database changes

- **0008_enquiry_protection:** adds SubmissionReceipt, nullable privacy_consent_at, and additional status choices. Original In progress/Resolved values remain valid. Historical enquiries retain NULL consent rather than inventing agreement.
- **0009_category_guidance:** one-time addition of guidance only where the category still has the exact original starter overview and no existing editorial sections. Uses frozen migration data and the configured database alias. It does not change owner revisions. Reversing this data migration does not delete content.
- Fresh seed_content adds the same guidance only when creating a category. Re-running the seed does not recreate a section the owner later removed or overwrite edits.

Both migrations were applied and tested in isolated databases. The Render migration verifier preserved a historical resolved enquiry and its message across migration. No production PostgreSQL changes were made here. The existing build command `bash build.sh` runs migrations and idempotent seeding automatically. Start remains `bash start.sh`; no disk or optional installer is required.

## E. Admin workflow

Enquiry lists retain sender/email/category/status/date, search and filters, and add date navigation. Original submission fields and consent timestamp are read-only; status and staff notes remain editable. New selected-row actions: Mark read, Mark replied, Mark spam, Archive. They require change_enquiry permission, affect only selected rows and send no email. View-only staff cannot invoke them. Existing Editor group permissions are preserved.

## F. Email

From: DEFAULT_FROM_EMAIL. To: CONTACT_NOTIFICATION_EMAIL (legacy ENQUIRY_EMAIL fallback remains). Reply-To: the validated visitor email. Subject and recipient are not taken from submitted fields. The body contains the enquiry and canonical admin review link, as plain text. Newlines in header-relevant fields are rejected.

A legitimate record is saved before notification. SMTP failure logs only the enquiry identifier; the stored record remains available in admin and retrying the form does not duplicate it or send repeated mail. No automatic mail retry queue is introduced. The admin is the reliable record; delivery should be checked separately.

## G. Cloudflare setup

1. Open the [Cloudflare dashboard](https://dash.cloudflare.com/), choose **Turnstile**, then **Add widget**.
2. Name it EuroAfrica enquiries, authorize **property.theadvoxy.com** (hostname only), and choose **Managed** mode. Pre-clearance is unnecessary for this form.
3. Create the widget and copy its site key and secret key.
4. Add them to Render Environment as TURNSTILE_SITE_KEY and TURNSTILE_SECRET_KEY. Store the secret in Render, never in Git or public HTML.
5. Redeploy/restart the service after changing environment values. Test a real enquiry and check the admin record and notification inbox.
6. When moving to the final domain, authorize the new hostname and update SITE_URL/ALLOWED_HOSTS/CSRF_TRUSTED_ORIGINS together. Code is not hardcoded to the current domain.

Turnstile can be used without moving DNS to Cloudflare. See [widget setup](https://developers.cloudflare.com/turnstile/get-started/widget-management/dashboard/) and [independent usage](https://developers.cloudflare.com/turnstile/plans/).

The widget loads only on the contact form. It uses compact sizing on narrow form columns and flexible sizing on wider columns. Content/navigation remain server-rendered; the live security challenge needs JavaScript, with a visible no-script explanation and an email alternative when the owner has configured one. Verification errors re-render a fresh challenge. The contact-only CSP allows Cloudflare script/frame/connect sources while the rest of the site retains its previous policy.

Production without real keys fails closed: public pages still start and load, but valid POSTs return 503 without saving or emailing; the form explains temporary unavailability. There is no production bypass switch. Official dummy keys are rejected in production. Local DEBUG=True with blank keys skips only remote Turnstile; all other anti-spam checks remain enabled. Automated tests mock the API and include explicit production-mode failure cases.

## H. Render environment

### ADD

```dotenv
TURNSTILE_SITE_KEY=<public-site-key-from-your-widget>
TURNSTILE_SECRET_KEY=<private-secret-key-from-your-widget>
```

### KEEP

```dotenv
DEBUG=False
SECRET_KEY=<existing-private-Django-secret>
DATABASE_URL=<existing-private-PostgreSQL-URL>
SITE_URL=https://property.theadvoxy.com
ALLOWED_HOSTS=<existing-approved-hostnames-including-property.theadvoxy.com>
CSRF_TRUSTED_ORIGINS=https://property.theadvoxy.com
INDEXABLE=false
STAGING=false
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=<existing-SMTP-host>
EMAIL_PORT=<existing-working-port>
EMAIL_USE_TLS=<existing-setting>
EMAIL_USE_SSL=<existing-setting-do-not-enable-both-TLS-and-SSL>
EMAIL_HOST_USER=<existing-SMTP-login>
EMAIL_HOST_PASSWORD=<existing-private-SMTP-key>
DEFAULT_FROM_EMAIL=<existing-verified-sender>
CONTACT_NOTIFICATION_EMAIL=<existing-manager-inbox>
```

Keep an existing GSC_VERIFICATION value if used. Render supplies RENDER and PORT. No domain configuration was changed by this work.

### REMOVE IF PRESENT

- MEDIA_ROOT=/var/data/media when no disk is mounted, as documented in the previous repair.
- A production console EMAIL_BACKEND; use your working SMTP backend instead.
- Any obsolete startup command invoking install_stock_images. Start remains Gunicorn only.

No additional environment variable needs removing for this feature. Turnstile's site key is public; its secret key, Django secret, database credentials and SMTP password are private. Do not paste real credentials into .env.example or commit .env.

## I. Verification

The local .env now points at a Render-internal PostgreSQL hostname. An initial makemigrations history check warned that it could not resolve that hostname; it created the migration file but made no database changes. Subsequent tests explicitly ignored .env and used isolated SQLite. All production configuration checks used a dummy PostgreSQL URL without opening that connection.

The initial suite exposed one test-fixture mismatch: a production-mode test issued HTTP under Django's test hostname and correctly received a canonical redirect. Fixing its hostname and HTTPS request corrected the test; security redirects were not disabled to pass it. The final run is below.

| Command/check | Result |
|---|---|
| manage.py check | Zero issues |
| manage.py makemigrations --check --dry-run | No changes detected |
| manage.py test --noinput | 68 tests passed, 11.783 seconds |
| manage.py migrate --noinput | All migrations through 0009 applied to isolated preview database |
| manage.py check --deploy | Exit 0; W005/W021 plus trade.W001 without configured Turnstile keys |
| manage.py collectstatic --noinput | Passed, including the new contact script |
| scripts/verify_render.py | Passed: routing, redirects, static/media, migration preservation and SEO audit |
| scripts/check_production.py | Passed; isolated helper opts into HSTS and reports missing Turnstile keys |
| node --check trade/static/trade/contact.js | Passed |
| scripts/smoke_production.py | Passed: production-mode HTML/admin/static/404 checks |
| manage.py audit_seo --simulate-indexing --json | 18 pages, 18 sitemap URLs, zero errors |
| git diff --check | Passed |

Local commands were invoked through `qa/run_local_checks.py`, an ignored wrapper around Django's management entry point that prevents loading production .env and uses qa/seo-preview.sqlite3. Reproduce the standard manage.py commands above in an explicitly configured test environment, never by resetting production PostgreSQL. Test files and migrations are tracked; qa databases/logs are not.

Coverage includes valid submissions, fixed headers/Reply-To, honeypot, signed timing/tampering/expiry, email/IP limits, replay/normalized duplicates, transactional rollback, Cloudflare success/failure/timeout/hostname/action validation, production missing/dummy keys, consent, international names, length/email validation, SMTP failure preservation, admin actions/permissions, CSRF, escaping, cleanup, metadata, sitemap, owner-content preservation and prior deployment regressions.

Browser checks used an isolated local site: labelled inputs, native validation, consent checkbox and successful submission; layouts at 320px, 390px and 1440px had no horizontal overflow. Honeypot stayed offscreen. The homepage hero loaded with high priority; below-fold images retained lazy loading. No real email was transmitted.

Measured unthrottled in-process rendering (not network TTFB or Core Web Vitals):

| Page | Render time | HTML bytes |
|---|---:|---:|
| / | 122.2 ms | 13565 |
| /contact/ | 25.4 ms | 8464 |
| /africa-to-europe/cut-flowers/ | 28.9 ms | 9982 |

Real production PostgreSQL concurrency, Cloudflare challenge completion, SMTP delivery and field Core Web Vitals were not tested. The live site has not received these edits. Performance measurements vary by machine/cache and are not a ranking prediction. Run PageSpeed Insights and inspect Search Console after real hosting is configured.

## Files changed

- `.env.example` — Document Turnstile keys and safe local/production behavior.
- `euroafrica/settings.py` — Turnstile configuration and conservative enquiry thresholds.
- `scripts/verify_render.py` — Verify historical enquiry preservation and rendered SEO.
- `trade/admin.py` — Permission-checked status actions and consent/date display.
- `trade/antispam.py` — Timing, hashes, transactional deduplication, rate limits and Siteverify.
- `trade/apps.py` — Register deployment configuration checks.
- `trade/category_guidance.py` — Thirteen original category-specific guidance sections.
- `trade/checks.py` — Visible deploy warning when production verification is unavailable.
- `trade/forms.py` — Required type/consent, signed timing, accessible honeypot and validation.
- `trade/management/commands/audit_seo.py` — Read-only rendered-page SEO audit.
- `trade/management/commands/clear_rate_windows.py` — Remove expired receipt digests as well as counters.
- `trade/management/commands/launch_check.py` — Require configured Turnstile and passing rendered SEO audit.
- `trade/management/commands/seed_content.py` — Add category guidance only for newly created starter categories.
- `trade/middleware.py` — Allow Cloudflare assets only on the contact route.
- `trade/migrations/0008_enquiry_protection.py` — Add schema without deleting or fabricating existing enquiry data.
- `trade/migrations/0009_category_guidance.py` — One-time safe enrichment of unchanged starter content.
- `trade/models.py` — Receipt digests, consent timestamp and additive enquiry statuses.
- `trade/seo.py` — Central metadata defaults and sharing-image fallbacks.
- `trade/static/trade/contact.js` — Progressive double-submit prevention and responsive widget rendering.
- `trade/static/trade/site.css` — Contact-only responsive and accessibility styling.
- `trade/templates/trade/base.html` — Sharing metadata and image dimensions.
- `trade/templates/trade/cards.html` — Correct responsive card sizes hints.
- `trade/templates/trade/contact.html` — Accessible errors, consent, verification and retry UI.
- `trade/templates/trade/image.html` — Allow per-layout responsive sizes hints.
- `trade/test_enquiry_security.py` — Anti-spam, privacy, email and admin regression tests.
- `trade/test_helpers.py` — Generate valid signed browser-equivalent test submissions.
- `trade/test_readiness.py` — Adapt existing valid-submission tests to signed form fields.
- `trade/test_seo_readiness.py` — Rendered SEO, sitemap freshness and content-preservation tests.
- `trade/tests.py` — Adapt existing submission/SMTP tests while preserving security checks.
- `trade/views.py` — Layered enquiry flow, safe mail headers and improved metadata/sitemap handling.
- `SEO_AND_ENQUIRY_READINESS.md` — this report, configuration and verification instructions.
- `OWNER_GUIDE.md` — enquiry actions, consent and verification setup.
- `README.md` — links to the new audit and deployment guide.

## J. Git and deployment

No automatic push was performed for this task. Review and publish when the Turnstile keys are ready, since production submissions intentionally close without them:

```bash
git status --short
git diff --check
git diff
# After reviewing all listed task changes (never add .env or database files):
git add .env.example euroafrica/settings.py scripts/verify_render.py trade README.md OWNER_GUIDE.md SEO_AND_ENQUIRY_READINESS.md
git diff --cached --stat
git commit -m "Improve SEO readiness and protect enquiry submissions"
git push origin main
```

Render Build Command: `bash build.sh`. Start Command: `bash start.sh`. The build applies 0008/0009 automatically. Use **Deploy latest commit** if auto-deploy is disabled; clearing build cache is unnecessary. Add the keys before deployment to avoid an unavailable form. Do not run a destructive database reset or rotate working credentials for this change.

## K. Post-deployment and launch checklist

- Keep the current domain and INDEXABLE=false while preparing real hosting.
- Configure the Managed widget for the actual hostname and set its real keys in Render.
- Submit a clearly labelled legitimate enquiry after spending a few seconds on the form; verify success, admin record and one notification with the correct Reply-To.
- Test the Read/Replied/Spam/Archive actions on that test record; confirm other enquiries are unchanged.
- Check the widget on mobile and desktop, keyboard access, visible labels/errors and no horizontal scrolling.
- Test rejection/duplicate/rate-limit behavior in staging or with the automated suite rather than flooding the manager's production inbox.
- Confirm a network/SMTP failure retains the saved legitimate enquiry; check sanitized logs and the admin.
- Schedule cleanup of expired rate counters/receipt digests and follow the owner's enquiry-retention policy.
- Before real launch: verify business identity/contact details and claims, publish an approved privacy notice, configure the final domain and Google verification, then set INDEXABLE=true.
- Run launch_check and audit_seo; confirm no production noindex/header/robots block, sitemap contains only published canonical URLs, and HTTPS redirects stay on the chosen hostname.
- Submit sitemap.xml to Search Console, inspect representative URLs, monitor indexing and measure mobile PageSpeed/Core Web Vitals. Fix measured issues; do not assume the audit guarantees rankings.
