# 番茄小说导出流程（中文）

## 项目用途

本项目把一次已验证的小说整理流程做成可复现工具链：输入数字 `book_id` 或分享链接，读取本地 Java 服务暴露的目录，按批次获取章节，按章节 ID 去重，清理正文，输出 TXT/EPUB，生成校验报告和服务器导入清单。

正式流程报告见 `docs/2026-08-24_fanqie-export-pipeline-report.md`。

仓库是**流程仓库，不是内容仓库**。不会提交任何整本小说、章节 JSON 缓存、服务器数据库、Cookie、设备 ID、会话 UUID、注册密钥、SSH 信息或 APK/SO/rootfs 运行时资源。

## 前置依赖

- Python 3.9+ 与 `requests`。
- Java 8+、Maven Wrapper；服务运行需要部署者自行准备匹配版本的 Unidbg 资源。
- 可选：Node.js（服务器已有 `import-with-manifest.js` 时使用）。

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install requests
```

## 完整流程

1. **解析输入**：接受数值 ID 或 `changdunovel.com/t/...`、`fanqienovel.com/page/...` 链接；数值 ID 直接使用，非数值短链由上游页面/已知解析器补全后再执行。
2. **读取目录**：调用本地 `GET /api/fqsearch/directory/{bookId}`，建立有序 `(item_id, title)` 列表。
3. **批量读取正文**：每 30 章优先请求 `chapterRange`；范围失败时使用同一批次的 `chapterIds`。
4. **断点续传**：成功章节写入 `cache/app/<book_id>/<item_id>.json`，临时文件原子替换；再次运行只补缺失或不合格章节。
5. **清理与去重**：去 HTML/XHTML 标签、实体、尾注和异常字符；以 `item_id` 去重并核验标题，避免重复章节混入导出。
6. **导出**：生成带书籍元数据的 TXT 和一个章节一个 XHTML 的 EPUB 3。
7. **验证**：执行 CRC、`mimetype`、容器文件和章节数检查，并在 `verification.json` 记录 SHA-256。
8. **导入**：生成 `manifest.json`，与 EPUB 放在同一暂存目录，通过服务器导入脚本按标题幂等处理。
9. **最终核验**：以服务器数据库/书架的最终书名、章节数和总书数为准，不以 `scp` 成功或脚本中间日志为准。

## 使用命令

```bash
python scripts/export_fanqie_reader.py '<book-id-or-share-url>' \
  --app-api "${FANQIE_APP_API:-http://127.0.0.1:9999}" \
  --output-root outputs --cache-root cache

python scripts/make_manifest.py outputs/<频道>/<书名> --channel '<频道>'
python scripts/validate_epub.py outputs/<频道>/<书名>/<书名>.epub
```

`--workers` 只为兼容旧命令保留；当前流程刻意串行，避免触发上游频控。

## Java 服务

```bash
cd service
cp application.example.yml application-local.yml
# 在 application-local.yml 或环境变量中填写部署配置
export SPRING_PROFILES_ACTIVE=dev,local
./mvnw spring-boot:run
```

默认只监听本机，且 `FANQIE_API_ENABLED=false`。真实的 `FANQIE_API_BASE_URL`、`FANQIE_COOKIE`、设备字段和 `FANQIE_REGISTRATION_KEY` 必须通过部署配置注入。Unidbg 所需 `apk/`、`lib/`、`rootfs/`、`other/` 目录不在仓库中。

## manifest 导入

示例格式：

```json
{
  "示例书名.epub": {
    "title": "示例书名",
    "channel": "示例频道"
  }
}
```

服务器导入约定：manifest 与 EPUB 同目录；按 `title` 幂等去重；已存在的书删除暂存副本并跳过；导入后查询最终数据库/书架状态。

## 限流和错误

- **429**：等待 `Retry-After` 或指数退避，复用 cache，不重复下载整本书。
- **ILLEGAL_ACCESS**：通常是设备风控或请求频率问题；降低频率、检查部署配置。
- **空响应**：确认本地服务健康、运行时资源完整，再只重试缺失批次。
- **EPUB 校验失败**：删除该 EPUB 后重生成，检查上传过程是否压缩/改写 ZIP。

补充故障排查见 `docs/troubleshooting.zh-CN.md`，英文版见 `docs/troubleshooting.en.md`。

## 隐私与发布边界

提交前确认 `git status --ignored` 中只出现预期的 `outputs/`、`cache/`、`target/`。如果日志里出现 Cookie、签名头、设备标识或真实密钥，先删除并轮换后再保存日志。
