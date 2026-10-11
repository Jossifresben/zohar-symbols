# Zohar Symbols — Design Spec

**Date:** 2026-10-11 · **Status:** approved conversationally, awaiting written review
**Author:** Jossi Fresco Benaim with Claude (Fable 5.1)
**Repo:** `Jossifresben/zohar-symbols` · **Domain:** zohar.digital (procured 2026-10-11)
**Design reference:** mockup canvas https://claude.ai/artifact/LNcGFhBgXUKqs3SuxRB8RS (Home + Moon page)

---

## 1. Purpose

A bilingual (ES/EN) web app for the curious reader of the Zohar. The Zohar speaks in a code of images (the Moon, the Sea, the Apple Orchard, the Right Hand) that stand for the ten sefirot and the forces around them. The app makes that code visible: what each symbol stands for, how its meaning shifts with its partners and states, and the passages where it lives. Every count is computed deterministically from the text; the model only phrases, translates and (in one clearly marked place) interprets.

A secondary Scholars section exposes the method, the tables and exports.

**Not** a seeker's tool, **not** a reading engine, **not** part of CosmicCoach. Open-access, Zenodo DOI, CITATION.cff.

### What the user said (brief)

- Audience: the curious, not scholars. Symbology is the heart. Scholars get a sub-section.
- Enter from the symbol; the family/marriage drama, not the Tree diagram, is the organising story.
- v1 = Symbols + Sefirot + Scholars tail + Ask. Full reader and Zohar Chadash / Tikkunei Zohar are v2.
- Ask: strict, cited answer first; then a "model reading" visibly marked as the model's.
- Translations and glosses by Claude Fable, attributed by name and model ID, with the caveat: *we are not scholars; we aim to provide a pleasant experience of the Zohar.* No human review gate; a "report a problem" path instead.
- Licences with attribution are acceptable (CC BY-SA). Nothing that depends on permission.
- Deploy on Render, Starter plan from the start.

### Hard rules carried in

- The LLM never produces a number. Deterministic code computes every count and correlation.
- Model output is a suggestion with provenance: model-pinned, prompt-hashed, cached.
- Never push, deploy or tag without the user saying so in that message.

---

## 2. Background the design rests on

- The ten sefirot predate the Zohar (Sefer Yetzirah, Bahir, Gerona/Castile). The Zohar takes the scheme for granted and speaks in *kinnuyim*: hundreds of images mapping onto ~12 nodes (ten sefirot, Ein Sof, Sitra Aḥra). It almost never uses the word "sefirot".
- Meaning is relational: the Moon means Malkhut because of the Sun; the Sea is Malkhut when rivers flow into it, Binah when it is the source. A glossary gets this wrong; co-occurrence gets it right. **This is the insight the app delivers.**
- The Tree diagram (ten circles, 22 paths) is post-Zoharic (14th-c. *ilanot*; Kircher 1652 fixed the Golden Dawn layout). It appears in the app as orientation, labelled as later.
- Prior art: hand-made lexica (Tishby; Liebes 1977; Scholem's card index at NLI; Cordovero *Pardes Rimonim* gate 23; Gikatilla *Sha'arei Orah*), text search sites (Sefaria, zoharonline), Koppel/Bar-Ilan stylometry on three sub-corpora. **No computed symbol dictionary exists.** The "artificial Aramaic" question (Scholem vs. Bar-Asher Siegal) is live; the app does not take a side.
- Base text: Hebrew Wikisource *Sefer ha-Zohar*, Mantua pagination (the standard citation system), CC BY-SA 4.0. Excluded: Matt's critical text (copyright), Sefaria's main Aramaic version (licence unknown), Soncino English (not PD in the EU until 2038), Pritzker.
- Vocabulary of the Zohar ≈ 6,000–6,300 words. Tractable.

---

## 3. Architecture

Approach chosen: **new app, shared core.** One repo, two packages that never import each other, sharing committed data.

```
zohar-symbols/
  pipeline/        offline, deterministic, run by hand per text version
    fetch.py       Wikisource → raw/zohar.v{N}.json (folio-keyed, Mantua)
    segment.py     folios → passages (paragraph units, stable ids)
    lemmatise.py   aramaic_core + seeds/zohar_overrides.tsv → tokens (root, stem, confidence)
    tag.py         seeds/kinnuyim.tsv → symbol mentions per passage
    compute.py     co-occurrence, states, strata, surfaced-passage selection
    translate.py   Fable drafts for surfaced passages; cached by passage hash
    gloss.py       Fable one-sentence meanings + "how it moves" per symbol; cached
    build.py       writes data/zohar.sqlite + data/tables.v{N}.json + report.md
  web/             Flask app; reads data/, never computes
  data/            committed outputs, versioned; what the DOI points at
    SOURCES.md     Wikisource revision ids, fetch date
  seeds/
    kinnuyim.tsv            symbol seed list (see §5)
    strata.tsv              folio ranges → stratum (Tishby's divisions)
    tradition_glosses.tsv   Cordovero / Gikatilla entries per symbol
    zohar_overrides.tsv     surface form → root, stem (lemmatiser overrides)
    translation_overrides.tsv
  docs/
  tests/
```

