---
name: task_table
description: >
  任务拆分与任务表制表器子技能：脚本标点粗分作「自动种子」——仅复杂任务（拆步≥2且至少一步命中执行性技能）送网关前自动建种子表（task_table.py·行数无上限·模型首轮据实改表），落 <SMS_HOME>/tasks/<id>.json 供右栏任务表与顶栏进度条/剩余时间预测；
  模型每步完成经 task_plan 置行 done，中途 add/remove/skill 改表；批18 主流程守卫 pending(conv)＝有未完成行禁止收口并注入续推（批23 收口＝形式停止非实质完成·每派发自开独立 conv）；批22 模型裁量：脚本判简单仍注入〔任务表·脚本未建〕，判多步即 op=plan 自建表·用户无须写「制表」；
  批29 子步骤并行真可用（task_res.py）：行资源声明 files=/dir=/reads=/port=/device=/skill= ＋冲突判定（写写·写读互斥，只读可共享，端口/设备恒互斥）＋ op=conflict 回传「哪几行可并发、哪几行必须串行」＋ op=run 把互不冲突的行组成并发批次执行（并行度上限·行级独立超时·失败隔离写 error 链）＋ eta 改「批内最大值求和」；开关 task.auto_table/auto_continue/batch_parallel/row_timeout/conflict_read_write/conflict_skill/eta_parallel/stale_min；批30 行状态自动回写：skill/task 派发返回即 auto_done 置行（漏 status 不再卡守卫），收口前 reconcile 按 result/写资源落盘补标，pending() 自愈 stale_requeue（running 超 task.stale_min 默认 30min 降级回 pending 移尾）。
license: MIT
metadata:
  category: meta
  kind: sub_skill
---

# task_table — 任务拆分与任务表制表器

使用 `task_table` skill 来完成用户请求。SMS 的**制表**子技能：把「该拆步骤、该派技能、该看进度、该并行」的诉求收拢为一张任务表（真源 `<SMS_HOME>/tasks/<id>.json`），执行仍由网关工具循环按表推进、由 SMS 整合收口。

## 何时建表 / 免表
- 自动种子表（＝脚本判复杂·批14「不是什么都建表」）：标点拆步≥2 **且**至少一步命中执行性技能（route 非 general_answer/constraint_arbiter）。
- 脚本判简单＝不建表但注入〔任务表·脚本未建〕一行——复杂与否由模型判，**用户无须写「制表」字样**；判多步动手即 `task_plan op=plan value=步骤逗号分隔`（或 `task_table.py new "<步骤>"`）自建表；纯问答/单步免表直送。
- 开关：`:config set task.auto_table false` 关自动制表（task_plan/手改仍可用）。

## 子步骤并行（批29·每轮照做）
- **声明资源**：建行/改行时在目标里写 `files=a.py,b.md`｜`dir=build`｜`reads=x.json`｜`port=8080`｜`device=mouse`｜`skill=xxx`（逗号分隔多个）；不声明则脚本按 goal 自动抽路径与端口判冲突。
- **判冲突**：同一资源被两行**写**占用＝冲突；写＋读同一资源＝冲突（`task.conflict_read_write false` 放行读写并发）；**只读可共享**；端口/设备/交互会话＝恒互斥；同技能默认不冲突（`task.conflict_skill true` 收紧）。
- **取分组**：`task_plan op=conflict <表id>`（value=all＝连其他在途表一起判·多任务之间的并行）→ 回「批N〔可并发…〕＋串行依据＋结论」：同批行一次并发、批间依序。
- **执行与预测**：`task_plan op=run <表id>` 一次跑完互不冲突的行（批内≤`task.batch_parallel` 默认 3·每行独立超时 `task.row_timeout` 秒（0＝不限）·失败隔离＝异常/超时只标该行并写 error 链），或继续用 `task` 工具 parallel=true 派发；顶栏剩余时间＝各批「批内最大值」求和（`task.eta_parallel false` 退回逐行累加旧口径）。

