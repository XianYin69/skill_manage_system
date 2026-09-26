---
name: general_answer
description: >
  通用回答子技能：一般知识/概念/解释类诉求的托管作答口（answer_general.py 调网关一次性作答）。
  SMS 本体不作答红线经此闭环——问答也来自托管 skill 执行结果；不确定明说、不动文件不联网、
  网关未启用即明确报错；结果记 tool_call/knowledge 链供做梦沉淀。
license: MIT
metadata:
  category: answer
---

# general_answer

SMS 的**通用回答**子技能：把「模型本身就能答」的诉求收拢到一个可派发目标，作答仍经托管技能执行、由 SMS 整合转达，不破坏「本体不作答」（红线 4）。

## 何时派发

- 用户话语是知识问答/概念解释/对比说明/闲聊寒暄，且注册表无更具执行性的技能命中。
- 其他技能明确"只干活不代答"后需要一段面向用户的说明文字。
- 需要动手（读写/执行/联网）→ 不派本技能，派 file_ops / 目标技能。

## 用法

```
python -B skill/scripts/answer_general.py ask "<问题>"
python -B skill/scripts/answer_general.py ask "<问题>" --json
```

- 非流式一次性作答（≤600 字·简体中文）；返回整段文本供 SMS 整合。
- 网关未启用 / 返回空正文 → 明确报错退出（exit 2），绝不静默代答。

## 联动

- 路由注入见 [skill_route.py](../../scripts/skill_route.py) 未命中分支与 [gateway.py](../../scripts/gateway.py) SYS 治理句。
- 作答记 tool_call 链＋knowledge 链（挂 conv/sess 边），由 [dream.py](../../scripts/dream.py) 做梦沉淀。
- 壳内等价入口：直接话语自动路由，或 `:dispatch general_answer <问题>`。

## 红线

- 不执行文件、命令、联网动作——发现诉求含执行意图时回退 SMS 改派具执行能力的技能（红线 6）。
- 回答经 SMS 整合后转达用户，本技能不直接面向用户会话。
- 悬空链接 = 0；本文件 ≤ 50 行；SKILL.md 含 YAML frontmatter。
