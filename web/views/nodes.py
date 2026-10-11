from . import bp


@bp.route("/sefirah/<nid>")
def node(nid):  # placeholder, replaced in Task 4
    return "coming in Task 4"


@bp.route("/tree")
def tree():  # placeholder, replaced in a later task
    return "coming soon"
