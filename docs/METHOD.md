# For scholars

_Generated from `web/strings.json` by `python -m web.method_doc`; the same text is on https://zohar.digital/scholars. Do not edit by hand._

Method, provenance, data and citation. No number on this site is produced by a model: deterministic code counts, a model only translates and interprets, and every step is listed here.

Code and data: https://github.com/Jossifresben/zohar-symbols · DOI [10.5281/zenodo.23305097](https://doi.org/10.5281/zenodo.23305097)

## Method

**Corpus and strata.** The text is the Hebrew Wikisource Zohar, in Mantua pagination, taken from its 29 parasha pages. Passages are the folio paragraphs. The editors' section labels and headings give nine text streams (main, Ra'aya Meheimna, Midrash ha-Ne'lam, Sitrei Torah, Raza de-Razin, Tosefta, Matnitin, other, addendum). Every non-main stream is its own stratum. Main-stream passages inside the conventional Idra Rabba and Idra Zuta ranges of seeds/strata.tsv take those strata, and those inside the Shemot Midrash ha-Ne'lam ranges (II 4a–5b, 14a–21b; text Wikisource leaves unlabelled) join the Midrash ha-Ne'lam stratum; all other main-stream passages stay "main". Eleven strata in all: main, Idra Rabba, Idra Zuta, and the eight labelled streams.

**Lemmatisation.** Each word is reduced to a root where possible, with the Aramaic Root Atlas (aramaic_core) and a Zohar override table; the override table takes precedence over aramaic_core. Overrides are looked up through the proclitics ו ד ב ל כ מ ש. An override with an empty root marks a known non-lexical token, such as the abbreviation הקב״ה. Words the extractor cannot place are kept and counted as unknown.

**Mention tagging.** A symbol is tagged by its surface aliases (matched through safe proclitic pairs) and by its distinctive roots; a surface alias takes precedence over a root match on the same token. For multi-word aliases the longest match wins. The word immediately after רבי, ר׳, א״ר or רב is not tagged at all, neither by a single-word alias nor by root, because it is the name of a sage; multi-word aliases are exempt from this rule.

**Co-occurrence and PMI.** Two symbols co-occur in a passage (a folio paragraph) only when each has at least one mention on a token the other does not tag; a symbol whose tokens are a subset of the other's is a rival, not a partner. PMI = log2(c·N / (fa·fb)), where c is the number of passages where the pair co-occurs, fa and fb the passages mentioning each symbol, and N all passages. It is shown only for pairs with at least 5 passages together.

**States.** A symbol's state (for example full or diminished) is detected in a passage that mentions the symbol when any one of the marker roots declared for that state occurs in the passage. The markers are declared in the seed, not inferred.

