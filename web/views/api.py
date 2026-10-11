"""Exports. Registered on the shared blueprint, so /es/api/... also resolves (same bytes; the API is language-independent)."""
import csv
import io

from flask import Response, jsonify

from .. import queries
from . import bp


def _version() -> str | None:
    return queries.meta().get("tables_version")


def _csv(name: str, header: list[str], rows: list[list]) -> Response:
    buf = io.StringIO(newline="")
    buf.write(f"# tables_version={_version()}\n")
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(header)
    w.writerows(rows)
    resp = Response("﻿" + buf.getvalue(), mimetype="text/csv")
    resp.headers["Content-Type"] = "text/csv; charset=utf-8"
    resp.headers["Content-Disposition"] = f'attachment; filename="{name}"'
    return resp


def _unknown(sid: str):
    return jsonify(error=f"unknown symbol: {sid}", tables_version=_version()), 404


@bp.route("/api/symbol/<sid>.csv")
def api_symbol_csv(sid):
    if not queries.symbol(sid, "en"):
        return _unknown(sid)
    cols = ["passage_id", "citation", "position", "matched_form", "via"]
    return _csv(f"{sid}.csv", cols, [[m[c] for c in cols] for m in queries.symbol_mentions(sid, "en")])


@bp.route("/api/symbol/<sid>.json")
def api_symbol_json(sid):
    s = queries.symbol(sid, "en")
    if not s:
        return _unknown(sid)
    row = next(r for r in queries.symbols_table("en") if r["id"] == sid)
    return jsonify(tables_version=_version(), symbol=row, mentions=queries.symbol_mentions(sid, "en"))


@bp.route("/api/pairs.csv")
def api_pairs_csv():
    cols = ["symbol_a", "symbol_b", "passages_together", "pmi"]
    return _csv("pairs.csv", cols, [[p[c] for c in cols] for p in queries.all_pairs()])


@bp.route("/api/symbols.json")
def api_symbols_json():
    return jsonify(tables_version=_version(), symbols=queries.symbols_table("en"))


@bp.route("/api/meta.json")
def api_meta_json():
    m = queries.meta()
    return jsonify(tables_version=m.get("tables_version"), meta=m)
