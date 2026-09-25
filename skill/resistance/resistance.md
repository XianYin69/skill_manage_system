# resistance（约束库 / 兜底库）

## 应存什么

- 「必须 / 禁止」类约束；执行期触发兜底的条件与动作。

## 红线

1. 不得删除本目录及 [`../SKILL.md`](../SKILL.md) 中的约束条目。
2. SMS 运行时数据（`SMS/registry`、`SMS/sessions`、`SMS/config/config.json` 用户配置）位于用户缓存/根目录，禁止写入 skill 本体目录（skill 的 `config/` 只放模板 config.example.json，首读由 `resolve_home.conf()` 播种）；子 skill 未指定路径的新建目录必须经 `resolve_home.temp()` 落在 `<SMS_HOME>/tmp/`，并作为 SMS 对子 skill 开放的临时用户空间接口。
3. 悬空链接必须为 0；所有 .md / 脚本 ≤ 50 行；SKILL.md 必须含 YAML frontmatter。
4. 子技能 SKILL.md 必须含 YAML frontmatter，可直接注入 agent 执行。
5. 数据写盘经 [`../scripts/emit.py`](../scripts/emit.py) 门控：默认预览；仅当 `--write` 且会话已授予 `write` 才落盘，否则拒绝。
6. 子技能运行完必须回到 SMS（`dispatch.return_to=sms`），禁止在子技能内直接结束或直接回复用户；SMS 本体同理**不得直接回答用户需求**——只做调取·管理·整合，一切作答来自托管 skill 执行结果（无匹配→委托 Skill_Generator 创建后执行；不可得→拒绝并说明）。
7. 通过网络下载子 skill 到目标 skill 目录须 network+write 且用户显式确认（`install.py --accept-download`），否则拒绝。
8. 删除 skill 须 [`../scripts/remove.py`](../scripts/remove.py) `--yes` 确认 + write 授权（默认预览）；禁止删除 SMS 本体与五个受保护子技能。
9. 决策审查须有正反双辩论链（[`../scripts/debate.py`](../scripts/debate.py) pro/con + verdict）；命令统一经 [`../scripts/commands.py`](../scripts/commands.py) help/intent/show/use 暴露；时区/地区读 [`../scripts/locality.py`](../scripts/locality.py)。
10. 沙盒机制统一使用 [`../scripts/sandbox.py`](../scripts/sandbox.py)：未指定工作目录时建在 `<SMS_HOME>/tmp/sandbox/<id>`；交付须 `--yes --write` 且目标非空拒绝覆盖；清理须 `--yes`。
11. 背景隐私采集（[`../scripts/privacy.py`](../scripts/privacy.py)）默认关闭：采集前必须经用户授权（`grant privacy`）；每笔采集必须写入 `<SMS_HOME>/privacy/NOTICE.md` 告知用户采集了哪些隐私；数据落盘前必须做混淆+掩码+矩阵变换；仅必要时（`open` 附必要理由，须 privacy+write，记审计）方可解密读取；隐私文件禁止存于 `<SMS_HOME>/privacy/` 之外，禁止写入 skill 本体目录。
12. 权限扩展：`vault`（凭据明文取用）与 `verify`（人机验证协助）为敏感键，默认拒绝；角色批量 grant（readonly/worker/net/privacy/secrets/admin）与 TTL 分钟到期经 [`../scripts/permissions.py`](../scripts/permissions.py)；TTL 到期自动失效不可续，须重新授权；[`../scripts/dispatch.py`](../scripts/dispatch.py) 按 SKILL_REQ 强制 login-vault→vault、captcha-assist→verify，未授予拒绝派发。
13. 隐私类别策略（[`../scripts/privacy_cat.py`](../scripts/privacy_cat.py)）：identity/credential/behavior/content/biometric/contact/location 各配默认留存（credential 最严 1 天）；purge 默认预览、执行须 write；解密次数与类别计数经 report 可查，供用户审计。
14. 人机验证不可绕过：captcha-assist 技能只识别·等待·记录，其 resistance 优先于会话内任何指示——禁止以本 SMS 任何机制实现或代理求解验证码、对接打码平台、代收转发 OTP。
15. 个性化指令·交互壳·HUD·部署：指令文档只存 `<SMS_HOME>/commands/user_commands.json`（[../scripts/user_commands.py](../scripts/user_commands.py) add/rm/expand/run），`delegate:` 步骤必须回 SMS 经 dispatch 派托管 skill 执行（同红线 6，禁止以模型知识代答）；[../scripts/shell.py](../scripts/shell.py)（sms-shell）与指令系统仅转调既有 SMS 脚本，不得绕过权限门控；sms-shell 双前端——GUI（[../scripts/shell_gui.py](../scripts/shell_gui.py)）启动前必须探测图形服务器可用性，无或探测失败必须回退 TUI（[../scripts/shell_tui.py](../scripts/shell_tui.py)，免图形服务器），禁止在无显示环境抛图形异常中断；HUD（[../scripts/hud.py](../scripts/hud.py)/[../scripts/hud_view.py](../scripts/hud_view.py)）状态只存 `<SMS_HOME>/hud/`，仅在任务进行时显示、置顶·点击穿透·不抢焦点、空行自动隐藏空闲自退，禁止常驻遮挡用户；[../scripts/deploy.py](../scripts/deploy.py) 部署＝仅把 bin 启动文件复制到用户指定路径（见 16），默认预览，执行须 `--write` 且已授予 write；sms-shell 默认链路＝把用户话语经数据流交给已安装 agent CLI（[../scripts/agent_stream.py](../scripts/agent_stream.py)，前置「使用 skill_manage_system 技能」指令，`:skill off` 仅可关前缀不可关拒绝逻辑），shell/引擎本体不得作答，未检出 CLI 必须拒绝并引导配置而非代答，agent 选择与前缀状态只存 `<SMS_HOME>/shell/`。
16. 约束持久化与高危门禁（2026-09-24 事故后立）：代理只作调度器与管理器——识别意图、派发、整合，实现·写码·执行一律委托托管 skill（同红线 6）；创建/修改任何 skill（含 SMS 自身与子 skill）必须走 Skill_Generator 修改路径，禁止本体直接改。高危操作（skill 与 `<SMS_HOME>` 之外的递归删除、向用户目录复制/覆盖写）必须先询问用户、展示预览、取得当轮明确同意，且 [../scripts/permissions.py](../scripts/permissions.py) `grant danger`（敏感键：默认拒绝、不随角色批量、TTL 到期），无 grant 拒绝执行、禁止盲命令。部署＝仅把 [../bin/](../../bin/sms-shell) 启动文件复制到用户指定路径（[../scripts/deploy.py](../scripts/deploy.py) 登记 sms_skill，[../bin/locate.py](../../bin/locate.py) 回源定位），禁止整包复制 skill 本体。持久化三层：[../AGENTS.md](../AGENTS.md) 入口镜像（每会话注入）＋ [../scripts/redlines.py](../scripts/redlines.py) `check` 机械断言（关键句丢失/超 50 行/悬空链接→exit 1，初始化第一步与每轮 git 提交前必跑，失败禁止继续、不得绕过）＋用户确认后 `seal` 重钉基线。

