"""Every figure a page shows is a column read here; nothing is computed by a model."""
import difflib
import math

from . import cite
from .db import fold, one, all as rows
from .i18n import fmt_num, get_string

NODE_ORDER = ["keter", "hokhmah", "binah", "hesed", "gevurah", "tiferet", "netzah", "hod", "yesod", "malkhut", "sitra_ahra", "ein_sof"]
NODE_AR = {"keter": "כתר", "hokhmah": "חכמה", "binah": "בינה", "hesed": "חסד", "gevurah": "גבורה", "tiferet": "תפארת",
           "netzah": "נצח", "hod": "הוד", "yesod": "יסוד", "malkhut": "מלכות", "sitra_ahra": "סטרא אחרא", "ein_sof": "אין סוף"}
STATE_ORDER = ["full", "diminished", "union", "exile"]  # display order; undeclared labels follow alphabetically
PILLAR = {"hesed": "right", "netzah": "right", "hokhmah": "right", "gevurah": "left", "hod": "left", "binah": "left",
          "keter": "middle", "tiferet": "middle", "yesod": "middle", "malkhut": "middle", "sitra_ahra": None, "ein_sof": None}


def t_node(n: str, lang: str) -> str:
    return get_string(f"node_{n}", lang)


def _lab(row, lang: str) -> str:
    return row[f"label_{lang}"] or row["label_en"]


def _size(count: int, cmax: int) -> int:
    if count <= 0:
        return 15
    return int(round(15 + 15 * math.log1p(count) / math.log1p(max(cmax, 1))))


def meta() -> dict:
    return {r["key"]: r["value"] for r in rows("select key, value from meta")}


def nodes_with_symbols(lang: str) -> list[dict]:
    syms = rows("select id,label_en,label_es,label_ar,kind,node,count_passages from symbol order by count_passages desc, id")
    cmax = syms[0]["count_passages"] if syms else 1
    by: dict[str, list] = {n: [] for n in NODE_ORDER}
    for r in syms:
        by.setdefault(r["node"], []).append(dict(id=r["id"], label=_lab(r, lang), label_ar=r["label_ar"], kind=r["kind"],
                                                 count_passages=r["count_passages"], size=_size(r["count_passages"], cmax)))
    return [dict(node=n, label=t_node(n, lang), label_ar=NODE_AR[n], symbols=by[n]) for n in NODE_ORDER]


def partners(sid: str, lang: str, k: int = 7) -> list[dict]:
    ps = rows("""select case when symbol_a=? then symbol_b else symbol_a end as other, passages_together, pmi
                 from cooccurrence where symbol_a=? or symbol_b=? order by passages_together desc, other limit ?""",
              (sid, sid, sid, k))
    if not ps:
        return []
    ids = [r["other"] for r in ps]
    info = {r["id"]: (_lab(r, lang), r["node"]) for r in rows(
        f"select id,label_en,label_es,node from symbol where id in ({','.join('?' * len(ids))})", tuple(ids))}
    return [dict(id=r["other"], label=info[r["other"]][0], node=info[r["other"]][1], passages_together=r["passages_together"])
            for r in ps]


def _n_passages(n: int, lang: str) -> str:
    return get_string("passages_one" if n == 1 else "passages_n", lang, n=fmt_num(n, lang))


def symbol(sid: str, lang: str) -> dict | None:
    s = one("select * from symbol where id=?", (sid,))
    if not s:
        return None
    other = "es" if lang == "en" else "en"
    surface, _, roots = (s["aliases"] or "").partition("|")
    label = _lab(s, lang)
    gloss = s[f"gloss_{lang}"]
    if not gloss:
        top = partners(sid, lang, 1)
        n = s["count_passages"]
        if n == 0:
            gloss = get_string("gloss_fallback_none", lang, label=label)
        elif top:
            m = top[0]["passages_together"]
            gloss = get_string("gloss_fallback", lang, label=label, passages=_n_passages(n, lang), partner=top[0]["label"],
                               together=get_string("passages_together_one" if m == 1 else "passages_together_n", lang, n=m))
        else:
            gloss = get_string("gloss_fallback_alone", lang, label=label, passages=_n_passages(n, lang))
    return dict(id=s["id"], label=label, label_ar=s["label_ar"], label_other=_lab(s, other), kind=s["kind"], node=s["node"],
                node_label=t_node(s["node"], lang),
                aliases_surface=[a for a in surface.split(";") if a], aliases_root=[a for a in roots.split(";") if a],
                count_raw=s["count_raw"], count_resolved=s["count_resolved"], count_passages=s["count_passages"],
                seed_source=s["seed_source"], gloss=gloss, moves=s[f"moves_{lang}"] or None)


