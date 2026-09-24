# scripts（脚本库）

本目录存放 SMS 的可执行脚本：路径解析、写盘门控、注册、打包、连接、会话、任务、进程、权限、并发调度、记忆与缓存清理、上下文自动压缩、安装同步与信任链。

## 应存什么

- 独立运行的 Python 脚本；文件名小写、中横线分隔；每个 ≤ 50 行。
- 数据写盘统一经 emit.py 门控：默认预览；`--write` 且会话已授予 write 才落盘。

## 当前内容

- [`resolve_home.py`](resolve_home.py)：解析 SMS 固定路径（env SMS_HOME → 用户配置 sms_home → 缓存目录 → 根目录）；`conf()` 读取 `<SMS_HOME>/config/config.json`（首读自动从 skill 模板 config.example.json 播种，用户配置不进 skill 目录）；分配子 skill 未指定路径的新建目录到 `<SMS_HOME>/tmp/`（`temp <rel> [--mkdir]`）。
- [`sandbox.py`](sandbox.py)：未指定路径的工作目录在 `<SMS_HOME>/tmp/sandbox/` 建立沙盒；create/list/deliver/clean（deliver/clean 默认预览，`--yes` 执行）。
- [`emit.py`](emit.py)：统一写盘门控（默认预览；已授予 write 才落盘；会话日目录写盘后自动触发上下文压缩）。
- [`bootstrap.py`](bootstrap.py)：确保 Skill_Generator 可用（查技能目录与 `<SMS_HOME>/config/config.json` 的 skill_generator，缺失则 GitHub 拉取）；创建目标 skill/子 skill 走其创建路径、修改（含 SMS 自身）走其修改路径。
- [`register.py`](register.py)：扫描技能安装位置与所用工具（默认根 = 用户 config 的 scan_roots）→ register.json。
- [`pack.py`](pack.py)：描述技能用途与接口 → interfaces.json。
- [`connect.py`](connect.py)：生成技能间上下文连接 → connections.json。
- [`deps.py`](deps.py) / [`deps_scan.py`](deps_scan.py)：依赖库 deps.json——deps_scan 以 AST 扫各技能 .py import 出「关联 python」（module→pip 发行名→安装状态，剔标准库/自带模块）；deps 于 .md 提及其他注册技能出「关联 skill」（独立于→independent，委托/依赖/调用→depends，其余 related，附证据片段）。
- [`session.py`](session.py)：建立 `sessions/<日期>/` 五元组。
- [`task.py`](task.py)：任务拆分·理解·整合 → task.json。
- [`process.py`](process.py)：进程式注册生命周期 spawn/run/suspend/resume/kill → processes.json。
- [`permissions.py`](permissions.py)：权限 grant/deny/check/audit——支持角色批量（readonly/worker/net/privacy/secrets/admin）与 TTL 分钟到期自动失效；键含敏感 vault（凭据明文）/verify(验证协助)，审计留痕。
- [`privacy.py`](privacy.py)：背景隐私采集 collect/notice/open：须 `grant privacy` 用户授权才可采集；每笔更新 NOTICE.md 告知用户；数据混淆+掩码+矩阵变换后存 `<SMS_HOME>/privacy/`；解密须 privacy+write 且写明必要理由并记审计。
- [`privacy_cat.py`](privacy_cat.py)：类别策略——identity/credential/behavior/content/biometric/contact/location 各配默认留存天数（credential 最严 1 天）；`report` 各类计数+解密次数；`purge` 超期清理（默认预览，--write 且 grant write 才执行并刷新 NOTICE）。
- [`scheduler.py`](scheduler.py)：五 lane 并发调度 → scheduler.json。
- [`dispatch.py`](dispatch.py)：子任务→技能→工具→权限映射 → dispatch.json（skill_executor 使用；quarantine/pending_review 技能拒绝派发；login-vault/captcha-assist 按 SKILL_REQ 强制 vault/verify 键）。
- [`init_registry.py`](init_registry.py)：初始设置一次性跑通 register → pack → connect → deps。
- [`memory_list.py`](memory_list.py)：重要记忆列表 add/list/remove → memory.json（记录的日期/路径为清理钉选）。
- [`cache_cleanup.py`](cache_cleanup.py) / [`skill_cache.py`](skill_cache.py)：缓存清理——cache_cleanup 删 sessions/ 早于 --keep-days 的日目录，memory 钉选保留（默认预览）；skill_cache 扫描 skill 目录缓存/运行时残留（`__pycache__`/`*.pyc` 删除，`tmp/`/`SMS/`/误落 config.json 迁入 `<SMS_HOME>/tmp/skill_legacy/`），默认预览、`--write` 且已授予 write 才执行。
- [`auto_compress.py`](auto_compress.py)：自动上下文压缩：日目录超阈时折叠 dialogue.md 旧记录为提纲，原文归档 context_archive.md（sha1 回溯；手动运行默认预览）。
- [`trust.py`](trust.py)：信任链标签 list/mark/review/audit：云端必 review，本地按日随机抽查，fail → quarantine。
- [`skill_errors.py`](skill_errors.py)：skill 错误位置与日志记录 → errors/skill_errors.json；未解决 ≥3 → 提示启用 self_update。
- [`install.py`](install.py)：本地 / `gh:owner/repo[/sub]` 安装到目标客户端 skills 文件夹（云端需 network+write 且 `--accept-download` 用户确认下载，标 pending_review）。
- [`sync_skills.py`](sync_skills.py)：SMS/skills hub ↔ 客户端目录 pull/push/status（冲突取新，未审/隔离不推送）。
- [`locality.py`](locality.py)：检查用户时区与地区（tz/locale/region）→ registry/locality.json，SMS 层接口。
- [`debate.py`](debate.py)：正反双辩论逻辑链（pro/con 两链 + verdict）→ sessions/<日期>/debate.json。
- [`commands.py`](commands.py)：命令系统 help/intent/show/use，汇总内置与暴露接口 → registry/commands.json。
- [`remove.py`](remove.py)：删除 skill（默认预览；--yes 确认 + --write 且已授予 write 才删；拒删受保护本体）。

## 数据契约

见 [`../schemas/`](../schemas/register.schema.json)：register / interfaces / connections / session / task / process / scheduler / memory / trust / error / locality / debate / commands / sandbox / privacy / deps。

## 运行约定

1. 使用项目默认 Python，并以 `python -B`（PYTHONDONTWRITEBYTECODE）运行，避免字节码缓存写入 skill 目录；
2. 数据写盘统一经 emit.py：默认预览；`--write` 且已授予 write 才落盘。
3. 先 `session.py --write` 建会话，再 `permissions.py grant write --write` 授权，之后写盘才生效。
4. 运行前先看 [`../resistance/resistance.md`](../resistance/resistance.md) 确认权限。