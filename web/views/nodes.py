from flask import abort, g, render_template

from .. import queries
from . import bp


@bp.route("/sefirah/<nid>")
def node(nid):
    n = queries.node(nid, g.lang)
    if n is None:
        abort(404)
    kinds = [k for k in queries.KINDS if k in n["symbols_by_kind"]]
    return render_template("node.html", n=n, kinds=kinds)
