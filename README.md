# zohar-symbols

**EN.** A computed dictionary of the Zohar's symbols. An offline pipeline reads the Aramaic text of *Sefer ha-Zohar*, extracts roots and symbol co-occurrences with deterministic code, and publishes the tables for scholars to inspect and cite.

**ES.** Un diccionario computado de los símbolos del Zohar. Un pipeline offline lee el texto arameo del *Sefer ha-Zohar*, extrae raíces y co-ocurrencias de símbolos con código determinista, y publica las tablas para que los investigadores las consulten y citen.

Spec: [docs/superpowers/specs/](docs/superpowers/specs/2026-10-11-zohar-symbols-design.md)

Status: pipeline in development

## Development setup

```bash
uv venv --python 3.11
uv pip install -e "../aramaic-root-atlas"
uv pip install -e ".[dev]" --no-deps && uv pip install requests pytest
```

Run tests with `uv run --no-sync pytest` (plain `uv run` re-resolves the GitHub Atlas, which lacks the package declaration until it is pushed).

The Atlas is installed editable from the sibling checkout; `pyproject.toml` keeps the GitHub URL for deployment.
