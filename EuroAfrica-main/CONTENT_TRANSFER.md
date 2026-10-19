# EuroAfrica: local content to the existing PostgreSQL VPS

This is an additive content/media transfer, not a deployment or database replacement.
The VPS remains Django → PostgreSQL, with file names in PostgreSQL and files under
`/var/www/euroafrica/app/media/`, served by the existing Nginx configuration.
No Nginx, Certbot, Gunicorn, authentication, UI or production settings changes are needed.

## What was found locally (4 October 2026)

Python's redirected stdout encoding is `cp1252`. Django JSON serialization includes
Unicode characters that this encoding cannot represent. The existing `trade_data.json`
is neither valid UTF-8 nor complete JSON when read as cp1252. Do not import or transcode
that truncated file. The SQLite values themselves are intact.

The new exporter explicitly writes UTF-8 JSON directly to a file; it does not pass data
through PowerShell `>` or a console codec. `-X utf8` also makes command diagnostics portable.
The package contains editorial models, paths, translations and referenced media only.
It never exports `.env`, database connection settings, users/passwords, auth permissions,
enquiries, sessions, submission counters/receipts, or stock-image initialization markers.

Local counts: SiteSettings 1, HomePage 1, TradeDirection 2, TradeCategory 10,
CategoryProduct/CategorySection/CategoryImage 0 each, FooterLink 6, ContentPage 2,
ContactPage 1, HomeFeature 4, ContentSection 2, URLHistory 0, ContentTranslation 595.
The second content page is the **unpublished privacy draft**; importing it does not publish it.
Category 3 has neither an image nor hero image locally. This is a source gap, not a lost file;
no image is invented. All non-empty local file references exist, including the tobacco
image and PDF. Responsive `-480.webp` and `-960.webp` companions are included where present.

## Merge policy and review

- Singleton settings/home/contact use ID 1. Directions/categories use unique seed keys
  and URL slugs (category slug scoped to its remapped direction). Contradictory keys abort.
- Content pages use slug; footer links use group + destination, rejecting ambiguities.
  Child records use their parent plus name/heading/image with PK collision checks.
  Ambiguous child identities abort for manual reconciliation rather than guessing.
- New records are inserted. Existing empty strings/NULLs are filled. Existing non-empty
  values, including `false`, `0`, production text and image paths, are retained by default.
  Dates are not treated as proof that one site's content is authoritative.
- Production-only records are retained. PK collisions on unrelated natural identities
  allocate new target IDs and remap references. PostgreSQL sequences are reset after inserts.
- Translations use target model + remapped object + language + field. ContentType IDs
  and translation PKs are never assumed to match between databases. Incoming translations
  whose source differs from retained production text are reported and skipped.
- Each differing existing field is listed in the UTF-8 preview with local/production values.
  Default conflicts are decisions to **keep production**, not silent overwrites. Review these
  and skipped translations; matching row counts alone does not prove content is complete.
- A different physical file at the same media path aborts. Existing media is never replaced
  or deleted. Resolve collisions by assigning a new uploaded filename and re-exporting;
  do not delete the production file to force the import.
- Applying requires a fresh PostgreSQL backup receipt and an unchanged reviewed plan.
  Database writes use one transaction with brief write locks (reads stay available).
  A five-second lock timeout aborts rather than waiting indefinitely. Media is copied first;
  an interrupted operation may leave harmless unreferenced new files, never partial DB edits.
- Running preview after a successful merge should produce zero new operations. Genuine
  conflicts remain visible; rerunning cannot create duplicate translations/content.

## 1. Local package (PowerShell)

Run from the existing local repository. Choose a new archive filename on each export:

```powershell
Set-Location 'C:\Users\10adn\OneDrive\Documents\Projects\Advoxy_Projects\Project_Euroafrica\EuroAfrica-main\EuroAfrica-main'
python -X utf8 manage.py check
python -X utf8 manage.py migrate --check
python -X utf8 scripts/package_content_transfer.py --output 'C:\Users\10adn\OneDrive\Documents\New project\euroafrica-content-20261004.zip'
```

The archive has `package/content.json`, `package/media/`, the transfer utility under
`tooling/`, a summary, and this runbook. A sibling `.zip.sha256` verifies the whole archive.
It deliberately excludes general application code/migrations: existing application code
must be compatible, and migration checksums are checked before planning or importing.

For an unpacked export instead:

```powershell
python -X utf8 manage.py transfer_content export --output 'C:\Users\10adn\OneDrive\Documents\New project\euroafrica-package-new'
```

## 2. Secure upload

The actual VPS hostname and SSH account were not provided. Set `$Vps` to your existing
SSH destination (and existing key/config); these are the only connection placeholders:

