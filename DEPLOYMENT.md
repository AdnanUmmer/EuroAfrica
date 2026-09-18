# Deployment and launch

Use a conventional Linux server with Python 3.12+, PostgreSQL, Gunicorn and Nginx. This project has not been deployed; the actual domain, infrastructure, SMTP, media and backups must be configured and tested.

## Application setup

Create a dedicated unprivileged `euroafrica` service account and a persistent project directory such as `/srv/euroafrica`. Create a PostgreSQL database and least-privilege database user using an interactive password prompt. Keep PostgreSQL bound to localhost or a private network; use verified TLS when the database is remote. Put secrets in a service-readable `.env` with mode 0600, outside version control.

```bash
cd /srv/euroafrica
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed_content
.venv/bin/python manage.py install_stock_images
.venv/bin/python manage.py createsuperuser
.venv/bin/python manage.py collectstatic --noinput
.venv/bin/python manage.py check --deploy
```

Required settings:

```dotenv
DEBUG=false
SECRET_KEY=<long-random-secret>
DATABASE_URL=postgresql://euroafrica:<url-encoded-password>@127.0.0.1:5432/euroafrica
SITE_URL=https://<canonical-domain>
ALLOWED_HOSTS=<canonical-domain>,<alternate-domain>
TRUST_LOCAL_PROXY=true
MEDIA_ROOT=/srv/euroafrica-shared/media
HSTS_INCLUDE_SUBDOMAINS=false
HSTS_PRELOAD=false
INDEXABLE=false
STAGING=true
STAGING_USER=<staging-login>
STAGING_PASSWORD=<staging-password>
```

Use protected staging first. Add HTTP Basic authentication at the **Nginx server level**, covering HTML, static and media, in addition to the application's staging gate. HTTPS is required. Credentials supplied to staging Basic authentication are separate from admin accounts. Do not enable production indexing on staging.

`TRUST_LOCAL_PROXY=true` is only safe when Gunicorn is bound to loopback and Nginx overwrites the forwarded protocol and client IP headers. Never expose that backend port publicly. If a CDN is added, configure Nginx's trusted real-IP ranges explicitly; do not trust arbitrary forwarded headers.

## Process supervision

Example `/etc/systemd/system/euroafrica.service` (adapt filesystem ownership):

```ini
[Unit]
Description=EuroAfrica Django website
After=network.target
[Service]
User=euroafrica
Group=euroafrica
WorkingDirectory=/srv/euroafrica
ExecStart=/srv/euroafrica/.venv/bin/gunicorn euroafrica.wsgi:application --bind 127.0.0.1:8001 --workers 3 --timeout 30 --access-logfile - --error-logfile -
Restart=on-failure
PrivateTmp=true
NoNewPrivileges=true
[Install]
WantedBy=multi-user.target
```

The application loads `.env` itself. Enable the service after checking permissions and secrets. Run `manage.py clear_rate_windows` hourly using your server's scheduler; counters older than two hours are removed. Rate limiting uses shared database rows, ten attempts per source IP per hour, and therefore works across workers. Add Nginx request limits for `/contact/` and `/admin/login/` as a second layer; set limits appropriate to the deployment.

## Nginx and HTTPS

Provision a valid certificate using your hosting provider or ACME client. Redirect the HTTP and alternate HTTPS hosts directly to the canonical HTTPS domain. Example canonical HTTPS server block (replace bracketed values):

```nginx
server {
    listen 443 ssl;
    server_name <canonical-domain>;
    ssl_certificate <certificate-fullchain-path>;
    ssl_certificate_key <private-key-path>;
    client_max_body_size 8m;

    # STAGING ONLY: enable for the whole server, including static and media.
    # auth_basic "EuroAfrica staging";
    # auth_basic_user_file /etc/nginx/euroafrica-staging.htpasswd;

    location /static/ {
        alias /srv/euroafrica/staticfiles/;
        expires 30d;
        add_header X-Content-Type-Options nosniff always;
    }
    location /media/ {
        alias /srv/euroafrica-shared/media/;
        expires 7d;
        add_header X-Content-Type-Options nosniff always;
        add_header Content-Security-Policy "default-src 'none'" always;
        limit_except GET HEAD { deny all; }
    }
    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

Never configure script execution within `/media/`. Missing assets must return 404. Keep uploaded media persistent across code releases. There is no public HTML cache, so publication changes take effect immediately; hashed static files use browser/proxy caching. Do not cache admin, previews, contact forms or submission results. Verify `Cache-Control`, `X-Robots-Tag` and security headers at the final proxy.

## SMTP and backups

Set `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `DEFAULT_FROM_EMAIL`, and `ENQUIRY_EMAIL`. TLS is enabled. Send a test through staging and confirm both the saved enquiry and delivery. Email contains only the enquiry identifier; staff read the details in admin. A delivery failure is logged without exposing server details to the visitor.

Schedule encrypted PostgreSQL dumps and incremental media backups to a separate restricted location. Include the environment configuration in a separate encrypted secrets backup. Define retention with the owner. Test restoration into an isolated environment before launch and periodically thereafter. Log monitoring should alert on 500 responses, notification failures, disk usage and failed backups; avoid logging form bodies or credentials.

## Explicit launch checklist

