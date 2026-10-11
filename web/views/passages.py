from flask import render_template

from . import bp


@bp.route("/passage/<pid>")
def passage(pid):  # placeholder, replaced in Task 4
    return render_template("stub.html")
