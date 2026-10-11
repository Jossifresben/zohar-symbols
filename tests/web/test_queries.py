from web import queries as q


def test_meta(app):
    with app.app_context():
        m = q.meta()
        assert m["tables_version"] and m["built_at"]


def test_nodes_with_symbols_sizes(app):
    with app.app_context():
        nodes = q.nodes_with_symbols("en")
        malkhut = next(n for n in nodes if n["node"] == "malkhut")
        moon = next(s for s in malkhut["symbols"] if s["id"] == "moon")
        # moon: 1.020a.001, 1.020a.002, 1.020b.001, 1.020b.003 (Ra'aya Meheimna)
        assert moon["count_passages"] == 4 and 15 <= moon["size"] <= 44
        assert [n["node"] for n in nodes] == q.NODE_ORDER
        assert malkhut["label"] == "Malkhut"
        assert q.nodes_with_symbols("es")[3]["label"] == "Jésed"


def test_symbol_and_partners(app):
    with app.app_context():
        s = q.symbol("moon", "es")
        assert s["label"] == "Luna" and s["label_other"] == "Moon" and s["node"] == "malkhut"
        assert s["aliases_surface"] == ["סיהרא", "לבנה"] and s["aliases_root"] == ["סהר"]
        assert s["gloss"] == "Luna: aparece en 4 pasajes del Zohar; su compañero más frecuente es Sol (juntos en 3 pasajes)."
        p = q.partners("moon", "en")
        # moon-sun are together in 1.020a.001, 1.020b.001, 1.020b.003
        assert p[0]["id"] == "sun" and p[0]["passages_together"] == 3 and p[0]["label"] == "Sun" and "pmi" not in p[0]
        assert q.partners("moon", "es")[0]["label"] == "Sol"


def test_states_and_unmarked(app):
    with app.app_context():
        st = q.states("moon")
        labels = {x["label"]: x["count"] for x in st["states"]}
        assert labels == {"full": 1, "diminished": 0}
        assert st["unmarked"] == 3


def test_strata(app):
    with app.app_context():
        assert {x["stratum"]: x["count"] for x in q.strata_distribution("moon")} == {"main": 3, "raaya_meheimna": 1}


def test_surfaced_order(app):
    with app.app_context():
        assert [p["id"] for p in q.surfaced("moon", "en")] == ["1.020b.001", "1.020a.001", "1.020a.002", "1.020b.003"]


def test_passage_card_and_folio(app):
    with app.app_context():
        p = q.passage("1.020b.002", "en")
        assert p["citation"] == "Zohar I:20b" and p["stream"] == "main"
        assert {m["symbol_id"] for m in p["mentions"]} >= {"king", "matronita", "coupling"}
        assert p["translation"] is None
        assert q.passage("1.020b.003", "en")["stream"] == "raaya_meheimna"
        f = q.folio(1, 20, "b", "en")
        assert [x["id"] for x in f] == ["1.020b.001", "1.020b.002", "1.020b.003"]


def test_node(app):
    with app.app_context():
        n = q.node("malkhut", "en")
        assert n["pillar"] == "middle"
        assert any("moon" == s["id"] for ss in n["symbols_by_kind"].values() for s in ss)
        assert n["partner_nodes"][0] == {"node": "tiferet", "label": "Tif'eret", "passages_together": 4}  # distinct passages: a.001, b.001, b.003 (moon+sun) + b.002 (matronita+king)
        assert q.node("hesed", "en")["pillar"] == "right" and q.node("nope", "en") is None


def test_search_and_nearest(app):
    with app.app_context():
        assert q.search("luna", "es")[0]["id"] == "moon"
        assert q.search("MOON", "en")[0]["id"] == "moon"
        assert q.search("סיהרא", "en")[0]["id"] == "moon"
        assert q.search("זווגין", "en")[0]["id"] == "coupling"
        assert q.search("סהר", "en") == []  # root part of aliases is not searched
        assert "moon" in [x["id"] for x in q.nearest_symbols("mooon", "en")]
        assert q.nearest_symbols("mooon", "es")[0]["label"] == "Luna"
        assert "river" in [x["id"] for x in q.search("RIO", "es")]  # seed label "Río"
        assert "hidden_eden" in [x["id"] for x in q.search("eden", "en")]  # "Edén oculto"


def test_scholars_pairs(app):
    with app.app_context():
        assert q.scholars_pairs(min_together=3)[0]["passages_together"] == 3
        p = q.scholars_pairs(min_together=3, lang="es")[0]
        assert {p["a_label"], p["b_label"]} == {"Luna", "Sol"} and "pmi" in p
        assert q.scholars_pairs(min_together=99) == []


def test_unknowns_return_none(app):
    with app.app_context():
        assert q.symbol("nope", "en") is None and q.passage("9.999z.999", "en") is None


def test_cite():
    from web import cite
    import pytest
    with pytest.raises(ValueError):
        cite.roman(4)
    assert cite.citation(1, 20, "a") == "Zohar I:20a" and cite.roman(3) == "III"
    f = cite.formats({"tables_version": "0.1.0"})
    assert "zohar.digital" in f["bibtex"] and "[DOI pending]" in f["chicago"]
