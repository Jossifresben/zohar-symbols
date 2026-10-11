from pathlib import Path
import pytest
from pipeline import translate as tr

REAL = Path(__file__).parent.parent / "data" / "zohar.sqlite"


def test_custom_id_round_trip():
    cid = tr.custom_id("3.152a.005", "es", "medium")
    assert cid == "3-152a-005__es__medium"
    assert tr.parse_custom_id(cid) == ("3.152a.005", "es", "medium")


def test_cost_is_batch_priced():
    u = {"input_tokens": 1_000_000, "output_tokens": 1_000_000,
         "cache_read_input_tokens": 1_000_000, "cache_creation_input_tokens": 1_000_000}
    assert tr.cost_usd(u) == pytest.approx(5.0 + 25.0 + 0.125 + 6.25)


def test_summarize_projects_both_languages_per_passage():
    rows = [dict(passage_id="p1", lang=l, effort="medium", status="succeeded", stop_reason="end_turn",
                 source_tokens=10, cost_usd=1.0, usage={"output_tokens": 1}) for l in ("en", "es")]
    s = tr.summarize(rows, all_tokens=100, all_passages=10)["medium"]
    assert s["cost_usd"] == 2.0 and s["projected_full_usd"] == 20.0   # $2 per 10 words, both langs


@pytest.mark.skipif(not REAL.exists(), reason="real database not built")
def test_requests_share_a_byte_identical_cached_system():
    conn = tr.connect(REAL)
    system = tr.system_blocks(conn)
    ids = tr.pilot_ids(conn, 20)
    assert len(ids) == 20 and len(set(ids)) == 20
    reqs = [tr.build_request(conn, pid, "en", "medium", system) for pid in ids[:3]]
    assert all(r["params"]["system"] == reqs[0]["params"]["system"] for r in reqs)
    assert "סיהרא" in system[0]["text"] and "Luna" in system[0]["text"]
    assert "[TARGET]" in reqs[0]["params"]["messages"][0]["content"]
    assert reqs[0]["params"]["model"] == "claude-fable-5-1"


def test_cost_prices_1h_cache_writes_at_double():
    u = {"cache_creation_input_tokens": 2_000_000,
         "cache_creation": {"ephemeral_1h_input_tokens": 1_000_000, "ephemeral_5m_input_tokens": 1_000_000}}
    assert tr.cost_usd(u) == pytest.approx(6.25 + 10.0)


@pytest.mark.skipif(not REAL.exists(), reason="real database not built")
def test_context_window_is_two_neighbours_each_side():
    conn = tr.connect(REAL)
    content = tr.user_content(conn, "3.199a.020", "en")
    ctx = content.split("Context:\n", 1)[1].split("\n\nTARGET passage", 1)[0]
    assert ctx.count("\n\n") == 4 and "[TARGET]" in ctx
