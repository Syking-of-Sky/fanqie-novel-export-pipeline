# Release draft (English)

Copy this into a GitHub Release body, or save version-specific notes under `docs/releases/<tag>.md`.

## Title template

`v0.1.0 - Fanqie export/import pipeline`

Recommended first formal public tag: `v0.1.0`.

## Release body

```md
This is the first public release of `fanqie-novel-export-pipeline`.

It turns a field-tested workflow into a reproducible, auditable, rerunnable toolchain: start from a share URL or `book_id`, read the catalog, fetch chapters in batches, resume safely from cache, deduplicate by chapter, write TXT/EPUB, validate the output, and hand `manifest.json` plus EPUBs to an idempotent server-side import step.

## Why this release matters

- It promotes a previously manual, experience-driven flow into a documented end-to-end repository.
- It locks down the fragile parts of the pipeline: resumable caching, deduplication, EPUB validation, and manifest-based import.
- It ships with bilingual README files, architecture notes, troubleshooting guides, and a formal workflow report for reuse or adaptation.

## Included in this release

- Python utilities for export, EPUB writing, EPUB validation, manifest generation, and upload/import examples.
- A Spring Boot + Unidbg local service sample with configuration templates.
- Mermaid flow and sequence diagrams for public repository presentation.
- Bilingual documentation: README, architecture notes, troubleshooting guides, and the formal workflow report.

## Repository boundary

- Includes workflow code, configuration templates, interface contracts, and sanitized examples only.
- Excludes novel content, chapter caches, server databases, cookies, device identifiers, registration keys, SSH details, and APK/SO/rootfs runtime assets.

## Who this is for

- Anyone who wants a reproducible export workflow instead of a one-off script.
- Anyone who needs TXT/EPUB output plus a clean import handoff.
- Anyone separating local signing, chapter retrieval, and server-side import responsibilities.

## Known limitations

- The Java service still requires external Unidbg runtime assets that are intentionally not shipped here.
- Upstream calls may hit `429` or `ILLEGAL_ACCESS`; reuse cache and back off serially.
- Opaque short links must be resolved to a canonical `book_id` outside this repository.

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
