import json
from pathlib import Path
from pipeline.wikisource import fetch_page, PageText


class FakeResp:
    def __init__(self, payload): self._p = payload
    def raise_for_status(self): pass
    def json(self): return self._p


class FakeSession:
    def __init__(self, payload): self.payload = payload; self.calls = 0
    def get(self, url, params=None, timeout=None):
        self.calls += 1
        return FakeResp(self.payload)


def _payload(title, text):
    return {"query": {"pages": [{"pageid": 123, "title": title, "revisions": [
        {"revid": 999, "timestamp": "2026-10-01T00:00:00Z",
         "slots": {"main": {"contentmodel": "wikitext", "contentformat": "text/x-wiki",
                            "content": text}}}]}]}}


def test_fetch_parses_and_caches(tmp_path: Path):
    sess = FakeSession(_payload("זוהר חלק א", "<קטע התחלה=דף א א/>טקסט<קטע סוף=דף א א/>"))
    p = fetch_page("זוהר חלק א", tmp_path, session=sess)
    assert isinstance(p, PageText)
    assert p.revid == 999 and "טקסט" in p.wikitext
    assert sess.calls == 1
    # second call hits the cache
    p2 = fetch_page("זוהר חלק א", tmp_path, session=sess)
    assert p2 == p and sess.calls == 1
    assert len(list(tmp_path.glob("*.json"))) == 1


def test_missing_page_raises(tmp_path: Path):
    sess = FakeSession({"query": {"pages": [{"title": "x", "missing": True}]}})
    import pytest
    with pytest.raises(LookupError):
        fetch_page("x", tmp_path, session=sess)
