from flask import render_template

from .. import queries
from . import bp

W, H = 600, 880  # canvas; the ten circles use the 800-high grid, the Sitra Aḥra shadow sits below it
# Normalised (x, y) on a 600x800 grid; the path list refers to these as 1..10.
SEFIROT = [("keter", .5, .08), ("hokhmah", .75, .22), ("binah", .25, .22), ("hesed", .75, .36), ("gevurah", .25, .36),
           ("tiferet", .5, .50), ("netzah", .75, .64), ("hod", .25, .64), ("yesod", .5, .78), ("malkhut", .5, .92)]
PATHS = [(1, 2), (1, 3), (1, 6), (2, 3), (2, 4), (2, 6), (3, 5), (3, 6), (4, 5), (4, 6), (4, 7),
         (5, 6), (5, 8), (6, 7), (6, 8), (6, 9), (7, 8), (7, 9), (7, 10), (8, 9), (8, 10), (9, 10)]


@bp.route("/tree")
def tree():
    pts = [dict(id=n, x=round(x * 600), y=round(y * 800), ar=queries.NODE_AR[n]) for n, x, y in SEFIROT]
    lines = [(pts[a - 1], pts[b - 1]) for a, b in PATHS]
    return render_template("tree.html", node_ids=queries.NODE_ORDER, pts=pts, lines=lines, shadow=dict(id="sitra_ahra", x=300, y=1.02 * 800 + 20, ar=queries.NODE_AR["sitra_ahra"]),
                           ein_sof=dict(id="ein_sof", x=300, y=14, ar=queries.NODE_AR["ein_sof"]))
