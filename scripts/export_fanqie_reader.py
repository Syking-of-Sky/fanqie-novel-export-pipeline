#!/usr/bin/env python3
"""Export a Fanqie book through the local reader service.

The exporter intentionally keeps runtime state outside the repository: chapter
cache and generated books are resumable, but are ignored by Git.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import time
import zipfile
from pathlib import Path
from urllib.parse import urlparse

import requests

from epub_writer import write_epub

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_ROOT = ROOT / "outputs"
DEFAULT_CACHE_ROOT = ROOT / "cache"
DEFAULT_USER_AGENT = "Mozilla/5.0 (compatible; FanqieExportPipeline/1.0)"
MIN_COVER_BYTES = 1024
JPEG_SIGNATURE = b"\xff\xd8\xff"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_name(value: str) -> str:
    return re.sub(r'[\\/:*?"<>|]', "_", value).strip() or "unnamed"


def normalize_title(value: str) -> str:
    return re.sub(r"[\s\u3000]+", "", html.unescape(value or "")).lower()


def extract_book_id(value: str) -> str:
    """Accept a numeric ID or a share URL that already contains a numeric ID.

    Opaque ``changdunovel.com/t/<token>`` links are deliberately not resolved
    here: resolve them outside this repository, then pass the resulting numeric
    book ID to keep the exporter deterministic and credential-free.
    """
    candidate = value.strip()
    if candidate.isdigit():
        return candidate
    path = urlparse(candidate).path.rstrip("/")
    match = re.search(r"/(?:t|page)/([0-9]+)$", path)
    if match:
        return match.group(1)
    match = re.search(r"(?:book[_-]?id|bookId)[=/]([0-9]+)", candidate, re.I)
    if match:
        return match.group(1)
    if re.search(r"changdunovel\.com/t/[^/?#]+", candidate, re.I):
        raise ValueError(
            "short share token requires external resolution to a numeric book_id"
        )
    raise ValueError("input must be a numeric book_id or a URL containing one")


def extract_state(document: str) -> dict:
    marker = "window.__INITIAL_STATE__="
    start = document.find(marker)
    if start < 0:
        raise RuntimeError("initial state marker not found")
    start += len(marker)
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(document)):
        char = document[index]
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                raw = document[start : index + 1]
                return json.loads(raw.replace(":undefined", ":null").replace(",undefined", ",null"))
    raise RuntimeError("initial state JSON is incomplete")


def clean_content(value: str) -> str:
    value = re.sub(r"<header>.*?</header>", "", value, flags=re.DOTALL | re.IGNORECASE)
    value = re.sub(r"<footer>.*?</footer>", "", value, flags=re.DOTALL | re.IGNORECASE)
    value = re.sub(r"<br\s*/?>", "\n", value, flags=re.IGNORECASE)
    value = re.sub(r"<p(?:\s[^>]*)?>", "\n", value, flags=re.IGNORECASE)
    value = re.sub(r"</p>", "\n", value, flags=re.IGNORECASE)
    value = re.sub(r"<[^>]+>", "", value)
    value = html.unescape(value).replace("\r\n", "\n").replace("\r", "\n")
    value = re.sub(r"【感谢.*?送出的礼物！】\s*$", "", value, flags=re.DOTALL)
    value = "".join(char for char in value if not (0xE000 <= ord(char) <= 0xF8FF))
    value = value.replace("\ufffd", "")
    value = "\n".join(line.strip() for line in value.splitlines())
    return re.sub(r"\n{3,}", "\n\n", value).strip()


def request_text(url: str, user_agent: str, attempts: int = 5) -> str:
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            response = requests.get(url, headers={"User-Agent": user_agent}, timeout=25)
            response.raise_for_status()
            if response.text:
                return response.text
            last_error = RuntimeError("empty response")
        except Exception as exc:  # retry transient 429/5xx and network errors
            last_error = exc
        if attempt + 1 < attempts:
            time.sleep(1.0 + attempt * 1.5)
    raise RuntimeError(f"request failed: {url}: {last_error}")


def _pick_cover_url(*candidates: object) -> str:
    for candidate in candidates:
        if not isinstance(candidate, str):
            continue
        value = candidate.strip()
        if value.startswith(("http://", "https://")):
            return value
    return ""


def _detect_cover_type(payload: bytes, content_type: str | None, source_url: str) -> tuple[str, str]:
    del content_type, source_url  # payload signature is authoritative here.
    if payload.startswith(JPEG_SIGNATURE):
        return "image/jpeg", "cover.jpg"
    if payload.startswith(PNG_SIGNATURE):
        return "image/png", "cover.png"
    raise RuntimeError("official cover is not a supported JPEG/PNG image")


def fetch_cover(url: str, user_agent: str, attempts: int = 5) -> tuple[bytes, str, str]:
    last_error: Exception | None = None
    for attempt in range(attempts):
        response: requests.Response | None = None
        try:
            response = requests.get(url, headers={"User-Agent": user_agent}, timeout=25)
            if response.status_code == 429:
                raise RuntimeError("cover request hit 429 Too Many Requests")
            response.raise_for_status()
            payload = response.content
            if len(payload) < MIN_COVER_BYTES:
                raise RuntimeError(f"cover payload too small: {len(payload)} bytes")
            media_type, cover_name = _detect_cover_type(payload, response.headers.get("Content-Type"), url)
            return payload, media_type, cover_name
        except Exception as exc:
            last_error = exc
        finally:
            if response is not None:
                response.close()
        if attempt + 1 < attempts:
            time.sleep(1.0 + attempt * 1.5)
    raise RuntimeError(f"cover request failed: {url}: {last_error}")


def parse_book(book_id: str, app_api_base: str, user_agent: str) -> tuple[dict, list[tuple[str, str]]]:
    response = requests.get(f"{app_api_base}/api/fqsearch/directory/{book_id}", timeout=60)
    response.raise_for_status()
    payload = response.json()
    if payload.get("code") != 0:
        raise RuntimeError(f"directory API error: {payload.get('message')}")
    data = payload.get("data") or {}
    app_info = data.get("book_info") or {}
    rows = data.get("item_data_list") or []
    entries: list[tuple[str, str]] = []
    seen: set[str] = set()
    for row in rows:
        item_id = str(row.get("item_id") or "")
        title = html.unescape(row.get("title") or "").strip()
        if not item_id or not title or item_id in seen:
            continue
        seen.add(item_id)
        entries.append((item_id, title))
    if not entries:
        raise RuntimeError("App directory is empty")

    document = request_text(f"https://fanqienovel.com/page/{book_id}", user_agent)
    page = extract_state(document).get("page", {})
    try:
        categories = json.loads(page.get("categoryV2") or "[]")
    except json.JSONDecodeError:
        categories = []
    main_category = next((item.get("Name") for item in categories if item.get("MainCategory")), "uncategorized")
    tags = [item.get("Name") for item in categories if item.get("Name") and not item.get("MainCategory")]
    metadata = {
        "book_id": book_id,
        "title": app_info.get("book_name") or app_info.get("bookName") or page.get("bookName") or f"book-{book_id}",
        "author": app_info.get("author") or page.get("authorName") or page.get("author") or "unknown",
        "category": main_category,
        "tags": tags,
        "word_number": int(app_info.get("wordNumber") or page.get("wordNumber") or 0),
        "chapter_total": len(entries),
        "creation_status": str(page.get("creationStatus") or ""),
        "last_chapter_title": entries[-1][1],
        "abstract": app_info.get("description") or page.get("abstract") or "",
        "cover_url": _pick_cover_url(
            app_info.get("coverUrl"),
            app_info.get("cover_url"),
            app_info.get("thumbUrl"),
            app_info.get("thumb_url"),
            page.get("coverUrl"),
            page.get("cover_url"),
            page.get("thumbUrl"),
            page.get("thumb_url"),
        ),
        "source": f"https://fanqienovel.com/page/{book_id}",
    }
    return metadata, entries


def _batch_response(response: requests.Response) -> dict:
    response.raise_for_status()
    payload = response.json()
    if payload.get("code") != 0:
        raise RuntimeError(f"batch API error: {payload.get('message') or 'unknown error'}")
    return (payload.get("data") or {}).get("chapters") or {}


def fetch_batch_by_range(app_api_base: str, book_id: str, start_index: int, end_index: int) -> dict:
    response = requests.post(
        f"{app_api_base}/api/fqnovel/chapters/batch",
        json={"bookId": book_id, "chapterRange": f"{start_index}-{end_index}"},
        timeout=120,
    )
    return _batch_response(response)


def fetch_batch_by_ids(app_api_base: str, book_id: str, chapter_ids: list[str]) -> dict:
    response = requests.post(
        f"{app_api_base}/api/fqnovel/chapters/batch",
        json={"bookId": book_id, "chapterIds": chapter_ids},
        timeout=120,
    )
    return _batch_response(response)


def validate_epub(epub_path: Path, chapter_count: int) -> None:
    with zipfile.ZipFile(epub_path) as archive:
        bad_member = archive.testzip()
        if bad_member:
            raise RuntimeError(f"EPUB CRC failure: {bad_member}")
        if archive.read("mimetype") != b"application/epub+zip":
            raise RuntimeError("EPUB mimetype is invalid")
        actual = sum(name.startswith("text/chapter-") and name.endswith(".xhtml") for name in archive.namelist())
        if actual != chapter_count:
            raise RuntimeError(f"EPUB chapter count mismatch: {actual} != {chapter_count}")


def export_book(
    book_id: str,
    requested_alias: str,
    workers: int,
    app_api_base: str,
    output_root: Path,
    cache_root: Path,
    user_agent: str,
    skip_cover: bool,
) -> dict:
    del workers  # retained for CLI compatibility; requests are intentionally serialized.
    metadata, entries = parse_book(book_id, app_api_base, user_agent)
    cache = cache_root / "app" / book_id
    cache.mkdir(parents=True, exist_ok=True)
    expected_by_id = dict(entries)
    chapter_map: dict[str, dict] = {}
    for start in range(0, len(entries), 30):
        group = entries[start : start + 30]
        uncached = []
        for item_id, _ in group:
            target = cache / f"{item_id}.json"
            try:
                record = json.loads(target.read_text(encoding="utf-8"))
                if record.get("id") == item_id and len(record.get("content") or "") >= 50:
                    chapter_map[item_id] = record
                    continue
            except (OSError, json.JSONDecodeError):
                pass
            uncached.append(item_id)
        if uncached:
            start_index = start + 1
            end_index = start + len(group)
            try:
                returned = fetch_batch_by_range(app_api_base, book_id, start_index, end_index)
                returned_by_id = {item_id: returned.get(str(index)) or {} for index, (item_id, _) in enumerate(group, start_index)}
            except RuntimeError:
                returned_by_id = fetch_batch_by_ids(app_api_base, book_id, uncached)
            for item_id, _ in group:
                entry = returned_by_id.get(item_id) or {}
                title = html.unescape(entry.get("chapterName") or "").strip()
                content = clean_content(entry.get("rawContent") or "")
                problems = []
                if normalize_title(title) != normalize_title(expected_by_id[item_id]):
                    problems.append(f"title mismatch: {title!r} != {expected_by_id[item_id]!r}")
                if len(content) < 50:
                    problems.append(f"content too short: {len(content)}")
                if problems:
                    raise RuntimeError(f"chapter {item_id}: {'; '.join(problems)}")
                record = {"id": item_id, "title": expected_by_id[item_id], "content": content}
                target = cache / f"{item_id}.json"
                temporary = target.with_suffix(".json.tmp")
                temporary.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
                temporary.replace(target)
                chapter_map[item_id] = record
        print(f"downloaded {min(start + len(group), len(entries))}/{len(entries)}", flush=True)
        if start + len(group) < len(entries):
            time.sleep(0.5)

    chapters = [{"index": index, **chapter_map[item_id]} for index, (item_id, _) in enumerate(entries, 1) if item_id in chapter_map]
    if len(chapters) != len(entries) or len({chapter["id"] for chapter in chapters}) != len(entries):
        raise RuntimeError("chapter deduplication validation failed")

    folder = output_root / safe_name(metadata["category"]) / safe_name(metadata["title"])
    folder.mkdir(parents=True, exist_ok=True)
    txt_path = folder / f"{safe_name(metadata['title'])}.txt"
    epub_path = folder / f"{safe_name(metadata['title'])}.epub"
    verification_path = folder / "verification.json"
    cover_url = str(metadata.get("cover_url") or "")
    cover_path: Path | None = None
    cover_bytes: bytes | None = None
    cover_media_type: str | None = None
    cover_name: str | None = None

    if not skip_cover:
        if not cover_url:
            raise RuntimeError("official cover URL not found; rerun with --skip-cover to export without cover")
        cover_bytes, cover_media_type, cover_name = fetch_cover(cover_url, user_agent)
        cover_path = folder / cover_name
        cover_path.write_bytes(cover_bytes)

    with txt_path.open("w", encoding="utf-8", newline="\n") as output:
        output.write(f"《{metadata['title']}》\n")
        if requested_alias and normalize_title(requested_alias) != normalize_title(metadata["title"]):
            output.write(f"分享名：《{requested_alias}》\n")
        output.write(
            f"作者：{metadata['author']}\n官方分类：{metadata['category']}\n"
            f"官方标签：{'、'.join(metadata['tags'])}\n官方封面：{cover_url or '未获取'}\n书籍 ID：{book_id}\n\n"
        )
        for chapter in chapters:
            output.write(f"{chapter['title']}\n\n{chapter['content']}\n\n")

    write_epub(
        epub_path,
        metadata["title"],
        metadata["author"],
        chapters,
        book_id,
        cover_bytes=cover_bytes,
        cover_media_type=cover_media_type,
        cover_name=cover_name,
    )
    validate_epub(epub_path, len(chapters))
    report = {
        **metadata,
        "requested_alias": requested_alias,
        "catalog_count": len(entries),
        "exported_count": len(chapters),
        "unique_chapter_ids": len({chapter["id"] for chapter in chapters}),
        "content_chars": sum(len(chapter["content"]) for chapter in chapters),
        "errors": [],
        "cover": {
            "skipped": skip_cover,
            "url": cover_url,
            "path": str(cover_path) if cover_path else "",
            "bytes": cover_path.stat().st_size if cover_path else 0,
            "sha256": sha256(cover_path) if cover_path else "",
            "media_type": cover_media_type or "",
        },
        "txt": {"path": str(txt_path), "bytes": txt_path.stat().st_size, "sha256": sha256(txt_path)},
        "epub": {"path": str(epub_path), "bytes": epub_path.stat().st_size, "sha256": sha256(epub_path)},
    }
    verification_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("book", help="numeric book ID or share URL")
    parser.add_argument("--alias", default="")
    parser.add_argument("--workers", type=int, default=1, help="compatibility option; requests remain serialized")
    parser.add_argument("--app-api", default=os.getenv("FANQIE_APP_API", "http://127.0.0.1:9999"))
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--cache-root", type=Path, default=DEFAULT_CACHE_ROOT)
    parser.add_argument("--user-agent", default=os.getenv("FANQIE_PUBLIC_USER_AGENT", DEFAULT_USER_AGENT))
    parser.add_argument("--skip-cover", action="store_true", help="export without fetching the official cover")
    args = parser.parse_args()
    export_book(
        extract_book_id(args.book), args.alias, max(1, min(args.workers, 8)), args.app_api.rstrip("/"),
        args.output_root, args.cache_root, args.user_agent, args.skip_cover,
    )


if __name__ == "__main__":
    main()