def states(sid: str) -> dict:
    decl = sorted(rows("select state_label, marker_roots from state_decl where symbol_id=?", (sid,)),
                  key=lambda d: (STATE_ORDER.index(d["state_label"]) if d["state_label"] in STATE_ORDER else len(STATE_ORDER),
                                 d["state_label"]))
    counts = {r["state_label"]: r["n"] for r in rows(
        "select state_label, count(*) n from state where symbol_id=? group by state_label", (sid,))}
    marked = one("select count(distinct passage_id) n from state where symbol_id=?", (sid,))["n"]
    tot = one("select count_passages n from symbol where id=?", (sid,))
    total = tot["n"] if tot else 0
    return dict(states=[dict(label=d["state_label"], marker_roots=d["marker_roots"], count=counts.get(d["state_label"], 0)) for d in decl],
                unmarked=max(0, total - marked))


def strata_distribution(sid: str) -> list[dict]:
    return [dict(stratum=r["stratum"], count=r["n"]) for r in rows(
        """select p.stratum, count(distinct p.id) n from mention m join passage p on p.id=m.passage_id
           where m.symbol_id=? group by p.stratum order by n desc, p.stratum""", (sid,))]


def surfaced(sid: str, lang: str) -> list[dict]:
    ids = [r["passage_id"] for r in rows("select passage_id from surfaced where symbol_id=? order by rank", (sid,))]
    return [p for p in (passage(pid, lang) for pid in ids) if p]


def passage(pid: str, lang: str) -> dict | None:
    p = one("select * from passage where id=?", (pid,))
    if not p:
        return None
    ms = rows("""select m.position, m.symbol_id, m.matched_form, s.label_en, s.label_es from mention m
                 join symbol s on s.id=m.symbol_id where m.passage_id=? order by m.position""", (pid,))
    tr = one("select text, model_id from translation where passage_id=? and lang=?", (pid, lang))
    return dict(id=p["id"], citation=cite.citation(p["volume"], p["folio"], p["side"]), volume=p["volume"], folio=p["folio"],
                side=p["side"], para=p["para"], parasha=p["parasha"], stream=p["stream"], stratum=p["stratum"],
                text_ar=p["text_ar"], verse_ref=p["verse_ref"], token_count=p["token_count"],
                translation=tr["text"] if tr else None, translation_model=tr["model_id"] if tr else None,
                mentions=[dict(position=m["position"], symbol_id=m["symbol_id"], matched_form=m["matched_form"], label=_lab(m, lang)) for m in ms])


SEED_SOURCES = ["cordovero_23", "gikatilla", "zohar_usage", "added"]  # where a symbol's sefirah assignment comes from


def passage_keys(pid: str, lang: str) -> list[dict]:
    """The symbols of one passage in reading order (first mention), each with the forms matched in the text,
    its sefirah and the source of that assignment. Read from the seed and the tagger, no model."""
    out: dict[str, dict] = {}
    for r in rows("""select m.symbol_id, m.matched_form, s.label_en, s.label_es, s.label_ar, s.kind, s.node, s.seed_source
                     from mention m join symbol s on s.id=m.symbol_id where m.passage_id=? order by m.position""", (pid,)):
        k = out.setdefault(r["symbol_id"], dict(id=r["symbol_id"], label=_lab(r, lang), label_ar=r["label_ar"], kind=r["kind"],
                                                node=r["node"], node_label=t_node(r["node"], lang), node_ar=NODE_AR[r["node"]],
                                                source=r["seed_source"], forms=[], count=0))
        k["count"] += 1
        if r["matched_form"] not in k["forms"]:
            k["forms"].append(r["matched_form"])
    return list(out.values())


def folio(volume: int, fol: int, side: str, lang: str) -> list[dict]:
    ids = [r["id"] for r in rows("select id from passage where volume=? and folio=? and side=? order by para, id", (volume, fol, side))]
    return [passage(pid, lang) for pid in ids]


def folio_neighbours(volume: int, fol: int, side: str) -> tuple[str | None, str | None]:
    """First passage id of the previous / next folio-side that exists (the data has gaps), ordered (volume, folio, side)."""
    cur = (volume, fol, side)
    sides = rows("select volume, folio, side, min(para) as para from passage group by volume, folio, side order by volume, folio, side")
    prev = nxt = None
    for r in sides:
        key = (r["volume"], r["folio"], r["side"])
        if key < cur:
            prev = r
        elif key > cur and nxt is None:
            nxt = r
    def pid(r):
        if not r:
            return None
        return one("select id from passage where volume=? and folio=? and side=? and para=? order by id limit 1",
                   (r["volume"], r["folio"], r["side"], r["para"]))["id"]
    return pid(prev), pid(nxt)


