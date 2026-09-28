#!/usr/bin/env python3
"""flow_guard.py — 主流程空口守卫（批20·2026-09-28 用户反馈「仍然会在莫名奇妙的地方停止」）：批18 任务表门控只约束有表的复杂任务，单步执行类诉求免表——模型宣告「现在开始写/Writing the animation now/Let me check」后以纯文本收口、零执行调用、磁盘无产物，用户被迫反复「继续」。promises(txt)＝中英「动手宣告」最小特征识别（gateway.run 在 depth==0、〔任务表〕无未完成行且本轮从未调 write/skill/task 时据此注入续推提示，共用 task.max_continue 熔断）；jargs(raw)＋TRUNC＝finish=length 截断致工具参数不完整时 gateway 不执行、回分段 write append 指引（防大文件在 max_tokens 内死循环）。仅特征识别与文案、不做路由裁决（裁决权在模型）。用法：python -B flow_guard.py test"""
import re, json
PROMISE = re.compile(r"(?:现在|马上|这就|立刻|正要|我将|我会|开始|正在|准备|接下来我|下面我|我先|我们先)[^。\n]{0,16}(?:写|创建|生成|制作|实现|构建|建立|修复|执行|动手|落盘|查看|检查|确认|做一|建一)|(?:now|next|i\s+wil[lm]|i'?m\s+going|let\s+me|first\s+i)[^.\n]{0,30}(?:writ|creat|generat|build|mak|implement|fix|check|look|see|list|insp|exam|exec|run|test)|(?:writ|creat|generat|build|implement|fix|check|insp)[a-z]+[^.\n]{0,30}(?:now|shortly|immediately|next)", re.I)
TRUNC = "⚠ 本轮输出达 max_tokens 被截断（finish=length）：工具调用参数不完整·未执行——大文件请分多段 write(append=true) 写入（每段≤600字），或精简单次输出后重试。"
def promises(txt): return bool(txt and PROMISE.search(str(txt)))
def jargs(raw):
    try: json.loads(raw or "{}"); return True
    except Exception: return False
def notice(pend, idle): return "• 主流程守卫：" + ("〔任务表〕仍有未完成行·自动续推中（第" if pend else "检测到空口宣告（说要动手·本轮零执行调用）·自动续推中（第") + str(idle) + "次·对话不结束）"
def inject(pend): return ("[SMS 主流程守卫] 主任务未完成·不得收口结束：\n" + pend + "\n据实改表并继续推进未完成行（无依赖用 task 工具并发·有依赖 parallel=false 或依序逐 skill·完成即 task_plan status done）·全部行 done 后才一句 ≤40 字收口——禁止重复宣告完成而不推进。" if pend else "[SMS 主流程守卫] 你刚宣告要动手，但本轮未调用任何 write/skill/task 执行工具、产物未落盘——禁止空口收口：立即用 write/exec/skill 真执行（长内容分多段 write append=true·每段≤600字·防 max_tokens 截断）；若确无需动手或已完成，给一句 ≤40 字事实结论。")
if __name__ == "__main__":
    ok = all(map(promises, ["现在开始写动画。", "Writing the animation now.", "Let me check the contents of tmp too.", "接下来我将创建文件", "我马上生成页面"])) and not any(map(promises, ["已完成，文件在 tmp\\a.html。", "链机制是省 token 的记忆介质。", "这段代码的含义是：先写头再写体。", ""])) and jargs('{"a":1}') and not jargs('{"a":1') and "主任务未完成" in inject("x") and "空口" in inject("")
    print("flow_guard selftest: " + ("OK" if ok else "FAIL")); raise SystemExit(0 if ok else 1)
