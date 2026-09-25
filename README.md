# skill_manage_system（SMS）— 独立智能体工具

技能操作系统的**独立智能体工具**（非客户端 skill 包）：以 `sms-shell` 为交互入口、`skill/scripts/` 为引擎，调度电脑上已安装的 agent CLI 与技能生态——本身不作答，一切用户请求经数据流派给已装 agent / 托管 skill 执行、由 SMS 整合结果作答（无匹配→委托 Skill_Generator 创建后执行，不可得→明确拒绝）。工具全部层集中于 `skill/`：skill 身份（SKILL.md/AGENTS.md/agent/ 四格式提示词）、`scripts/` 引擎、`schemas/` 契约、`config/` 模板、`resistance/` 红线、`sub_skills/` 子技能；根目录只留跨 OS 入口（sms.py/sms/sms.cmd）与部署包 `bin/`（sms-shell·sms-api 格式 API 启动文件），工具本体不依赖客户端发现机制。

## 结构

- 根 [`sms.py`](sms.py)＋[`sms`](sms)/[`sms.cmd`](sms.cmd)：跨 OS（Win/macOS/Linux）入口程序——**开箱即用**（建 SMS_HOME、播种配置、红线自检）→**依赖嗅探与修补**（PySide6/git/agent CLI，`--rebuild` 重建注册表、`--install-deps` 经同意装 PySide6）→**引导至 CLI**（交棒 sms-shell）；`sms.py doctor` 只诊断不启动。
- [`skill/`](skill/SKILL.md)：工具全部层——[SKILL.md](skill/SKILL.md)（YAML frontmatter 入口）、[AGENTS.md](skill/AGENTS.md)（入口红线镜像，redlines.py 机械断言）、[agent/](skill/agent/CLAUDE.md)（四格式提示词）、[scripts/](skill/scripts/scripts.md)（引擎，53 脚本 ≤50 行；十一链记忆体系见 [chains.md](skill/scripts/chains.md)）、[schemas/](skill/schemas/register.schema.json)（20 份 JSON 契约）、[config/](skill/config/config.example.json)（模板，真实 config 首读播种到 `<SMS_HOME>/config/`）、[resistance/](skill/resistance/resistance.md)（红线，不得删改）、[sub_skills/](skill/sub_skills/skill_register/SKILL.md)（五个子技能）。
- [`bin/`](bin/sms-shell)：交互入口部署包＝sms-shell(.cmd)＋[locate.py](bin/locate.py)（相邻→SMS_SKILL→sms_skill 三级定位回源）＋格式 API sms-api(.cmd)／[sms_api.py](bin/sms_api.py)／[sms_formats.py](bin/sms_formats.py)——claude SKILL.md 格式、claude-code（CLAUDE.md＋斜杠指令）、OpenAI 全系（Chat/Responses tools·Assistants·realtime/Codex）互转导出；部署＝仅把这些文件复制到指定路径，目标处直接运行。

## 快速开始

```bash
# 根入口（跨 OS）：三段齐走后进 sms-shell——进去就像对 agent 说话，话语经数据流交给已装 agent CLI（GUI=PySide6 窗口终端，探测失败自动回退 TUI）
python -B sms.py                        # 或 ./sms（POSIX）/ sms.cmd（Windows）；诊断：python -B sms.py doctor；部署后亦可用 <目标>/sms-shell(.cmd)
# 例：`查天气然后写报告` → 流式回显 agent 输出；`:agents` 看检测到的 CLI；`:use codex` 换；`:skill off` 关指令前缀
# 部署＝仅复制 bin 启动文件到指定路径（locate 回源定位，禁止整包复制工具本体）；sms-api＝多格式 skill 接口
python -B skill/scripts/deploy.py D:\agents --write
python -B bin/sms_api.py export <skill路径或id> --out <dir> --format all   # claude/claude-code/openai，默认预览，--write 落盘
# 治理命令流（可选）：建会话 → 授 write → 初始设置 → 拆分/调度/派发
python -B skill/scripts/session.py "查天气，然后写报告" --write
python -B skill/scripts/permissions.py grant write --write
python -B skill/scripts/init_registry.py --write
python -B skill/scripts/task.py "查天气，然后写报告" --write
python -B skill/scripts/scheduler.py "查天气，然后写报告" --slots 3 --write
python -B skill/scripts/process.py spawn skill_connector --write
python -B skill/scripts/bootstrap.py --write
python -B skill/scripts/dispatch.py --write
# 个性化指令（如 skill-update→委托 Skill_Generator 迭代）与任务进行时顶面 HUD
python -B skill/scripts/commands.py alias skill-update --desc="迭代指定 skill" --args=skill,需求 --step="script:session.py 迭代{skill}" --step="delegate:Skill_Generator 修改 {skill}：{需求}" --write
python -B skill/scripts/hud.py session "SMS 任务进行中"
# 十一链记忆：语句碎片（向量/频次/语义边，存 <SMS_HOME>/chains/）·压缩检索·做梦整理
python -B skill/scripts/chains.py user "偏好精简记忆"
python -B skill/scripts/prompt_pack.py pack "当前问题关键词"
python -B skill/scripts/dream.py run
# 配置系统与上游模型元数据：settings.py dot-path 读写 · model_meta.py refresh（Token/上下文/RPM→<SMS_HOME>/config/models.json）
python -B skill/scripts/settings.py status
# 加密网页壳（127.0.0.1 TLS 指纹证书＋配对 token）；对外端口默认关闭（ML-DSA 指纹验签）
python -B skill/scripts/web_shell.py start   # 或壳内 :web start；对外：:ext enable --yes → :ext start
```

## 固定路径 SMS

`SMS_HOME` 覆盖 → 用户配置 `<SMS_HOME>/config/config.json` → 用户缓存目录 → 用户根目录，统一建 `SMS/`；运行时数据与缓存一律不落工具目录。详见 [resolve_home.py](skill/scripts/resolve_home.py)。

## 红线摘要

- 不删 skill/resistance/ 约束；运行时数据（HUD 状态、个性化指令、部署登记）不进工具本体目录；隐私文件仅存 `<SMS_HOME>/privacy/`，采集须授权+告知，解密须必要理由；SMS 不直接作答用户需求，一律 dispatch→已装 agent/托管 skill→整合 链路。
- 悬空链接 = 0；所有 .md / 脚本 ≤ 50 行；skill/SKILL.md 含 YAML frontmatter，创建/修改目标 skill 与子 skill 均可委托 Skill_Generator（2026-09-24 起非强制）；写盘经 emit 门控：默认预览，`--write` 且已授予 write 才落盘；高危操作先询问 + `grant danger`（敏感键）；约束持久化＝[skill/AGENTS.md](skill/AGENTS.md) 镜像 + [skill/scripts/redlines.py](skill/scripts/redlines.py) 机械断言 + seal 基线（resistance #16）；部署＝仅复制 bin 文件到指定路径；网络面（resistance #18）：配置改动一律 settings.py（api_key 掩码），网页壳只绑 127.0.0.1＋指纹证书＋配对 token，对外端口默认关闭、`enable --yes` 当轮确认＋ML-DSA 指纹验签＋限速封禁。
