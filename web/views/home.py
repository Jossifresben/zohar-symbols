from flask import g, render_template, request

from .. import queries
from ..i18n import get_string
from . import bp

TOP_N = 20

# (key, grid span, node ids, title key, blurb key or None). "events" is built from kind == event.
CLUSTERS = [
    ("malkhut", 7, ["malkhut"], "cluster_malkhut_title", "cluster_malkhut_blurb"),
    ("tiferet", 5, ["tiferet"], "cluster_tiferet_title", "cluster_tiferet_blurb"),
    ("binah", 4, ["binah"], "cluster_binah_title", None),
    ("sides", 4, ["hesed", "gevurah"], "cluster_sides_title", None),
    ("yesod", 4, ["yesod"], "cluster_yesod_title", None),
    ("head", 5, ["keter", "hokhmah", "ein_sof"], "cluster_head_title", "cluster_head_blurb"),
    ("sitra", 4, ["sitra_ahra"], "cluster_sitra_title", None),
    ("events", 3, [], "cluster_events_title", None),
    ("nh", 4, ["netzah", "hod"], "cluster_nh_title", None),
]


def build_clusters(lang: str) -> list[dict]:
    nodes = {n["node"]: n for n in queries.cached("nodes_with_symbols", lang)}
    events = sorted((s for n in nodes.values() for s in n["symbols"] if s["kind"] == "event"),
                    key=lambda s: (-s["count_passages"], s["id"]))
    out = []
    for key, span, ids, title, blurb in CLUSTERS:
        if key == "events":
            parts = [dict(node=None, label=None, label_ar=None, chips=events[:TOP_N],
                          more=max(0, len(events) - TOP_N), total=len(events))]
        else:
            parts = []
            for nid in ids:
                syms = [s for s in nodes[nid]["symbols"] if s["kind"] != "event"]
                parts.append(dict(node=nid, label=nodes[nid]["label"], label_ar=nodes[nid]["label_ar"],
                                  chips=syms[:TOP_N], more=max(0, len(syms) - TOP_N), total=len(syms)))
        out.append(dict(key=key, span=span, title=title, blurb=blurb, parts=parts,
                        total=sum(p["total"] for p in parts), single=len(parts) == 1))
    return out


def _page(q: str = "", results=None, heading: str | None = None):
    return render_template("home.html", clusters=build_clusters(g.lang), q=q, results=results, heading=heading)


@bp.route("/")
def home():
    return _page()


@bp.route("/search")
def search():
    kind = request.args.get("kind", "")
    if kind in queries.KINDS:
        return _page("", queries.by_kind(kind, g.lang), heading=get_string(f"kind_{kind}", g.lang))
    q = request.args.get("q", "").strip()
    if not q:
        return _page()
    return _page(q, queries.search(q, g.lang))
