# Zohar Symbols · zohar.digital

**[zohar.digital](https://zohar.digital)** &nbsp; [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23305097.svg)](https://doi.org/10.5281/zenodo.23305097)

A computed dictionary of the Zohar's symbols (*kinnuyim*), for curious readers. The Zohar speaks in images: the moon, the river, the bride, gold, the beard. Each image points to a sefirah. Deterministic code reads the Aramaic text of *Sefer ha-Zohar*, finds every image, counts where it appears and what it appears with, and shows you the passages. Bilingual English/Spanish, open access.

**How it works:** [docs/METHOD.md](docs/METHOD.md) covers the method, provenance, how the translations and interpretations are made, and how to cite.

## What the site shows

- **Symbols** — 139 symbols, each with its counts, its partners (co-occurrence and PMI), its states and the passages where it is strongest.
- **Sefirot and the Tree** — the symbols grouped by the sefirah they point to; the Tree diagram is orientation only (a post-Zoharic drawing, Kircher's layout).
- **Read** — the whole main body, 15,909 passages in Mantua pagination, folio by folio. Every passage page has a **Keys** panel: every image in reading order, the sefirah it usually stands for, and the source of that assignment (Cordovero, *Pardes Rimonim* gate 23; Gikatilla, *Sha'arei Orah*; or this project's reading of Zohar usage, labelled as such).
- **Translations** — 678 surfaced passages translated into English and Spanish (1,356 texts) by Claude Fable 5.1, attributed on the page and not reviewed by specialists; every translation has a "report a problem" link.
- **What this passage means** — a short plain-language interpretation under 677 of those translations, by the same model, labelled as inferred: not a traditional commentary, not reviewed by specialists.
- **Scholars** — method, strata, strongest pairs, exports (CSV/JSON API under `/api/`), citation formats.

## Model use and provenance

Every count, correlation and ranking is computed by deterministic code; no model produces a number. The model writes only the translations and the interpretations. Each one is stored with its model id, prompt version, date and a hash of the source passage; a translation whose source text changed is dropped at build time. Hand corrections go in `data/translation_overrides.tsv` and replace the model text. We are not scholars: the aim is a pleasant, honest experience of the Zohar.

## Data

| File | What it is |
|---|---|
| `data/tables.v0.1.0.json` | The computed tables (symbols, counts, pairs, states, strata) |
| `data/tables.v0.1.0.sha256` | Its fingerprint; the deploy fails if a rebuild differs |
| `data/translations.v0.1.0.jsonl` | The model translations, with provenance per row |
| `data/translation_overrides.tsv` | Hand corrections (empty so far) |
| `data/interpretations.v0.1.0.jsonl` | The model interpretations, with provenance per row |
| `data/interpretation_overrides.tsv` | Hand corrections to interpretations |
| `data/report.md` | Build report: corpus, lemmatisation and tagging statistics |
| `data/SOURCES.md` | Pinned Wikisource revisions |
| `seeds/` | Symbol seed (`kinnuyim.tsv`), strata, parashot, lemma overrides |

`data/zohar.sqlite` (~65 MB) is **not** committed; rebuild it with `uv run --no-sync python -m pipeline.run_all`. The method, provenance and model use are written up in [docs/METHOD.md](docs/METHOD.md), generated from the same text as the Scholars page. Changes per release are in [CHANGELOG.md](CHANGELOG.md); deferred work is in [docs/BACKLOG.md](docs/BACKLOG.md).

## Pipeline

```bash
uv run --no-sync python -m pipeline.run_all        # fetch (pinned) → segment → lemmatise → tag → compute → build
uv run --no-sync python -m pipeline.check_tables   # verify the rebuilt tables against the committed sha256
uv run --no-sync python -m pipeline.translate --help   # translation stage (Batch API; needs ANTHROPIC_API_KEY)
```

Lemmatisation uses `aramaic_core` from the [Aramaic Root Atlas](https://github.com/Jossifresben/aramaic-root-atlas) (DOI [10.5281/zenodo.19358625](https://doi.org/10.5281/zenodo.19358625)), pinned to a commit. `pipeline/interpret.py` writes the interpretations (Batch API, or chunk files for Claude Code sub-agents); `pipeline/commentary.py` caches public-domain Sefaria commentary that was tested as background and not used.

## Development setup

```bash
uv venv --python 3.11
uv pip install -e "../aramaic-root-atlas"
uv pip install -e ".[dev]" --no-deps && uv pip install requests pytest
```

Run tests with `uv run --no-sync pytest` (plain `uv run` re-resolves the GitHub Atlas, which lacks the package declaration until it is pushed).

The Atlas is installed editable from the sibling checkout; `pyproject.toml` keeps the GitHub URL for deployment.

## Run locally

Requires `data/zohar.sqlite` (build it with `uv run --no-sync python -m pipeline.run_all`). Optionally point `ZOHAR_DB` at another database file.

```bash
uv run --no-sync flask --app web run --port 5055   # http://localhost:5055
```

## Deploy

`render.yaml` defines a Render web service (Starter). Python is pinned to 3.11.11 (`PYTHON_VERSION`; Render requires a full x.y.z). The build runs `pip install .`, then the pipeline from the pinned Wikisource revisions, then `python -m pipeline.check_tables`, which recomputes the sha256 of the rebuilt `data/tables.v0.1.0.json` and fails the deploy if it differs from the committed `data/tables.v0.1.0.sha256`, so the deployed database is verifiably reproducible; Render health-checks `/healthz`; it starts with `gunicorn web.wsgi:app`. Prerequisites: the build needs network access to he.wikisource.org, and `pyproject.toml` pins the Atlas to a full commit SHA (`6e5f715…`), and that commit must be pushed to GitHub first (otherwise `pip install .` fails). The domain `zohar.digital` is configured in the Render dashboard. `ZOHAR_DB` overrides the database path.

## Cite

Fresco Benaim, Jose. (2026). *Zohar Symbols: a computed dictionary of the Zohar's kinnuyim* (v0.1.1). Zenodo. https://doi.org/10.5281/zenodo.23305097

See also [CITATION.cff](CITATION.cff). The concept DOI always resolves to the latest version.

## Licence

Code: MIT ([LICENSE](LICENSE)). Text, tables and translations: CC BY-SA 4.0, attributing Hebrew Wikisource ([LICENSE-DATA.md](LICENSE-DATA.md)).
