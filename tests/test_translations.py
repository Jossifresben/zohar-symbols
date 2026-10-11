import json
from pipeline import translations as tr

PASSAGES = [{"id": "1.020a.001", "text_ar": "שמשא וסיהרא"}, {"id": "1.020a.002", "text_ar": "אחרא"}]


def _write(tmp_path, rows):
    p = tmp_path / "t.jsonl"
    p.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    return p


def _row(pid, lang, text, src):
    return dict(passage_id=pid, lang=lang, text=text, model="claude-fable-5-1", prompt_version="t2",
                source_hash=tr.source_hash(src), created_at="2026-10-11")


def test_load_keeps_matching_drops_stale_and_unknown(tmp_path):
    path = _write(tmp_path, [_row("1.020a.001", "en", "Sun and moon", "שמשא וסיהרא"),
                             _row("1.020a.002", "en", "Other", "changed text"),
                             _row("9.999a.001", "en", "Nowhere", "x")])
    rows, stats = tr.load(path, tmp_path / "none.tsv", PASSAGES)
    assert [r[:3] for r in rows] == [("1.020a.001", "en", "Sun and moon")]
    assert stats["translations stale (source changed)"] == 1
    assert stats["translations for unknown passages"] == 1


def test_override_wins(tmp_path):
    path = _write(tmp_path, [_row("1.020a.001", "es", "Sol y luna", "שמשא וסיהרא")])
    ov = tmp_path / "ov.tsv"
    ov.write_text("passage_id\tlang\ttext\tnote\tdate\n1.020a.001\tes\tEl sol y la luna\tissue #1\t2026-10-12\n",
                  encoding="utf-8")
    rows, stats = tr.load(path, ov, PASSAGES)
    assert rows == [("1.020a.001", "es", "El sol y la luna", tr.OVERRIDE_MODEL, "issue #1", "2026-10-12")]
    assert stats["translations corrected by hand"] == 1


def test_committed_file_matches_current_passages():
    from pathlib import Path
    import sqlite3
    root = Path(__file__).parent.parent
    f, db = root / "data" / "translations.v0.1.0.jsonl", root / "data" / "zohar.sqlite"
    if not (f.exists() and db.exists()):
        import pytest; pytest.skip("data not built")
    con = sqlite3.connect(db)
    passages = [{"id": i, "text_ar": t} for i, t in con.execute("select id, text_ar from passage")]
    rows, stats = tr.load(f, root / "data" / "translation_overrides.tsv", passages)
    assert stats["translations"] == 1356 and stats["translations stale (source changed)"] == 0