def folio_symbols(volume: int, fol: int, side: str, lang: str) -> list[dict]:
    """Distinct symbols mentioned on a folio-side, by passage count then id (display-only, no sizes)."""
    return [dict(id=r["id"], kind=r["kind"], label=_lab(r, lang), label_ar=r["label_ar"], size=16) for r in rows(
        """select s.id, s.kind, s.label_en, s.label_es, s.label_ar, count(distinct m.passage_id) n from mention m
           join passage p on p.id=m.passage_id join symbol s on s.id=m.symbol_id
           where p.volume=? and p.folio=? and p.side=? group by s.id order by n desc, s.id""", (volume, fol, side))]


def node(nid: str, lang: str) -> dict | None:
    if nid not in NODE_ORDER:
        return None
    by_kind: dict[str, list] = {}
    cm = one("select max(count_passages) as m from symbol")
    cmax = (cm["m"] if cm else 1) or 1
    for r in rows("select id,label_en,label_es,label_ar,kind,count_passages from symbol where node=? order by count_passages desc, id", (nid,)):
        by_kind.setdefault(r["kind"], []).append(dict(id=r["id"], label=_lab(r, lang), label_ar=r["label_ar"], kind=r["kind"],
                                                      count_passages=r["count_passages"], size=_size(r["count_passages"], cmax)))
    pn = rows("""select s2.node as other, count(distinct m1.passage_id) as n
                 from mention m1 join symbol s1 on s1.id=m1.symbol_id
                 join mention m2 on m2.passage_id=m1.passage_id join symbol s2 on s2.id=m2.symbol_id
                 where s1.node=? and s2.node<>s1.node
                 group by s2.node order by n desc, s2.node""", (nid,))
    return dict(node=nid, label=t_node(nid, lang), label_ar=NODE_AR[nid], pillar=PILLAR.get(nid),
                symbols_by_kind=by_kind,
                partner_nodes=[dict(node=r["other"], label=t_node(r["other"], lang), passages_together=r["n"]) for r in pn])


def search(q: str, lang: str, k: int = 10) -> list[dict]:
    q = q.strip()
    if not q:
        return []
    qf = fold(q)
    rs = rows("""select id,label_en,label_es,label_ar,kind,node,count_passages from symbol
                 where instr(fold(label_en),?)>0 or instr(fold(label_es),?)>0 or instr(label_ar,?)>0
                    or instr(substr(aliases,1,instr(aliases||'|','|')-1),?)>0
                 order by count_passages desc, id limit ?""", (qf, qf, q, q, k))
    return [dict(id=r["id"], label=_lab(r, lang), label_ar=r["label_ar"], kind=r["kind"], node=r["node"],
                 count_passages=r["count_passages"]) for r in rs]


KINDS = ("person", "object", "quality", "event")


def by_kind(kind: str, lang: str) -> list[dict]:
    rs = rows("""select id,label_en,label_es,label_ar,kind,node,count_passages from symbol
                 where kind=? order by count_passages desc, id""", (kind,))
    return [dict(id=r["id"], label=_lab(r, lang), label_ar=r["label_ar"], kind=r["kind"], node=r["node"],
                 count_passages=r["count_passages"]) for r in rs]


def nearest_symbols(q: str, lang: str, k: int = 3) -> list[dict]:
    names: dict[str, str] = {}
    labels: dict[str, str] = {}
    for r in rows("select id,label_en,label_es from symbol"):
        labels[r["id"]] = _lab(r, lang)
        for cand in (r["id"], r["label_en"], r["label_es"]):
            names.setdefault(fold(cand), r["id"])
    out: list[str] = []
    for m in difflib.get_close_matches(fold(q.strip()), list(names), n=k * 3, cutoff=0.6):
        if names[m] not in out:
            out.append(names[m])
    return [dict(id=i, label=labels[i]) for i in out[:k]]


