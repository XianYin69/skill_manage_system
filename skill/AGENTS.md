# AGENTS.md — 入口红线镜像（skill_manage_system）

代理在此 skill 内的角色红线（正文见 [SKILL.md](SKILL.md) 与 [resistance/resistance.md](resistance/resistance.md)）。
本文件与两份正文由 [scripts/redlines.py](scripts/redlines.py) `check` 机械断言，关键句缺失即拒绝初始化、拒绝提交。

1. **调度器与管理器（2026-09-24 用户废止「一律委托」强制红线）**：SMS 常规运行仍是识别意图→派发→整合；agent 可直接实现/修改本工具及其 skill 层，创建/修改 skill 亦可选委托 Skill_Generator 走其修改路径（非强制）。**主流程守卫（批18·相信大模型）**：子会话/子技能收口＝返回 SMS 主流程继续推进，〔任务表〕仍有未完成行时不得结束对话——由模型判断继续派发或改表，gateway 机械保障收口前表已清空（仅对话主流程 depth==0 生效）；任务表行数无上限、由模型据实拆分，无冲突子任务并发派发、有依赖依序。
2. **高危操作先询问**：递归删除、向用户目录复制/覆盖写——先向用户展示预览并取得当轮明确同意，且 `permissions.py grant danger`（敏感键，不随角色批量、TTL 到期）；禁止盲命令、禁止无 grant 执行。
3. **部署＝仅复制 bin 文件**：把 `bin/` 下统一入口文件（sms-shell(.cmd)/sms-shell.py 启动器＋原生 DOS TUI 七件 ps1：sms_shell/sms_state/sms_chain/sms_dos/sms_gw/sms_gw_http/sms_route——壳完全在系统 shell 运行·本体零 python＋locate.py·sms_formats.py——格式 API 已并入 sms-shell，`api` 子命令/`:api`）复制到用户指定路径即完成部署；绝不整包复制 skill 本体（2026-09-24 事故教训，resistance #16）。
4. **LLM 主导·脚本辅助（2026-09-27 批16 用户指示改红线·旧「本体不作答」废止）**：纯知识问答/闲聊由大模型直接回答，不必先派子技能；凡要动手（读写/执行/派技能）必须真用工具或 skill 子会话执行并留账，禁止空口声称已执行；[SMS 路由] 打分行仅供参考，裁决权在模型；技能不可得且属新领域→委托 Skill_Generator 创建；未检出执行器→拒绝并引导配置，不得假装已执行。
5. **约束不得静默丢失**：初始化第一步与每次 git 提交前跑 `python -B skill/scripts/redlines.py check`；失败即停、向用户报告，不得绕过；经用户确认的约束变更完成后须 `redlines.py seal` 重钉基线。
6. **根入口程序**：跨 OS 入口＝根目录 `sms.py`（三段：开箱即用→依赖嗅探与修补→引导至 CLI）＋ `sms`/`sms.cmd` 壳；初始化与诊断一律经它，三段职责不得并入其他脚本。
7. **十一链记忆·对话隔离·做梦**：会话碎片链存 `<SMS_HOME>/chains/`（含向量/频次/边）；所有链必须 git 管理（chains_git.py 自动建仓＋写入自动提交）；每次用户输入＝开新对话（压缩记忆＋当前输入），agent 的 skill 必须开新子会话并收口（resistance #17）。
8. 全部 .md/脚本 ≤50 行；悬空链接 = 0；数据写盘一律经 emit 门控（默认预览）。
9. **配置系统与网络壳（resistance #18）**：配置增改唯一经 settings.py（模型输入参数 config.json·api_key 恒掩码）与 skills_config.py（技能列表配置独立存 skills.json·scan_roots 等首访幂等搬出）；SMS 工作区产物目录：workspace()/wtmp() 一律取 SMS_WORKSPACE（env→配置→内建虚拟）下 tmp/——真实与虚拟工作区均自动创建、对话生成文件只入此（env SMS_TMP），大模型与技能配置恒直读 <SMS_HOME>/config 文件、禁止复制/重建到工作区；tmp 内目标为工作区文件的产物经用户审核（diff 预览）后须用户当轮明确同意加 --yes 且 :grant danger 方可经 ws_release.py 收编回工作区（源限 tmp/、目标限工作区内）；model_meta 抓上游模型 Token/上下文/RPM 只写用户缓存；网页壳只绑 127.0.0.1＋指纹证书＋配对 token；对外端口默认关闭——`enable --yes` 当轮确认才置位，外部请求须本地 enroll 指纹＋ML-DSA 验签，只开对话面、限速封禁，证书/密钥/token 不落 skill 目录。
10. **firefox lite 内核·TTS·学习·基本操作（resistance #19）**：ff_lite.py 搜索/取页/下载须 grant network（默认拒绝），下载只落 `<SMS_HOME>/downloads/`、覆盖须 --yes 语义的 `--force`＋grant danger、缺渲染内核回退报错绝不自动装依赖；tts.py 阿林娜（alina）机械女声默认关闭，仅用户开启后逐句朗读模型输出、文本本机合成不出网；file_ops/path_ops（sub_skills/file_ops）写盘 grant write、拒写删 skill 本体目录、复制/移动/删除须预览＋grant danger；learn.py 学习产物只入 knowledge/logic 链并联动做梦。
11. **链直读写·人在回路旁·做梦后台（2026-09-27 批17 用户指示）**：相信大模型——十一链首要目的是省 token，经验由模型经 chain 工具直接读写（涉既往先 recall、有价值结论即 append），脚本不代裁决；收口链（memory/knowledge/time/event）会话中缓冲、对话收口统一落盘（chain_timing.py）。决策岔路用 debate 正反双链自辩修正路径＋做梦错误自修＝**人多在回路旁、少部分在回路中**——仅高危节点（grant danger/云端下载/对外端口/ask_user）须人类确认。做梦跑在分离后台子进程（dream_bg.py·对话前台零占用），内容＝链整理＋记忆沉淀＋skill 修正（dream_fix）＋网络漫游拓扑经验入链（dream_roam·须 grant network·开关 dream.roam）。
