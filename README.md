# skill_manage_system（SMS）

Agent 工具的"技能操作系统"：本身不作答——一切用户请求经 dispatch 派给托管 skill 执行、由 SMS 整合结果作答（无匹配→委托 Skill_Generator 创建）；像 OS 调度进程一样发现、打包、连接、拆分、并发调度、进程注册并调度技能（子技能运行完回到 SMS），支持按天缓存清理、上下文自动压缩、本地/云端安装（下载须确认）、多客户端同步与信任链审查，创建目标 skill/子 skill 与修改（含 SMS 自身）均委托 Skill_Generator，并以依赖库 deps.json 记录各技能的关联 skill（depends/independent/related）与关联 python（import→pip 名→安装状态），权限支持角色批量与 TTL 到期、敏感键 vault/verify 门控凭据与验证协助技能，隐私采集按类别留存到期清理（privacy_cat），并暴露时区地区、正反双辩论、删除 skill、命令系统（help/intent/show/use）与完全个性化指令（alias 定义指令格式，如 skill-update→委托 Skill_Generator 迭代 skill）、sms-shell 双前端（有图形服务器→GUI 窗口，无→pwsh/bash/zsh 式 TUI；任意话语经数据流交给已装 agent CLI 执行、默认前置「使用 skill_manage_system 技能」指令，`:agents/:use/:skill` 治理，本体不作答；按指令部署到其他目录并生成可执行启动器）、界面顶面不打扰 HUD（置顶·穿透·不抢焦点，任务进行时提示）、背景隐私采集（须用户授权+每笔告知+混淆/掩码/矩阵变换）接口。

## 结构

- [`SKILL.md`](SKILL.md)：入口（YAML frontmatter，可直接注入 agent）。
- [`agent/`](agent/CLAUDE.md)：四格式提示词。
- [`sub_skills/`](sub_skills/skill_register/SKILL.md)：五个子技能（register / packer / connector / scheduler / executor）。
- [`scripts/`](scripts/scripts.md)：39 个 Python 脚本（英文名、均 ≤ 50 行，含 sandbox/privacy/deps/privacy_cat/skill_cache/user_commands/shell×4/agent_stream/deploy/hud）。
- [`bin/`](bin/sms-shell)：sms-shell 启动入口（Windows `.cmd` + POSIX 可执行 sh），相对自身定位；部署后其他路径直接执行，或 `deploy.py --launcher` 在目标根再生成一份。
- [`schemas/`](schemas/register.schema.json)：十八份 JSON 数据契约（含 sandbox/privacy/deps/user_commands）。
- [`config/`](config/config.example.json)：用户配置模板（真实 config.json 存 `<SMS_HOME>/config/`，首读自动播种）。
- [`resistance/`](resistance/resistance.md)：红线与降级策略。

## 快速开始

```bash
# 1) 建会话（播种只读 grants）
python scripts/session.py "查天气，然后写报告，最后发邮件" --write
# 2) 授予 write（数据写盘的前提，默认拒绝）
python scripts/permissions.py grant write --write
# 3) 初始设置（生成注册表 JSON）
python scripts/init_registry.py --write
# 拆分·整合 + 五 lane 并发调度（--slots 指定并发槽）
python scripts/task.py "查天气，然后写报告，最后发邮件" --write
python scripts/scheduler.py "查天气，然后写报告" --slots 3 --write
# 进程式注册 + 规划派发（未授权拒绝；无匹配先 bootstrap 拉 Skill_Generator，创建/修改均委托它）
python scripts/process.py spawn skill_connector --write
python scripts/bootstrap.py --write
python scripts/dispatch.py --write
# sms-shell：进去就像对 agent 说话——话语直接以数据流交给已装 agent CLI（默认前置 skill_manage_system 指令）
python -B scripts/shell.py            # GUI（有图形服务器）或 TUI；部署后任意路径跑 <目标>/sms-shell(.cmd)
# 例：`查天气然后写报告` → 流式回显 agent 输出；`:agents` 看检测到的 CLI；`:use codex` 换；`:skill off` 关指令前缀
# 个性化指令优先于数据流，支持命名参数透传：`sms-skill init --Path "C:\x" --NewFolder Yes --FolderName SMSH` → 展开为 deploy 执行
# 个性化指令：定义 skill-update（迭代 skill）→ 查看展开计划 → 任务进行时界面顶面 HUD 提示
python -B scripts/commands.py alias skill-update --desc="迭代指定 skill" --args=skill,需求 --step="script:session.py 迭代{skill}" --step="delegate:Skill_Generator 修改 {skill}：{需求}" --write
python -B scripts/commands.py intent "更新 sms"
python -B scripts/hud.py session "SMS 任务进行中"
python -B scripts/deploy.py D:\agents --launcher --skills all --write   # 目标根生成可执行 sms-shell，其他路径直接跑
```

## 固定路径 SMS

`SMS_HOME` 覆盖 → 用户缓存目录 → 用户根目录，统一建 `SMS/`。详见 [resolve_home.py](scripts/resolve_home.py)。

## 红线摘要

- 不删 resistance/ 约束；SMS 运行时数据（含 HUD 状态、个性化指令、部署缓存）不进 skill 本体目录；隐私文件仅存 `<SMS_HOME>/privacy/`，采集须授权+告知，解密须必要理由；SMS 不直接作答用户需求，一律 dispatch→托管 skill→整合 链路。
- 悬空链接 = 0；所有 .md / 脚本 ≤ 50 行；SKILL.md 含 YAML frontmatter；写盘经 emit 门控：默认预览，`--write` 且已授予 write 才落盘。