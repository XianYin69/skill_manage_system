# 十一链记忆体系（chain_store / chains / chains_git / prompt_pack / dream）

十一链：user 用户链 · memory 记忆链 · knowledge 钉选链 · logic 逻辑链 · time 时间链 · event 事件链 · session 会话链 · skill_call 调用skill链 · tool_call 调用工具链 · subsession 子会话链 · dialogue 代理对话链。

## 存储（chain_store.py，契约 [../schemas/chains.schema.json](../schemas/chains.schema.json)）

- 碎片＝语句化·最小化 JSON：`{"id","chain","ts","text","vec","freq","edges"}`，存 `<SMS_HOME>/chains/<链>/<id>.json`，禁止入 skill 目录。
- 向量 `vec`：64 维哈希投影（语句指向，纯 stdlib）；数值 `freq`：检索命中自动 +1（使用频次）；边 `edges`：`[目标id, 关系, 权重]`，关系∈semantic/temporal/causal/ref（树形·神经网络型语义关系）。
- 所有链必须 git 管理（chains_git.py，2026-09-25 用户红线）：首次触链自动 `git init <SMS_HOME>/chains` 并把既有全部链导入首笔提交；之后任何链写入防抖 5 秒自动 commit、进程退出兜底 flush；git 缺失静默降级不阻断记录。手动：`python chains_git.py status|log [n]`。

## 记录与对话隔离（chains.py）

- CLI：`python chains.py <链> "<语句>" [--to 目标id --rel 关系]`；`list [链]`；`log skill|tool|sub <名>`（子代理登记调用链/子会话链）。
- `conversation(text)`＝双层对话规则前缀：`[压缩记忆]`（prompt_pack 限额）＋对话规则（每输入开新对话、仅当前输入有效、agent skill 必开新子会话并收口）＋`[当前输入·唯一指令]`。
- 会话/对话/时间链钩子已内置于 agent_stream 每次派发（open→close 收口）与 session.py 建会话。

## 提示词四操作（prompt_pack.py）

- `split` 按句拆分碎片；`simplify` 打分简化取要；`merge` 跨链近义合并（并频次）；`pack` 压缩检索＝向量余弦＋频次＋一跳语义邻域 → ≤max_chars 的发送大模型记忆块（简短精准，禁止整段历史直灌）。

## 做梦机制（dream.py，惰性触发）

- `maybe()` 由 sms.py 入口、emit 会话写盘、agent_stream 派发调用；间隔＝config `dream_interval_min`（默认 360 分钟），`doctor` 显示状态。
- 一次做梦：跨链合并近义碎片 → 修剪陈旧低频（knowledge 钉选除外）→ 重建 `chains/retrieval.md` → 高频 knowledge 同步 `memory.json` 钉选 → 审计对话开-收口与子会话悬挂（`chains/violations.md`）→ skill_errors≥3 记升级事件（user_commands `skill-update`→Skill_Generator 修改路径，实现所有 skill 自动迭代）→ event 链留痕。
- 手动：`python dream.py run|maybe|status [--sync]`。

## 各链与做梦设置（config 段 chains / dream，settings.py 统一改）

- `chains.<链>` 覆盖 `chains.default{enabled, merge_thr, prune_days, min_freq}`：enabled=false 停写该链（chain_store 建库时读取、add 拒绝并提示恢复命令），merge/修剪按链取阈值与天数；`dream.enabled`／`dream.interval_min` 控制做梦（旧键 dream_interval_min 兼容）；knowledge 钉选链不参与修剪停用。改法：`python -B settings.py set chains.tool_call.enabled false`、壳内 `:config set ...`、或网页壳「链设置」区；每次变更记 event 链（契约 [../schemas/settings.schema.json](../schemas/settings.schema.json)）。

## 目标

每次发送大模型的记忆链＝简短而精准的碎片 Top-K（向量定位＋频次加权＋语义邻域），配合每输入新对话隔离，保证输出快且准。
