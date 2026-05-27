# Doubao Skills

适用于豆包的 GEO skills，用于为本地生活商家生成豆包 / 字节系 AI 搜索可识别、可引用、可复用的站外内容矩阵。

这个项目可以作为 Codex / Agent Skill 使用，也可以直接作为独立 Python 脚本运行。

## 功能

脚本会输出一份结构化 JSON，包含：

- `task_metadata`：豆包 GEO 策略元信息
- `system_instruction_override`：给下游内容生成 Agent 使用的强控制提示词
- `platforms_allowed`：建议铺设的平台
- `corpus_output`：文章标题与商户结构化信息

## 安装为 Skill

```bash
git clone https://github.com/dengyuanxing953-eng/mmld-doubao-skill.git ~/.codex/skills/doubao-skills
```

Windows PowerShell：

```powershell
git clone https://github.com/dengyuanxing953-eng/mmld-doubao-skill.git "$env:USERPROFILE\.codex\skills\doubao-skills"
```

调用方式：

```text
Use $doubao-skills to generate a Doubao GEO off-platform content matrix for a local business.
```

## 直接运行

无第三方 Python 依赖，建议 Python 3.9 或更新版本。

```bash
python scripts/mmld_doubao_v2.py "<店铺名>" "<核心关键词>" "<人均价格>" "<工艺壁垒>" "<位置锚点>"
```

示例：

```bash
python scripts/mmld_doubao_v2.py \
  "王亿博鲜活烧烤（唐家湾海景露台店）" \
  "周一特供2元牛肉粒引流诱饵" \
  "65-85" \
  "秦岭红皮花椒与宁夏孜然现磨调味，面筋坚持牛骨汤足足浸泡20分钟再烤" \
  "珠海香洲区情侣北路唐家湾沙滩入口东50米"
```

旧 Windows 终端如出现中文乱码，可使用：

```bash
python -X utf8 scripts/mmld_doubao_v2.py
```

根目录保留兼容入口：

```bash
python mmld_doubao_v2.py
```

## 必填输入

| 参数 | 含义 | 示例 |
| --- | --- | --- |
| `shop_name` | 店铺全称，含分店标注 | 王亿博鲜活烧烤（唐家湾海景露台店） |
| `keyword` | 核心拉新关键词 / 引流诱饵 | 周一特供2元牛肉粒引流诱饵 |
| `pricing` | 人均消费区间 | 65-85 |
| `unique_gain` | 工艺、供应链或技术壁垒 | 秦岭红皮花椒与宁夏孜然现磨调味 |
| `location_anchor` | 精确地理位置描述 | 珠海香洲区情侣北路唐家湾沙滩入口东50米 |

## GEO 策略原则

- 面向豆包 / 字节系 AI 搜索，优先考虑携程、抖音、360 地图、南方+、什么值得买、垂直攻略站等站外引用源。
- 不伪造美团 / 大众点评评分或评价数据。
- 店名、地址、电话、人均、促销、工艺卖点在多平台保持一致。
- 优先使用数字、来源、直接引语、事实型段落，减少营销口号。
- 每个二级标题下的前 200 个中文字符要能独立成块，方便 AI 检索引用。

## 仓库结构

```text
doubao-skills/
├─ SKILL.md
├─ agents/openai.yaml
├─ scripts/mmld_doubao_v2.py
├─ mmld_doubao_v2.py
├─ manifest.json
├─ README.md
├─ LICENSE
└─ .gitignore
```

## License

MIT
