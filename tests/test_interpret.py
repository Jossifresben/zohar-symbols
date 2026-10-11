from pathlib import Path
import pytest
from pipeline import interpret as ip
from pipeline import translate as tr

REAL = Path(__file__).parent.parent / "data" / "zohar.sqlite"


def test_custom_id_parses_as_both_languages_and_variant():
    assert tr.parse_custom_id(ip.custom_id("1.027a.004", "grounded")) == ("1.027a.004", "both", "grounded")


def test_split_langs():
    assert ip.split_langs("### EN\nOne.\n### ES\nUno.") == {"en": "One.", "es": "Uno."}
    assert ip.split_langs("### EN\nOne.") is None
    assert ip.split_langs("### EN\n\n### ES\nUno.") is None


@pytest.mark.skipif(not REAL.exists(), reason="real database not built")
def test_plain_and_grounded_requests_differ_only_by_background():
    conn = tr.connect(REAL)
    pid = "1.027a.004"
    plain = ip.user_content(conn, pid, grounded=False)
    assert "TARGET passage:" in plain and "Keys (image -> usual sefirah):" in plain and "Background:" not in plain
    grounded = ip.user_content(conn, pid, grounded=True)
    assert grounded.startswith(plain)
    assert ip.build_request(conn, pid, "plain")["params"]["model"] == tr.MODEL


def test_check_length_tolerance_and_idra_terms():
    body = " ".join(["word"] * 230)
    assert ip.check(f"### EN\n{body}\n### ES\n{body}") is None
    long = " ".join(["word"] * 280)
    assert ip.check(f"### EN\n{long}\n### ES\nuno") == "en 280 words"
    t = "### EN\nZeir Anpin here.\n### ES\nZeir Anpin aquí."
    assert ip.check(t, "דזעיר אנפין") is None
    assert ip.check(t, "בלא") == "banned: ['Zeir Anpin']"


def test_commentator_names_are_whole_words_case_sensitive():
    assert ip.check("### EN\nnefesh, the vital soul\n### ES\nel alma vital") is None
    assert ip.check("### EN\nas Vital explains\n### ES\nuno") == "banned: ['Vital']"
