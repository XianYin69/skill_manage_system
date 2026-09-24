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
- [`task.py`](task.py) / [`process.py`](process.py)：任务拆分·理解·整合 → task.json；进程式注册生命周期 spawn/run/suspend/resume/kill → processes.json。
- [`permissions.py`](permissions.py)：权限 grant/deny/check/audit——支持角色批量（readonly/worker/net/privacy/secrets/admin）与 TTL 分钟到期自动失效；键含敏感 vault（凭据明文）/verify(验证协助)，审计留痕。
- [`privacy.py`](privacy.py)：背景隐私采集 collect/notice/open：须 `grant privacy` 用户授权才可采集；每笔更新 NOTICE.md 告知用户；数据混淆+掩码+矩阵变换后存 `<SMS_HOME>/privacy/`；解密须 privacy+write 且写明必要理由并记审计。
- [`privacy_cat.py`](privacy_cat.py)：类别策略——identity/credential/behavior/content/biometric/contact/location 各配默认留存天数（credential 最严 1 天）；`report` 各类计数+解密次数；`purge` 超期清理（默认预览，--write 且 grant write 才执行并刷新 NOTICE）。
- [`scheduler.py`](scheduler.py) / [`dispatch.py`](dispatch.py)：五 lane 并发调度 → scheduler.json；子任务→技能→工具→权限映射 → dispatch.json（skill_executor 使用；quarantine/pending_review 拒绝派发；login-vault/captcha-assist 按 SKILL_REQ 强制 vault/verify 键）。
- [`init_registry.py`](init_registry.py) / [`memory_list.py`](memory_list.py)：初始设置一次性跑通 register → pack → connect → deps；重要记忆列表 add/list/remove → memory.json（记录的日期/路径为清理钉选）。
- [`cache_cleanup.py`](cache_cleanup.py) / [`skill_cache.py`](skill_cache.py)：缓存清理——cache_cleanup 删 sessions/ 早于 --keep-days 的日目录，memory 钉选保留（默认预览）；skill_cache 扫描 skill 目录缓存/运行时残留（`__pycache__`/`*.pyc` 删除，`tmp/`/`SMS/`/误落 config.json 迁入 `<SMS_HOME>/tmp/skill_legacy/`），默认预览、`--write` 且已授予 write 才执行。
- [`auto_compress.py`](auto_compress.py)：自动上下文压缩：日目录超阈时折叠 dialogue.md 旧记录为提纲，原文归档 context_archive.md（sha1 回溯；手动运行默认预览）。
- [`trust.py`](trust.py)：信任链标签 list/mark/review/audit：云端必 review，本地按日随机抽查，fail → quarantine。
- [`skill_errors.py`](skill_errors.py)：skill 错误位置与日志记录 → errors/skill_errors.json；未解决 ≥3 → 提示启用 self_update。
- [`install.py`](install.py) / [`sync_skills.py`](sync_skills.py)：本地 / `gh:owner/repo[/sub]` 安装到目标客户端 skills 文件夹（云端需 network+write 且 `--accept-download` 确认，标 pending_review）；SMS/skills hub ↔ 客户端目录 pull/push/status（冲突取新，未审/隔离不推送）。
- [`shell.py`](shell.py)：sms-shell 入口（有图形服务器→GUI，否则 TUI，`--tui/--gui` 强制，GUI 探测失败自动回退）；入口 [`../bin/sms-shell`](../bin/sms-shell)（POSIX，可执行位）与 `sms-shell.cmd`（Windows）相对自身定位，部署后在其他路径直接执行。
- [`agent_stream.py`](agent_stream.py) / [`shell_core.py`](shell_core.py)：数据流引擎——检测电脑上已装 agent 的 CLI（claude/codex/cursor/kilocode/kilo/aider，用户配置 `agent_cli` 可增改 {bin,args}），把用户话语默认前置「使用 skill_manage_system 技能」指令送入 CLI、其 stdout 逐行流回前端，未检出即拒绝并引导配置（本体不作答），当前 agent/前缀状态只存 `<SMS_HOME>/shell/`；路由引擎——任意话语直达 agent、命中个性化指令名自动展开执行、`:` 元指令（agents/use/skill/cmds/intent/alias/unalias/hud/deploy/session/grant/help/quit）治理。
- [`shell_tui.py`](shell_tui.py) / [`shell_gui.py`](shell_gui.py)：TUI 前端（免图形服务器，pwsh/bash/zsh 式即时对话，readline 历史+Tab 补全含个性化指令名）；GUI 前端（tkinter 窗口终端，工作线程流式回填不卡窗，`tui` 另起终端壳）。
- [`locality.py`](locality.py) / [`debate.py`](debate.py)：检查用户时区与地区（tz/locale/region）→ registry/locality.json；对论断生成 pro/con 正反双链 + verdict → sessions/<日期>/debate.json。
- [`commands.py`](commands.py) / [`user_commands.py`](user_commands.py)：命令系统 help/intent/show/use，汇总内置/skill 接口/个性化指令 → registry/commands.json，alias/unalias/hud/deploy/shell/temp/sandbox/privacy 路由转发；个性化指令——自定义格式（名称/描述/arg_names/步骤模板）存 `<SMS_HOME>/commands/user_commands.json`，步骤前缀 `script:`（调 SMS 脚本，写盘仍经 emit 门控）/`delegate:`（必回 SMS 派发，如 `delegate:Skill_Generator 修改 {skill}` 实现 skill-update 迭代）/`say:`，`{arg}`/`{args}` 占位展开（script 步骤按 token 传参，Windows 路径与含空格值不破坏），run 逐步执行。
- [`deploy.py`](deploy.py)：按指令部署 SMS 本体与托管 skills 到其他目录/客户端（位置参数目录、`--clients a,b`、或命名参数 `--Path P [--NewFolder Yes] [--FolderName F]`＝init 语义；`--skills a,b|all`；`--launcher` 在目标根生成可执行 `sms-shell(.cmd)` 启动器；复制排除 .git/__pycache__/tmp；默认预览，`--write` 且 grant write 才执行）。
- [`hud.py`](hud.py) / [`hud_view.py`](hud_view.py)：界面顶面 HUD——任务进行时置顶·点击穿透·不抢焦点·只读，居屏幕顶中（alert 红/session/step 三行）；session/step/alert/hide/status；状态只存 `<SMS_HOME>/hud/`，查看进程后台拉起、空闲 120s 自退。
- [`remove.py`](remove.py)：删除 skill（默认预览；--yes 确认 + --write 且已授予 write 才删；拒删受保护本体）。

## 数据契约

见 [`../schemas/`](../schemas/register.schema.json)：register / interfaces / connections / session / task / process / scheduler / memory / trust / error / locality / debate / commands / sandbox / privacy / deps / [user_commands](../schemas/user_commands.schema.json)。

## 运行约定

1. 使用项目默认 Python，并以 `python -B`（PYTHONDONTWRITEBYTECODE）运行，避免字节码缓存写入 skill 目录；
2. 数据写盘统一经 emit.py：默认预览；`--write` 且已授予 write 才落盘。
3. 先 `session.py --write` 建会话，再 `permissions.py grant write --write` 授权，之后写盘才生效。
4. 运行前先看 [`../resistance/resistance.md`](../resistance/resistance.md) 确认权限。