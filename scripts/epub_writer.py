#!/usr/bin/env python3
"""Small, dependency-free EPUB 3 writer used by the export pipeline."""

from __future__ import annotations

import html
import re
import uuid
import zipfile
from pathlib import Path
from typing import Iterable, Mapping


def _xml(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def _xhtml(value: str) -> str:
    # Chapter text has already been normalized to plain text. Escape it before
    # inserting line breaks so a malformed upstream tag cannot become markup.
    return "<p>" + "</p><p>".join(_xml(value).split("\n\n")) + "</p>"


def write_epub(
    output: Path,
    title: str,
    author: str,
    chapters: Iterable[Mapping[str, object]],
    book_id: str,
    cover_bytes: bytes | None = None,
    cover_media_type: str | None = None,
    cover_name: str | None = None,
) -> Path:
    """Write a deterministic EPUB with one XHTML document per chapter."""
    chapter_rows = list(chapters)
    output.parent.mkdir(parents=True, exist_ok=True)
    identifier = f"urn:fanqie:{book_id}"
    modified = "2000-01-01T00:00:00Z"
    files: dict[str, bytes] = {}
    manifest: list[str] = []
    spine: list[str] = []
    cover_meta = ""

    if cover_bytes and cover_media_type and cover_name:
        cover_href = f"images/{cover_name}"
        files[cover_href] = cover_bytes
        files["cover.xhtml"] = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="zh-CN">
<head><meta charset="utf-8"/><title>{_xml(title)}</title></head>
<body><section epub:type="cover"><img src="{_xml(cover_href)}" alt="{_xml(title)} cover" style="max-width:100%;height:auto;"/></section></body>
</html>
""".encode("utf-8")
        manifest.append(
            f'<item id="cover-image" href="{cover_href}" media-type="{cover_media_type}" properties="cover-image"/>'
        )
        manifest.append('<item id="cover" href="cover.xhtml" media-type="application/xhtml+xml"/>')
        spine.append('<itemref idref="cover"/>')
        cover_meta = '\n    <meta name="cover" content="cover-image"/>'

    for index, chapter in enumerate(chapter_rows, 1):
        item_id = f"chapter-{index:05d}"
        href = f"text/{item_id}.xhtml"
        chapter_title = str(chapter.get("title") or f"Chapter {index}")
        content = str(chapter.get("content") or "")
        files[href] = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" lang="zh-CN">
<head><meta charset="utf-8"/><title>{_xml(chapter_title)}</title></head>
<body><h1>{_xml(chapter_title)}</h1>{_xhtml(content)}</body>
</html>
""".encode("utf-8")
        manifest.append(f'<item id="{item_id}" href="{href}" media-type="application/xhtml+xml"/>')
        spine.append(f'<itemref idref="{item_id}"/>')

    files["package.opf"] = f"""<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="book-id">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="book-id">{_xml(identifier)}</dc:identifier>
    <dc:title>{_xml(title)}</dc:title>
    <dc:creator>{_xml(author)}</dc:creator>
    <dc:language>zh-CN</dc:language>
    <meta property="dcterms:modified">{modified}</meta>{cover_meta}
  </metadata>
  <manifest>
    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
    {''.join(manifest)}
  </manifest>
  <spine>
    {''.join(spine)}
  </spine>
</package>
""".encode("utf-8")

    nav_items = "".join(
        f'<li><a href="text/chapter-{index:05d}.xhtml">{_xml(str(chapter.get("title") or f"Chapter {index}"))}</a></li>'
        for index, chapter in enumerate(chapter_rows, 1)
    )
    files["nav.xhtml"] = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="zh-CN">
<head><meta charset="utf-8"/><title>{_xml(title)}</title></head>
<body><nav epub:type="toc" id="toc"><h1>{_xml(title)}</h1><ol>{nav_items}</ol></nav></body>
</html>
""".encode("utf-8")
    files["META-INF/container.xml"] = b'''<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles><rootfile full-path="package.opf" media-type="application/oebps-package+xml"/></rootfiles>
</container>
'''

    with zipfile.ZipFile(output, "w") as archive:
        # EPUB readers require mimetype to be the first, uncompressed member.
        archive.writestr("mimetype", b"application/epub+zip", compress_type=zipfile.ZIP_STORED)
        for name in sorted(files):
            archive.writestr(name, files[name], compress_type=zipfile.ZIP_DEFLATED)
    return output