```powershell
$Vps = 'YOUR_SSH_USER@YOUR_VPS_HOST'
$Archive = 'C:\Users\10adn\OneDrive\Documents\New project\euroafrica-content-20261004.zip'
ssh $Vps 'umask 077; mkdir -p ~/euroafrica-transfer'
scp $Archive "$Archive.sha256" "${Vps}:euroafrica-transfer/"
```

Use your normal SSH host-key verification. Do not disable host-key checking or place
passwords in commands. The archive should stay outside public web/media directories.

## 3. Prepare on the VPS without changing services

Use the **existing application/deployment account**, with access to the current `.env`
and write permission to the application and media directories. Use the current deployment's
virtualenv, not a newly created environment. If you uploaded as a different account, first
grant the application account access to this private staging directory without making it public.

```bash
set -euo pipefail
umask 077
cd "$HOME/euroafrica-transfer"
sha256sum -c euroafrica-content-20261004.zip.sha256
STAGE="$HOME/euroafrica-transfer/release-20261004"
test ! -e "$STAGE"
mkdir "$STAGE"
# Enter the absolute Python executable used by the existing Gunicorn virtualenv.
read -r -p 'Existing application virtualenv Python path: ' PY
test -x "$PY"
"$PY" -m zipfile -e euroafrica-content-20261004.zip "$STAGE"
cd /var/www/euroafrica/app
for f in trade/content_transfer.py trade/management/commands/transfer_content.py; do
  # Refuse to overwrite a different previously installed utility.
  if test -e "$f"; then cmp -s "$f" "$STAGE/tooling/$f"; fi
  install -m 0644 "$STAGE/tooling/$f" "$f"
done
"$PY" manage.py shell -c 'from django.db import connection; from django.conf import settings; from pathlib import Path; assert connection.vendor == "postgresql", "STOP: not PostgreSQL"; assert Path(settings.MEDIA_ROOT).resolve() == Path("/var/www/euroafrica/app/media").resolve(), "STOP: unexpected media root"; print("Confirmed PostgreSQL and existing media root")'
```

If this check fails, stop and inspect the existing deployment environment. Do not switch
engines or edit `.env` to make the check pass. Do not source/print secret values in the shell.

## 4. Back up PostgreSQL before any database changes

`pg_dump` and `pg_restore` must be installed and compatible with the PostgreSQL server.
The command below uses Django's existing connection settings, passing the password only
in the child process environment. It never writes credentials to the dump receipt or command
line. It creates a custom-format **whole database backup**, SHA-256 receipt, and checks the
archive with `pg_restore --list`. It does not reset or recreate any database.

```bash
BACKUP="$HOME/euroafrica-transfer/backup-$(date -u +%Y%m%dT%H%M%SZ)"
"$PY" manage.py transfer_content backup --output "$BACKUP"
pg_restore --list "$BACKUP/database.dump" > "$BACKUP/archive-list.txt"
"$PY" manage.py showmigrations
"$PY" manage.py migrate --plan
"$PY" manage.py migrate --check
"$PY" manage.py check
```

If `migrate --check` fails, **stop the sequence**. Inspect the pending migrations and deploy
the matching existing application release through your normal process. After reviewing the
plan and retaining the pre-migration backup, the schema command is:

```bash
"$PY" manage.py migrate --noinput
"$PY" manage.py migrate --check
```

Do not use `--fake`, `--fake-initial`, or `build.sh` to bypass a mismatch. The transfer also
requires matching migration file checksums, including the multilingual data migration JSON.
No extra migration was introduced for this utility. If migrations changed data, make another
fresh backup immediately before merging. Keep both backups; receipts expire after 24 hours.
Archive listing is not a restore rehearsal: retain your existing verified off-server backups.

## 5. Preview and review exact field changes

```bash
PLAN="$STAGE/plan.json"
"$PY" manage.py transfer_content plan --package "$STAGE/package" --output "$PLAN"
"$PY" -m json.tool "$PLAN" | less
```

Inspect `operations`, `before_counts`, `after_counts`, `conflicts`, and
`skipped_translations`. This command changes neither PostgreSQL nor production media.
Expect missing image fields to be filled only when local has a path. Do not assume that
production will end at exactly 595 translations: valid production-only rows are preserved.

If a specific differing field is confirmed to need the local value, create a private UTF-8
`$STAGE/resolutions.json` containing only approved keys copied from `conflicts`, for example:

```json
{"homepage:1:hero_heading": "local"}
```

This is an example, not an instruction to overwrite that field. `production` explicitly
records a keep decision. It can also preserve an intentionally empty field that the preview
proposes filling: use `model:SOURCE_ID:field` (source IDs are in `package/content.json`).
Identity/URL/relationship fields cannot be forced. Generate a new
plan; never edit the generated plan itself:

```bash
PLAN="$STAGE/plan-reviewed.json"
"$PY" manage.py transfer_content plan --package "$STAGE/package" --resolutions "$STAGE/resolutions.json" --output "$PLAN"
"$PY" -m json.tool "$PLAN" | less
```

