# resistance（约束库 / 兜底库）

SMS 不可逾越的规则、红线与降级策略。

## 应存什么

- 「必须 / 禁止」类约束；执行期触发兜底的条件与动作。

## 红线

1. 不得删除本目录及 [`../SKILL.md`](../SKILL.md) 中的约束条目。
2. SMS 运行时数据（`SMS/registry`、`SMS/sessions`）位于用户缓存/根目录，禁止写入 skill 本体目录。
3. 悬空链接必须为 0；所有 .md / 脚本 ≤ 50 行；SKILL.md 必须含 YAML frontmatter。
4. 子技能 SKILL.md 必须含 YAML frontmatter，可直接注入 agent 执行。
5. 数据写盘经 [`../scripts/emit.py`](../scripts/emit.py) 门控：默认预览；仅当 `--write` 且会话已授予 `write` 才落盘，否则拒绝。
6. 子技能运行完必须回到 SMS（`dispatch.return_to=sms`），禁止在子技能内直接结束或直接回复用户。
7. 通过网络下载子 skill 到目标 skill 目录须 network+write 且用户显式确认（`install.py --accept-download`），否则拒绝。
8. 删除 skill 须 [`../scripts/remove.py`](../scripts/remove.py) `--yes` 确认 + write 授权（默认预览）；禁止删除 SMS 本体与五个受保护子技能。
9. 决策审查须有正反双辩论链（[`../scripts/debate.py`](../scripts/debate.py) pro/con + verdict）；命令统一经 [`../scripts/commands.py`](../scripts/commands.py) help/intent/show/use 暴露；时区/地区读 [`../scripts/locality.py`](../scripts/locality.py)。

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

- `SMS_HOME` 未定义 → 回退缓存目录 → 再回退用户根目录（见 [`../scripts/resolve_home.py`](../scripts/resolve_home.py)）。
- `register.json` 缺失 → 进入初始设置（[`../scripts/init_registry.py`](../scripts/init_registry.py)），不接写盘。
- 无匹配技能 → 先由 [`../scripts/bootstrap.py`](../scripts/bootstrap.py) 查技能目录/配置，缺 Skill_Generator 则从 GitHub 拉取（需 network+write）；再委托新建。
- `--slots` 非法 → 回退为 lane 数；权限不足 → 默认拒绝并记 audit。