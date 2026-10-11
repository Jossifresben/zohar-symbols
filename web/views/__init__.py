"""Route registration. One blueprint, mounted twice: at / (English) and /es (Spanish)."""
from flask import Blueprint, g, jsonify, render_template, request

from .. import db

bp = Blueprint("site", __name__)


def register(app) -> None:
    from . import ask, home, nodes, passages, scholars, symbols, tree  # noqa: F401  (decorate bp)

    @app.context_processor
    def _meta():
        row = db.one("select value from meta where key='tables_version'")
        return {"tables_version": row["value"] if row else ""}

    with app.app_context():
        row = db.one("select id from passage order by volume, folio, side, para limit 1")
    app.jinja_env.globals["first_passage_id"] = row["id"] if row else ""

    @app.before_request
    def _set_lang():
        g.lang = "es" if request.path == "/es" or request.path.startswith("/es/") else "en"

    @app.errorhandler(404)
    def _not_found(_e):
        return render_template("stub.html", msg="not_found"), 404

    @app.route("/healthz")
    def healthz():
        row = db.one("select value from meta where key='tables_version'")
        return jsonify(ok=True, tables_version=row["value"] if row else None)

    app.register_blueprint(bp)
    app.register_blueprint(bp, url_prefix="/es", name="site_es")
