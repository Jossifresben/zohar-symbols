"""UI strings (strings.json) and the `t()` template helper. Task 8 makes g.lang URL-driven."""
import json
from pathlib import Path

from flask import g

STRINGS_PATH = Path(__file__).parent / "strings.json"


def init_i18n(app) -> None:
    strings = json.loads(STRINGS_PATH.read_text(encoding="utf-8"))

    def t(key: str, **kw) -> str:
        entry = strings.get(key)
        if entry is None:
            if app.testing:
                raise KeyError(key)
            return key
        return entry[g.get("lang", "en")].format(**kw)

    @app.before_request
    def _set_lang():
        g.lang = "en"

    @app.context_processor
    def _ctx():
        return {"lang": g.get("lang", "en")}

    app.jinja_env.globals["t"] = t
