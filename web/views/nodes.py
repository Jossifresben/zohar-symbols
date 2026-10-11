from flask import render_template

from . import bp


@bp.route("/sefirah/<nid>")
def node(nid):  # placeholder, replaced in Task 4
    return render_template("stub.html")
