"""Route registration. One blueprint, mounted twice: at / (English) and /es (Spanish)."""
from flask import Blueprint, g, has_request_context, jsonify, render_template, request, url_for
from markupsafe import Markup, escape

from pipeline.lemmatise import SPLIT, is_word, protect_gershayim

from .. import db, queries

bp = Blueprint("site", __name__)


def highlight(text_ar: str, mentions: list[dict], prefer: str | None = None) -> Markup:
    """The passage text, reproduced exactly, with each mentioned token wrapped in a link to its symbol.

    Splits with the pipeline's own separator pattern (`SPLIT`, on gershayim-protected text so offsets match)
    and counts only the pieces `tokenize` keeps, so the counter equals `mention.position`. Separators and
    non-word pieces are emitted verbatim (escaped). A position tagged with several symbols links to `prefer`
    (the page's own symbol) when present, else to the first by symbol id. Positions past the end are ignored.
    """
    if not text_ar:
        return Markup("")
    at: dict[int, list[str]] = {}
    for m in mentions:
        at.setdefault(m["position"], []).append(m["symbol_id"])
    out, pos = [], 0
    protected = protect_gershayim(text_ar)
    for kind, a, b in _pieces(protected):
        orig = text_ar[a:b]
        if kind == "word":
            ids = at.get(pos)
            if ids:
                sid = prefer if prefer in ids else min(ids)
                out.append(Markup('<a class="mention" href="{}">{}</a>').format(_symbol_href(sid), orig))
            else:
                out.append(escape(orig))
            pos += 1
        else:
            out.append(escape(orig))
    return Markup("").join(out)


def _pieces(protected: str):
    """(kind, start, end) spans covering `protected` exactly: 'sep' for SPLIT matches, 'word'/'other' between."""
    i = 0
    for m in SPLIT.finditer(protected):
        if m.start() > i:
            yield ("word" if is_word(protected[i:m.start()]) else "other", i, m.start())
        yield ("sep", m.start(), m.end())
        i = m.end()
    if i < len(protected):
        yield ("word" if is_word(protected[i:]) else "other", i, len(protected))


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
        if "/sefirah/" in request.path:
            return render_template("404_node.html", node_ids=queries.NODE_ORDER), 404
        q = request.path.rstrip("/").rsplit("/", 1)[-1]
        suggestions = queries.nearest_symbols(q, g.lang) if q and q != "es" else []
        return render_template("404.html", suggestions=suggestions), 404

    @app.route("/healthz")
    def healthz():
        row = db.one("select value from meta where key='tables_version'")
        return jsonify(ok=True, tables_version=row["value"] if row else None)

    app.register_blueprint(bp)
    app.register_blueprint(bp, url_prefix="/es", name="site_es")
