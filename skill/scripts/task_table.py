#!/usr/bin/env python3
"""task_table.py — 任务拆分与任务表制表器（SMS 子技能 task_table 本体·批12②·批14①改复杂任务门控）：仅复杂任务（拆步≥2 且至少一步命中执行性技能）的用户话语在送网关前先拆步建表——task.decompose 拆子任务、逐行 skill_route 定「特定步骤指定特定 skill」，落 <SMS_HOME>/tasks/<id>.json（与 agent_task/shell_tui_tasks 同 schema 同真源·右栏任务表即时可见）＋msg_flow task 信封（done/total/eta_s→顶栏进度条按任务表＋模型反应时间预测剩余）；attach() 产注入网关的〔任务表〕块并命令模型按行执行——每步完成调 task_plan status 置 done，中途发现表不合理调 task_plan add/remove/skill 就地改表（改表亦经本子技能·同一真源）。免表＝非复杂：单步话语（含命中单技能·走直接派发）、纯问答、无技能命中多步一律直送网关（用户 2026-09-27 指示「不是什么都写任务表，只是复杂任务才建表」）。eta()＝未完成行×该技能 latency 均值（缺样本退 llm 均值再退 45s）。用法：python -B task_table.py plan <诉求>|show <tid>|next <tid>|eta <tid>|status <tid> <t#> <状态>|add <tid> <目标> [技能id]|remove <tid> <t#>|skill <tid> <t#> <技能id>"""
import os, sys, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import resolve_home, chains, task as tsk, skill_route, settings, atomic_io, latency, msg_flow
SMS = resolve_home.ensure(); GEN = ("general_answer", "constraint_arbiter")
def _tf(tid): return os.path.join(SMS, "tasks", tid + ".json")
def _save(doc): os.makedirs(os.path.join(SMS, "tasks"), exist_ok=True); atomic_io.wjson(_tf(doc["id"]), doc)
def _load(tid):
    try: return atomic_io.rjson(_tf(tid))
    except Exception: return None
def eta(doc):
    llm = latency.avg("llm|" + str(settings.get("llm_gateway.model", "auto"))) or 45000; s = 0
    for x in doc.get("subtasks") or []:
        if x.get("status") in ("pending", "running"): s += (latency.avg("skill|" + str(x.get("skill"))) or llm) if x.get("skill") else llm
    return round(s / 1000)
def emit(doc, note="任务表"):
    import agent_tools as at; subs = doc.get("subtasks") or []; dn = sum(1 for x in subs if x.get("status") == "done")
    at.emit("task", note + " " + str(doc["id"])[-14:] + "：" + str(dn) + "/" + str(len(subs)) + " " + msg_flow.fmt(eta(doc)), tool="task", meta={"id": doc["id"], "done": dn, "total": len(subs), "eta_s": eta(doc)})
def plan(intent):
    subs = tsk.decompose(str(intent)); hs = []
    for x in subs:
        sid, _ = skill_route.route(x["goal"]); h = (sid or "").split(",")[0] or None; x["skill"] = h; x["inst"] = h or x["id"]; x["status"] = "pending"; hs.append(h)
    if len(subs) < 2 or not any(h and h not in GEN for h in hs): return None
    tid = "task-" + time.strftime("%Y%m%d-%H%M%S") + "-" + "%03d" % (time.time() * 1000 % 1000)
    doc = {"id": tid, "intent": str(intent), "conv": chains.ACTIVE["conv"], "sess": chains.cur_sess(), "created": time.strftime("%Y-%m-%d %H:%M:%S"), "table": "task_table", "subtasks": subs}
    _save(doc); emit(doc, "任务表（task_table 拆分建表）"); return doc
def block(doc):
    rows = "\n".join("%s %s%s" % (x["id"], str(x["goal"])[:70], ("〔技能:" + str(x["skill"]) + "〕" if x.get("skill") else "〔工具自办〕")) for x in doc["subtasks"])
    return "\n〔任务表 " + doc["id"] + "（task_table 制表·预测" + msg_flow.fmt(eta(doc)) + "）〕\n" + rows + "\n〔执行规则〕按行序推进：标〔技能:x〕的步骤必须调 skill 工具派发 x 真执行；〔工具自办〕用 exec/read/write/glob/grep 等自办；每步完成立刻 task_plan status <表id> <行id> done（顶栏进度与剩余时间据此实时刷新）；中途发现表不合理（拆错/漏步/派错技能）必须 task_plan add/remove/skill 改表，不得绕开表自由发挥；全部行 done 才输出整合结果收口。\n"
def attach(intent): return "" if not settings.get("task.auto_table", True) else (block(d) if (d := plan(intent)) else "")
def revise(op, tid, row="", value=""):
    doc = _load(tid) if tid else None
    if not doc: return "无任务表：" + str(tid) + "（task_table plan <诉求> 先建表）"
    subs = doc.get("subtasks") or []; x = next((s for s in subs if s.get("id") == row), None)
    if op == "show": return json.dumps({"id": doc["id"], "subtasks": subs}, ensure_ascii=False)[:1800]
    if op == "next": p = next((s for s in subs if s.get("status") == "pending"), None); return (p and (str(p["id"]) + "｜" + str(p.get("skill") or "工具自办") + "｜" + str(p["goal"])[:80])) or "全部完成"
    if op == "eta": return "剩余预测 " + msg_flow.fmt(eta(doc))
    if op == "add":
        n = 1 + max([int(str(s["id"])[1:]) for s in subs if str(s["id"]).startswith("t") and str(s["id"])[1:].isdigit()] or [0]); sid, _ = skill_route.route(str(value)); h = (sid or "").split(",")[0] or None; subs.append({"id": "t%d" % n, "goal": str(value), "skill": h, "inst": h or "t%d" % n, "status": "pending"}); _save(doc); emit(doc, "任务表加行"); return "已加 t%d｜%s%s" % (n, str(value)[:60], ("·指定技能 " + h) if h else "")
    if op == "remove" and x: subs.remove(x); _save(doc); emit(doc, "任务表删行"); return "已删 " + str(row)
    if op == "status" and x: x["status"] = value if value in ("pending", "running", "done", "error", "stopped") else "done"; _save(doc); emit(doc, "任务表步进"); return str(row) + " → " + x["status"] + "（" + str(sum(1 for s in subs if s.get("status") == "done")) + "/" + str(len(subs)) + "·" + msg_flow.fmt(eta(doc)) + "）"
    if op == "skill" and x: x["skill"] = str(value); x["inst"] = str(value); _save(doc); emit(doc, "任务表改派"); return str(row) + " 指定技能：" + str(value)
    return "用法 task_plan show|next|eta|add|remove|status|skill <表id> [行id] [值]"
if __name__ == "__main__":
    a = sys.argv[1:] or ["help"]
    if a[0] == "plan" and len(a) > 1: d = plan(" ".join(a[1:])); print(block(d) if d else "（非复杂任务·免表，直接送网关）")
    elif a[0] == "attach" and len(a) > 1: print(attach(" ".join(a[1:])) or "（非复杂任务·免表）")
    elif len(a) > 1: print(revise(a[0], a[1], a[2] if len(a) > 2 else "", " ".join(a[3:])))
    else: print(__doc__.strip().splitlines()[-1])
