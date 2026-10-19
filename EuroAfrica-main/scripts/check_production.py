import os, secrets, subprocess, sys
os.environ.update(DEBUG='false',SECRET_KEY=secrets.token_urlsafe(64),DATABASE_URL='postgresql://check:unused@127.0.0.1:5432/check?sslmode=require',SITE_URL='https://www.euroafrica.example',ALLOWED_HOSTS='www.euroafrica.example',HSTS_INCLUDE_SUBDOMAINS='true',HSTS_PRELOAD='true',STAGING='false')
for args in [('check','--deploy'),('collectstatic','--noinput')]:
 result=subprocess.run([sys.executable,'manage.py',*args],check=False)
 if result.returncode: sys.exit(result.returncode)
