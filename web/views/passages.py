from flask import abort, g, render_template

from .. import queries
from . import bp


@bp.route("/passage/<pid>")
def passage(pid):
    p = queries.passage(pid, g.lang)
    if not p:
        abort(404)
    paras = queries.folio(p["volume"], p["folio"], p["side"], g.lang)
    prev_id, next_id = queries.folio_neighbours(p["volume"], p["folio"], p["side"])
    nb = {k: queries.passage(v, g.lang) if v else None for k, v in (("prev", prev_id), ("next", next_id))}
    return render_template("passage.html", p=p, paras=paras, nb=nb,
                           symbols=queries.folio_symbols(p["volume"], p["folio"], p["side"], g.lang))
