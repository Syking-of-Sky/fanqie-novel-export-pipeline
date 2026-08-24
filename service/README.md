# Fanqie reader/signing service

这是流程中的**本地 Java 服务**：它把上游客户端签名、目录查询和批量章节读取封装成稳定的本地 HTTP API，供 `scripts/export_fanqie_reader.py` 断点导出。服务默认关闭上游请求，仓库只保存代码和配置模板，不保存 APK/SO、Cookie、设备标识、注册密钥或小说正文。

## 目录

- `src/main/java/.../web`：本地 HTTP 控制器。
- `src/main/java/.../service`：目录、章节和签名服务。
- `src/main/java/.../service/FqCrypto.java`：AES-128-CBC/GZIP 内容处理。
- `src/main/resources/application.yml`：安全默认值（上游关闭、`example.invalid`）。
- `application.example.yml`：部署配置模板。
- `tools/batch_device_register_xml.py`：按需生成本地设备配置；输出目录默认被 Git 忽略。

## 准备运行时资源

Unidbg 需要与目标客户端版本匹配的运行时资源。请在本地准备以下目录，**不要提交到 GitHub**：

```text
service/src/main/resources/com/dragon/read/oversea/gp/
├── apk/
├── lib/
├── rootfs/
└── other/
```

资源来源、授权和版本由部署者自行管理；仓库不会包含二进制文件。

## 本地启动

```bash
cd service
cp application.example.yml application-local.yml
# 编辑 application-local.yml，或通过环境变量提供 FANQIE_* 值
export SPRING_PROFILES_ACTIVE=dev,local
./mvnw spring-boot:run
```

默认监听 `127.0.0.1:9999`。只有在明确配置 `FANQIE_API_ENABLED=true`、上游 URL、Cookie、设备字段和 `FANQIE_REGISTRATION_KEY` 后，服务才会发起真实上游请求。建议把 `application-local.yml` 放在未跟踪路径，并限制文件权限。

## 导出器使用的接口

| 用途 | 方法与路径 |
| --- | --- |
| 目录 | `GET /api/fqsearch/directory/{bookId}` |
| 批量章节 | `POST /api/fqnovel/chapters/batch` |
| 批量请求体 | `{"bookId":"<id>","chapterRange":"1-30"}` 或 `{"bookId":"<id>","chapterIds":["<id>"]}` |

批量范围优先；如果上游目录与序号不一致，导出器会回退到显式 `chapterIds`。服务端按请求返回章节 ID、标题、HTML 原文和解密后的文本字段。

## 安全与故障处理

- `ILLEGAL_ACCESS`：暂停请求，检查设备配置和频率；不要改成高并发重试。
- `429 Too Many Requests`：按 `Retry-After` 或指数退避等待，复用缓存，不要重复下载已完成章节。
- 空响应/CRC 错误：保留缓存，删除对应损坏 JSON 后只重试该批次。
- 日志不要打印 Cookie、完整签名头、注册密钥或章节正文。

完整端点和响应约定见 [`docs/FQNOVEL_API.md`](docs/FQNOVEL_API.md)。
