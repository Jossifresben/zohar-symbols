def test_version_string():
    from pipeline.version import TABLES_VERSION
    assert TABLES_VERSION.startswith("0.")


def test_aramaic_core_imports():
    from aramaic_core import AramaicCorpus, RootExtractor
    assert AramaicCorpus and RootExtractor
