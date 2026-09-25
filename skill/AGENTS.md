# AGENTS.md — 入口红线镜像（skill_manage_system）

代理在此 skill 内的角色红线（正文见 [SKILL.md](SKILL.md) 与 [resistance/resistance.md](resistance/resistance.md)）。
本文件与两份正文由 [scripts/redlines.py](scripts/redlines.py) `check` 机械断言，关键句缺失即拒绝初始化、拒绝提交。

1. **调度器与管理器（2026-09-24 用户废止「一律委托」强制红线）**：SMS 常规运行仍是识别意图→派发→整合；agent 可直接实现/修改本工具及其 skill 层，创建/修改 skill 亦可选委托 Skill_Generator 走其修改路径（非强制）。
2. **高危操作先询问**：递归删除、向用户目录复制/覆盖写——先向用户展示预览并取得当轮明确同意，且 `permissions.py grant danger`（敏感键，不随角色批量、TTL 到期）；禁止盲命令、禁止无 grant 执行。
3. **部署＝仅复制 bin 文件**：把 `bin/` 下启动文件（sms-shell·sms-api·locate.py·sms_api.py·sms_formats.py）复制到用户指定路径即完成部署；绝不整包复制 skill 本体（2026-09-24 事故教训，resistance #16）。
4. **本体不作答**：一切作答来自托管 skill 执行结果；无匹配→委托 Skill_Generator 创建后执行；不可得→明确拒绝并说明。
5. **约束不得静默丢失**：初始化第一步与每次 git 提交前跑 `python -B skill/scripts/redlines.py check`；失败即停、向用户报告，不得绕过；经用户确认的约束变更完成后须 `redlines.py seal` 重钉基线。
6. **根入口程序**：跨 OS 入口＝根目录 `sms.py`（三段：开箱即用→依赖嗅探与修补→引导至 CLI）＋ `sms`/`sms.cmd` 壳；初始化与诊断一律经它，三段职责不得并入其他脚本。
7. **十一链记忆·对话隔离·做梦**：会话碎片链存 `<SMS_HOME>/chains/`（含向量/频次/边）；所有链必须 git 管理（chains_git.py 自动建仓＋写入自动提交）；每次用户输入＝开新对话（压缩记忆＋当前输入），agent 的 skill 必须开新子会话并收口（resistance #17）。
8. 全部 .md/脚本 ≤50 行；悬空链接 = 0；数据写盘一律经 emit 门控（默认预览）。
9. **配置系统与网络壳（resistance #18）**：配置增改唯一经 settings.py（api_key 恒掩码）；model_meta 抓上游模型 Token/上下文/RPM 只写用户缓存；网页壳只绑 127.0.0.1＋指纹证书＋配对 token；对外端口默认关闭——`enable --yes` 当轮确认才置位，外部请求须本地 enroll 指纹＋ML-DSA 验签，只开对话面、限速封禁，证书/密钥/token 不落 skill 目录。
