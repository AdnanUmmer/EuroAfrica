#!/usr/bin/env bash
set -o errexit
# Render disks exist only at runtime, never during build/pre-deploy.
if [ -n "${MEDIA_ROOT:-}" ]; then
    python manage.py install_stock_images
fi
exec gunicorn euroafrica.wsgi:application --bind "0.0.0.0:${PORT:-10000}"
