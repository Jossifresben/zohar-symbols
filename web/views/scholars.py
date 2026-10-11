from flask import render_template

from . import bp


@bp.route("/scholars")
def scholars():  # placeholder, replaced in Task 7
    return render_template("base.html")
