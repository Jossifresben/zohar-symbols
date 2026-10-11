# zohar-symbols

**EN.** A computed dictionary of the Zohar's symbols. An offline pipeline reads the Aramaic text of *Sefer ha-Zohar*, extracts roots and symbol co-occurrences with deterministic code, and publishes the tables for scholars to inspect and cite.

**ES.** Un diccionario computado de los símbolos del Zohar. Un pipeline offline lee el texto arameo del *Sefer ha-Zohar*, extrae raíces y co-ocurrencias de símbolos con código determinista, y publica las tablas para que los investigadores las consulten y citen.

Spec: [docs/superpowers/specs/](docs/superpowers/specs/2026-10-11-zohar-symbols-design.md)

Status: pipeline in development

## Data

`data/tables.v*.json`, `data/report.md` and `data/SOURCES.md` are committed. `data/zohar.sqlite` is **not** (the full-Zohar database is ~65 MB; kept out of git to avoid churn in a binary file); regenerate it with `uv run --no-sync python -m pipeline.run_all`.

## Development setup

```bash
uv venv --python 3.11
uv pip install -e "../aramaic-root-atlas"
uv pip install -e ".[dev]" --no-deps && uv pip install requests pytest
```

Run tests with `uv run --no-sync pytest` (plain `uv run` re-resolves the GitHub Atlas, which lacks the package declaration until it is pushed).

The Atlas is installed editable from the sibling checkout; `pyproject.toml` keeps the GitHub URL for deployment.

## Run locally / Ejecutar en local

**EN.** Requires `data/zohar.sqlite` (build it with `uv run --no-sync python -m pipeline.run_all`). Optionally point `ZOHAR_DB` at another database file.

**ES.** Requiere `data/zohar.sqlite` (se construye con `uv run --no-sync python -m pipeline.run_all`). Opcionalmente, `ZOHAR_DB` apunta a otro archivo de base de datos.

```bash
uv run --no-sync flask --app web run --port 5055   # http://localhost:5055
```

## Deploy / Despliegue

**EN.** `render.yaml` defines a Render web service (Starter). The build runs `pip install .` and then the pipeline from the pinned Wikisource revisions, so the deployed database is reproducible; it starts with `gunicorn web.wsgi:app`. Prerequisites: the build needs network access to he.wikisource.org, and the Atlas repository on GitHub must contain the commit that declares `aramaic_core` as a package (push it first, otherwise `pip install .` fails). The domain `zohar.digital` is configured in the Render dashboard. `ZOHAR_DB` overrides the database path.

**ES.** `render.yaml` define un servicio web en Render (Starter). El build ejecuta `pip install .` y luego el pipeline con las revisiones fijadas de Wikisource, de modo que la base desplegada es reproducible; arranca con `gunicorn web.wsgi:app`. Requisitos: el build necesita acceso de red a he.wikisource.org, y el repositorio del Atlas en GitHub debe contener el commit que declara `aramaic_core` como paquete (súbelo antes, o `pip install .` falla). El dominio `zohar.digital` se configura en el panel de Render. `ZOHAR_DB` cambia la ruta de la base de datos.
