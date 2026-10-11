"""Route registration. Later tasks add blueprints here."""
from flask import jsonify

from .. import db


def register(app) -> None:
    @app.context_processor
    def _meta():
        row = db.one("select value from meta where key='tables_version'")
        return {"tables_version": row["value"] if row else ""}

    @app.route("/healthz")
    def healthz():
        row = db.one("select value from meta where key='tables_version'")
        return jsonify(ok=True, tables_version=row["value"] if row else None)

    @app.route("/")
    def index():
        from flask import render_template
        return render_template("base.html")

    @app.route("/scholars")
    def scholars():
        from flask import render_template
        return render_template("base.html")
