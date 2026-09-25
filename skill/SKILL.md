---
name: skill_manage_system
description: >
  技能操作系统（SMS）：只调取与管理技能及其副产物、本身不作答——读固定路径注册表，识别用户意图，按日期建会话五元组＋十一链碎片（向量/频次/边 JSON）
  （对话/用户链/逻辑链/技能/权限；时间/事件/会话/调用skill/调用工具/子会话/代理对话/记忆/钉选），提示词拆分·简化·合并·压缩注入，每输入开新对话、做梦机制定期整理链与会话并触发 skill 迭代，五 lane 并发拆分·整合与进程注册、权限门控，
  支持错误自愈、本地/云端安装、多客户端同步与信任链审查；并提供时区地区检查、
  正反双辩论逻辑链、完全个性化指令系统（alias 定义指令格式，如 skill-update→迭代 skill）、sms-shell 交互壳（操作已装 agent 客户端、按指令部署到其他目录）、配置系统（API key·基础URL·各链启用修剪·做梦时间·模型参数 temperature/top_p）、上游模型 Token/上下文/RPM 自动抓取、本地加密网页壳（127.0.0.1 指纹证书＋配对 token）与对外端口（ML-DSA 指纹验签·默认关闭）、界面顶面不打扰 HUD（任务进行时提示）、删除 skill 与子技能回主接口；创建/修改目标 skill 与子 skill 均可委托 Skill_Generator（2026-09-24 起非强制）；技能间依赖库 deps.json（关联 skill + 关联 python）；权限支持角色批量与 TTL 到期自动失效，敏感键 vault/verify 控凭据与验证协助；背景隐私采集默认关闭：须用户授权、每笔告知、类别留存到期清理，数据混淆/掩码/矩阵变换后仅存 SMS 固定目录。
license: MIT
metadata:
  category: meta
---

# skill_manage_system

使用 `skill_manage_system` skill 来完成用户请求。SMS 只调取·管理技能及其副产物，**本身不直接回答用户需求**——一切请求经 dispatch 派给托管 skill 执行、由 SMS 整合其结果作答；无匹配技能 → 委托 Skill_Generator 创建后执行；仍无可用技能则明确拒绝，禁止用模型自身知识代答。Agent 工具的技能操作系统：发现 → 打包 → 连接 → 拆分 → 并发调度 → 进程注册 → 权限门控 → 整合。

## 固定路径 SMS

- 解析顺序：env `SMS_HOME` → 用户配置 `<SMS_HOME>/config/config.json` 的 `sms_home` → 用户缓存目录（Windows `%LOCALAPPDATA%` · macOS `~/Library/Caches` · Linux `~/.cache`，缺省回退 `~/SMS`）→ 用户根目录；统一建 `SMS/`；用户配置固定存 `<SMS_HOME>/config/config.json`（`resolve_home.conf()` 首读自动从 skill 模板 [config/config.example.json](config/config.example.json) 播种，skill 本体目录只放模板）。

## 运行流程

