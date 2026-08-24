# Local API contract

本文件描述导出器依赖的**本地服务**，不是上游平台的官方 API 文档。所有 ID、Cookie、设备字段和密钥都使用占位符。

## Directory

```http
GET /api/fqsearch/directory/{bookId}
```

成功响应至少包含：

```json
{
  "code": 0,
  "data": {
    "book_info": {"book_name": "示例书名", "author": "示例作者"},
    "item_data_list": [
      {"item_id": "<chapter-id>", "title": "第一章"}
    ]
  }
}
```

导出器以 `item_id` 为唯一键去重，并把目录标题作为权威标题。

## Batch chapters

```http
POST /api/fqnovel/chapters/batch
Content-Type: application/json
```

范围请求：

```json
{"bookId":"<book-id>","chapterRange":"1-30"}
```

显式 ID 回退：

```json
{"bookId":"<book-id>","chapterIds":["<chapter-id-1>","<chapter-id-2>"]}
```

响应的 `data.chapters` 可以按序号或章节 ID 映射；每项至少提供 `chapterName` 和 `rawContent`。导出器会清理 XHTML、HTML 实体、尾注和异常私有区字符，然后检查标题一致性与正文最小长度。

## Crypto boundary

服务内部使用部署时注入的 `fq.api.registration-key` 生成注册载荷，并用返回的章节密钥执行 AES-128-CBC 解密及可选 GZIP 解压。注册密钥没有源码默认值；未配置时服务应保持禁用或明确报错。

## Error model

```json
{"code": -1, "message": "error description", "data": null}
```

常见情况：

- `429`：限流，等待并复用 cache。
- `ILLEGAL_ACCESS`：设备风控或请求频率异常，降低频率并检查配置。
- `code != 0`：记录错误消息，避免把响应当作章节正文。