- Confirm the legal company identity, public contact email, content accuracy, image licences and approved privacy notice. Review the installed illustrative photographs and their source register in `assets/stock/README.md`; replace any that do not suit the approved content.
- Confirm the canonical domain in `SITE_URL`, matching certificate, allowed hosts, and one-hop HTTP/alternate-host redirects. Check the slash redirect and changed-slug redirects.
- On **production only**, set `STAGING=false` and `INDEXABLE=true`; remove staging Basic authentication at Nginx. Keep staging protected with indexing disabled.
- Run `manage.py check --deploy` and `manage.py launch_check`. Address failures; these commands do not replace review of live responses.
- Inspect homepage, both directions, a category in each direction and contact source for unique title, description, H1, canonical, Open Graph and valid Organization/WebSite/BreadcrumbList JSON-LD. Verify no production `noindex` header or meta tag remains on indexable pages.
- Fetch `/sitemap.xml`: final HTTPS URLs only, published/indexable pages only, real last-modification dates. Fetch `/robots.txt`: crawling allowed and the canonical sitemap URL present.
- Confirm drafts and unknown pages return 404, previews require permission, results/admin are noindex, and there are no orphaned categories or broken internal links.
- Verify the domain property in Google Search Console (DNS verification), or set `GSC_VERIFICATION` for the HTML-token method. Submit `https://<canonical-domain>/sitemap.xml` in Sitemaps.
- Use URL Inspection on representative canonical pages and request indexing where appropriate. Check selected canonical, crawl status, sitemap discovery and indexing exclusions after launch. Recheck over the following weeks; indexing and rankings are not guaranteed.
- Measure the real site with PageSpeed Insights/Lighthouse on mobile and desktop after final images are installed. Track LCP, INP and CLS using field data when available; local development timings do not establish Core Web Vitals performance.
- Test keyboard navigation, mobile menu, contact validation and submission at 360/390/768/1440px. Confirm database persistence when SMTP is deliberately unavailable in staging.

Do not launch while the default privacy draft or unknown company details remain unresolved.

## Exact commissioning sequence

Before the setup commands above, copy the repository to `/srv/euroafrica`, create `.env` from `.env.example`, and set its real values. Generate a secret with `python3 -c "import secrets; print(secrets.token_urlsafe(64))"` and store it only in the protected environment file. Production startup rejects development or placeholder secrets, non-HTTPS URLs and wildcard/test hosts. URL-encode database passwords; for a remote database use `?sslmode=verify-full&sslrootcert=/absolute/path/to/ca.pem` with its verified certificate. Do not use the check scripts' example database settings in production.

Prepare persistent storage, owned by the service user and readable by Nginx:

```bash
sudo install -d -o euroafrica -g www-data -m 2750 /srv/euroafrica-shared/media
sudo chmod 600 /srv/euroafrica/.env
```

Run the application setup commands as the `euroafrica` user. On an existing installation, take a backup before `migrate`; do not replace its database or media. `seed_content` adds missing starter records and permissions without resetting edited text or existing group permissions. `install_stock_images` is optional and fills only empty image fields. Migrations 0004/0005 add captions, focal points, legal copy and footer links; the existing content remains intact.

After writing the service and Nginx configurations above and provisioning certificates:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now euroafrica
sudo nginx -t
sudo systemctl reload nginx
sudo systemctl status euroafrica --no-pager
sudo journalctl -u euroafrica -n 50 --no-pager
```

HSTS applies to the main hostname. Django warns about `security.W005` and `security.W021` when subdomain inclusion/preload remain false. Enable `HSTS_INCLUDE_SUBDOMAINS=true` only after all subdomains support HTTPS; enable `HSTS_PRELOAD=true` only after an explicit organizational decision about the long-lived preload commitment. Re-run `check --deploy` with the actual values and document any intentional warnings. The verification run enabled both in an isolated configuration; it did not submit the domain to a preload list.

`EMAIL_USE_TLS=true` suits STARTTLS on port 587. For a provider requiring implicit TLS on 465, set `EMAIL_USE_TLS=false` and `EMAIL_USE_SSL=true`. Never enable both. Confirm sender authentication and real delivery with the provider.

## Backup and recovery example

Use PostgreSQL service definitions and a restricted `.pgpass` file rather than putting passwords in shell commands. With `PGSERVICE=euroafrica` configured for the live database:

```bash
pg_dump --format=custom --file=/secure-backups/euroafrica.dump
rsync -a /srv/euroafrica-shared/media/ /secure-backups/media/
```

Encrypt and copy these to separately protected storage. For a restoration rehearsal, create a separate empty database and separate media directory, configure a protected staging instance to use them, then run:

```bash
pg_restore --no-owner --dbname=euroafrica_restore /secure-backups/euroafrica.dump
rsync -a /secure-backups/media/ /srv/euroafrica-restore/media/
```

Verify record counts, logins, representative images and enquiries before considering the backup usable. Never point the rehearsal at the production database. After each code release, run migrations and collectstatic, restart the service, and repeat the live HTTP/SEO checks above. Keep the previous release and a matching database/media backup for recovery.

## Verification limits

Local `scripts/check_production.py` runs production-oriented security checks and static collection with throwaway settings. `scripts/smoke_production.py` checks DEBUG=false HTML and WhiteNoise using a disposable SQLite database. These scripts do not test a real PostgreSQL server, Linux process supervision, Nginx media delivery, DNS/TLS, SMTP delivery or backup recovery. Those remain required commissioning checks on the chosen server. Media is intentionally served by Nginx, not Django in production.

## Render deployment

For the existing Render service, use [RENDER_DEPLOYMENT.md](RENDER_DEPLOYMENT.md). It supersedes the Linux/Nginx examples above for that host and includes the homepage initialization repair, Render HTTPS proxy settings, build/start commands and persistent-media requirements.
