#!/usr/bin/env bash
set -euo pipefail

# Copy only generated EPUBs and manifest. Keep server paths and credentials in
# environment variables or an ignored local wrapper, never in Git history.
: "${SERVER_SSH:?set SERVER_SSH, e.g. admin@example.invalid}"
: "${REMOTE_IMPORT_DIR:?set REMOTE_IMPORT_DIR}"
: "${REMOTE_IMPORT_SCRIPT:?set REMOTE_IMPORT_SCRIPT}"
: "${LOCAL_IMPORT_DIR:?set LOCAL_IMPORT_DIR}"

scp -r "${LOCAL_IMPORT_DIR}"/. "${SERVER_SSH}:${REMOTE_IMPORT_DIR}/"
ssh "${SERVER_SSH}" node "${REMOTE_IMPORT_SCRIPT}" \
  --input "${REMOTE_IMPORT_DIR}" \
  --manifest "${REMOTE_IMPORT_DIR}/manifest.json"
