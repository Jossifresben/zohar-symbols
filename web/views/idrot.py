from flask import g, render_template

from .. import queries
from . import bp


@bp.route("/idrot")
def idrot():
    return render_template("idrot.html", idrot=[d for d in (queries.idra(s, g.lang) for s in queries.IDROT) if d])
