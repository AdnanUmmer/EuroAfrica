#!/usr/bin/env bash
set -o errexit
# Optional content/media setup must never block web-server startup.
exec gunicorn euroafrica.wsgi:application --bind "0.0.0.0:${PORT:-10000}"
