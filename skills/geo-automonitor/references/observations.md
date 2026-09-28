# 观测记录

脚本输入JSON数组，或{"observations": [...]}。每个字段来自真实观察，不能为通过校验虚构数据。

必要字段：
- id：一次测试的稳定ID；多版本须有不同updated_at，以最新版本为准。相同ID/时间却内容冲突会拒绝。
- engine、surface、mode：真实产品与模式。surface例如consumer_web、consumer_app、api_search，不合并托管模型与官网产品。
- prompt_kind：natural（不喂目标链接）、url_seeded（定向读页）、self_report（问模型依赖什么）、other。
- question_id：固定问题标识；原问题文本可另存内部文件。
- observed_at、updated_at：带时区ISO时间；updated_at不早于observed_at。
- status：answered、blocked、error。
- capture：complete、partial、not_captured；blocked/error只能not_captured且sources为空。
- declared_source_count：已显示总数，或null；不能把未展开来源填0。
- sources：包含url（缺则null）、label（可选）、body_supported（默认false）的数组。true必须有support_excerpt及support_evidence来定位并核对支持关系。

示例：
~~~json
[
  {
    "id": "sample-1",
    "engine": "example-assistant",
    "surface": "consumer_web",
    "mode": "default",
    "prompt_kind": "natural",
    "question_id": "q1",
    "observed_at": "2026-09-28T10:00:00+08:00",
    "updated_at": "2026-09-28T10:00:00+08:00",
    "status": "answered",
    "capture": "partial",
    "declared_source_count": 2,
    "sources": [
      {"url": "https://example.com/article/1?utm_source=search", "body_supported": false}
    ]
  }
]
~~~

统计口径：
- 原始可见链接出现次数、每回答去重URL数、跨回答去重URL数、站点覆盖回答数各不相同。
- 只对完整捕获且明确无来源的回答记录“零来源”；未捕获为null/unknown。
- partial的比例不能当完整AI引用率；title-only可记标签数，不擅自补域名。
- 去重移除已知追踪参数，保留id等正文标识；头条item/article/group同ID归一，黑猫同投诉ID的地方域名归一。域名归并不代表重复事件已核验，不按相似标题合并不同投诉。
- 来源出现不证明因果、排名、推荐或事实真实性。这个脚本不计算stable，也不输出固定权重。