1. 初始化第一步先跑 `python -B skill/scripts/redlines.py check`（约束持久化机械断言：入口镜像关键句/≤50 行/零悬空链接，失败即停并报告、禁止绕过），再解析 SMS_HOME，读 `SMS/registry/register.json`（含信任标签）；[locality.py](scripts/locality.py) 检查时区/地区 → `registry/locality.json` 供会话读取。
2. 缺失 → 初始设置：[init_registry.py](scripts/init_registry.py) 跑 register → pack → connect → deps。
3. 识别意图（只产生路由/创建决策，不触发作答），[session.py](scripts/session.py) 建 `SMS/sessions/<日期>/` 五元组（dialogue/user_chain/logic_chain/skills/permissions），会话日/意图同步登记 `<SMS_HOME>/chains/` 十一链碎片（[chains.py](scripts/chains.py)·[chain_store.py](scripts/chain_store.py)，链数据必须 git 管理——[chains_git.py](scripts/chains_git.py) 自动建仓＋写入自动提交）。
4. 数据写盘前先授权：`permissions.py grant write`（默认只读，未授予 emit 拒绝落盘）；可 `grant role secrets [分钟]` 批量+TTL 到期自动失效，`deny` 随时撤销；敏感键 vault/verify 由 dispatch 对 login-vault/captcha-assist 强制。
5. 拆分·整合（[task.py](scripts/task.py)）+ 五 lane 并发（[scheduler.py](scripts/scheduler.py)）+ 进程生命周期（[process.py](scripts/process.py)）。
6. 调度目标技能：[skill_executor](sub_skills/skill_executor/SKILL.md) 用 [dispatch.py](scripts/dispatch.py) 规划；每条 `return_to=sms`——子技能运行完回到 SMS 整合，不得直接回复用户；调用链经 [chains.py](scripts/chains.py) `log skill|tool|sub` 登记（使用 agent 的 skill 必开新子会话并收口，红线 17）；无匹配 → [bootstrap.py](scripts/bootstrap.py) 拉取 Skill_Generator（network+write），委托其创建目标 skill/子 skill；改已有 skill（含 SMS 自身与子 skill）→ 同样委托 Skill_Generator 修改路径。
7. 治理：按天缓存清理（[cache_cleanup.py](scripts/cache_cleanup.py)）与 skill 目录缓存残留自净（[skill_cache.py](scripts/skill_cache.py)，误落入 skill 的 tmp/pyc 迁移或删除）；emit 会话写盘后自动压缩上下文（[auto_compress.py](scripts/auto_compress.py)）＋惰性做梦整理十一链与会话记录（[dream.py](scripts/dream.py)，间隔可配，入口 doctor 显示状态）；背景隐私采集 [privacy.py](scripts/privacy.py)（`grant privacy` 用户授权才可采集，每笔写 NOTICE.md 告知，混淆/掩码/矩阵变换后存 `<SMS_HOME>/privacy/`，仅必要时凭理由解密）；类别策略 [privacy_cat.py](scripts/privacy_cat.py) list/report/purge（credential 默认仅留 1 天）。
8. 错误自愈：[skill_errors.py](scripts/skill_errors.py) 记录出错位置；未解决 ≥3 → 提示启用 Skill_Generator self_update 修复（经其修改路径），`resolve` 销账。
9. 安装：[install.py](scripts/install.py) 本地或 `gh:owner/repo[/sub]` 装入客户端 skills；云端需 network+write 且 `--accept-download` 用户确认下载，标 pending_review。
10. 同步与信任：[sync_skills.py](scripts/sync_skills.py) hub pull/push/status；[trust.py](scripts/trust.py) 云端必审、本地抽查，fail → quarantine。
11. 决策审查：[debate.py](scripts/debate.py) 对论断生成 pro/con 正反双链 + verdict → `sessions/<日期>/debate.json`。
12. 命令系统：[commands.py](scripts/commands.py) 汇总内置/skill 接口/个性化指令 → `registry/commands.json`，`help/intent/show/use` 调用；个性化指令格式经 [user_commands.py](scripts/user_commands.py) `alias/unalias` 定义（`script:`调脚本、`delegate:`必回 SMS 派发、`say:`提示，`{arg}` 占位；如 skill-update→委托 Skill_Generator 迭代）；[shell.py](scripts/shell.py)（入口 [bin/sms-shell](../bin/sms-shell)）双前端（GUI/TUI）——任意话语默认经数据流交给原生网关或已安装 agent CLI 执行（[agent_stream.py](scripts/agent_stream.py)：config `llm_gateway` 启用则走 [gateway.py](scripts/gateway.py) OpenAI 兼容直连〔对话·工具·视觉〕，否则 claude/codex… 适配器可配，前置「使用 skill_manage_system 技能」指令，本体不作答），命中个性化指令自动展开（支持 `sms-skill init --Path … --NewFolder Yes --FolderName …` 式命名参数 token 透传），`:` 元指令治理（含 `:dream/:config/:web/:ext`，[shell_core.py](scripts/shell_core.py)；配置系统 [settings.py](scripts/settings.py) dot-path 读写·api_key 掩码·链设置·做梦时间·模型参数，[model_meta.py](scripts/model_meta.py) 自动抓上游模型 Token/上下文/RPM，本地加密网页壳 [web_shell.py](scripts/web_shell.py)（127.0.0.1＋指纹证书＋配对 token）与对外端口 [external.py](scripts/external.py)（默认关闭，ML-DSA 指纹验签·限速，resistance #18），发送前提示词四操作拆分/简化/合并/压缩（[prompt_pack.py](scripts/prompt_pack.py)），经 [deploy.py](scripts/deploy.py) 部署＝仅复制 bin 启动文件到用户指定路径（[bin/locate.py](../bin/locate.py) 相邻→SMS_SKILL→sms_skill 三级定位回源，禁止整包复制 skill），多格式 skill API＝[bin/sms_api.py](../bin/sms_api.py)＋[sms_formats.py](../bin/sms_formats.py)（sms-api formats/detect/show/validate/export：claude SKILL.md·claude-code·OpenAI 全系）；任务进行时 [hud.py](scripts/hud.py)+[hud_view.py](scripts/hud_view.py) 在界面顶面常显置顶·穿透·不抢焦点提示，任务结束 hide。
13. 删除：[remove.py](scripts/remove.py) `--yes --write` 从客户端/hub 移除 skill（默认预览，拒删受保护本体）。