When retaining production text, supply/review translations for that exact text through the
translation editor; importing a translation for different source text would be incorrect.

## 6. Apply only the reviewed plan

Choose a low-traffic moment; pause editorial/admin editing during preview and apply.
The site can continue serving reads. Enquiry writes may wait briefly for the transaction.

```bash
JOURNAL="$STAGE/merge-journal.json"
"$PY" manage.py transfer_content apply --package "$STAGE/package" --plan "$PLAN" --backup "$BACKUP" --journal "$JOURNAL"
```

If content changed after preview, the command aborts with no database edits. Regenerate and
review a plan using a new filename. Do not remove freshness checks. The journal is written
before commit so every successful commit has rollback data; a journal left by a failed
commit will fail the rollback state check rather than undo unrelated changes.
No Gunicorn/Nginx restart is needed for content rows and media. Existing files are retained;
new public media files are readable by Nginx. Existing directory permissions are not modified.

## 7. Verify database, files and HTTPS through Nginx

```bash
"$PY" manage.py migrate --check
"$PY" manage.py check
"$PY" manage.py transfer_content verify --package "$STAGE/package" --output "$STAGE/verification.json" --http
"$PY" manage.py audit_translations
"$PY" manage.py transfer_content plan --package "$STAGE/package" --output "$STAGE/repeat-plan.json"
```

Verification reports every included model count, pending merge operations, differing fields,
source-mismatched translations, and empty category image references. It checks every non-empty
ImageField/FileField against disk, including the tobacco PDF. `--http` uses the configured
canonical HTTPS `SITE_URL`, validates TLS, checks all published pages in six languages with
matching `lang`/`dir` and headings, and downloads `/media/` assets (including responsive variants)
to compare SHA-256 bytes with the files on disk. Thus a 200 HTML error page cannot masquerade
as a valid image/PDF. No enquiry is submitted and no external account is contacted.

Missing files, translation gaps or pending operations produce a failure exit. Retained
production conflicts are reported for review rather than overwritten. A category missing an
image on both sites remains a documented source gap. If protected staging is enabled, the
HTTP verification will fail until run against the intended authenticated/public environment;
do not disable working security just to pass a check.

Also manually open the homepage, About, Contact, both trade directions, category pages and
tobacco brochure through HTTPS. Switch all six languages and follow navigation to confirm
cookie persistence; inspect Arabic RTL and mobile/tablet/desktop layout. No products exist
locally to import, so do not expect new product rows. Check production logs for new errors
using your current logging tools without changing services.

## 8. Rollback this merge without resetting PostgreSQL

Use the journal path from the successful import:

```bash
"$PY" manage.py transfer_content rollback --journal "$JOURNAL" --confirm
"$PY" manage.py check
```

This transaction restores only the fields changed by this merge and removes only rows it
inserted, in dependency order. It preserves enquiries, auth records and all physical files.
It refuses if editorial content changed after the import or new enquiries refer to imported
categories; this avoids deleting legitimate later work. Harmless newly copied media is left
on disk deliberately. Do not delete media recursively. Rollback does not undo separately
applied Django migrations or deploy older application code.

If automatic rollback refuses, retain the journal and full PostgreSQL backup for a reviewed
manual recovery. Do not force a whole-database restore onto the live database: that would
discard later legitimate transactions. A DBA can rehearse the custom-format dump into an
**isolated recovery database** using existing secure PostgreSQL service credentials:

```bash
pg_restore --no-owner --no-acl --exit-on-error --dbname=service=euroafrica_recovery "$BACKUP/database.dump"
```

`euroafrica_recovery` must be an independently configured service pointing to an empty,
isolated recovery database, never the production service. This recovery service was not
created by the utility. The journal command above is the normal production rollback command.

## Do NOT run

- `loaddata trade_data.json`, a blind full fixture import, or PowerShell `dumpdata > file.json`.
- `flush`, `dropdb`, schema/table deletion, `pg_restore --clean` against production, or a SQLite replacement.
- `build.sh`, `seed_content`, `seed_translations`, `install_stock_images` or `link_stock_images`
  as a substitute for this reviewed transfer.
- `rsync --delete`, an archive extraction over the live media directory, or recursive media deletion.
- Commands that print `.env`, `DATABASE_URL`, `settings.DATABASES` or passwords into logs.

## Verification limits

Local automated tests exercise UTF-8 export, conflicts, remapped identities, idempotence,
transaction rollback, media collision/path protections and rollback dependency checks with
a disposable SQLite test database. Production write guards and backup failures are tested
with mocks. A real PostgreSQL server, VPS filesystem permissions, `pg_dump` restoration,
Nginx/HTTPS and live pages cannot be certified until the VPS commands above are run.
No SSH hostname/access was supplied, so no production change is claimed.
