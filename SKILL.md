---
name: skill_manage_system
description: >
  技能操作系统（SMS）：读取固定路径注册表，识别用户意图，按日期建会话五元组
  （对话/用户链/逻辑链/技能/权限），调度 register/packer/connector/scheduler，
  五 lane 并发拆分·整合任务、进程式注册与权限门控，无技能时委托新建。
license: MIT
metadata:
  category: meta
---

# skill_manage_system

Agent 工具的技能操作系统：发现 → 打包 → 连接 → 拆分 → 并发调度 → 进程注册 → 权限门控 → 整合。

## 固定路径 SMS

- 解析顺序：环境变量 `SMS_HOME` → 用户缓存目录 → 用户根目录；统一建 `SMS/`。
- Windows `%LOCALAPPDATA%` · macOS `~/Library/Caches` · Linux `~/.cache`（缺省回退 `~/SMS`）。
- 实现：[scripts/resolve_home.py](scripts/resolve_home.py)；覆盖见 [config/config.example.json](config/config.example.json)。

## 运行流程

1. 解析 SMS_HOME，读取 `SMS/registry/register.json`。
2. 缺失 → 初始设置：[scripts/init_registry.py](scripts/init_registry.py) 跑 register → pack → connect。
3. 识别意图，[scripts/session.py](scripts/session.py) 建 `SMS/sessions/<日期>/` 五元组（dialogue/user_chain/logic_chain/skills/permissions）。
4. 数据写盘前先授权：`permissions.py grant write`（默认只读，未授予 emit 拒绝落盘）。
5. 拆分·整合任务（[scripts/task.py](scripts/task.py)）+ 五 lane 并发（[scripts/scheduler.py](scripts/scheduler.py)：理解/拆分/注册/权限/整合）。
6. 进程式注册生命周期（[scripts/process.py](scripts/process.py)：spawn/run/suspend/resume/kill）。
7. 权限门控与写盘（[scripts/permissions.py](scripts/permissions.py)、[scripts/emit.py](scripts/emit.py)）。
8. 依据 register + interfaces + connections 调度目标技能，由 [skill_executor](sub_skills/skill_executor/SKILL.md) 用 [scripts/dispatch.py](scripts/dispatch.py) 规划与调用 agent 工具（未授予权限拒绝）。
9. 无匹配 → [scripts/bootstrap.py](scripts/bootstrap.py) 查技能目录/配置；缺 skill_generator 则从 GitHub 拉取（需 network+write），再委托新建。
10. 按天缓存清理与重要记忆列表（[scripts/cache_cleanup.py](scripts/cache_cleanup.py) 删超期日目录；[scripts/memory_list.py](scripts/memory_list.py) 钉选日期/路径不被清理）。

## 子技能

- [skill_register](sub_skills/skill_register/SKILL.md)（位置+工具）· [skill_packer](sub_skills/skill_packer/SKILL.md)（接口+用途）
- [skill_connector](sub_skills/skill_connector/SKILL.md)（上下文）· [skill_scheduler](sub_skills/skill_scheduler/SKILL.md)（并发/整合）· [skill_executor](sub_skills/skill_executor/SKILL.md)（工具调度）

## 数据契约与脚本

- [register.schema.json](schemas/register.schema.json) · [interfaces.schema.json](schemas/interfaces.schema.json) · [connections.schema.json](schemas/connections.schema.json) · [session.schema.json](schemas/session.schema.json) · [task.schema.json](schemas/task.schema.json) · [process.schema.json](schemas/process.schema.json) · [scheduler.schema.json](schemas/scheduler.schema.json) · [dispatch.schema.json](schemas/dispatch.schema.json) · [memory.schema.json](schemas/memory.schema.json)
- [scripts/scripts.md](scripts/scripts.md)：resolve_home / emit / bootstrap / register / pack / connect / session / init_registry / task / process / permissions / scheduler / dispatch / memory_list / cache_cleanup

## 红线

- 不得删除 [resistance/](resistance/resistance.md) 约束；SMS 运行时数据不进 skill 本体目录。
- 悬空链接 = 0；所有 .md / 脚本 ≤ 50 行；SKILL.md 含 YAML frontmatter。
- 调度前写 session 五元组 + 进程表；数据写盘经 emit 门控，未授予 write 拒绝（--write 才写）。