## 用法
```
python -B skill/scripts/task_table.py new "<步骤1，步骤2…>"   # 模型裁量自建表（批22·免标点门控）
python -B skill/scripts/task_table.py plan "<诉求>" | show <表id> | next <表id> | eta <表id>
python -B skill/scripts/task_table.py conflict <表id> [all]   # 哪几行可并发、哪几行必须串行
python -B skill/scripts/task_table.py run <表id>              # 互不冲突的行组成并发批次执行
python -B skill/scripts/task_table.py res <表id> t2 "files=a.py,dir=build"   # 给行声明资源
python -B skill/scripts/task_table.py status <表id> t2 done | add <表id> "<目标>" | remove <表id> t3 | skill <表id> t2 <技能id> | lane <表id> t3 bg | stale [分钟] | reconcile [conv]
```

## 行状态自动回写与对账（批30-33）
- **派发/自办即回写**：`auto_done` 由 [agent_dispatch.py](../../scripts/agent_dispatch.py) 的 skill 与 task 两条路径在返回后调用，成功判据＝`task_table.dispatch_ok(result)`（空输出/无输出占位串≠成功）；未 done 行中「行 skill 同名」优先、goal 匹配次之，命中→`done`＋`result[:600]`＋`auto="skill"`，判假→`error`；只动本对话的表（`_mine`＝表 conv 为空或等于当前 conv），他对话表一律拒写并 log 一笔；`task_plan status` 传乱值→回「合法集合 pending/running/done/error/stopped」且**不改该行状态**（批33 缺陷D：旧版把乱值当 done＝误标完成）。
- **收口对账补标**：`reconcile` 挂 [agent_stream.py](../../scripts/agent_stream.py) 收口 `finally`（`chains.record("session","close:")` 之前），判据＝行 `result` 非空 **或** 行写资源（`w:`/`d:`）本轮新落盘（存在且 mtime ≥ 表 `created`）→ 补 `done`＋`auto="reconcile"`；不满足保留不动（宁缺勿滥，免把没做的行标成完成）。
- **陈旧行降级重排**：`stale_requeue` 按**行级** `started_at`（置 running 时写入；旧表无此字段才回落表 mtime）算活动度，超 `task.stale_min`（默认 30 分钟）即 `running`→`pending`、移到表尾、记 error/logic 链；`pending()` 每 60 秒顺带自愈一次，手查 CLI `python -B skill/scripts/task_table.py stale [分钟]`。

## 接线
- 建表口：[agent_stream.py](../../scripts/agent_stream.py) `attach()`＝话语前注入〔任务表〕块＋执行规则（含并行范式）；守卫：[gateway.py](../../scripts/gateway.py) 经 `tt.pending(conv)` 检测未完成行（`task.auto_continue`/`task.max_continue` 控）。
- 工具口：[agent_dispatch.py](../../scripts/agent_dispatch.py) `task_plan`（op=plan/new/show/next/eta/conflict/run/res/add/remove/status/skill/lane）；并行执行：[agent_task.py](../../scripts/agent_task.py) `_row_fn`/`run_table`；自动回写挂点：agent_dispatch skill/task 分支返回后 `tt.auto_done`、agent_stream 收口 `close:` 前 `tt.reconcile`、`pending()` 开头 `tt.stale_requeue` 自愈。
- 冲突与批次：[task_res.py](../../scripts/task_res.py)（资源抽取·conflicts/batches/batch_eta·run_rows 行级超时与失败隔离）；进度/预测：[msg_flow.py](../../scripts/msg_flow.py) task 信封 meta → 顶栏 `shell_tui_index._taskbar`＋右栏 [shell_tui_tasks.py](../../scripts/shell_tui_tasks.py)；均值样本来自 [latency.py](../../scripts/latency.py)。

## 红线
- 改表唯一经本制表器（add/remove/status/skill/res 均落同一真源并重发进度信封），模型与用户不得旁改 JSON；并行不越权：行只是「目标＋技能＋资源」，执行仍按各技能自身门禁（grant/预览/stop）。
- 悬空链接 = 0；本文件 ≤ 50 行；SKILL.md 含 YAML frontmatter。
