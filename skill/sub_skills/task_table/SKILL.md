---
name: task_table
description: >
  任务拆分与任务表制表器子技能：非通用回答的用户话语送网关前自动拆步建表
  （task_table.py·特定步骤经 skill_route 指定特定 skill），落 <SMS_HOME>/tasks/<id>.json
  供右栏任务表与顶栏进度条/剩余时间预测（latency 反应时间均值×未完成行预测）；
  模型每步完成经 task_plan 工具置行 done，中途发现表不合理同径 add/remove/skill 改表；
  单步且无执行性技能命中＝通用问答免表；建表开关 task.auto_table（F4）。
license: MIT
metadata:
  category: meta
  kind: sub_skill
---

# task_table — 任务拆分与任务表制表器

SMS 的**制表**子技能：把「该拆步骤、该派技能、该看进度」的诉求收拢为一张任务表（真源 `<SMS_HOME>/tasks/<id>.json`），执行仍由网关工具循环按表推进、由 SMS 整合收口。

## 何时建表 / 免表

- 建表：话语拆出多步，或命中执行性技能（route 非 general_answer/constraint_arbiter）。
- 免表：单步且仅命中通用回答/仲裁＝「经通用回答」路径，直接送托管作答口。
- 开关：`:config set task.auto_table false` 关自动制表（task_plan/手改仍可用）。

## 用法

```
python -B skill/scripts/task_table.py plan "<诉求>"        # 拆步建表（输出〔任务表〕块）
python -B skill/scripts/task_table.py show <表id>          # 看行与状态
python -B skill/scripts/task_table.py next <表id>          # 下一个未完成行
python -B skill/scripts/task_table.py eta <表id>           # 剩余时间预测
python -B skill/scripts/task_table.py status <表id> t2 done
python -B skill/scripts/task_table.py add <表id> "<补漏步骤目标>"   # 自动路由指定技能
python -B skill/scripts/task_table.py remove <表id> t3
python -B skill/scripts/task_table.py skill <表id> t2 <技能id>     # 壳内 :task <同参数> 手改
```

## 接线

- 建表口：[agent_stream.py](../../scripts/agent_stream.py) 原生网关分支 `attach()`＝话语前注入〔任务表〕块＋执行规则。
- 工具口：[agent_dispatch.py](../../scripts/agent_dispatch.py) `task_plan`（op/tid/row/value）→ [gateway.py](../../scripts/gateway.py) SYS「按表推进·改表不绕表」。
- 进度/预测：[msg_flow.py](../../scripts/msg_flow.py) task 信封 meta（done/total/eta_s）→ 顶栏 `shell_tui_index._taskbar` 进度条＋右栏 [shell_tui_tasks.py](../../scripts/shell_tui_tasks.py) 表；均值样本来自 [latency.py](../../scripts/latency.py)。
- task 工具（[agent_task.py](../../scripts/agent_task.py)）与本表同 schema 同库，命中多技能话语由 SMS 直接经其并行派发并建表。

## 红线

- 改表唯一经本制表器（add/remove/status/skill 均落同一真源并重发进度信封），模型与用户不得旁改 JSON。
- 拆步不越权：行只是「目标＋指定技能」，执行仍按各技能自身门禁（grant/预览/stop）。
- 悬空链接 = 0；本文件 ≤ 50 行；SKILL.md 含 YAML frontmatter。
