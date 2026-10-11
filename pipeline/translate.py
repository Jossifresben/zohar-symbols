"""Model-drafted translations of surfaced passages (spec §8), via the Message Batches API.

Every number this module reports (token counts, cost) is computed by code from the API's
usage fields; the model only writes the translation text.

    python -m pipeline.translate pilot --submit [--n 20] [--efforts medium,high]
    python -m pipeline.translate prewarm                      # write the 1h cache entry once
    python -m pipeline.translate full --name full_a --range 0:100 [--submit]
    python -m pipeline.translate collect <batch_id> [--name full_a]
"""
import argparse
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "zohar.sqlite"
WORK = ROOT / "work" / "translate"

MODEL = "claude-fable-5-1"
PROMPT_VERSION = "t2"
EFFORT = "medium"
CONTEXT_RADIUS = 2   # neighbouring paragraphs on each side, same folio side
LANGS = {"en": "English", "es": "Spanish"}

# Batch prices, USD per million tokens: half the standard Claude Fable 5.1 rates
# ($10 in / $50 out / $0.25 cache read; cache write 1.25x input at 5 min TTL, 2x at 1 h).
BATCH_PRICE = {"input": 5.0, "output": 25.0, "cache_read": 0.125,
               "cache_write": 6.25, "cache_write_1h": 10.0}

INSTRUCTIONS = """You translate passages of the Zohar from Aramaic (with occasional Hebrew) for a bilingual website that shows curious, non-specialist readers how the Zohar's images work.

How to translate:
- Translate faithfully and readably. Prefer clear modern prose over word-for-word calques, but do not paraphrase away the content.
- Keep the Zohar's images as images. Do not decode them: "the Moon" stays "the Moon", never "Malkhut" or "the Shekhinah" unless the text itself says so. Showing the images is the purpose of the site.
- Render every word listed in the glossary below with its glossary label, consistently, in the target language. Write glossary labels as ordinary words in normal case ("gold", "the beard", "the moon" / "oro", "la barba", "la luna"); capitalise only proper names (Abraham, Jacob, Matronita).
- Translate biblical quotations and mark them with quotation marks.
- Use the conventional forms of the sages' names (Rabbi Shimon, Rabbi Abba / Rabí Shimón, Rabí Abba).
- Add a transliteration in square brackets only where a technical term would otherwise be lost, and sparingly.
- Spanish: neutral peninsular Spanish, «» quotation marks.

You are given the neighbouring paragraphs for context. Translate only the passage marked TARGET.
Output only the translation: no title, no notes, no commentary, no transliteration of the whole passage."""


def connect(path: Path = DB) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def glossary(conn: sqlite3.Connection) -> str:
    """One line per symbol, sorted by id, so the cached system prefix is byte-identical."""
    lines = []
    for r in conn.execute("select id, label_en, label_es, aliases from symbol order by id"):
        surfaces = (r["aliases"] or "").partition("|")[0].replace(";", ", ")
        lines.append(f"{surfaces} → EN: {r['label_en']} · ES: {r['label_es']}")
    return "Glossary (Aramaic/Hebrew forms → labels):\n" + "\n".join(lines)


def system_blocks(conn: sqlite3.Connection, ttl: str | None = None, cache: bool = True) -> list[dict]:
    """The shared instructions + glossary. In the Batch API the cache was written by nearly every
    request (measured: 5,030 of 5,352 tokens per request in the first 100), so batch runs send it
    uncached: plain input at 1x is cheaper than a cache write at 1.25x/2x."""
    block = {"type": "text", "text": INSTRUCTIONS + "\n\n" + glossary(conn)}
    if cache:
        block["cache_control"] = {"type": "ephemeral", **({"ttl": ttl} if ttl else {})}
    return [block]


def surfaced_ids(conn: sqlite3.Connection) -> list[str]:
    return [r[0] for r in conn.execute("select distinct passage_id from surfaced order by passage_id")]


