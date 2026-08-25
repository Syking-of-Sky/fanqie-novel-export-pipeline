# Changelog

This project follows a simple Keep a Changelog-style format for workflow and documentation changes.

## [0.1.0] - 2026-08-24

### Added

- Reproducible export pipeline from share URL or numeric `book_id` to TXT/EPUB output.
- Resumable per-chapter cache with range-first batch fetching and `chapterIds` fallback.
- Built-in EPUB writer, EPUB validator, manifest generator, and upload/import shell example.
- Spring Boot + Unidbg local service sample with sanitized configuration templates.
- Bilingual README files, architecture notes, troubleshooting guides, and the formal workflow report.
- Homepage-friendly Mermaid flowchart and sequence diagram for public repository presentation.
- Bilingual release draft templates for GitHub Releases.

### Security

- Sanitized logs, examples, keys, device identifiers, and short-link handling before publication.
- Excluded novels, chapter caches, build artifacts, runtime assets, cookies, and deployment secrets from version control.

## Versioning notes

- Use `vMAJOR.MINOR.PATCH` tags such as `v0.1.0`.
- Increase `PATCH` for documentation-only or non-breaking workflow fixes.
- Increase `MINOR` for new pipeline capabilities or import/export features.
- Increase `MAJOR` only when command contracts or expected deployment behavior change incompatibly.
