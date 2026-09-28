#!/usr/bin/env python3
"""task_table.py — 任务表制表器（SMS 子技能 task_table·批12②·批14①复杂门控·批18 行数无上限＋主流程守卫）：仅复杂任务（拆步≥2 且至少一步命中执行性技能）话语送网关前先粗分建表——task.decompose 粗分种子、逐行 skill_route 定技能，落 <SMS_HOME>/tasks/<id>.json＋msg_flow task 信封（顶栏进度/剩余）；attach() 注入〔任务表〕块命令模型首轮据实改表（行数无上限·不得只跑一两行就停）按行推进·每步 task_plan status done·中途 add/remove/skill 改表；pending(conv)＝本对话未完成行清单供 gateway 主流程守卫续推（未完成不得收口·无依赖 task 工具并发·有依赖依序）。免表＝非复杂直送网关。eta()＝未完成行×latency 均值。用法：python -B task_table.py plan <诉求>|show <tid>|next <tid>|eta <tid>|status <tid> <t#> <状态>|add <tid> <目标> [技能id]|remove <tid> <t#>|skill <tid> <t#> <技能id>|pending [conv]"""
import os, sys, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import resolve_home, chains, task as tsk, skill_route, settings, atomic_io, latency, msg_flow
SMS = resolve_home.ensure(); GEN = ("general_answer", "constraint_arbiter"); TD = os.path.join(SMS, "tasks")
def _tf(tid): return os.path.join(TD, tid + ".json")
def _save(doc): os.makedirs(TD, exist_ok=True); atomic_io.wjson(_tf(doc["id"]), doc)
def _load(tid):
    try: return atomic_io.rjson(_tf(tid))
    except Exception: return None
def eta(doc):
    llm = latency.avg("llm|" + str(settings.get("llm_gateway.model", "auto"))) or 45000
    return round(sum(((latency.avg("skill|" + str(x.get("skill"))) or llm) if x.get("skill") else llm) for x in (doc.get("subtasks") or []) if x.get("status") in ("pending", "running")) / 1000)
def emit(doc, note="任务表"):
    import agent_tools as at; subs = doc.get("subtasks") or []; dn = sum(1 for x in subs if x.get("status") == "done"); at.emit("task", note + " " + str(doc["id"])[-14:] + "：" + str(dn) + "/" + str(len(subs)) + " " + msg_flow.fmt(eta(doc)), tool="task", meta={"id": doc["id"], "done": dn, "total": len(subs), "eta_s": eta(doc)})
def plan(intent):
    subs = tsk.decompose(str(intent)); hs = []
    for x in subs: sid, _ = skill_route.route(x["goal"]); h = (sid or "").split(",")[0] or None; x["skill"] = h; x["inst"] = h or x["id"]; x["status"] = "pending"; hs.append(h)
    if len(subs) < 2 or not any(h and h not in GEN for h in hs): return None
    tid = "task-" + time.strftime("%Y%m%d-%H%M%S") + "-" + "%03d" % (time.time() * 1000 % 1000)
    doc = {"id": tid, "intent": str(intent), "conv": chains.ACTIVE["conv"], "sess": chains.cur_sess(), "created": time.strftime("%Y-%m-%d %H:%M:%S"), "table": "task_table", "subtasks": subs}
    _save(doc); emit(doc, "任务表（粗分种子·首轮据实改表）"); return doc
def block(doc):
    rows = "\n".join("%s %s%s" % (x["id"], str(x["goal"])[:70], ("〔技能:" + str(x["skill"]) + "〕" if x.get("skill") else "〔工具自办〕")) for x in doc["subtasks"])
    return "\n〔任务表 " + doc["id"] + "（粗分种子·预测" + msg_flow.fmt(eta(doc)) + "）〕\n" + rows + "\n〔执行规则〕这是脚本粗分种子——首轮必须据实改表（task_plan add/remove/skill）到真实步骤数，行数无上限、不得只跑一两行就停；按行推进：〔技能:x〕调 skill 派发、〔工具自办〕用 exec/read/write/glob/grep 自办；子任务无依赖可用 task 工具并发派发（你判断无冲突才并发·有依赖则 parallel=false 或依序逐 skill）；每步完成立刻 task_plan status <表id> <行id> done（顶栏进度据此刷新）；全部行 done 才输出整合结果收口——子会话收口＝返回主流程继续未完成行，禁止把单个子技能完成当作整段对话结束。\n"