def pilot_ids(conn: sqlite3.Connection, n: int = 20) -> list[str]:
    """Every k-th surfaced passage in id order: spread across the book and across lengths,
    so the pilot's cost per passage extrapolates to the full set."""
    ids = surfaced_ids(conn)
    step = max(1, len(ids) // n)
    return ids[::step][:n]


def source_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def user_content(conn: sqlite3.Connection, pid: str, lang: str) -> str:
    p = conn.execute("select * from passage where id=?", (pid,)).fetchone()
    folio = conn.execute(
        "select id, text_ar from passage where volume=? and folio=? and side=? order by para",
        (p["volume"], p["folio"], p["side"])).fetchall()
    i = next(k for k, r in enumerate(folio) if r["id"] == pid)
    window = folio[max(0, i - CONTEXT_RADIUS): i + CONTEXT_RADIUS + 1]
    ctx = "\n\n".join(("[TARGET] " if r["id"] == pid else "") + r["text_ar"] for r in window)
    verse = f"The folio comments on {p['verse_ref']}.\n" if p["verse_ref"] else ""
    return (f"Target language: {LANGS[lang]}.\n{verse}\nContext:\n{ctx}\n\n"
            f"TARGET passage ({pid}):\n{p['text_ar']}")


def custom_id(pid: str, lang: str, effort: str) -> str:
    return f"{pid.replace('.', '-')}__{lang}__{effort}"


def parse_custom_id(cid: str) -> tuple[str, str, str]:
    pid, lang, effort = cid.split("__")
    v, folio, para = pid.split("-")
    return f"{v}.{folio}.{para}", lang, effort


def build_request(conn, pid: str, lang: str, effort: str, system: list[dict]) -> dict:
    return {"custom_id": custom_id(pid, lang, effort),
            "params": {"model": MODEL, "max_tokens": 16000, "system": system,
                       "output_config": {"effort": effort},
                       "messages": [{"role": "user", "content": user_content(conn, pid, lang)}]}}


def cost_usd(usage: dict) -> float:
    """Batch-priced cost of one request from its usage block (1 h cache writes priced at 2x)."""
    detail = usage.get("cache_creation") or {}
    w1h = detail.get("ephemeral_1h_input_tokens", 0) or 0
    w5m = (usage.get("cache_creation_input_tokens", 0) or 0) - w1h
    return (usage.get("input_tokens", 0) * BATCH_PRICE["input"]
            + usage.get("output_tokens", 0) * BATCH_PRICE["output"]
            + (usage.get("cache_read_input_tokens", 0) or 0) * BATCH_PRICE["cache_read"]
            + w5m * BATCH_PRICE["cache_write"] + w1h * BATCH_PRICE["cache_write_1h"]) / 1_000_000


def submit(requests: list[dict]) -> str:
    import anthropic
    batch = anthropic.Anthropic().messages.batches.create(requests=requests)
    return batch.id


def collect(batch_id: str, conn) -> list[dict]:
    import anthropic
    client = anthropic.Anthropic()
    b = client.messages.batches.retrieve(batch_id)
    if b.processing_status != "ended":
        raise SystemExit(f"batch {batch_id} is {b.processing_status}: {b.request_counts}")
    rows = []
    for res in client.messages.batches.results(batch_id):
        pid, lang, effort = parse_custom_id(res.custom_id)
        row = dict(passage_id=pid, lang=lang, effort=effort, status=res.result.type)
        if res.result.type == "succeeded":
            msg = res.result.message
            usage = msg.usage.to_dict()
            row.update(stop_reason=msg.stop_reason, model=msg.model, usage=usage,
                       cost_usd=round(cost_usd(usage), 6),
                       text="".join(b.text for b in msg.content if b.type == "text").strip())
        src = conn.execute("select text_ar, token_count from passage where id=?", (pid,)).fetchone()
        row.update(source_hash=source_hash(src["text_ar"]), source_tokens=src["token_count"],
                   prompt_version=PROMPT_VERSION)
        rows.append(row)
    rows.sort(key=lambda r: (r["passage_id"], r["lang"], r["effort"]))
    return rows


def summarize(rows: list[dict], all_tokens: int, all_passages: int) -> dict:
    """Per effort: totals, cost per source token, and the extrapolation to every surfaced passage
    in both languages."""
    out = {}
    for effort in sorted({r["effort"] for r in rows}):
        ok = [r for r in rows if r["effort"] == effort and r["status"] == "succeeded"]
        cost = sum(r["cost_usd"] for r in ok)
        src = sum({r["passage_id"]: r["source_tokens"] for r in ok}.values())  # each passage once
        out[effort] = dict(
            requests=len([r for r in rows if r["effort"] == effort]), succeeded=len(ok),
            refusals=sum(1 for r in ok if r["stop_reason"] == "refusal"),
            input_tokens=sum(r["usage"].get("input_tokens", 0) for r in ok),
            cache_read_tokens=sum(r["usage"].get("cache_read_input_tokens", 0) for r in ok),
            cache_write_tokens=sum(r["usage"].get("cache_creation_input_tokens", 0) for r in ok),
            output_tokens=sum(r["usage"].get("output_tokens", 0) for r in ok),
            cost_usd=round(cost, 4),
            # both languages per source token -> full set (all surfaced passages, both languages)
            projected_full_usd=round(cost / src * all_tokens, 2) if src else None,
            projected_basis=f"{all_passages} passages, {all_tokens} source words, EN+ES")
    return out


def _all_tokens(conn, ids):
    q = ",".join("?" * len(ids))
    return conn.execute(f"select sum(token_count) from passage where id in ({q})", ids).fetchone()[0]


def prewarm(conn) -> dict:
    """One synchronous max_tokens=0 request: writes the 1 h cache entry the batch then reads."""
    import anthropic
    r = anthropic.Anthropic().messages.create(
        model=MODEL, max_tokens=0, system=system_blocks(conn, "1h"),
        output_config={"effort": EFFORT},
        messages=[{"role": "user", "content": "warm"}])
    return r.usage.to_dict()


def main(argv=None) -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pilot")
    p.add_argument("--n", type=int, default=20)
    p.add_argument("--efforts", default="medium,high")
    p.add_argument("--submit", action="store_true")
    sub.add_parser("prewarm")
    f = sub.add_parser("full")
    f.add_argument("--name", required=True)
    f.add_argument("--range", default="0:")
    f.add_argument("--submit", action="store_true")
    f.add_argument("--no-cache", action="store_true")
    c = sub.add_parser("collect")
    c.add_argument("batch_id")
    c.add_argument("--name", default="pilot")
    a = ap.parse_args(argv)
    conn = connect()
    WORK.mkdir(parents=True, exist_ok=True)
    if a.cmd == "pilot":
        system = system_blocks(conn)
        reqs = [build_request(conn, pid, lang, eff, system)
                for pid in pilot_ids(conn, a.n) for lang in LANGS for eff in a.efforts.split(",")]
        (WORK / "pilot_requests.json").write_text(json.dumps(reqs, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{len(reqs)} requests written to {WORK / 'pilot_requests.json'}")
        if a.submit:
            bid = submit(reqs)
            (WORK / "pilot_batch_id").write_text(bid)
            print(f"submitted batch {bid}")
    elif a.cmd == "prewarm":
        print(json.dumps(prewarm(conn)))
    elif a.cmd == "full":
        system = system_blocks(conn, "1h", cache=not a.no_cache)
        all_reqs = [build_request(conn, pid, lang, EFFORT, system)
                    for pid in surfaced_ids(conn) for lang in LANGS]
        lo, _, hi = a.range.partition(":")
        reqs = all_reqs[int(lo or 0): int(hi) if hi else None]
        (WORK / f"{a.name}_requests.json").write_text(json.dumps(reqs, ensure_ascii=False), encoding="utf-8")
        print(f"{len(reqs)} of {len(all_reqs)} requests -> {a.name}")
        if a.submit:
            bid = submit(reqs)
            (WORK / f"{a.name}_batch_id").write_text(bid)
            print(f"submitted batch {bid}")
    else:
        rows = collect(a.batch_id, conn)
        with (WORK / f"{a.name}_results.jsonl").open("w", encoding="utf-8") as fh:
            for r in rows:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        ids = surfaced_ids(conn)
        s = summarize(rows, _all_tokens(conn, ids), len(ids))
        (WORK / f"{a.name}_summary.json").write_text(json.dumps(s, indent=1), encoding="utf-8")
        json.dump(s, sys.stdout, indent=1)
        print()


if __name__ == "__main__":
    main()
