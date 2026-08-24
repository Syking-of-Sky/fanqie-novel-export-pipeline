# Troubleshooting (English)

| Symptom | Response |
| --- | --- |
| `429 Too Many Requests` | Wait for backoff, reuse cache, and reduce batch frequency; do not rerun the whole book in parallel. |
| `ILLEGAL_ACCESS` | Check session/device deployment data and request pacing; do not write error JSON into the chapter cache. |
| `empty response` | Verify the local service, runtime assets, and upstream state; retry only the missing batch. |
| Title mismatch | Treat the catalog title as authoritative; delete the suspect batch and fetch it again. |
| EPUB CRC/mimetype error | Regenerate the EPUB and confirm the transfer path did not rewrite the ZIP. |
| Duplicate import on server | Query final bookshelf/database state by title; remove the staging copy and keep `manifest.json` next to the EPUB. |
