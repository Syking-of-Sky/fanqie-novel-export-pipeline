# Release 草稿（中文）

适合直接复制到 GitHub Release，也可以按版本号另存为 `docs/releases/<tag>.md`。

## 标题模板

`v0.1.0 - Fanqie export/import pipeline`

推荐把当前公开基线打成首个正式 tag：`v0.1.0`。

## 发布说明模板

```md
## 本次发布包含

- 可复现的“分享链接 / `book_id` -> 目录 -> 批量章节 -> cache 断点续传 -> 去重 -> TXT/EPUB -> 校验 -> manifest -> 服务器幂等导入”流程。
- Python 脚本：目录导出、EPUB 写入、EPUB 校验、manifest 生成、上传导入示例。
- Spring Boot + Unidbg 本地服务样例工程与配置模板。
- 中英文 README、架构说明、故障排查与正式流程报告。

## 仓库内容边界

- 只包含流程代码、配置模板、接口契约和脱敏示例。
- 不包含小说正文、章节缓存、服务器数据库、Cookie、设备标识、注册密钥、SSH 信息或 APK/SO/rootfs 运行时资源。

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

## 验证范围

- Python 脚本通过 `python3 -m py_compile scripts/*.py service/tools/*.py`
- EPUB fixture 校验通过
- manifest fixture 生成通过
- 数字 ID / 非数字短链边界行为已记录

## 已知限制

- Java 服务构建依赖外部 Unidbg 运行时资源；仓库默认不提供。
- 上游接口可能触发 `429` 或 `ILLEGAL_ACCESS`，应复用 cache 并串行退避。
- 非数字短链需要在仓库外先解析为 canonical `book_id`。

## 升级 / 发布检查清单

- [ ] `git status --ignored` 中仅出现预期忽略目录
- [ ] 未提交 `outputs/`、`cache/`、`results/`、`service/target/`
- [ ] 未提交真实 Cookie、设备字段、注册密钥、绝对路径
- [ ] README / 双语文档 / 报告链接可点开
- [ ] 关键命令可在干净环境复现
```
