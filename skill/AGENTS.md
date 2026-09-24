# AGENTS.md — 入口红线镜像（skill_manage_system）

代理在此 skill 内的角色红线（正文见 [SKILL.md](SKILL.md) 与 [resistance/resistance.md](resistance/resistance.md)）。
本文件与两份正文由 [scripts/redlines.py](scripts/redlines.py) `check` 机械断言，关键句缺失即拒绝初始化、拒绝提交。

1. **调度器与管理器（2026-09-24 用户废止「一律委托」强制红线）**：SMS 常规运行仍是识别意图→派发→整合；agent 可直接实现/修改本工具及其 skill 层，创建/修改 skill 亦可选委托 Skill_Generator 走其修改路径（非强制）。
2. **高危操作先询问**：递归删除、向用户目录复制/覆盖写——先向用户展示预览并取得当轮明确同意，且 `permissions.py grant danger`（敏感键，不随角色批量、TTL 到期）；禁止盲命令、禁止无 grant 执行。
3. **部署＝仅复制 bin 文件**：把 `bin/` 下启动文件（sms-shell·sms-api·locate.py·sms_api.py·sms_formats.py）复制到用户指定路径即完成部署；绝不整包复制 skill 本体（2026-09-24 事故教训，resistance #16）。
4. **本体不作答**：一切作答来自托管 skill 执行结果；无匹配→委托 Skill_Generator 创建后执行；不可得→明确拒绝并说明。
5. **约束不得静默丢失**：初始化第一步与每次 git 提交前跑 `python -B skill/scripts/redlines.py check`；失败即停、向用户报告，不得绕过；经用户确认的约束变更完成后须 `redlines.py seal` 重钉基线。
6. **根入口程序**：跨 OS 入口＝根目录 `sms.py`（三段：开箱即用→依赖嗅探与修补→引导至 CLI）＋ `sms`/`sms.cmd` 壳；初始化与诊断一律经它，三段职责不得并入其他脚本。
7. 全部 .md/脚本 ≤50 行；悬空链接 = 0；数据写盘一律经 emit 门控（默认预览）。
