from flask import render_template

from . import bp


@bp.route("/symbol/<sid>")
def symbol(sid):  # placeholder, replaced in Task 4
    return render_template("stub.html")
