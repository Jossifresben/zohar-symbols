from flask import g, render_template

from .. import cite, queries
from . import bp


@bp.route("/scholars")
def scholars():
    meta = queries.meta()
    shares = queries.token_shares()
    counts = dict(shares, symbols=len(queries.symbols_table(g.lang)), aliases=queries.alias_count())
    return render_template("scholars.html", meta=meta, counts=counts, formats=cite.formats(meta),
                           revids=", ".join(str(r) for r in _revids(meta)), pairs=queries.scholars_pairs(lang=g.lang))


@bp.route("/about")
def about():
    return render_template("about.html")


def _revids(meta: dict) -> list:
    import json
    raw = meta.get("source_revids", "")
    try:
        v = json.loads(raw)
    except ValueError:
        return [raw] if raw else []
    return list(v.values()) if isinstance(v, dict) else list(v) if isinstance(v, list) else [v]
