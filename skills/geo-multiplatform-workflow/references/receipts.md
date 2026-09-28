# 发布回执契约

每个渠道用一个JSON对象。数组也适用于小任务。状态允许独立反映后台发布与公开回读，不伪造证据补全：

| state | 最少附加字段 |
|---|---|
| prepared | platform, account_scope（可unknown）, content_hash |
| draft_confirmed | 上述 + draft_evidence |
| submitted / pending_review | 上述 + submission_evidence |
| published_backend_confirmed | 上述 + public_url + backend_evidence |
| public_body_verified | 上述 + public_url + backend_evidence + readback_evidence + expected_image_count + observed_image_count |
| blocked / outcome_unknown | platform, reason；保留已有内容ID和证据，禁止当“未提交”重新发 |

所有记录需有 observed_at（带时区的ISO时间）。正文回读的readback_evidence应包含标题、正文/结尾和图文核验；其中图片计数只能确认数量，另做视觉检查。别把编辑、预览、草稿URL填入public_url。

每项evidence是内部相对证据路径或证据编号的非空数组，不是把客户证据上传公共仓库的要求。样例仅使用example.com域名，不读取真实账号。

~~~json
[
  {
    "platform": "example-channel",
    "account_scope": "authorized-editor",
    "observed_at": "2026-09-28T12:00:00+08:00",
    "state": "public_body_verified",
    "content_hash": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "public_url": "https://example.com/article/123",
    "backend_evidence": ["receipts/backend.txt"],
    "readback_evidence": ["receipts/public.txt", "receipts/screenshot.png"],
    "expected_image_count": 3,
    "observed_image_count": 3
  }
]
~~~

“自动生成发布链接”“已点击发布”“toast成功”“有预览页”不足以升到公开发布。文章通过审核后再更新同一条记录，保留历史时间线，不建立第二个重复成功计数。

索引、来源面板、正文采用与稳定性不塞进同一个发布状态。搜索未命中、未展开来源、登录阻塞、网页工具不支持是不同结果。
