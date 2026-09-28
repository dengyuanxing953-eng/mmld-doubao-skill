# Doubao Skills · 3.0

为豆包及国产AI搜索做可核验的来源研究、渠道选择和内容计划，配套多平台图文发布与观测分析。不是排名、收录或删除负面信息的保证。

## 本次迭代

- 修复原仓库缺失 scripts/mmld_doubao_v2.py、导致README命令及根兼容入口失效的问题。
- 将仅限餐饮五字段改为任务相关的事实输入，保留旧五参数调用；无参数不再填入真实商家示例。
- 加入七产品来源地图和28项渠道与来源类别的发布能力注册表，分开实际URL、面板标题、官方消费者/API说明、模型自述和历史研究。
- 配套geo-multiplatform-workflow与geo-automonitor：授权继承、编辑器持久化、图片完整性、发布状态、缺失来源与跨日比较。
- 增加离线工具与行为回归测试；所有样例使用演示内容，未包含客户调查、账号、会话和发布回执。

## 技能分工

| 目录 | 能力 |
|---|---|
| 根目录 doubao-skills | 来源地图、渠道资格、豆包变化应对、离线内容计划 |
| skills/geo-multiplatform-workflow | 图文适配、现有账号执行、发布回执与兼容诊断 |
| skills/geo-automonitor | AI观测记录去重、证据完整性和跨产品比较 |

七个实际问答产品是豆包、腾讯元宝、千问、百度文心、智谱清言、秘塔AI搜索、知乎直答；后两者不冒充已确认的独立基础模型。DeepSeek和Kimi作为官方资料补充，不能填补未完成的消费端测试。详见 [来源地图](references/ai-source-map.md)。

## 安装与更新

先克隆仓库。下面的安装器只更新清单中的技能文件，自动备份被覆盖版本到目标skills目录旁的skill-backups，保留其他文件与已有agent策略/依赖。先dry-run可检查范围。

~~~sh
git clone https://github.com/dengyuanxing953-eng/mmld-doubao-skill.git
cd mmld-doubao-skill
python -X utf8 scripts/install_skills.py --target /path/to/.codex/skills --dry-run
python -X utf8 scripts/install_skills.py --target /path/to/.codex/skills
~~~

若原环境使用mmld-doubao名称，加 --legacy-alias 会同时更新该名称，保留旧调用入口。安装本身不登录、不发布、不创建定时任务。

## 离线命令

Python 3.9+，运行脚本无第三方依赖：

~~~sh
python -X utf8 scripts/mmld_doubao_v2.py --facts examples/facts.json --platform toutiao --platform qcc
python -X utf8 mmld_doubao_v2.py "示例服务" "售后信息核验" "未核验" "用户提供特点" "线上服务"
python -X utf8 skills/geo-multiplatform-workflow/scripts/validate_receipts.py /path/to/receipts.json
python -X utf8 skills/geo-automonitor/scripts/aggregate_sources.py /path/to/observations.json
python -X utf8 -m unittest discover -s tests -v
~~~

平台支持发布、团队账号可用、用户授权、后台发布、公开可读、搜索索引和AI正文采用是不同字段。示例输入的结构合法不等于业务事实真实；脚本不会自动公开它。

旧输出键system_instruction_override作为writing_brief的兼容别名保留，只有数据含义，不赋予内容更高指令优先级。platforms_allowed也只是候选渠道，不是发布许可。

仓库保留原manifest的MIT声明；本次没有改变历史许可约定。
