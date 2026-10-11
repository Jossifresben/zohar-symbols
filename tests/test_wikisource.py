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


class RevSession:
    """Serves revisions by id; 'latest' answers a titles= query."""
    def __init__(self, revs: dict[int, tuple[str, str]], latest: dict[str, int]):
        self.revs, self.latest, self.calls = revs, latest, []

    def get(self, url, params=None, timeout=None):
        self.calls.append(dict(params))
        if "revids" in params:
            rid = int(params["revids"])
            if rid not in self.revs:
                return FakeResp({"query": {"badrevids": {str(rid): {"revid": rid}}}})
        else:
            rid = self.latest[params["titles"]]
        title, text = self.revs[rid]
        return FakeResp({"query": {"pages": [{"pageid": 1, "title": title, "revisions": [
            {"revid": rid, "timestamp": "2026-10-01T00:00:00Z",
             "slots": {"main": {"content": text}}}]}]}})


def test_fetch_pinned_revision(tmp_path: Path):
    sess = RevSession({1: ("זוהר חלק א", "ישן"), 2: ("זוהר חלק א", "חדש")}, {"זוהר חלק א": 2})
    p = fetch_page("זוהר חלק א", tmp_path, session=sess, revid=1)
    assert (p.revid, p.wikitext) == (1, "ישן")
    assert sess.calls[-1]["revids"] == "1" and "titles" not in sess.calls[-1]
    assert fetch_page("זוהר חלק א", tmp_path, session=sess, revid=1) == p and len(sess.calls) == 1
    # the cache holds rev 1; asking for rev 2 refetches
    assert fetch_page("זוהר חלק א", tmp_path, session=sess, revid=2).wikitext == "חדש"
    assert len(sess.calls) == 2


def test_fetch_bad_revision_raises(tmp_path: Path):
    import pytest
    sess = RevSession({}, {})
    with pytest.raises(LookupError):
        fetch_page("x", tmp_path, session=sess, revid=7)


def test_lockfile_pins_adds_and_refetch_rewrites(tmp_path: Path):
    from pipeline.fetch import fetch_locked
    revs = {1: ("A", "a1"), 2: ("A", "a2"), 5: ("B", "b5"), 6: ("B", "b6")}
    sess = RevSession(revs, {"A": 2, "B": 6})
    lock = tmp_path / "lock.json"
    lock.write_text(json.dumps({"A": 1}), encoding="utf-8")
    cache = tmp_path / "cache"
    got = fetch_locked(["A", "B"], cache, lock, session=sess)
    assert [p.wikitext for p in got] == ["a1", "b6"]            # A pinned; B missing -> latest
    assert json.loads(lock.read_text(encoding="utf-8")) == {"A": 1, "B": 6}
    got = fetch_locked(["A", "B"], cache, lock, refetch=True, session=sess)
    assert [p.wikitext for p in got] == ["a2", "b6"]
    assert json.loads(lock.read_text(encoding="utf-8")) == {"A": 2, "B": 6}
    n = len(sess.calls)
    fetch_locked(["A", "B"], cache, lock, session=sess)      # cached at the locked revisions
    assert len(sess.calls) == n


def test_refetch_only_clears_the_requested_titles(tmp_path: Path):
    from pipeline.fetch import fetch_locked
    sess = RevSession({1: ("A", "a1"), 2: ("A", "a2"), 5: ("B", "b5"), 6: ("B", "b6")}, {"A": 1, "B": 5})
    lock, cache = tmp_path / "lock.json", tmp_path / "cache"
    fetch_locked(["A", "B"], cache, lock, session=sess)
    sess.latest = {"A": 2, "B": 6}
    got = fetch_locked(["A"], cache, lock, refetch=True, session=sess)       # --refetch --only 1
    assert [p.wikitext for p in got] == ["a2"]
    assert json.loads(lock.read_text(encoding="utf-8")) == {"A": 2, "B": 5}
    n = len(sess.calls)
    assert fetch_locked(["A", "B"], cache, lock, session=sess)[1].wikitext == "b5"  # B still cached
    assert len(sess.calls) == n
