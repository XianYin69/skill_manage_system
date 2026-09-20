---
name: skill_manage_system
description: >
  技能操作系统（SMS）：读取固定路径注册表，识别用户意图，按日期建会话五元组
  （对话/用户链/逻辑链/技能/权限），调度 register/packer/connector，无技能时新建。
license: MIT
metadata:
  category: meta
---

# skill_manage_system

Agent 工具的技能操作系统（Skill Management System）。像 OS 调度进程一样调度技能：
发现 → 打包接口 → 连接上下文 → 调度执行 → 需要时新建技能。

## 固定路径 SMS

- 解析顺序：环境变量 `SMS_HOME` → 用户缓存目录 → 用户根目录；统一建 `SMS/`。
- Windows `%LOCALAPPDATA%` · macOS `~/Library/Caches` · Linux `~/.cache`（缺省回退 `~/SMS`）。
- 实现：[scripts/resolve_home.py](scripts/resolve_home.py)；覆盖见 [config/config.example.json](config/config.example.json)。

## 运行流程

1. 解析 SMS_HOME，读取 `SMS/registry/register.json`。
2. 缺失 → 初始设置：[scripts/init_registry.py](scripts/init_registry.py) 依次跑 register → packer → connector。
3. 存在 → 识别意图，[scripts/session.py](scripts/session.py) 建立 `SMS/sessions/<日期>/` 五元组
   （dialogue.md / user_chain.json / logic_chain.json / skills.json / permissions.json）。
4. 依据 register + interfaces + connections 调度目标技能（注入其 SKILL.md）。
5. 无匹配 → 委托 Skill_Generator 新建 → skill_register 重新登记。

## 子技能

- [skill_register](sub_skills/skill_register/SKILL.md)：安装位置与工具 → register.json
- [skill_packer](sub_skills/skill_packer/SKILL.md)：接口与用途 → interfaces.json
- [skill_connector](sub_skills/skill_connector/SKILL.md)：技能间上下文 → connections.json

## 数据契约与脚本

- [register.schema.json](schemas/register.schema.json) · [interfaces.schema.json](schemas/interfaces.schema.json) · [connections.schema.json](schemas/connections.schema.json) · [session.schema.json](schemas/session.schema.json)
- [scripts/scripts.md](scripts/scripts.md)：resolve_home / register / pack / connect / session / init_registry

## 红线

- 不得删除 [resistance/](resistance/resistance.md) 约束；SMS 运行时数据不进 skill 本体目录。
- 悬空链接 = 0；所有 .md / 脚本 ≤ 50 行；SKILL.md 含 YAML frontmatter。
- 调度前写 session 五元组；权限未授予的写盘/执行/联网动作默认拒绝（--dry-run 默认）。