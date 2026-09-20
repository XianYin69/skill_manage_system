# skill_manage_system（SMS）

Agent 工具的"技能操作系统"：像 OS 调度进程一样发现、打包、连接并调度技能。

## 结构

- [`SKILL.md`](SKILL.md)：入口（YAML frontmatter，可直接注入 agent）。
- [`agent/`](agent/CLAUDE.md)：四格式提示词（CLAUDE.md / .cursorrules / instructions.md / agent_prompt.md）。
- [`sub_skills/`](sub_skills/skill_register/SKILL.md)：三个子技能（register / packer / connector）。
- [`scripts/`](scripts/scripts.md)：6 个 Python 脚本（英文名、均 ≤ 50 行）。
- [`schemas/`](schemas/register.schema.json)：四份 JSON 数据契约。
- [`config/`](config/config.example.json)：SMS 固定路径覆盖示例。
- [`resistance/`](resistance/resistance.md)：红线与降级策略。

## 快速开始

```bash
# 初始设置（生成三份注册表 JSON）
python scripts/init_registry.py --write 2>/dev/null || python scripts/init_registry.py

# 识别意图后建立今日会话目录
python scripts/session.py "你的意图"

# 干跑预览（不写盘）
python scripts/register.py --dry-run
python scripts/pack.py --dry-run
python scripts/connect.py --dry-run
```

## 固定路径 SMS

`SMS_HOME` 覆盖 → 用户缓存目录 → 用户根目录，统一建 `SMS/`。详见 [resolve_home.py](scripts/resolve_home.py)。

## 红线摘要

- 不删 resistance/ 约束；SMS 运行时数据不进 skill 本体目录。
- 悬空链接 = 0（`python ../Skill_Generator/scripts/check-links.py` 类校验）；所有 .md / 脚本 ≤ 50 行。
- 写盘动作默认 `--dry-run`，权限未授予拒绝执行。