def scholars_pairs(min_together: int = 5, limit: int = 200, lang: str = "en") -> list[dict]:
    return [dict(a=r["symbol_a"], b=r["symbol_b"], a_label=_lab({"label_en": r["ae"], "label_es": r["as_"]}, lang),
                 b_label=_lab({"label_en": r["be"], "label_es": r["bs"]}, lang), a_ar=r["aa"], b_ar=r["ba"],
                 passages_together=r["passages_together"], pmi=r["pmi"])
            for r in rows("""select c.symbol_a, c.symbol_b, a.label_en ae, a.label_es as_, a.label_ar aa, b.label_en be, b.label_es bs, b.label_ar ba,
                                    c.passages_together, c.pmi
                             from cooccurrence c join symbol a on a.id=c.symbol_a join symbol b on b.id=c.symbol_b
                             where c.passages_together >= ? order by c.pmi desc, c.symbol_a, c.symbol_b limit ?""",
                          (min_together, limit))]


def token_shares() -> dict:
    """Token totals by lemma outcome: with a root, known non-lexical (empty-root override), unknown; plus confidence >= 0.8."""
    r = one("""select count(*) tokens,
                      coalesce(sum(case when root is not null then 1 else 0 end),0) with_root,
                      coalesce(sum(case when source='override' and root is null then 1 else 0 end),0) non_lexical,
                      coalesce(sum(case when root is null and source='none' then 1 else 0 end),0) unknown,
                      coalesce(sum(case when confidence >= 0.8 then 1 else 0 end),0) conf_high
               from token""")
    return dict(tokens=r["tokens"], with_root=r["with_root"], non_lexical=r["non_lexical"], unknown=r["unknown"],
                conf_high=r["conf_high"])


def passage_totals() -> dict:
    r = one("select count(*) passages, count(distinct volume||'.'||folio||side) sides from passage")
    return dict(passages=r["passages"], sides=r["sides"])


def alias_split() -> dict:
    """Alias totals as surface forms and roots (the two kinds the tagger matches on)."""
    forms = roots_n = 0
    for r in rows("select aliases from symbol"):
        surface, _, roots = r["aliases"].partition("|")
        forms += len([a for a in surface.split(";") if a])
        roots_n += len([a for a in roots.split(";") if a])
    return dict(surfaces=forms, roots=roots_n)


def alias_count() -> int:
    s = alias_split()
    return s["surfaces"] + s["roots"]


def symbol_mentions(sid: str, lang: str) -> list[dict]:
    return [dict(passage_id=r["passage_id"], citation=cite.citation(r["volume"], r["folio"], r["side"]), position=r["position"],
                 matched_form=r["matched_form"], via=r["via"])
            for r in rows("""select m.passage_id, p.volume, p.folio, p.side, m.position, m.matched_form, m.via
                             from mention m join passage p on p.id=m.passage_id where m.symbol_id=?
                             order by p.volume, p.folio, p.side, p.para, m.position""", (sid,))]


def symbols_table(lang: str) -> list[dict]:
    return [dict(id=r["id"], label=_lab(r, lang), label_en=r["label_en"], label_es=r["label_es"], label_ar=r["label_ar"],
                 kind=r["kind"], node=r["node"], count_raw=r["count_raw"], count_resolved=r["count_resolved"],
                 count_passages=r["count_passages"], seed_source=r["seed_source"])
            for r in rows("""select id,label_en,label_es,label_ar,kind,node,count_raw,count_resolved,count_passages,seed_source
                             from symbol order by id""")]


def all_pairs() -> list[dict]:
    return [dict(symbol_a=r["symbol_a"], symbol_b=r["symbol_b"], passages_together=r["passages_together"], pmi=r["pmi"])
            for r in rows("select symbol_a, symbol_b, passages_together, pmi from cooccurrence order by pmi desc, symbol_a, symbol_b")]


LANGS = ("en", "es")


def warm(app) -> None:
    """Compute the expensive page data once; the DB never changes between deploys, so the cache is immutable.

    Call inside an app context. Stores `app.config["CACHE"]` (key -> value, or key -> {lang: value}) and
    `app.config["CACHE_WARM_MS"]`.
    """
    import time
    t0 = time.perf_counter()
    app.config["CACHE"] = {
        "meta": meta(),
        "nodes_with_symbols": {lang: nodes_with_symbols(lang) for lang in LANGS},
        "token_shares": token_shares(),
        "passage_totals": passage_totals(),
        "alias_split": alias_split(),
        "scholars_pairs": {lang: scholars_pairs(lang=lang) for lang in LANGS},
    }
    app.config["CACHE_WARM_MS"] = round((time.perf_counter() - t0) * 1000, 1)


def cached(key: str, lang: str | None = None):
    """A warmed value; KeyError for an unknown key (or language). Treat the result as read-only."""
    from flask import current_app
    v = current_app.config["CACHE"][key]
    return v if lang is None else v[lang]
