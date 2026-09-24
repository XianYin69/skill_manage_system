---
name: skill_manage_system
description: >
  技能操作系统（SMS）：只调取与管理技能及其副产物、本身不作答——读固定路径注册表，识别用户意图，按日期建会话五元组
  （对话/用户链/逻辑链/技能/权限），五 lane 并发拆分·整合与进程注册、权限门控，
  支持错误自愈、本地/云端安装、多客户端同步与信任链审查；并提供时区地区检查、
  正反双辩论逻辑链、命令系统（help/intent/show/use）、删除 skill 与子技能回主接口；创建/修改目标 skill 与子 skill 均委托 Skill_Generator；技能间依赖库 deps.json（关联 skill + 关联 python）；权限支持角色批量与 TTL 到期自动失效，敏感键 vault/verify 控凭据与验证协助；背景隐私采集默认关闭：须用户授权、每笔告知、类别留存到期清理，数据混淆/掩码/矩阵变换后仅存 SMS 固定目录。
license: MIT
metadata:
  category: meta
---

# skill_manage_system

使用 `skill_manage_system` skill 来完成用户请求。SMS 只调取·管理技能及其副产物，**本身不直接回答用户需求**——一切请求经 dispatch 派给托管 skill 执行、由 SMS 整合其结果作答；无匹配技能 → 委托 Skill_Generator 创建后执行；仍无可用技能则明确拒绝，禁止用模型自身知识代答。Agent 工具的技能操作系统：发现 → 打包 → 连接 → 拆分 → 并发调度 → 进程注册 → 权限门控 → 整合。

## 固定路径 SMS

- 解析顺序：env `SMS_HOME` → 用户配置 `<SMS_HOME>/config/config.json` 的 `sms_home` → 用户缓存目录（Windows `%LOCALAPPDATA%` · macOS `~/Library/Caches` · Linux `~/.cache`，缺省回退 `~/SMS`）→ 用户根目录；统一建 `SMS/`；用户配置固定存 `<SMS_HOME>/config/config.json`（`resolve_home.conf()` 首读自动从 skill 模板 [config/config.example.json](config/config.example.json) 播种，skill 本体目录只放模板）。

## 运行流程

1. 解析 SMS_HOME，读 `SMS/registry/register.json`（含信任标签）；[locality.py](scripts/locality.py) 检查时区/地区 → `registry/locality.json` 供会话读取。
2. 缺失 → 初始设置：[init_registry.py](scripts/init_registry.py) 跑 register → pack → connect → deps。
3. 识别意图（只产生路由/创建决策，不触发作答），[session.py](scripts/session.py) 建 `SMS/sessions/<日期>/` 五元组（dialogue/user_chain/logic_chain/skills/permissions）。
4. 数据写盘前先授权：`permissions.py grant write`（默认只读，未授予 emit 拒绝落盘）；可 `grant role secrets [分钟]` 批量+TTL 到期自动失效，`deny` 随时撤销；敏感键 vault/verify 由 dispatch 对 login-vault/captcha-assist 强制。
5. 拆分·整合（[task.py](scripts/task.py)）+ 五 lane 并发（[scheduler.py](scripts/scheduler.py)）+ 进程生命周期（[process.py](scripts/process.py)）。
6. 调度目标技能：[skill_executor](sub_skills/skill_executor/SKILL.md) 用 [dispatch.py](scripts/dispatch.py) 规划；每条 `return_to=sms`——子技能运行完回到 SMS 整合，不得直接回复用户；无匹配 → [bootstrap.py](scripts/bootstrap.py) 拉取 Skill_Generator（network+write），委托其创建目标 skill/子 skill；改已有 skill（含 SMS 自身与子 skill）→ 同样委托 Skill_Generator 修改路径。
7. 治理：按天缓存清理（[cache_cleanup.py](scripts/cache_cleanup.py)）；emit 会话写盘后自动压缩上下文（[auto_compress.py](scripts/auto_compress.py)）；背景隐私采集 [privacy.py](scripts/privacy.py)（`grant privacy` 用户授权才可采集，每笔写 NOTICE.md 告知，混淆/掩码/矩阵变换后存 `<SMS_HOME>/privacy/`，仅必要时凭理由解密）；类别策略 [privacy_cat.py](scripts/privacy_cat.py) list/report/purge（credential 默认仅留 1 天）。
8. 错误自愈：[skill_errors.py](scripts/skill_errors.py) 记录出错位置；未解决 ≥3 → 提示启用 Skill_Generator self_update 修复（经其修改路径），`resolve` 销账。
9. 安装：[install.py](scripts/install.py) 本地或 `gh:owner/repo[/sub]` 装入客户端 skills；云端需 network+write 且 `--accept-download` 用户确认下载，标 pending_review。
10. 同步与信任：[sync_skills.py](scripts/sync_skills.py) hub pull/push/status；[trust.py](scripts/trust.py) 云端必审、本地抽查，fail → quarantine。
11. 决策审查：[debate.py](scripts/debate.py) 对论断生成 pro/con 正反双链 + verdict → `sessions/<日期>/debate.json`。
12. 命令系统：[commands.py](scripts/commands.py) 汇总内置与暴露接口 → `registry/commands.json`，`help/intent/show/use` 查看与调用。
13. 删除：[remove.py](scripts/remove.py) `--yes --write` 从客户端/hub 移除 skill（默认预览，拒删受保护本体）。

