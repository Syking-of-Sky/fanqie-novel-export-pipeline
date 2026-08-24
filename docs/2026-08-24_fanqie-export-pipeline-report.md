# Fanqie export/import pipeline report · 番茄导出/导入流程报告

## Summary | 摘要

This repository packages a reproducible pipeline for: resolving a numeric `book_id`, reading the catalog from a local Java service, fetching chapters in serialized batches, deduplicating by chapter `item_id`, exporting TXT/EPUB, validating the EPUB, generating a manifest, and performing a title-idempotent server import.

本仓库将一条已验证流程整理为可复现工具链：解析数值 `book_id`，通过本地 Java 服务读取目录，串行批量获取章节，按章节 `item_id` 去重，导出 TXT/EPUB，校验 EPUB，生成 manifest，并执行按标题幂等的服务器导入。

The repository intentionally excludes chapter content, resumable caches, cookies, device identifiers, registration keys, runtime APK/SO/rootfs assets, server database files, and remote deployment paths.

仓库明确排除正文内容、断点缓存、Cookie、设备标识、注册密钥、APK/SO/rootfs 运行时资源、服务器数据库文件与远程部署路径。

## Scope boundary | 发布边界

- Keep only workflow code, interface contracts, config templates, and redacted examples.
- Do not commit generated novels, `outputs/`, `cache/`, `results/`, `service/target/`, or runtime binaries.
- Inject real upstream URL, cookies, device fields, and registration key only via environment variables or ignored local config.
- Treat the final bookshelf/database state as the authoritative success signal.

- 仅保留流程代码、接口契约、配置模板和脱敏示例。
- 不提交生成的小说文件、`outputs/`、`cache/`、`results/`、`service/target/` 或运行时二进制。
- 真实上游 URL、Cookie、设备字段和注册密钥只能通过环境变量或已忽略本地配置注入。
- 以最终书架/数据库状态作为导入成功的权威证据。

## End-to-end workflow | 端到端流程

1. Resolve a numeric `book_id`. Opaque `changdunovel.com/t/<token>` links stay out of scope until an external resolver returns the numeric ID.
2. Read the ordered `(item_id, title)` catalog from `GET /api/fqsearch/directory/{bookId}`.
3. Fetch chapters in batches of at most 30. Try `chapterRange` first; on mapping failure, retry the same batch with explicit `chapterIds`.
4. Atomically cache each successful chapter as `cache/app/<book_id>/<item_id>.json` to support resume without re-downloading complete books.
5. Normalize XHTML/text, verify chapter titles against the catalog, and deduplicate by `item_id`.
6. Write TXT and EPUB 3 outputs.
7. Validate ZIP CRC, uncompressed `mimetype`, container metadata, chapter count, and file hash; record results in `verification.json`.
8. Generate `manifest.json`, upload only EPUB + manifest to the server staging directory, and run the existing import job.
9. Verify the final bookshelf/database title and chapter count instead of trusting upload logs alone.

1. 先解析数值 `book_id`。`changdunovel.com/t/<token>` 这类 opaque 短链必须由仓库外解析器转换成数值 ID。
2. 通过 `GET /api/fqsearch/directory/{bookId}` 获取有序 `(item_id, title)` 目录。
3. 每批最多请求 30 章，优先使用 `chapterRange`；映射失败时对同批章节改用显式 `chapterIds`。
4. 每个成功章节原子写入 `cache/app/<book_id>/<item_id>.json`，支持断点续传，避免整本重抓。
5. 清理 XHTML/正文，按目录校验标题，并以 `item_id` 去重。
6. 输出 TXT 与 EPUB 3。
7. 校验 ZIP CRC、未压缩 `mimetype`、容器元数据、章节数与文件哈希，并写入 `verification.json`。
8. 生成 `manifest.json`，只上传 EPUB 与 manifest 到服务器暂存目录，再调用现有导入任务。
9. 最终以书架/数据库中的标题与章节数核验结果，而不是只看上传日志。

## Flowchart | 流程图

Synced with `docs/import-flow.mmd`.

```mermaid
flowchart LR
  share[Share URL or book ID] --> catalog[Local directory API]
  catalog --> cache[Resumable cache]
  cache --> batch[Batch chapters: range first]
  batch --> fallback{Range works?}
  fallback -- no --> ids[Explicit chapterIds fallback]
  fallback -- yes --> clean[Normalize HTML/XHTML]
  ids --> clean
  clean --> dedup[Deduplicate by chapter ID + title check]
  dedup --> export[TXT + EPUB]
  export --> validate[ZIP CRC/mimetype/chapter count]
  validate --> manifest[manifest.json]
  manifest --> import[Server import job]
  import --> verify[Verify final title/chapter state]
```

## Replay commands | 复现命令

### 1. Python syntax checks

```bash
cd github-export-20260824
python3 -m py_compile scripts/*.py service/tools/*.py
```

### 2. EPUB fixture generation and validation

