# Release 草稿（中文）

适合直接复制到 GitHub Release，也可以按版本号另存为 `docs/releases/<tag>.md`。

## 标题模板

`v0.1.0 - Fanqie export/import pipeline`

推荐把当前公开基线打成首个正式 tag：`v0.1.0`。

## 发布说明正文

```md
这是 `fanqie-novel-export-pipeline` 的首个公开版本。

它把一条已经验证过的流程整理成可复现、可审计、可再次执行的工作流：从分享链接或 `book_id` 出发，读取目录、批量获取章节、断点续传、按章节去重、补抓官方封面、生成 TXT/EPUB、校验产物，再把 `manifest.json` 和 EPUB 交给服务器做幂等导入。

## 这次发布解决了什么

- 把“脚本 + 手工经验”整理成了清晰的端到端流程仓库。
- 把缓存、去重、官方封面补齐、EPUB 校验、manifest 导入这些容易漏掉的环节固定下来。
- 把中英文 README、架构说明、故障排查和正式报告一起补齐，适合直接复用或二次改造。

## 这次发布包含

- Python 工具：目录导出、官方封面抓取、EPUB 写入、EPUB 校验、manifest 生成、上传导入示例。
- Spring Boot + Unidbg 本地服务样例工程与配置模板。
- Mermaid 首页流程图 / 时序图，方便公开展示整个链路。
- 双语文档：README、架构说明、故障排查、正式流程报告。

## 仓库边界

- 仓库只包含流程代码、配置模板、接口契约和脱敏示例。
- 不包含小说正文、章节缓存、服务器数据库、Cookie、设备标识、注册密钥、SSH 信息或 APK/SO/rootfs 运行时资源。

## 适合谁用

- 想把导出流程做成可复现脚本的人。
- 想保留 TXT/EPUB 产物、补齐封面并进行后续导入的人。
- 想拆分本地签名服务、章节抓取和服务器导入边界的人。

## 已知限制

- Java 服务构建依赖外部 Unidbg 运行时资源；仓库默认不提供。
- 上游接口可能触发 `429` 或 `ILLEGAL_ACCESS`，应复用 cache 并串行退避。
- 目录元数据如果没有返回 `coverUrl`/`thumbUrl`，则需要显式使用 `--skip-cover` 才会继续导出无封面版本。
- 非数字短链需要在仓库外先解析为 canonical `book_id`。

## Quick start

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install requests

python scripts/export_fanqie_reader.py '<book-id-or-share-url>' \
  --app-api http://127.0.0.1:9999 \
  --output-root outputs --cache-root cache

python scripts/make_manifest.py outputs/<频道>/<书名> --channel '<频道>'
python scripts/validate_epub.py outputs/<频道>/<书名>/<书名>.epub
```
