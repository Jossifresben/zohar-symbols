from flask import render_template

from . import bp


@bp.route("/tree")
def tree():  # placeholder
    return render_template("stub.html")
