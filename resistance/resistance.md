# resistance（约束库 / 兜底库）

SMS 不可逾越的规则、红线与降级策略。

## 应存什么

- 「必须 / 禁止」类约束；执行期触发兜底的条件与动作。

## 红线

1. 不得删除本目录及 [`../SKILL.md`](../SKILL.md) 中的约束条目。
2. SMS 运行时数据（`SMS/registry`、`SMS/sessions`）位于用户缓存/根目录，禁止写入 skill 本体目录。
3. 悬空链接必须为 0；所有 .md / 脚本 ≤ 50 行；SKILL.md 必须含 YAML frontmatter。
4. 子技能 SKILL.md 必须含 YAML frontmatter，可直接注入 agent 执行。
5. 任何写盘脚本默认 `--dry-run`；`permissions.json` 未授予的写盘/执行/联网动作必须拒绝。

## 默认权限模型

- `read`（默认开）、`write`（默认关）、`execute`（默认关）、`network`（默认关）。
- 会话内按 `SMS/sessions/<日期>/permissions.json` 的 grants 逐项授予。

## 降级策略

- `SMS_HOME` 未定义 → 回退缓存目录 → 再回退用户根目录（见 [`../scripts/resolve_home.py`](../scripts/resolve_home.py)）。
- `register.json` 缺失 → 进入初始设置（[`../scripts/init_registry.py`](../scripts/init_registry.py)），不接写盘。
- 无匹配技能 → 委托 Skill_Generator 新建，完成后用 register 重新登记。