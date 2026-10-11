from flask import render_template

from . import bp


@bp.route("/api/symbol/<sid>.csv")
def api_symbol_csv(sid):  # placeholder, replaced in Task 7
    return render_template("stub.html")
