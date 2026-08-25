# Release draft (English)

Copy this into a GitHub Release body, or save version-specific notes under `docs/releases/<tag>.md`.

## Title template

`v0.1.0 - Fanqie export/import pipeline`

## Release body template

```md
## Included in this release

- A reproducible `share URL / book_id -> catalog -> batch chapters -> resumable cache -> dedup -> TXT/EPUB -> validation -> manifest -> idempotent server import` workflow.
- Python utilities for export, EPUB writing, EPUB validation, manifest generation, and upload/import examples.
- A Spring Boot + Unidbg local service sample with configuration templates.
- Bilingual READMEs, architecture notes, troubleshooting guides, and the formal workflow report.

## Repository boundary

- Includes workflow code, configuration templates, interface contracts, and sanitized examples only.
- Excludes novel content, chapter caches, server databases, cookies, device identifiers, registration keys, SSH details, and APK/SO/rootfs runtime assets.

## Quick start

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install requests

python scripts/export_fanqie_reader.py '<book-id-or-share-url>' \
  --app-api http://127.0.0.1:9999 \
  --output-root outputs --cache-root cache

python scripts/make_manifest.py outputs/<channel>/<title> --channel '<channel>'
python scripts/validate_epub.py outputs/<channel>/<title>/<title>.epub
```

## Validation coverage

- Python scripts pass `python3 -m py_compile scripts/*.py service/tools/*.py`
- EPUB fixture validation passes
- Manifest fixture generation passes
- Numeric-ID and opaque-shortlink edge cases are documented

## Known limitations

- The Java service still requires external Unidbg runtime assets that are intentionally not shipped here.
- Upstream calls may hit `429` or `ILLEGAL_ACCESS`; reuse cache and back off serially.
- Opaque short links must be resolved to a canonical `book_id` outside this repository.

## Release checklist

- [ ] `git status --ignored` shows only expected ignored directories
- [ ] No `outputs/`, `cache/`, `results/`, or `service/target/` artifacts are tracked
- [ ] No real cookies, device identifiers, registration keys, or absolute paths are present
- [ ] README / bilingual docs / report links render correctly
- [ ] Key commands reproduce from a clean environment
```