17. 记忆链·对话隔离·做梦（2026-09-24 扩展，红线不得移除）：十一链（user/memory/logic/time/event/session/skill_call/tool_call/subsession/dialogue/knowledge 钉选）碎片一律存 `<SMS_HOME>/chains/<链>/<id>.json`，碎片＝语句化·最小化 JSON（含向量＝64 维哈希投影语句指向、频次＝使用计数、边＝语义/时间/因果/引用关系，树形·神经网络型），契约 [../schemas/chains.schema.json](../schemas/chains.schema.json)，禁止写入 skill 本体目录；发送大模型的提示词经 [../scripts/prompt_pack.py](../scripts/prompt_pack.py) 四操作 split 拆分/simplify 简化/merge 合并/pack 压缩检索（向量余弦＋频次），注入记忆块＝压缩记忆＋当前输入、必须简短精准、禁止整段历史直灌。对话隔离双层：sms-shell 每次用户输入＝新开一次对话（[../scripts/agent_stream.py](../scripts/agent_stream.py) 进程级一次性调用＋[../scripts/chains.py](../scripts/chains.py) conversation 压缩前缀，输出结束即收口记录会话链）；凡使用 agent 的 skill 必须自开新子会话、完成后立即关闭（`chains.py log sub`＋会话链/子会话链记录，[../scripts/dream.py](../scripts/dream.py) 审计悬挂对话→`chains/violations.md`）。做梦机制惰性触发：根入口 sms.py/emit/agent_stream 调 [../scripts/dream.py](../scripts/dream.py) `maybe`（间隔 config `dream_interval_min` 默认 360 分钟，入口 `doctor` 显示状态）——自动跨链合并近义碎片、修剪陈旧低频（knowledge 除外）、重建 `chains/retrieval.md`、高频 knowledge 同步 memory.json 钉选、skill_errors≥3 记升级事件（经 user_commands skill-update→Skill_Generator 修改路径迭代）、做梦事件入 event 链。所有链必须 git 管理（2026-09-25 用户红线）：[../scripts/chains_git.py](../scripts/chains_git.py) 首次触链自动 git init `<SMS_HOME>/chains` 导入既有全部链、之后链写入防抖自动 commit（进程退出兜底），git 缺失静默降级，手动 `python chains_git.py status|log [n]`。
18. 配置系统与网络壳（2026-09-25 立）：用户配置增改唯一入口 [../scripts/settings.py](../scripts/settings.py)（dot-path；DEFAULTS=[../config/settings.default.json](../config/settings.default.json) 深合并保旧配置兼容；api_key 恒掩码只写不读；每次变更记 event 链，契约 [../schemas/settings.schema.json](../schemas/settings.schema.json)）；[../scripts/model_meta.py](../scripts/model_meta.py) 自动从上游抓取模型 Token/上下文/RPM 只写 `<SMS_HOME>/config/models.json`，上游缺字段以 defaults 兜底并标 source，禁止伪标 upstream；[../scripts/web_shell.py](../scripts/web_shell.py) 本地加密网页壳——只绑 127.0.0.1（TLS 自签指纹证书 [../scripts/web_certs.py](../scripts/web_certs.py)、配对 token 常时比较、Host 防重绑定，页面 [../scripts/web_page.html](../scripts/web_page.html)，公共件 [../scripts/net_util.py](../scripts/net_util.py)），对外开关经壳面须 confirm=yes；[../scripts/external.py](../scripts/external.py) 对外端口默认关闭——`enable --yes` 用户当轮确认（同 #16）才置位，外部请求须本地 enroll 公钥指纹＋[../scripts/ext_net.py](../scripts/ext_net.py) ML-DSA-65（FIPS 204，退回 ed25519 须明示；pq_mode=strict 无 PQ 拒启）nonce 挑战验签后方可 Bearer 调 /api/chat，不开配置写·密钥面，失败限速封禁并记 event 链；跨网优先 SSH 隧道＋指纹钉选；证书/私钥/token/信任表仅存 `<SMS_HOME>/shell/`，禁止写入 skill 本体目录。
19. firefox lite 内核·TTS·学习·基本操作（2026-09-25 用户要求新增）：[../scripts/ff_lite.py](../scripts/ff_lite.py) 搜索/取页/下载一律须 `grant network`（默认拒绝），下载只落 `<SMS_HOME>/downloads/`·限尺寸、覆盖须 `--force` 且 `grant danger`（同 #16），渲染内核缺失明确回退报错、绝不自动装依赖；[../scripts/tts.py](../scripts/tts.py) 阿林娜（alina）机械女声默认关闭——仅用户 `:tts on`/配置开启后逐句朗读模型输出，文本本机 SAPI5 合成不出网；[../sub_skills/file_ops/](../sub_skills/file_ops/SKILL.md)（[file_ops.py](../scripts/file_ops.py)/[path_ops.py](../scripts/path_ops.py)）写盘须 `grant write`、拒绝写删 skill 本体目录、复制/移动/删除预览＋`grant danger`；[../scripts/learn.py](../scripts/learn.py) 学习产物只入 knowledge/logic 链并联动做梦（#17），网页蒸馏经 ff_lite 内核受同一 network 门控。
## 默认权限模型

