"""Read-only access to data/zohar.sqlite, one connection per request."""
import sqlite3
import unicodedata
from flask import current_app, g


def fold(s) -> str:
    """Case- and accent-insensitive form (SQLite lower() is ASCII-only)."""
    d = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in d if not unicodedata.combining(c)).casefold()


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        path = current_app.config["DB_PATH"]
        g.db = sqlite3.connect(f"file:{path}?mode=ro", uri=True, check_same_thread=False)
        g.db.row_factory = sqlite3.Row
        g.db.create_function("fold", 1, fold, deterministic=True)
    return g.db


def close_db(_exc=None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def one(sql: str, params: tuple = ()) -> sqlite3.Row | None:
    return get_db().execute(sql, params).fetchone()


def all(sql: str, params: tuple = ()) -> list[sqlite3.Row]:
    return get_db().execute(sql, params).fetchall()
