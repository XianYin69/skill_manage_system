# skill_manage_system（SMS）

Agent 工具的"技能操作系统"：像 OS 调度进程一样发现、打包、连接、拆分、并发调度、进程注册并调度技能。

## 结构

- [`SKILL.md`](SKILL.md)：入口（YAML frontmatter，可直接注入 agent）。
- [`agent/`](agent/CLAUDE.md)：四格式提示词。
- [`sub_skills/`](sub_skills/skill_register/SKILL.md)：四个子技能（register / packer / connector / scheduler）。
- [`scripts/`](scripts/scripts.md)：12 个 Python 脚本（英文名、均 ≤ 50 行）。
- [`schemas/`](schemas/register.schema.json)：七份 JSON 数据契约。
- [`config/`](config/config.example.json)：SMS 固定路径覆盖示例。
- [`resistance/`](resistance/resistance.md)：红线与降级策略。

## 快速开始

```bash
# 1) 建会话（播种只读 grants）
python scripts/session.py "查天气，然后写报告，最后发邮件" --write

# 2) 授予 write（数据写盘的前提，默认拒绝）
python scripts/permissions.py grant write --write

# 3) 初始设置（生成注册表 JSON）
python scripts/init_registry.py --write

# 拆分·理解·整合（默认预览；--write 且已授权才落盘）
python scripts/task.py "查天气，然后写报告，最后发邮件" --write

# 五 lane 并发调度（--slots 指定并发槽）
python scripts/scheduler.py "查天气，然后写报告" --slots 3 --write

# 进程式注册：spawn 一个进程
python scripts/process.py spawn skill_connector --write

# 无匹配技能时：查技能目录/配置，缺 Skill_Generator 则从 GitHub 拉取（需授权）
python scripts/bootstrap.py --write
```

## 固定路径 SMS

`SMS_HOME` 覆盖 → 用户缓存目录 → 用户根目录，统一建 `SMS/`。详见 [resolve_home.py](scripts/resolve_home.py)。

## 红线摘要

- 不删 resistance/ 约束；SMS 运行时数据不进 skill 本体目录。
- 悬空链接 = 0；所有 .md / 脚本 ≤ 50 行；SKILL.md 含 YAML frontmatter。
- 写盘经 emit 门控：默认预览，`--write` 且已授予 write 才落盘。