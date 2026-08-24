# Architecture (English)

```mermaid
sequenceDiagram
  participant E as Exporter
  participant S as Local Java service
  participant U as Upstream API
  participant C as Local cache
  participant I as Server import job

  E->>S: GET directory(bookId)
  S->>U: Signed catalog request
  U-->>S: catalog(item_id,title)
  S-->>E: Local catalog response
  E->>C: Read completed chapters
  E->>S: POST batch(range)
  S->>U: Signed/decrypted batch request
  U-->>S: rawContent
  S-->>E: chapters
  E->>C: Atomically write item_id.json
  E->>E: Normalize, verify titles, deduplicate
  E->>E: TXT/EPUB + CRC/mimetype validation
  E->>I: EPUB + manifest
  I-->>E: Final title/chapter state
```

The Java service owns the local API and decryption boundary. The exporter owns resumable state, deduplication, and file validation. The server import job owns final title-idempotent state. Runtime binaries and deployment secrets remain outside Git.