- `aramaic_core` is installed as a git dependency from `Jossifresben/aramaic-root-atlas`. The Atlas's `pyproject.toml` packages the whole app, not the core alone; if that blocks a clean import, the fix is a small packaging change **in the Atlas repo**, never a fork. Found out in rollout step 1.
- The pipeline is rerunnable end-to-end and idempotent per stage: each stage writes a file the next reads. A bad lemmatisation run never touches fetched text.
- One `TABLES_VERSION` string stamps every output and appears in the Scholars tail of every page.

---

## 4. Data model

All tables produced by the pipeline, read-only in the web app (SQLite).

| Table | Columns | Notes |
|---|---|---|
| **passage** | `id` (`1.020a.003` = volume.folio.paragraph; paragraphs of a folio-side run main stream first, then the labelled streams), `volume`, `folio`, `parasha`, `stream`, `stratum`, `text_ar`, `verse_ref`, `token_count` | The unit of everything. `stream` from the Wikisource section label (main, Ra'aya Meheimna, Midrash ha-Ne'lam, ...); stratum = the stream, or for main passages the `strata.tsv` range (Idras). |
| **token** | `passage_id`, `position`, `surface`, `root`, `stem`, `confidence`, `source` (`aramaic_core` / `override`) | Same shape as the Atlas, so exports are compatible. |
| **symbol** | `id`, `label_en`, `label_es`, `label_ar`, `kind` (person / object / quality / event), `node`, `aliases` (surface forms + roots), `gloss_en`, `gloss_es`, `moves_en`, `moves_es`, `seed_source` | The dictionary. Glosses are model-drafted, attributed. |
| **mention** | `symbol_id`, `passage_id`, `position`, `matched_form` | Output of `tag.py`; the join everything derives from. |
| **cooccurrence** | `symbol_a`, `symbol_b`, `passages_together`, `pmi`, `tables_version` | Symmetric, passage as unit. |
| **state** | `symbol_id`, `state_label`, `marker_roots`, `passage_id` | Declared in seed, detected by root co-presence. |
| **translation** | `passage_id`, `lang`, `text`, `model_id`, `prompt_hash`, `created_at` | Provenance one join away. |
| **gloss** | `symbol_id`, `source`, `locus`, `summary_en`, `summary_es` | Tradition entries (Cordovero, Gikatilla). |

**Surfaced passages** (the six shown on a symbol page) are a deterministic query: score = (2·own + 1·top-partner mentions) / (tokens + 20), a smoothed density so short passages cannot win on length alone; passages of at least 12 tokens are taken first and shorter ones only to fill up to six; one per stratum where possible, ties broken by id.

---

## 5. Tagging and computation

**Lemmatisation.** `aramaic_core` first; `zohar_overrides.tsv` wins when it matches. The pipeline emits a report of low-confidence tokens by frequency; the user fixes the top ones, reruns. Confidence is kept per token; the Scholars tail reports the share of text on firm ground.

**Mention tagging.** A mention is any token whose surface or root matches a symbol's aliases. No model disambiguation. Ambiguous forms (ימא Sea → Malkhut or Binah; ארץ Earth → Malkhut or ground) are seeded as two symbols sharing aliases; co-occurrence decides which reading dominates per passage; counts show raw ambiguous total alongside resolved.

**Co-occurrence.** Per passage. `passages_together` (shown to readers) and PMI vs. expected (Scholars table). Home-field clustering: seeded node for the cluster, PMI for placement inside it.

**States.** Declared per symbol as (label, marker roots). A passage is in the state when symbol and any marker root co-occur. Moon: *full* ← fullness/wholeness/Sabbath roots; *diminished* ← ז-ע-ר, מ-ע-ט, exile roots. Unmarked passages are shown as unmarked. No model.

