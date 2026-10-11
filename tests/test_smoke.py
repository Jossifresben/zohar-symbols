def test_version_string():
    from pipeline.version import TABLES_VERSION
    assert TABLES_VERSION.startswith("0.")


def test_aramaic_core_imports():
    from aramaic_core import AramaicCorpus, RootExtractor
    assert AramaicCorpus and RootExtractor


def test_report_round_trip_and_headline(tmp_path):
    from pipeline.report import write_report, read_report, headline, write_sections
    rows = [("passages", 3), ("continued: 1.020a", 2), ("size outlier: 1.020a", "7 paras, 70 tokens"),
            ("top #1: moon", 4), ("a | b", "x")]
    write_report(tmp_path / "r.md", "fetch", rows)
    title, back = read_report(tmp_path / "r.md")
    assert title == "fetch" and back == [(k, str(v)) for k, v in rows]
    assert headline(back) == [("passages", "3"), ("size outlier: 1.020a", "7 paras, 70 tokens"), ("a | b", "x")]
    write_sections(tmp_path / "s.md", [("a", [("x", 1)]), ("b", [("y", 2)])])
    assert (tmp_path / "s.md").read_text().count("| item | value |") == 2
