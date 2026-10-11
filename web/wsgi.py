"""WSGI entry point: `gunicorn web.wsgi:app`."""
from werkzeug.middleware.proxy_fix import ProxyFix

from web import create_app

app = create_app()
# Behind Render's TLS proxy: trust one hop so request.is_secure / host are correct
# (the language cookie's `secure` flag depends on it).
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