**Strata.** A passage's stream comes from its Wikisource section label (`רע"מ דף …`, `מדרש הנעלם דף …`, …) or, for a plain `דף` label, from the level-2 heading that governs it; editors' inlined appendix text (השמטות) is stream `addendum`. A non-main stream is the stratum; main-stream passages fall back to the `strata.tsv` ranges (Idra Rabba, Idra Zuta, and the unlabelled Shemot Midrash ha-Ne'lam, Tishby). Shown as "where in the book"; Scholars tail notes the ranges are conventional.

**Glosses.** Fable receives counts, top partners, states and tradition entries for a symbol and writes a one-sentence meaning and a short "how it moves" in EN and ES. Prompt forbids symbolism absent from the input. Stored with model id and prompt hash; shown with attribution.

**Seed provenance.** `kinnuyim.tsv` carries `seed_source` per row (Cordovero gate 23 / Gikatilla / Zohar usage / added). Initial seed, by node:

- **Ein Sof / Keter**: Atika Kadisha, Arikh Anpin, Skull, Hidden Brain, Forehead, Beard (13 curls), Supernal Point, Ayin
- **Ḥokhmah**: Abba, Point, Reshit, Primordial Light, Hidden Eden, Seed, Thought
- **Binah**: Imma, River from Eden, Womb, Palace, Fifty Gates, Teshuvah, Upper Sea, Jubilee, Leah, Upper Shekhinah, Heart
- **Ḥesed**: Right, Right Arm, Abraham, Water, White, Silver, Milk, South, Morning, Priest
- **Gevurah**: Left, Left Arm, Isaac, Fire, Red, Gold, Wine, North, Din, Sword, Night
- **Tif'eret**: King, Sun, Jacob/Israel, Written Torah, Tree of Life, Middle Pillar, Body, Heaven, Bridegroom, Voice, Ze'eir Anpin
- **Netzaḥ / Hod**: Two Thighs, Two Pillars, Moses and Aaron, Two Olives, Kidneys
- **Yesod**: Tzaddik, Covenant, Sign, Joseph, Mouth of the River, Shalom, End of the Body, Living God, Pillar of the World
- **Malkhut / Shekhinah**: Matronita, Bride, Knesset Yisra'el, Moon, Sea, Apple Orchard, Rose, Garden, Well, Lamp, Dove, Deer, Earth, Jerusalem, Zion, Temple, Ark, Sabbath, Night, Oral Torah, King David, Rachel, Lower Eden, Daughter, Lower Point, Gate, Field, Cloud of Glory, Mirror that does not shine
- **Sitra Aḥra**: Serpent, Samael, Lilith, Kelipah, Dross of Gold, Esau/Edom, Dog, Dregs of Wine
- **Events**: Zivuga (coupling), Yiḥuda, Nehora, Shefa, Kiss, Embrace, Exile of the Shekhinah, Feminine Waters, Sweetening of Judgement

Four kinds (person / object / quality / event) are a column, used for the home-page filter and chip colour.

---

## 6. Web app

Flask + Jinja, vanilla JS for filter, search and hovers. Server-rendered. Same stack and i18n pattern as the Atlas.

| Route | Page |
|---|---|
| `/` | Home: the field. Clusters per node, chip size = mention count, filters by kind and node, search. |
| `/symbol/<id>` | Symbol page (mockup's Moon page): title → claim → evidence strip → partners / states → six passages (Aramaic + EN/ES, mentions underlined) → tradition → where in the book → Scholars tail. |
| `/sefirah/<id>` | Node page: symbols grouped by kind, partner nodes, pillar. |
| `/tree` | Tree diagram as orientation, each sefirah a link, provenance note. Static SVG. |
| `/passage/<id>` | Whole folio in Aramaic, translation where it exists, mentions underlined, prev/next folio. Reached via "read it" links; not a browse UI. |
| `/ask` | §7. |
| `/scholars` | Method, seed provenance, tables version, exports (CSV / JSON / TEI), citation (BibTeX / Chicago / SBL), DOI. |
| `/about` | What it is, who, the caveat, licences. |
| `/api/...` | JSON for exports and Ask retrieval. |

- Language in the URL (`/es/`), EN default, cookie remembers, never header-detected. UI strings in `strings.{en,es}.json`; content from `_en`/`_es` columns. Hebrew/Aramaic always `dir="rtl"`, `lang="arc"`/`"he"`.
- Look: the mockup ported to one CSS file. Ground `#12131C`, surface `#1B1D2A`, text `#ECE6D8`, muted `#A39E90`, gold `#D9B36A` (Hebrew, emphasis), blue `#7FA7C9` (events), dull red `#C98A7F` (Sitra Aḥra). Cormorant Garamond (display), Source Sans 3 (body), Frank Ruhl Libre (Aramaic). Dark only in v1. Phone: clusters stack, evidence strip below claim, passage columns stack Aramaic first.
- Performance: SQLite reads; home field and node pages cached in memory at startup; ≤1 query per section.
- Not in v1: accounts, bookmarks, annotations, browse-the-book reader, light mode.

---

## 7. Ask

**Retrieval (deterministic).** Question normalised; terms matched against symbol labels and aliases (EN, ES, Aramaic/Hebrew) and node names → symbol set → their glosses, top co-occurrences, states, surfaced passages with translations, tradition glosses. No embeddings in v1; the dictionary is the index. Empty match → empty retrieval.

**Layer 1: strict answer.** Fable gets only the retrieved rows; every sentence tagged with the row it rests on (symbol / passage / gloss id); tags render as links. Empty retrieval → no model call; page says "I can only answer about the Zohar's symbols" and lists three nearest symbol pages by string similarity.

**Layer 2: model reading.** Below a visible divider, "A reading by Fable, from the same passages." Fable gets the same passages (Aramaic + translation), may interpret and connect, may not cite a folio it wasn't given. Different ground colour, attribution line.

**Controls.** Pinned model id in config; prompt versions hashed; cache keyed by (question hash, lang, tables version, prompt hash); per-IP rate limit; monthly spend cap on the key. Questions not stored beyond cache; no accounts.

**Failure modes.** Model error/timeout → Layer 1's retrieved rows as plain links with "the answer couldn't be composed". Ambiguous retrieval (the Sea) → show both readings.

---

## 8. Translation and attribution

- **Scope:** surfaced passages only (six per symbol, deduplicated; expect 400–700), EN and ES. Rest of each folio shows Aramaic with "not yet translated".
- **How:** `translate.py` sends Fable the passage, its folio as context, the symbol rows for every mention, and the verse under comment. Plain, readable, symbol labels consistent with the dictionary, key terms bracketed on first use, no explaining. Cached by (passage id, lang, model id, prompt hash).
- **Spanish** translated directly from the Aramaic, not via English; the EN rendering is supplied afterwards only as a label-consistency check.
- **Attribution line** under every translation and gloss: *Translated by Claude Fable 5.1 (claude-fable-5-1) · report a problem*.
- **Caveat** on About and Scholars, both languages: *We are not scholars. We aim to provide a pleasant experience of the Zohar. Translations and symbol glosses are produced by Anthropic's Claude Fable and have not been reviewed by specialists.*
- **Report a problem:** prefilled GitHub issue (passage id, lang, model id). Fixes go into `translation_overrides.tsv`, which wins on next build.

---

## 9. Licensing, citation, i18n plumbing

- **Code:** MIT. **Text and anything containing it** (sqlite, passage pages, exports with text): CC BY-SA 4.0, attributing Hebrew Wikisource, with revision ids and fetch date in `data/SOURCES.md`. **Tables, seeds, glosses, translations:** CC BY-SA 4.0 too. Tradition glosses cite Cordovero and Gikatilla (PD). Model outputs attributed per §8.
- **Citation:** `CITATION.cff`; Zenodo DOI on first tagged release, covering repo + data; "Cite this" on Scholars and every symbol tail, with `tables_version`; ORCID on author line.
- **Repo hygiene:** bilingual README; `docs/` for the method write-up; `CHANGELOG.md` keyed to tables versions; GitHub Actions run tests and the pipeline fixture build; no auto-deploy — Render deploys from `main` when the user pushes.

---

## 10. Errors, tests, rollout

**Pipeline errors** fail loudly: missing/malformed folio stops `fetch.py` with its id; unplaceable token → `root=NULL, confidence=0`, counted, never dropped; seed row with unknown symbol/root fails `tag.py` before compute. Every stage writes `report.md` (counts in/out, unknowns, top anomalies).

**Web errors** are boring: unknown symbol/passage → 404 with three nearest pages; Ask model failure → retrieved links; missing translation → Aramaic + fallback line. No page depends on the model being up.

**Tests**
- Pipeline: 5–6 fixture folios, hand-counted mentions / co-occurrences / states; determinism (run twice, diff); every `kinnuyim.tsv` row resolves.
- Web: route smoke tests in both languages; every home-field link resolves; Ask contract tests (citations resolve; Layer 2 never cites outside its input).
- Translation: every surfaced passage has both languages or the fallback line.

**Rollout**
1. Pipeline on Bereshit only; prove the chain, tune overrides, settle `aramaic_core` packaging.
2. Full main body; tables v0.1 on Render Starter, unlisted.
3. Translations for the surfaced set; Ask strict only.
4. Ask layer 2; About and Scholars complete; tag v1.0; Zenodo DOI; user decides when public.
v1.1: Zohar Chadash, Tikkunei Zohar.

**Parked, decided later:** product name (domain is zohar.digital); `aramaic_core` packaging (step 1); exact stratum boundaries (transcribe Tishby into `strata.tsv`).