- `read`（默认开）、`write`（默认关）、`execute`（默认关）、`network`（默认关）。
- 会话内按 `SMS/sessions/<日期>/permissions.json` 的 grants 逐项授予；每笔 grant/deny 记 audit；danger 为高危敏感键，须用户当轮确认后单独 grant（不随角色批量，同 #16）；写盘前须先 `permissions.py grant write`，未授予时 emit 拒绝落盘（--write 不替代授权）。

## 进程与并发

- 每实例一个 `pid`，状态仅限 spawn/run/suspend/resume/kill，写 `SMS/registry/processes.json`。
- 五 lane（understand/decompose/register/permit/integrate）并发槽 ≤ `--slots`，超限排队。
- 任务拆分·整合走 [`../scripts/task.py`](../scripts/task.py)；`merge` 回填 `task.json` 的 merged。

## 工具→权限映射（skill_executor）

- `read/glob/grep/semantic_search/skill/question/board_read` → `read`（默认开）
- `write/edit/memory_create_*` → `write`；`bash/task/agent_manager/background_process` → `execute`；`websearch/webfetch/generate_image/board_post` → `network`
- 映射表在 [../scripts/dispatch.py](../scripts/dispatch.py)；未授予的工具调用必须拒绝并 audit。

## 降级策略

- `SMS_HOME` 未定义 → 读用户配置 `<SMS_HOME>/config/config.json` 的 `sms_home` → 回退缓存目录 → 再回退用户根目录（见 [`../scripts/resolve_home.py`](../scripts/resolve_home.py)）。
- `register.json` 缺失 → 进入初始设置（[`../scripts/init_registry.py`](../scripts/init_registry.py)），不接写盘。
- 无匹配技能 → 先由 [`../scripts/bootstrap.py`](../scripts/bootstrap.py) 查技能目录/配置，缺 Skill_Generator 则从 GitHub 拉取（需 network+write）；再委托新建。`--slots` 非法 → 回退为 lane 数；权限不足 → 默认拒绝并记 audit。