## 子技能

- [skill_register](sub_skills/skill_register/SKILL.md) · [skill_packer](sub_skills/skill_packer/SKILL.md) · [skill_connector](sub_skills/skill_connector/SKILL.md) · [skill_scheduler](sub_skills/skill_scheduler/SKILL.md) · [skill_executor](sub_skills/skill_executor/SKILL.md)

## 数据契约与脚本

- schemas/：register · interfaces · connections · session · chains · task · process · scheduler · dispatch · memory · trust · error · [locality](schemas/locality.schema.json) · [debate](schemas/debate.schema.json) · [commands](schemas/commands.schema.json) · [sandbox](schemas/sandbox.schema.json) · [privacy](schemas/privacy.schema.json) · [deps](schemas/deps.schema.json) · [user_commands](schemas/user_commands.schema.json)
- [scripts/scripts.md](scripts/scripts.md)：resolve_home / sandbox / emit / bootstrap / register / pack / connect / deps / session / chain_store / chains / chains_git / prompt_pack / dream / init_registry / task / process / permissions / privacy / privacy_cat / scheduler / dispatch / memory_list / cache_cleanup / skill_cache / auto_compress / trust / skill_errors / install / sync_skills / locality / debate / commands / user_commands / shell / agent_stream / gateway / shell_core / shell_tui / shell_gui / settings / model_meta / web_certs / net_util / ext_net / web_shell / external / deploy / hud / hud_view / remove

## 红线

- 不得删除 [resistance/](resistance/resistance.md) 约束；SMS 运行时数据与一切缓存文件（`__pycache__`/截图/tmp/日志/用户 config.json）不得写入任何 skill 目录；子 skill 未指定路径的新建目录必须经 [resolve_home.py](scripts/resolve_home.py) 分配到 `<SMS_HOME>/tmp/`，工程任务优先用 [sandbox.py](scripts/sandbox.py) 建 `<SMS_HOME>/tmp/sandbox/<id>`，并向子 skill 暴露该能力；子技能运行完必须回到 SMS；**SMS 本体不得直接回答用户需求**——一切经 dispatch 派托管 skill 执行、SMS 整合结果作答（无匹配→委托 Skill_Generator 创建后执行；仍不可得→明确拒绝，不得以模型自身知识代答）。
- 悬空链接 = 0；所有 .md / 脚本 ≤ 50 行；SKILL.md 含 YAML frontmatter。
- 数据写盘经 emit 门控（--write 才写）；云端下载须 network+write 且用户确认；删除须 --yes 且 grant danger；隐私采集须用户授权（`grant privacy`）且每笔告知，解密须必要理由，隐私文件仅存 `<SMS_HOME>/privacy/`。**十一链记忆·对话隔离·做梦**（resistance #17）：碎片链存 `<SMS_HOME>/chains/`（向量/频次/边），所有链必须 git 管理（chains_git 自动 init＋防抖提交），每输入开新对话（压缩记忆＋当前输入），agent skill 必开新子会话并收口，提示词简短精准。**高危操作先询问**（resistance #16）：skill/SMS_HOME 外递归删除、向用户目录复制/覆盖写——必须先向用户预览并取得当轮明确同意，且 `permissions.py grant danger`（敏感键、不随角色批量、TTL 到期）。约束持久化：[AGENTS.md](AGENTS.md) 入口镜像＋redlines.py 机械断言（初始化与 git 提交前必跑）＋`seal` 基线；部署＝仅复制 bin 文件，创建/修改 skill 一律委托 Skill_Generator。**配置系统与网络壳**（resistance #18）：配置增改唯一经 [settings.py](scripts/settings.py)（api_key 恒掩码），网页壳 [web_shell.py](scripts/web_shell.py) 只绑 127.0.0.1＋指纹证书＋配对 token，对外端口 [external.py](scripts/external.py) 默认关闭——`enable --yes` 当轮确认＋enroll 指纹＋ML-DSA 挑战验签＋限速封禁，证书/密钥/token/信任表仅存 `<SMS_HOME>/shell/`。
