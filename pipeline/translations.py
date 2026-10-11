"""Committed model translations (data/translations.v*.jsonl) plus hand corrections
(data/translation_overrides.tsv), checked against the current passage text at build time."""
import csv
import hashlib
import json
from pathlib import Path

OVERRIDE_MODEL = "human-correction"


def source_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def load(path: Path, overrides_path: Path, passages: list[dict]) -> tuple[list[tuple], dict]:
    """Rows for the `translation` table and counts for the build report.

    A model translation is kept only if its source_hash matches the passage's current text
    (stale ones are dropped and counted). An override row wins over the model text for the
    same (passage_id, lang)."""
    text = {p["id"]: p["text_ar"] for p in passages}
    out, stale, unknown = {}, 0, 0
    if path.exists():
        for line in path.open(encoding="utf-8"):
            r = json.loads(line)
            if r["passage_id"] not in text:
                unknown += 1
            elif r["source_hash"] != source_hash(text[r["passage_id"]]):
                stale += 1
            else:
                out[(r["passage_id"], r["lang"])] = (r["passage_id"], r["lang"], r["text"], r["model"],
                                                     r["prompt_version"], r["created_at"])
    overridden = 0
    if overrides_path.exists():
        with overrides_path.open(encoding="utf-8") as f:
            for r in csv.DictReader(f, delimiter="\t"):
                if r["passage_id"] in text and r["text"].strip():
                    out[(r["passage_id"], r["lang"])] = (r["passage_id"], r["lang"], r["text"].strip(),
                                                         OVERRIDE_MODEL, r.get("note", "") or "", r.get("date", "") or "")
                    overridden += 1
    rows = [out[k] for k in sorted(out)]
    return rows, {"translations": len(rows), "translations stale (source changed)": stale,
                  "translations for unknown passages": unknown, "translations corrected by hand": overridden}
