"""docs/METHOD.md, generated from the strings the Scholars page shows, so the
page and the repository never say different things.

    python -m web.method_doc          # rewrite it (a test fails if it is stale)
"""
import json
from pathlib import Path

from pipeline.version import TABLES_VERSION

from . import cite
from .i18n import fmt_num

ROOT = Path(__file__).resolve().parent.parent
STRINGS = json.loads((ROOT / "web" / "strings.json").read_text(encoding="utf-8"))
OUT = {"en": ROOT / "docs" / "METHOD.md"}   # English only in the repository; the site has both languages
METHOD_KEYS = ["corpus", "lemma", "tag", "cooc", "states", "surf", "resolve"]
MODEL_KEYS = ["translate", "interpret", "checks", "status"]
EXPORTS = [("/api/symbols.json", "sch_e_symbols"), ("/api/pairs.csv", "sch_e_pairs"), ("/api/meta.json", "sch_e_meta")]
NOTE = {"en": "Generated from `web/strings.json` by `python -m web.method_doc`; the same text is on https://zohar.digital/scholars. Do not edit by hand.",
        "es": "Generado desde `web/strings.json` con `python -m web.method_doc`; el mismo texto está en https://zohar.digital/es/scholars. No editar a mano."}
FIGURES = {"en": "Figures for this build (passages, tokens, roots, mentions, pairs, translations, interpretations): [data/report.md](../data/report.md).",
           "es": "Cifras de esta construcción (pasajes, tokens, raíces, menciones, pares, traducciones, interpretaciones): [data/report.md](../data/report.md)."}


def t(key: str, lang: str, **kw) -> str:
    return STRINGS[key][lang].format(**kw)


def bold_head(text: str) -> str:
    """'Heading. Body…' -> '**Heading.** Body…' (the Scholars page renders the same split)."""
    i = text.find(". ") + 1
    return f"**{text[:i]}**{text[i:]}"


def counts(lang: str) -> dict:
    """Passages with a translation / an interpretation, counted from the committed data files."""
    out = {}
    for key, name in (("translated", "translations"), ("interpreted", "interpretations")):
        path = ROOT / "data" / f"{name}.v{TABLES_VERSION}.jsonl"
        ids = {json.loads(line)["passage_id"] for line in path.open(encoding="utf-8")} if path.exists() else set()
        out[key] = fmt_num(len(ids), lang)
    return out


def render(lang: str) -> str:
    n = counts(lang)
    fmt = cite.formats({"tables_version": TABLES_VERSION}, lang)
    lines = [f"# {t('sch_title', lang)}", "", f"_{NOTE[lang]}_", "", t("sch_intro", lang), "",
             f"{t('sch_repo', lang)}: https://github.com/Jossifresben/zohar-symbols · DOI [{cite.DOI}](https://doi.org/{cite.DOI})", "",
             f"## {t('sch_method_h', lang)}", ""]
    lines += [bold_head(t(f"sch_m_{k}", lang)) + "\n" for k in METHOD_KEYS]
    lines += [f"## {t('sch_prov_h', lang)}", "", t("sch_p_seed", lang), "", FIGURES[lang], "", t("sch_p_cav", lang), "",
              f"## {t('sch_model_h', lang)}", ""]
    lines += [bold_head(t(f"sch_x_{k}", lang, **n)) + "\n" for k in MODEL_KEYS]
    lines += [f"## {t('sch_tables_h', lang)}", "", f"{t('sch_t_version', lang)}: `{TABLES_VERSION}`. "
              f"[{t('sch_t_sources', lang)}](../data/SOURCES.md)", "", f"## {t('sch_exports_h', lang)}", ""]
    lines += [f"- `https://zohar.digital{path}`: {t(key, lang)}" for path, key in EXPORTS]
    lines += ["", t("sch_e_symbol", lang), "", f"## {t('sch_cite_h', lang)}", ""]
    for k in ("bibtex", "chicago", "sbl"):
        head = t(f"sch_cite_{k}", lang)
        lines += [f"**{head}**", "", "```", fmt[k], "```", ""]
    lines += [f"## {t('sch_caveat_h', lang)}", "", t("caveat", lang), "", f"## {t('sch_lic_h', lang)}", "", t("sch_lic_text", lang), ""]
    return "\n".join(lines)


def main() -> None:
    for lang, path in OUT.items():
        path.write_text(render(lang), encoding="utf-8")
        print(path)


if __name__ == "__main__":
    main()
