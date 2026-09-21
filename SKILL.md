---
name: skill_manage_system
description: >
  技能操作系统（SMS）：读取固定路径注册表，识别用户意图，按日期建会话五元组
  （对话/用户链/逻辑链/技能/权限），五 lane 并发拆分·整合与进程注册、权限门控，
  并支持错误自愈、本地/云端安装、多客户端同步与信任链审查。
license: MIT
metadata:
  category: meta
---

# skill_manage_system

使用 `skill_manage_system` skill 来完成用户请求。Agent 工具的技能操作系统：发现 → 打包 → 连接 → 拆分 → 并发调度 → 进程注册 → 权限门控 → 整合。

## 固定路径 SMS

- 解析顺序：env `SMS_HOME` → 用户缓存目录（Windows `%LOCALAPPDATA%` · macOS `~/Library/Caches` · Linux `~/.cache`，缺省回退 `~/SMS`）→ 用户根目录；统一建 `SMS/`（实现 [scripts/resolve_home.py](scripts/resolve_home.py)，覆盖见 [config/config.example.json](config/config.example.json)）。

## 运行流程

1. 解析 SMS_HOME，读取 `SMS/registry/register.json`（每技能带信任标签）。
2. 缺失 → 初始设置：[scripts/init_registry.py](scripts/init_registry.py) 跑 register → pack → connect。
3. 识别意图，[scripts/session.py](scripts/session.py) 建 `SMS/sessions/<日期>/` 五元组（dialogue/user_chain/logic_chain/skills/permissions）。
4. 数据写盘前先授权：`permissions.py grant write`（默认只读，未授予 emit 拒绝落盘）。
5. 拆分·整合（[task.py](scripts/task.py)）+ 五 lane 并发（[scheduler.py](scripts/scheduler.py)：理解/拆分/注册/权限/整合）+ 进程生命周期（[process.py](scripts/process.py)：spawn/run/suspend/resume/kill）。
6. 调度目标技能：[skill_executor](sub_skills/skill_executor/SKILL.md) 用 [dispatch.py](scripts/dispatch.py) 规划调用（未授予权限与 quarantine/pending_review 标签拒绝）；无匹配 → [bootstrap.py](scripts/bootstrap.py) 拉取 Skill_Generator（network+write，拉取后标 pending_review 云端必审），委托新建。
7. 运行时治理：按天缓存清理（[cache_cleanup.py](scripts/cache_cleanup.py)，[memory_list.py](scripts/memory_list.py) 钉选保留）；emit 会话写盘后自动压缩上下文（[auto_compress.py](scripts/auto_compress.py)，归档 sha1 可回溯）。
8. 错误自愈：[skill_errors.py](scripts/skill_errors.py) 记录 skill 出错位置与日志；未解决 ≥3 处 → `due` 提示启用 Skill_Generator 的 self_update 修复，`resolve` 销账。
9. 技能安装：[install.py](scripts/install.py) 从本地目录或 `gh:owner/repo[/sub]` 装入目标客户端 skills 文件夹；云端需 network+write，一律标 pending_review。
10. 多客户端同步：[sync_skills.py](scripts/sync_skills.py) 以 `SMS/skills/` 为 hub pull/push/status（sha1 比对、冲突取新；未审/隔离不推送）。
11. 信任链：[trust.py](scripts/trust.py) 每 skill 一标签——云端必 `review pass/fail`，本地按日随机 `audit` 抽查，fail → quarantine。

## 子技能

- [skill_register](sub_skills/skill_register/SKILL.md)（位置+工具）· [skill_packer](sub_skills/skill_packer/SKILL.md)（接口+用途）
- [skill_connector](sub_skills/skill_connector/SKILL.md)（上下文）· [skill_scheduler](sub_skills/skill_scheduler/SKILL.md)（并发/整合）· [skill_executor](sub_skills/skill_executor/SKILL.md)（工具调度）

## 数据契约与脚本

- [register.schema.json](schemas/register.schema.json) · [interfaces.schema.json](schemas/interfaces.schema.json) · [connections.schema.json](schemas/connections.schema.json) · [session.schema.json](schemas/session.schema.json) · [task.schema.json](schemas/task.schema.json) · [process.schema.json](schemas/process.schema.json) · [scheduler.schema.json](schemas/scheduler.schema.json) · [dispatch.schema.json](schemas/dispatch.schema.json) · [memory.schema.json](schemas/memory.schema.json) · [trust.schema.json](schemas/trust.schema.json) · [error.schema.json](schemas/error.schema.json)
- [scripts/scripts.md](scripts/scripts.md)：resolve_home / emit / bootstrap / register / pack / connect / session / init_registry / task / process / permissions / scheduler / dispatch / memory_list / cache_cleanup / auto_compress / trust / skill_errors / install / sync_skills

## 红线

- 不得删除 [resistance/](resistance/resistance.md) 约束；SMS 运行时数据不进 skill 本体目录。
- 悬空链接 = 0；所有 .md / 脚本 ≤ 50 行；SKILL.md 含 YAML frontmatter。
- 调度前写 session 五元组 + 进程表；数据写盘经 emit 门控，未授予 write 拒绝（--write 才写）。