```bash
cd github-export-20260824
python3 - <<'PY'
from pathlib import Path
import sys
sys.path.insert(0, "scripts")
from epub_writer import write_epub

write_epub(
    Path("/tmp/fixture.epub"),
    "Fixture Book",
    "Fixture Author",
    [
        {"title": "Chapter 1", "content": "A" * 80},
        {"title": "Chapter 2", "content": "B" * 80},
    ],
    "fixture-book-id",
)
PY
python3 scripts/validate_epub.py /tmp/fixture.epub
```

### 3. Manifest fixture

```bash
mkdir -p /tmp/manifest-fixture
cp /tmp/fixture.epub "/tmp/manifest-fixture/Fixture Book.epub"
python3 scripts/make_manifest.py /tmp/manifest-fixture --channel fixture
cat /tmp/manifest-fixture/manifest.json
```

### 4. Short-link boundary

```bash
cd github-export-20260824
python3 - <<'PY'
import sys
sys.path.insert(0, "scripts")
from export_fanqie_reader import extract_book_id

assert extract_book_id("1234567890123456789") == "1234567890123456789"

try:
    extract_book_id("https://changdunovel.com/t/fixture-token")
except ValueError as exc:
    assert "external resolution" in str(exc)
else:
    raise AssertionError("opaque token should not be accepted")
PY
```

### 5. Optional Java packaging attempt

```bash
cd github-export-20260824/service
chmod +x mvnw
JAVA_HOME=/opt/homebrew/Cellar/openjdk/26.0.2.1/libexec/openjdk.jdk/Contents/Home \
  mvn -q -DskipTests package
```

## Operational evidence | 关键证据

- The exporter keeps cache entries one chapter per file and resumes from missing chapters only.
- Batch requests cap at 30 chapters and reuse the same chapter set during range-to-ID fallback.
- EPUB validation verifies file structure instead of assuming any ZIP is acceptable.
- The upload helper copies only EPUBs and `manifest.json`; remote hostnames and import paths stay in environment variables.
- The Java service defaults to local binding and disabled upstream calls.

- 导出器以“每章一个缓存文件”的方式保存状态，只补缺失章节。
- 批量请求上限为 30 章，范围失败时对同一章节集合做 ID fallback。
- EPUB 校验显式检查文件结构，而不是把任意 ZIP 当作有效结果。
- 上传脚本只传 EPUB 和 `manifest.json`；远程主机与导入路径保留在环境变量中。
- Java 服务默认只监听本机，且上游调用默认关闭。

## Validation status | 当前校验状态

- `python3 -m py_compile scripts/*.py service/tools/*.py` passes.
- The EPUB fixture validates successfully, including chapter count and ZIP structure checks.
- The manifest fixture is generated successfully from the validated EPUB.
- The current Java snapshot does not package cleanly with `mvn -q -DskipTests package`; the observed compile failures are pre-existing in `IdleFQ` and `FQNovelService` and should be fixed separately from this publication step.

- `python3 -m py_compile scripts/*.py service/tools/*.py` 已通过。
- EPUB fixture 校验成功，章节数与 ZIP 结构检查均通过。
- manifest fixture 已能基于校验通过的 EPUB 正常生成。
- 当前 Java 快照执行 `mvn -q -DskipTests package` 仍无法成功打包；现有报错集中在 `IdleFQ` 与 `FQNovelService` 的既有编译问题，应与本次发布整理分开修复。

## Failure handling | 故障处理

- `429 Too Many Requests`: honor `Retry-After` or exponential backoff, reuse cache, and avoid restarting a full-book download.
- `ILLEGAL_ACCESS`: check deployment-only device/session data and request pacing; do not persist error payloads as chapter text.
- `empty response`: confirm local service health and runtime assets, then retry only the corrupted or missing batch.
- EPUB validation failure: regenerate the EPUB and verify the transfer path does not recompress or mutate the ZIP.

- `429 Too Many Requests`：遵守 `Retry-After` 或指数退避，复用 cache，不重启整本下载。
- `ILLEGAL_ACCESS`：检查仅部署时注入的设备/会话数据与请求节奏，不要把错误载荷写成章节正文。
- `empty response`：先确认本地服务健康与运行时资源，再只重试损坏或缺失批次。
- EPUB 校验失败：重新生成 EPUB，并确认传输链路没有二次压缩或改写 ZIP。

## GitHub publishing checklist | GitHub 发布检查清单

- [ ] `git diff --cached --check` passes.
- [ ] `git status --ignored` shows only expected ignored runtime paths.
- [ ] No novel content, cookies, device IDs, registration keys, SSH material, or runtime APK/SO/rootfs assets remain tracked.
- [ ] `README.md`, `README.zh-CN.md`, and `README.en.md` all describe the same workflow boundary.
- [ ] Remote repo visibility and branch state are verified after push.

- [ ] `git diff --cached --check` 通过。
- [ ] `git status --ignored` 只出现预期的运行时忽略目录。
- [ ] 已跟踪文件中不存在小说正文、Cookie、设备 ID、注册密钥、SSH 材料或 APK/SO/rootfs 运行时资源。
- [ ] `README.md`、`README.zh-CN.md` 与 `README.en.md` 对流程边界描述一致。
- [ ] 推送后已核验远端仓库可见性与分支状态。