def attach(intent): return "" if not settings.get("task.auto_table", True) else (block(d) if (d := plan(intent)) else "")
def pending(conv=""):
    c = conv or chains.ACTIVE.get("conv") or ""; out = []
    for tid in ([fn[:-5] for fn in sorted(os.listdir(TD)) if fn.endswith(".json")] if os.path.isdir(TD) else []):
        doc = _load(tid); rest = [x for x in (doc.get("subtasks") or []) if x.get("status") != "done"] if doc and doc.get("conv") == c else []
        rest and out.append("〔任务表 " + tid[-14:] + "〕未完成 " + str(len(rest)) + "/" + str(len(doc.get("subtasks") or [])) + "：" + "；".join(str(x.get("id")) + "｜" + str(x.get("skill") or "工具自办") + "｜" + str(x.get("goal"))[:40] + "〔" + str(x.get("status", "pending")) + "〕" for x in rest)[:600])
    return "\n".join(out)
def revise(op, tid, row="", value=""):
    doc = _load(tid) if tid else None
    if not doc: return "无任务表：" + str(tid) + "（task_table plan <诉求> 先建表）"
    subs = doc.get("subtasks") or []; x = next((s for s in subs if s.get("id") == row), None)
    if op == "show": return json.dumps({"id": doc["id"], "subtasks": subs}, ensure_ascii=False)[:1800]
    if op == "next": p = next((s for s in subs if s.get("status") == "pending"), None); return (p and (str(p["id"]) + "｜" + str(p.get("skill") or "工具自办") + "｜" + str(p["goal"])[:80])) or "全部完成"
    if op == "eta": return "剩余预测 " + msg_flow.fmt(eta(doc))
    if op == "add": n = 1 + max([int(str(s["id"])[1:]) for s in subs if str(s["id"]).startswith("t") and str(s["id"])[1:].isdigit()] or [0]); sid, _ = skill_route.route(str(value)); h = (sid or "").split(",")[0] or None; subs.append({"id": "t%d" % n, "goal": str(value), "skill": h, "inst": h or "t%d" % n, "status": "pending"}); _save(doc); emit(doc, "任务表加行"); return "已加 t%d｜%s%s" % (n, str(value)[:60], ("·指定技能 " + h) if h else "")
    if op == "remove" and x: subs.remove(x); _save(doc); emit(doc, "任务表删行"); return "已删 " + str(row)
    if op == "status" and x: x["status"] = value if value in ("pending", "running", "done", "error", "stopped") else "done"; _save(doc); emit(doc, "任务表步进"); return str(row) + " → " + x["status"] + "（" + str(sum(1 for s in subs if s.get("status") == "done")) + "/" + str(len(subs)) + "·" + msg_flow.fmt(eta(doc)) + "）"
    if op == "skill" and x: x["skill"] = str(value); x["inst"] = str(value); _save(doc); emit(doc, "任务表改派"); return str(row) + " 指定技能：" + str(value)
    return "用法 task_plan show|next|eta|add|remove|status|skill <表id> [行id] [值]"
if __name__ == "__main__":
    a = sys.argv[1:] or ["help"]
    if a[0] == "plan" and len(a) > 1: d = plan(" ".join(a[1:])); print(block(d) if d else "（非复杂任务·免表，直接送网关）")
    elif a[0] == "pending": print(pending(a[1] if len(a) > 1 else "") or "（本对话无未完成任务表）")
    elif len(a) > 1: print(revise(a[0], a[1], a[2] if len(a) > 2 else "", " ".join(a[3:])))
    else: print(__doc__.strip().splitlines()[-1])
