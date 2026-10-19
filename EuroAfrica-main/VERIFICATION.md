# Verification record

## Responsive repair after owner review

The owner reported an overlap above the About section. Browser inspection confirmed that inline category-image links allowed images to extend beyond their card boxes. The links now use block layout, cards contain their content, and the About section has a measured 55px mobile / 88px desktop gap after the cards. Grid children can shrink and long text wraps; the contact layout stacks on tablets, and navigation switches to the mobile menu at 900px. Development now serves current source static assets rather than the collected WhiteNoise copy.

After the fix: measured homepage widths 320, 390, 540, 768, 900, 1024 and 1440px without horizontal or card-content overflow. Direction cards and contact checked at 390px without overflow. All 19 Django tests passed again; the crawl still reached 18 pages without broken internal links or referenced assets. The earlier screenshot review did not catch this card overflow; this follow-up supersedes that aspect of the original review.

Verified locally on 16 September 2026 using Python 3.12 and Django 5.2.17 with SQLite. Production PostgreSQL, Gunicorn, Nginx, HTTPS, SMTP and Search Console have **not** been exercised in this environment.

## Completed

- Database migrations applied and idempotent content seed executed: 2 directions, 13 categories and all supplied product examples. Seed keys preserve owner changes, including renamed slugs.
- Django system checks: no issues. Migration consistency check: no changes detected. Static collection: 130 files collected, including Django admin assets.
- 19 automated tests passed. Tests cover all 18 public pages, unique title/description/H1, canonical URLs, parsed JSON-LD types, sitemap count and publication rules, draft isolation, permission-protected previews, editor permissions, actual admin text editing, enquiry preselection/validation/persistence, honeypot, CSRF rejection, rate limiting, SMTP failure, chained slug changes resolving directly to the latest URL, real 404s, slash redirects, production host redirects, staging authentication, reserved slugs, modification dates, upload format validation and responsive WebP conversion.
- Read-only HTTP crawl from the homepage reached all 18 published pages. No broken internal links or referenced assets. The three shared local frontend assets totalled 83,024 bytes before transfer compression. No external fonts or public JavaScript bundles.
- Browser review: homepage at 1440px and 390px; mobile direction and category pages; contact at 390px, 768px and desktop. Inspected screenshots of homepage, category and contact. Measured document width did not exceed viewport width at the checked sizes. Native mobile menu opened; navigation reached a direction and category. Category enquiry link selected Fresh Fruits & Vegetables on the contact form.
- Logo visually inspected after extraction: actual first blue/gold design, transparent background, no swatches or presentation watermark.
- `launch_check` ran and failed as expected for local mode, blocked indexing, local domain/database, draft privacy, missing public email and placeholder hero.

## Measured local HTTP responses

Ten unthrottled samples per route, using the Django development server and local SQLite. These include response download, not browser rendering.

| Page | Median | Maximum | HTML size |
| --- | ---: | ---: | ---: |
| Home | 16.14 ms | 18.83 ms | 9,469 bytes |
| Africa to Europe | 18.00 ms | 20.22 ms | 8,782 bytes |
| Cut Flowers | 20.45 ms | 21.79 ms | 7,012 bytes |
| Contact | 16.16 ms | 18.06 ms | 5,807 bytes |

Reproduce the read-only crawl and timing report with `.venv\Scripts\python.exe scripts/audit_site.py` while the local server runs. Raw results are written to ignored `qa/audit.json`.

## Remaining checks and owner decisions

- Replace the shared illustrative placeholders with approved, licensed category and hero photography. Imagery is not represented as company facilities or operations. Final photography will change transfer sizes and loading performance.
- Verify company identity, public contact information, actual services/supply capabilities and the regulated-category editorial notes. Privacy is intentionally unpublished and must be completed and reviewed before live collection.
- Configure and exercise PostgreSQL, real domain redirects, HTTPS, proxy headers, persistent media, backups/restores and optional SMTP on the chosen host. Validate database concurrency under deployment load.
- Run mobile/desktop Lighthouse or PageSpeed Insights after deployment and final imagery. LCP, INP, CLS and field performance have not been measured; the local response numbers above are not a Core Web Vitals assessment.
- Run a full accessibility audit, including screen-reader and touch-device review. Keyboard focus styles and native controls are implemented, but this is not an accessibility conformance certification.
- Complete the production launch and post-launch indexing checklist in DEPLOYMENT.md. Search rankings and indexing are not guaranteed.
