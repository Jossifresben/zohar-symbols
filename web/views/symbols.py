from flask import abort, g, render_template

from .. import cite, queries
from ..i18n import get_string
from . import bp

TOP_GOLD = 3          # evidence strip: the first three partners are gold
ALSO_WITH = 4         # "How it moves": partners listed after the top one
ALL_STRATA_MIN = 3    # strata chip says "across strata" from this many on


def _pct(n: int, total: int) -> int:
    """Bar width as an integer percentage, 0–100; a non-zero count never draws an empty bar."""
    if not total or n <= 0:
        return 0
    return max(1, min(100, round(100 * n / total)))


def _state_label(label: str, lang: str) -> str:
    try:
        return get_string(f"state_{label}", lang)
    except KeyError:
        return label


@bp.route("/symbol/<sid>")
def symbol(sid):
    s = queries.symbol(sid, g.lang)
    if s is None:
        abort(404)
    n = s["count_passages"]
    partners = queries.partners(sid, g.lang)
    for i, p in enumerate(partners):
        p["width"] = _pct(p["passages_together"], n)
        p["tone"] = "red" if p["node"] == "sitra_ahra" else ("gold" if i < TOP_GOLD else "blue")
    st = queries.states(sid)
    for x in st["states"]:
        x["display"] = _state_label(x["label"], g.lang)
    strata = queries.strata_distribution(sid)
    for x in strata:
        x["width"] = _pct(x["count"], n)
    also = [a for a in s["aliases_surface"] if a != s["label_ar"]]
    return render_template("symbol.html", s=s, partners=partners, also_with=partners[1:1 + ALSO_WITH],
                           states=st, strata=strata, all_strata=len(strata) >= ALL_STRATA_MIN,
                           cards=queries.surfaced(sid, g.lang), also=also,
                           citation=cite.formats(queries.meta())["chicago"])
