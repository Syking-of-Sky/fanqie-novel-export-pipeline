# Fanqie novel export pipeline (English)

## Overview

This repository turns a verified workflow into a reproducible toolchain: accept a numeric `book_id` or share URL, read the directory from the local Java service, fetch chapters in batches, deduplicate by chapter ID, normalize the text, write TXT/EPUB, validate the EPUB, create a manifest, and run a title-idempotent server import.

The formal release report lives in `docs/2026-08-24_fanqie-export-pipeline-report.md`.

For a homepage-friendly diagram view, use the Mermaid sections in `README.md`. The source files live in `docs/homepage-flow.mmd` and `docs/homepage-sequence.mmd`. For GitHub Releases, start from `docs/release-draft.en.md`.

This is a **workflow repository, not a content mirror**. It intentionally excludes novels, chapter caches, server databases, cookies, device IDs, session UUIDs, registration keys, SSH details, and Unidbg APK/SO/rootfs assets.

## Prerequisites

- Python 3.9+ and `requests`.
- Java 8+ and the Maven Wrapper. The deployer supplies matching Unidbg runtime resources.
- Optional Node.js for the existing server-side `import-with-manifest.js` job.

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install requests
```

## End-to-end flow

1. **Resolve input**: accept a numeric ID or a share URL. Resolve short links outside this repository when necessary.
2. **Read the catalog**: call local `GET /api/fqsearch/directory/{bookId}` and build an ordered `(item_id, title)` list.
3. **Fetch batches**: request up to 30 chapters by ordinal range first; fall back to explicit `chapterIds` if range resolution fails.
4. **Resume safely**: atomically write `cache/app/<book_id>/<item_id>.json`; reruns fetch only missing or invalid chapters.
5. **Normalize and deduplicate**: remove HTML/XHTML noise, entities, footers, and private-use characters; use `item_id` as the uniqueness key and verify titles.
6. **Export**: write metadata-rich TXT and EPUB 3 (one XHTML document per chapter).
7. **Validate**: check ZIP CRC, uncompressed `mimetype`, container metadata, and chapter count; record SHA-256 in `verification.json`.
8. **Import**: create `manifest.json`, place it next to the EPUBs, and invoke the server import job.
9. **Verify final state**: query the server database/bookshelf for title, chapter count, and total count; do not treat a successful copy as final success.

## Commands

```bash
python scripts/export_fanqie_reader.py '<book-id-or-share-url>' \
  --app-api "${FANQIE_APP_API:-http://127.0.0.1:9999}" \
  --output-root outputs --cache-root cache

python scripts/make_manifest.py outputs/<channel>/<title> --channel '<channel>'
python scripts/validate_epub.py outputs/<channel>/<title>/<title>.epub
```

`--workers` remains a compatibility flag; requests are intentionally serialized to reduce rate-limit pressure.

## Java service

```bash
cd service
cp application.example.yml application-local.yml
# Fill local configuration via the ignored file or environment variables.
export SPRING_PROFILES_ACTIVE=dev,local
./mvnw spring-boot:run
```

The safe default binds locally and keeps upstream calls disabled. Supply `FANQIE_API_BASE_URL`, `FANQIE_COOKIE`, device fields, and `FANQIE_REGISTRATION_KEY` only at deployment time. Unidbg `apk/`, `lib/`, `rootfs/`, and `other/` assets are intentionally external.

## Manifest import

```json
{
  "Example title.epub": {
    "title": "Example title",
    "channel": "Example channel"
  }
}
```

The server contract is: keep manifest and EPUBs together; deduplicate by title; remove the staging copy when a title already exists; verify the final database/bookshelf state.

## Troubleshooting

- **429 Too Many Requests**: honor `Retry-After` or exponential backoff, reuse cache, and do not restart a full-book download.
- **ILLEGAL_ACCESS**: check device/session configuration and request rate.
- **Empty response**: verify local service health and runtime assets, then retry only missing batches.
- **EPUB validation failure**: regenerate the EPUB and ensure the transfer path does not rewrite the ZIP.

See `docs/troubleshooting.en.md` for the expanded troubleshooting table.

## Release notes

- Use the Mermaid sections in the root `README.md` for the public repository landing page.
- Reuse `docs/release-draft.en.md` for release text; the Chinese companion lives at `docs/release-draft.zh-CN.md`.

## Security and privacy

Before committing, review `git status --ignored` and scan for identifiers, cookies, bearer values, registration keys, and absolute paths. Keep deployment secrets in a secret manager, environment, or ignored local profile; rotate any value that was accidentally logged.
