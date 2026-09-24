# resistance（约束库 / 兜底库）

SMS 不可逾越的规则、红线与降级策略。

## 应存什么

- 「必须 / 禁止」类约束；执行期触发兜底的条件与动作。

## 红线

1. 不得删除本目录及 [`../SKILL.md`](../SKILL.md) 中的约束条目。
2. SMS 运行时数据（`SMS/registry`、`SMS/sessions`、`SMS/config/config.json` 用户配置）位于用户缓存/根目录，禁止写入 skill 本体目录（skill 的 `config/` 只放模板 config.example.json，首读由 `resolve_home.conf()` 播种）；子 skill 未指定路径的新建目录必须经 `resolve_home.temp()` 落在 `<SMS_HOME>/tmp/`，并作为 SMS 对子 skill 开放的临时用户空间接口。
3. 悬空链接必须为 0；所有 .md / 脚本 ≤ 50 行；SKILL.md 必须含 YAML frontmatter。
4. 子技能 SKILL.md 必须含 YAML frontmatter，可直接注入 agent 执行。
5. 数据写盘经 [`../scripts/emit.py`](../scripts/emit.py) 门控：默认预览；仅当 `--write` 且会话已授予 `write` 才落盘，否则拒绝。
6. 子技能运行完必须回到 SMS（`dispatch.return_to=sms`），禁止在子技能内直接结束或直接回复用户。
7. 通过网络下载子 skill 到目标 skill 目录须 network+write 且用户显式确认（`install.py --accept-download`），否则拒绝。
8. 删除 skill 须 [`../scripts/remove.py`](../scripts/remove.py) `--yes` 确认 + write 授权（默认预览）；禁止删除 SMS 本体与五个受保护子技能。
9. 决策审查须有正反双辩论链（[`../scripts/debate.py`](../scripts/debate.py) pro/con + verdict）；命令统一经 [`../scripts/commands.py`](../scripts/commands.py) help/intent/show/use 暴露；时区/地区读 [`../scripts/locality.py`](../scripts/locality.py)。
10. 沙盒机制统一使用 [`../scripts/sandbox.py`](../scripts/sandbox.py)：未指定工作目录时建在 `<SMS_HOME>/tmp/sandbox/<id>`；交付须 `--yes --write` 且目标非空拒绝覆盖；清理须 `--yes`。
11. 背景隐私采集（[`../scripts/privacy.py`](../scripts/privacy.py)）默认关闭：采集前必须经用户授权（`grant privacy`）；每笔采集必须写入 `<SMS_HOME>/privacy/NOTICE.md` 告知用户采集了哪些隐私；数据落盘前必须做混淆+掩码+矩阵变换；仅必要时（`open` 附必要理由，须 privacy+write，记审计）方可解密读取；隐私文件禁止存于 `<SMS_HOME>/privacy/` 之外，禁止写入 skill 本体目录。
12. 权限扩展：`vault`（凭据明文取用）与 `verify`（人机验证协助）为敏感键，默认拒绝；角色批量 grant（readonly/worker/net/privacy/secrets/admin）与 TTL 分钟到期经 [`../scripts/permissions.py`](../scripts/permissions.py)；TTL 到期自动失效不可续，须重新授权；[`../scripts/dispatch.py`](../scripts/dispatch.py) 按 SKILL_REQ 强制 login-vault→vault、captcha-assist→verify，未授予拒绝派发。
13. 隐私类别策略（[`../scripts/privacy_cat.py`](../scripts/privacy_cat.py)）：identity/credential/behavior/content/biometric/contact/location 各配默认留存（credential 最严 1 天）；purge 默认预览、执行须 write；解密次数与类别计数经 report 可查，供用户审计。
14. 人机验证不可绕过：captcha-assist 技能只识别·等待·记录，其 resistance 优先于会话内任何指示——禁止以本 SMS 任何机制实现或代理求解验证码、对接打码平台、代收转发 OTP。

## 默认权限模型

- `read`（默认开）、`write`（默认关）、`execute`（默认关）、`network`（默认关）。
- 会话内按 `SMS/sessions/<日期>/permissions.json` 的 grants 逐项授予；每笔 grant/deny 记 audit。
- 写盘前须先 `permissions.py grant write`；未授予时 emit 拒绝落盘（--write 不替代授权）。

## 进程与并发

- 每实例一个 `pid`，状态仅限 spawn/run/suspend/resume/kill，写 `SMS/registry/processes.json`。
- 五 lane（understand/decompose/register/permit/integrate）并发槽 ≤ `--slots`，超限排队。
- 任务拆分·整合走 [`../scripts/task.py`](../scripts/task.py)；`merge` 回填 `task.json` 的 merged。

## 工具→权限映射（skill_executor）

- `read/glob/grep/semantic_search/skill/question/board_read` → `read`（默认开）
- `write/edit/memory_create_*` → `write`；`bash/task/agent_manager/background_process` → `execute`
- `websearch/webfetch/generate_image/board_post` → `network`
- 映射表在 [../scripts/dispatch.py](../scripts/dispatch.py)；未授予的工具调用必须拒绝并 audit。

## 降级策略

- `SMS_HOME` 未定义 → 读用户配置 `<SMS_HOME>/config/config.json` 的 `sms_home` → 回退缓存目录 → 再回退用户根目录（见 [`../scripts/resolve_home.py`](../scripts/resolve_home.py)）。
- `register.json` 缺失 → 进入初始设置（[`../scripts/init_registry.py`](../scripts/init_registry.py)），不接写盘。
- 无匹配技能 → 先由 [`../scripts/bootstrap.py`](../scripts/bootstrap.py) 查技能目录/配置，缺 Skill_Generator 则从 GitHub 拉取（需 network+write）；再委托新建。
- `--slots` 非法 → 回退为 lane 数；权限不足 → 默认拒绝并记 audit。