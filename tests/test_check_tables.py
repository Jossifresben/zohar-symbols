import shutil
from pathlib import Path

from pipeline import check_tables
from pipeline.version import TABLES_VERSION

DATA = Path(__file__).resolve().parents[1] / "data"


def _copy(tmp_path):
    for n in (f"tables.v{TABLES_VERSION}.json", f"tables.v{TABLES_VERSION}.sha256"):
        shutil.copy(DATA / n, tmp_path / n)
    return tmp_path


def test_check_tables_match(tmp_path):
    assert check_tables.check(_copy(tmp_path)) == 0


def test_check_tables_tamper(tmp_path, capsys):
    d = _copy(tmp_path)
    f = d / f"tables.v{TABLES_VERSION}.json"
    f.write_bytes(f.read_bytes() + b" ")
    assert check_tables.check(d) == 1
    assert "does not match" in capsys.readouterr().err


def test_check_tables_missing_hash(tmp_path):
    d = _copy(tmp_path)
    (d / f"tables.v{TABLES_VERSION}.sha256").unlink()
    assert check_tables.check(d) == 1


def test_committed_hash_matches_committed_tables():
    assert check_tables.check() == 0
