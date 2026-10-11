"""Zohar Symbols web app: thin Flask over the precomputed tables."""
import os
from pathlib import Path

from flask import Flask

ROOT = Path(__file__).resolve().parent.parent


def create_app(db_path: str | None = None) -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config["DB_PATH"] = db_path or os.environ.get("ZOHAR_DB", str(ROOT / "data" / "zohar.sqlite"))
    app.config["JSON_AS_ASCII"] = False
    if not Path(app.config["DB_PATH"]).exists():
        raise FileNotFoundError(f"database not found: {app.config['DB_PATH']} — run `python -m pipeline.run_all`")

    from . import db
    app.teardown_appcontext(db.close_db)

    from .i18n import init_i18n
    init_i18n(app)

    from .views import register
    register(app)
    return app
