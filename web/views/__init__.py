"""Route registration. One blueprint, mounted twice: at / (English) and /es (Spanish)."""
import re

from flask import Blueprint, g, has_request_context, jsonify, render_template, request, url_for
from markupsafe import Markup, escape

from pipeline.lemmatise import SPLIT, is_word, protect_gershayim

from .. import db, queries
from ..i18n import get_string

bp = Blueprint("site", __name__)


MODEL_NAMES = {"claude-fable-5-1": "Claude Fable 5.1"}
BOOKS = ("Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy")


def verse_ref(ref: str | None) -> str:
    """Localise the book name of a pipeline verse reference ("Exodus 23:17")."""
    if not ref:
        return ""
    book, _, rest = ref.partition(" ")
    if book in BOOKS:
        name = get_string(f"book_{book.lower()}", g.lang)
        return f"{name} {rest}".strip()
    return ref


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


_PID = re.compile(r"^(\d)\.(\d{3})([a-z])\.(\d{3})$")


def _passage_suggestions(pid: str, lang: str) -> list[dict]:
    """Where to go from a passage id that does not exist: the first passage of its folio-side if that exists, the
    neighbouring folio-sides' first passages, and always the very first passage. Each is {id, citation}."""
    ids: list[str] = []
    m = _PID.match(pid)
    if m:
        v, f, s = int(m.group(1)), int(m.group(2)), m.group(3)
        own = db.one("select id from passage where volume=? and folio=? and side=? order by para, id limit 1", (v, f, s))
        if own:
            ids.append(own["id"])
        ids += [x for x in queries.folio_neighbours(v, f, s) if x]
    first = db.one("select id from passage order by volume, folio, side, para limit 1")
    if first and first["id"] not in ids:
        ids.append(first["id"])
    out = []
    for i in ids:
        p = queries.passage(i, lang)
        if p:
            out.append(dict(id=i, citation=p["citation"]))
    return out


def register(app) -> None:
    from . import api, ask, home, nodes, passages, scholars, symbols, tree  # noqa: F401  (decorate bp)

    app.jinja_env.filters["highlight"] = highlight
    app.jinja_env.filters["verse_ref"] = verse_ref

    @app.context_processor
    def _meta():
        return {"tables_version": queries.cached("meta").get("tables_version", "")}

    with app.app_context():
        row = db.one("select id from passage order by volume, folio, side, para limit 1")
    def passage_url(pid: str) -> str:
        """Passage page URL scrolled to the paragraph (`#p<para>`); pid is `v.FFFs.PPP`."""
        para = int(pid.rsplit(".", 1)[-1])
        return url_for(("site_es." if g.get("lang") == "es" else "site.") + "passage", pid=pid) + f"#p{para}"

    app.jinja_env.globals["passage_url"] = passage_url

    def report_url(pid: str) -> str:
        """A prefilled GitHub issue for a translation problem (no backend, no accounts)."""
        from urllib.parse import urlencode
        lang = g.get("lang", "en")
        body = (f"Passage: {pid}\nLanguage: {lang}\nPage: https://zohar.digital{passage_url(pid)}\n\n"
                "What is wrong, and what should it say?\n")
        return "https://github.com/Jossifresben/zohar-symbols/issues/new?" + urlencode(
            {"title": f"Translation: {pid} ({lang})", "labels": "translation", "body": body})

    app.jinja_env.globals["report_url"] = report_url
    app.jinja_env.globals["model_name"] = lambda m: MODEL_NAMES.get(m, m)
    app.jinja_env.globals["first_passage_id"] = row["id"] if row else ""

    @app.before_request
    def _set_lang():
        g.lang = "es" if request.path == "/es" or request.path.startswith("/es/") else "en"

    @app.errorhandler(404)
    def _not_found(_e):
        if "/passage/" in request.path:
            return render_template("404.html", message="passage_not_found", suggestions=[],
                                   passage_suggestions=_passage_suggestions(request.path.rstrip("/").rsplit("/", 1)[-1], g.lang)), 404
        if "/sefirah/" in request.path:
            return render_template("404_node.html", node_ids=queries.NODE_ORDER), 404
        q = request.path.rstrip("/").rsplit("/", 1)[-1]
        suggestions = queries.nearest_symbols(q, g.lang) if q and q != "es" else []
        return render_template("404.html", suggestions=suggestions), 404

    @app.route("/healthz")
    def healthz():
        row = db.one("select value from meta where key='tables_version'")
        return jsonify(ok=True, tables_version=row["value"] if row else None, cache_warm_ms=app.config["CACHE_WARM_MS"])

    app.register_blueprint(bp)
    app.register_blueprint(bp, url_prefix="/es", name="site_es")