## 子技能

- [skill_register](sub_skills/skill_register/SKILL.md) · [skill_packer](sub_skills/skill_packer/SKILL.md) · [skill_connector](sub_skills/skill_connector/SKILL.md) · [skill_scheduler](sub_skills/skill_scheduler/SKILL.md) · [skill_executor](sub_skills/skill_executor/SKILL.md)

## 数据契约与脚本

- schemas/：register · interfaces · connections · session · task · process · scheduler · dispatch · memory · trust · error · [locality](schemas/locality.schema.json) · [debate](schemas/debate.schema.json) · [commands](schemas/commands.schema.json) · [sandbox](schemas/sandbox.schema.json) · [privacy](schemas/privacy.schema.json) · [deps](schemas/deps.schema.json)
- [scripts/scripts.md](scripts/scripts.md)：resolve_home / sandbox / emit / bootstrap / register / pack / connect / deps / session / init_registry / task / process / permissions / privacy / privacy_cat / scheduler / dispatch / memory_list / cache_cleanup / auto_compress / trust / skill_errors / install / sync_skills / locality / debate / commands / remove

## 红线

- 不得删除 [resistance/](resistance/resistance.md) 约束；SMS 运行时数据与一切缓存文件（`__pycache__`/截图/tmp/日志/用户 config.json）不得写入任何 skill 目录；子 skill 未指定路径的新建目录必须经 [resolve_home.py](scripts/resolve_home.py) 分配到 `<SMS_HOME>/tmp/`，工程任务优先用 [sandbox.py](scripts/sandbox.py) 建 `<SMS_HOME>/tmp/sandbox/<id>`，并向子 skill 暴露该能力；子技能运行完必须回到 SMS；**SMS 本体不得直接回答用户需求**——一切经 dispatch 派托管 skill 执行、SMS 整合结果作答（无匹配→委托 Skill_Generator 创建后执行；仍不可得→明确拒绝，不得以模型自身知识代答）。
- 悬空链接 = 0；所有 .md / 脚本 ≤ 50 行；SKILL.md 含 YAML frontmatter。
- 数据写盘经 emit 门控（--write 才写）；云端下载须 network+write 且用户确认；删除须 --yes；隐私采集须用户授权（`grant privacy`）且每笔告知，解密须必要理由，隐私文件仅存 `<SMS_HOME>/privacy/`。
