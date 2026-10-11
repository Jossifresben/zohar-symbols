"""Route registration. One blueprint, mounted twice: at / (English) and /es (Spanish)."""
from flask import Blueprint, g, has_request_context, jsonify, render_template, request, url_for
from markupsafe import Markup, escape

from pipeline.lemmatise import tokenize

from .. import db, queries

bp = Blueprint("site", __name__)


def highlight(text_ar: str, mentions: list[dict]) -> Markup:
    """The passage text with each mentioned token wrapped in a link to its symbol.

    Re-tokenises with the pipeline's own `tokenize`, whose indices are what `mention.position` counts, and
    re-joins with single spaces. The pipeline normalised whitespace, so this reproduces the text except that
    punctuation-only tokens (dropped by `tokenize`) and punctuation glued to words outside Hebrew letters are lost.
    """
    if not text_ar:
        return Markup("")
    at = {m["position"]: m["symbol_id"] for m in mentions}
    out = []
    for i, tok in enumerate(tokenize(text_ar)):
        if i in at:
            out.append(Markup('<a class="mention" href="{}">{}</a>').format(_symbol_href(at[i]), tok))
        else:
            out.append(escape(tok))
    return Markup(" ").join(out)


def _symbol_href(sid: str) -> str:
    if has_request_context():
        return url_for(("site_es." if g.get("lang") == "es" else "site.") + "symbol", sid=sid)
    return f"/symbol/{escape(sid)}"


def register(app) -> None:
    from . import api, ask, home, nodes, passages, scholars, symbols, tree  # noqa: F401  (decorate bp)

    app.jinja_env.filters["highlight"] = highlight

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
        q = request.path.rstrip("/").rsplit("/", 1)[-1]
        suggestions = queries.nearest_symbols(q, g.lang) if q and q != "es" else []
        return render_template("404.html", suggestions=suggestions), 404

    @app.route("/healthz")
    def healthz():
        row = db.one("select value from meta where key='tables_version'")
        return jsonify(ok=True, tables_version=row["value"] if row else None)

    app.register_blueprint(bp)
    app.register_blueprint(bp, url_prefix="/es", name="site_es")
