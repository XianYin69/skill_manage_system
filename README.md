# skill_manage_system（SMS）— 独立智能体工具

技能操作系统的**独立智能体工具**（非客户端 skill 包）：以 `sms-shell` 为交互入口、`scripts/` 为引擎，调度电脑上已安装的 agent CLI 与技能生态——本身不作答，一切用户请求经数据流派给已装 agent / 托管 skill 执行、由 SMS 整合结果作答（无匹配→委托 Skill_Generator 创建后执行，不可得→明确拒绝）。工具资产：`schemas/`（数据契约）、`config/`（配置模板）、`resistance/`（红线与兜底）；skill 身份层（SKILL.md/AGENTS.md/agent/ 提示词）存于 `skill/` 子目录，供注入任意 agent 客户端使用，工具本体不依赖客户端发现机制。

## 结构

- [`skill/`](skill/SKILL.md)：skill 身份层——[SKILL.md](skill/SKILL.md)（YAML frontmatter 入口）、[AGENTS.md](skill/AGENTS.md)（入口红线镜像，redlines.py 机械断言）、[agent/](skill/agent/CLAUDE.md)（四格式提示词）。
- [`scripts/`](scripts/scripts.md)：工具引擎，40 个 Python 脚本（英文名、均 ≤ 50 行，含 sandbox/privacy/deps/user_commands/shell×4/agent_stream/deploy/hud/redlines）。
- [`bin/`](bin/sms-shell)：交互入口部署包＝sms-shell(.cmd)＋[locate.py](bin/locate.py)（相邻→SMS_SKILL→sms_skill 三级定位回源）；部署＝仅把这些文件复制到指定路径，目标处直接运行。
- [`sub_skills/`](sub_skills/skill_register/SKILL.md)：五个子技能（register / packer / connector / scheduler / executor）。
- [`schemas/`](schemas/register.schema.json)：十八份 JSON 数据契约（含 sandbox/privacy/deps/user_commands）。
- [`config/`](config/config.example.json)：配置模板（真实 config.json 存 `<SMS_HOME>/config/`，首读自动播种）。
- [`resistance/`](resistance/resistance.md)：红线与降级策略（工具资产，不得删改）。

## 快速开始

```bash
# 交互入口：进去就像对 agent 说话——话语经数据流交给已装 agent CLI（GUI=PySide6 窗口终端，探测失败自动回退 TUI）
python -B scripts/shell.py            # 或部署后任意路径跑 <目标>/sms-shell(.cmd)
# 例：`查天气然后写报告` → 流式回显 agent 输出；`:agents` 看检测到的 CLI；`:use codex` 换；`:skill off` 关指令前缀
# 部署＝仅复制 bin 启动文件到指定路径（locate 回源定位，禁止整包复制工具本体）
python -B scripts/deploy.py D:\agents --write
# 治理命令流（可选）：建会话 → 授 write → 初始设置 → 拆分/调度/派发
python -B scripts/session.py "查天气，然后写报告" --write
python -B scripts/permissions.py grant write --write
python -B scripts/init_registry.py --write
python -B scripts/task.py "查天气，然后写报告" --write
python -B scripts/scheduler.py "查天气，然后写报告" --slots 3 --write
python -B scripts/process.py spawn skill_connector --write
python -B scripts/bootstrap.py --write
python -B scripts/dispatch.py --write
# 个性化指令（如 skill-update→委托 Skill_Generator 迭代）与任务进行时顶面 HUD
python -B scripts/commands.py alias skill-update --desc="迭代指定 skill" --args=skill,需求 --step="script:session.py 迭代{skill}" --step="delegate:Skill_Generator 修改 {skill}：{需求}" --write
python -B scripts/hud.py session "SMS 任务进行中"
```

## 固定路径 SMS

`SMS_HOME` 覆盖 → 用户配置 `<SMS_HOME>/config/config.json` → 用户缓存目录 → 用户根目录，统一建 `SMS/`；运行时数据与缓存一律不落工具目录。详见 [resolve_home.py](scripts/resolve_home.py)。

## 红线摘要

- 不删 resistance/ 约束；运行时数据（HUD 状态、个性化指令、部署登记）不进工具本体目录；隐私文件仅存 `<SMS_HOME>/privacy/`，采集须授权+告知，解密须必要理由；SMS 不直接作答用户需求，一律 dispatch→已装 agent/托管 skill→整合 链路。
- 悬空链接 = 0；所有 .md / 脚本 ≤ 50 行；skill/SKILL.md 含 YAML frontmatter，创建/修改目标 skill 与子 skill 均委托 Skill_Generator；写盘经 emit 门控：默认预览，`--write` 且已授予 write 才落盘；高危操作先询问 + `grant danger`（敏感键）；约束持久化＝[skill/AGENTS.md](skill/AGENTS.md) 镜像 + [scripts/redlines.py](scripts/redlines.py) 机械断言 + seal 基线（resistance #16）；部署＝仅复制 bin 文件到指定路径。