**Surfaced passages.** Candidates are the passages that mention the symbol. Each is scored (2·own mentions + mentions of the symbol's top three partners) / (tokens + 20). Passages of at least 12 tokens have priority and, among them, one per stratum comes first, then the rest by score; shorter passages are used only to fill six. Ties are broken by passage id (folio order).

**Raw and resolved counts.** The raw count is every tagged mention. When two or more symbols are tagged on the same token, a symbol's mention is dropped from its resolved count only when a rival on that token has strictly more support than the symbol itself; ties keep both. Support of a symbol is the number of symbols of its node present in the passage, not counting any of the symbols tagged on the shared token. Support is not normalised by node size, so nodes with many seeded symbols (Malkhut) win more often. The raw count is always shown beside the resolved one.

## Provenance

Seed sources. The symbols and their aliases are seeded from Cordovero's Pardes Rimonim (gate 23), Gikatilla's Sha'arei Orah, the Zohar's own usage, and additions. Each symbol records its seed source.

Figures for this build (passages, tokens, roots, mentions, pairs, translations, interpretations): [data/report.md](../data/report.md).

Caveats. The strata ranges are conventional. Parasha is a page-level label, not a property of each passage. A scholarly spot-check of the boundaries of the Midrash ha-Ne'lam and the addenda is pending. No passage is numbered Zohar III 116a–b. Wikisource marks no folio 116, and the three classical commentaries on Sefaria (Ohr HaChamah, Mikdash Melekh, Yahel Or) have no comment there either; 115b is of ordinary length and Bamidbar opens at 117a. This looks like a skip in the printed numbering, not lost text, but it has not been checked against a scan of the print.

## Translations and interpretations

**Translations.** 678 surfaced passages (the strongest passages of each symbol, deduplicated) are translated from the Aramaic into English and into Spanish, each language directly from the Aramaic, by Claude Fable 5.1 (claude-fable-5-1) through Anthropic's Batch API. The model is given the passage, two paragraphs on each side for context, the verse under comment and a glossary of every symbol label, so the images keep the dictionary's names. It is told to keep images as images ("the moon" stays "the moon") and not to decode them; Teshuvah keeps its name, glossed as "the return of the he".

**Interpretations.** Under 677 of those translations, "What this passage means" is a plain-language reading of about 120–200 words in each language (some run longer), by the same model. It is given the passage, its neighbours, our English translation and the passage's keys (each image and the sefirah it usually stands for), and asked to say what happens, what the images stand for and why it matters; to gloss every technical term; to say so where a passage is open; and not to use later Kabbalistic terms (partzufim, tzimtzum) unless the passage itself does. It is given no commentary and cites none: in a blind pilot, readings written with the classical commentaries Ohr HaChamah and Mikdash Melekh as background were not preferred to plain ones. The model declined one passage (III 128a, Idra Rabba), which has none.

**Checks and provenance.** Code, not the model, checks every output: its shape, its length, and that it uses no later terms and names no commentator. Each row stores the model id, the prompt version, the date and a hash of the Aramaic it was made from; if that text changes, the row is dropped at the next build. Hand corrections go into data/translation_overrides.tsv and data/interpretation_overrides.tsv and replace the model text. Every translation and interpretation has a "Report a problem" link.

**Status.** None of this has been reviewed by specialists. Read the interpretations as one informed reading, not as the tradition's verdict. The prompts are in the repository (pipeline/translate.py, pipeline/interpret.py).

## Tables

tables_version: `0.1.0`. [Full source list: data/SOURCES.md](../data/SOURCES.md)

## Exports

- `https://zohar.digital/api/symbols.json`: all symbols with counts (JSON)
- `https://zohar.digital/api/pairs.csv`: all co-occurrence pairs (CSV)
- `https://zohar.digital/api/meta.json`: build metadata (JSON)

Per symbol: every mention as CSV (UTF-8 with BOM, opens in Excel; the first line is a comment, # tables_version=…, so read it with pandas comment='#') or JSON, e.g. /api/symbol/moon.csv. Every export carries the tables_version.

## Cite

**BibTeX**

```
@misc{zohar_symbols_2026,
  author = {Fresco Benaim, Jose},
  title = {Zohar Symbols: a computed dictionary of the Zohar's kinnuyim},
  year = {2026},
  version = {0.1.0},
  url = {https://zohar.digital},
  doi = {10.5281/zenodo.23305097}
}
```

**Chicago**

```
Fresco Benaim, Jose. 2026. “Zohar Symbols: a computed dictionary of the Zohar's kinnuyim.” Version 0.1.0. https://zohar.digital. https://doi.org/10.5281/zenodo.23305097.
```

**SBL**

```
Fresco Benaim, Jose. Zohar Symbols: a computed dictionary of the Zohar's kinnuyim. Version 0.1.0. 2026. https://zohar.digital. https://doi.org/10.5281/zenodo.23305097.
```

## Caveat

We are not scholars. We aim to provide a pleasant experience of the Zohar. Translations and symbol glosses are produced by Anthropic's Claude Fable and have not been reviewed by specialists.

## Licences

Code: MIT. Text and tables: CC BY-SA 4.0, attributing Hebrew Wikisource. The cited works of Cordovero and Gikatilla are in the public domain; this project's summaries of them are CC BY-SA 4.0 like the rest of the tables.
