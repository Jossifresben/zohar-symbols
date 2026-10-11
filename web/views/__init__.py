"""Route registration. One blueprint, mounted twice: at / (English) and /es (Spanish)."""
from flask import Blueprint, g, jsonify, request

from .. import db

bp = Blueprint("site", __name__)


def register(app) -> None:
    from . import home, nodes, passages, scholars, symbols  # noqa: F401  (decorate bp)

    @app.context_processor
    def _meta():
        row = db.one("select value from meta where key='tables_version'")
        return {"tables_version": row["value"] if row else ""}

    @app.before_request
    def _set_lang():
        g.lang = "es" if request.blueprint == "site_es" else "en"

    @app.route("/healthz")
    def healthz():
        row = db.one("select value from meta where key='tables_version'")
        return jsonify(ok=True, tables_version=row["value"] if row else None)

    app.register_blueprint(bp)
    app.register_blueprint(bp, url_prefix="/es", name="site_es")
