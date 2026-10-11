from flask import render_template

from . import bp


@bp.route("/ask")
def ask():  # placeholder
    return render_template("stub.html", msg="ask_coming")
