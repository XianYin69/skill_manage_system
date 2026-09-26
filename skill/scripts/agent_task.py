#!/usr/bin/env python3
"""agent_task.py — 任务工具 task/task_detail（单一诉求拆分·并行子任务·子代理记忆联系）：task.decompose 把诉求拆子任务→各子任务独立经 skill_route 路由（命中→agent_tools.run_skill 子会话真派发；未命中→ask 子问答）→ThreadPool≤3 并行执行；每完成一笔落 <SMS_HOME>/tasks/<id>.json 并发 msg_flow task 信封（meta.done/total→顶栏实时进度）；子任务结果与 conv/sess 边回写十一链（subsession+skill_call 在 run_skill 内记），task_detail 复算并再发进度信封（模型/顶栏共用同一进度真源）。用法：python -B agent_task.py run "<诉求>" | detail [task-id]"""
import os, sys, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import resolve_home, chains, skill_route, task as tsk, agent_tools as at
SMS = resolve_home.ensure()
def _tf(tid): return os.path.join(SMS, "tasks", tid + ".json")
def _save(doc):
    os.makedirs(os.path.join(SMS, "tasks"), exist_ok=True); json.dump(doc, open(_tf(doc["id"]), "w", encoding="utf-8"), ensure_ascii=False)
def task(intent):
    from concurrent.futures import ThreadPoolExecutor
    subs = tsk.decompose(str(intent)); tid = "task-" + time.strftime("%Y%m%d-%H%M%S")
    doc = {"id": tid, "intent": str(intent), "conv": chains.ACTIVE["conv"], "sess": chains.cur_sess(), "created": time.strftime("%Y-%m-%d %H:%M:%S"), "subtasks": subs}; _save(doc)
    at.emit("task", "任务 " + tid + "：拆出 " + str(len(subs)) + " 子任务并行派发", tool="task", meta={"id": tid, "done": 0, "total": len(subs)})
    def one(st):
        st["status"] = "running"; sid, _ = skill_route.route(st["goal"]); st["skill"] = (sid or "").split(",")[0] or None
        st["result"] = str(at.run_skill(st["skill"], st["goal"]) if sid else at.ask(st["goal"]))[:600]; st["status"] = "done"
        dn = sum(1 for x in subs if x["status"] == "done"); _save(doc)
        at.emit("task", "任务 " + tid + " 进度 " + str(dn) + "/" + str(len(subs)) + "（" + st["id"] + " " + st["goal"][:30] + ("⧉" + str(st.get("skill")) if st.get("skill") else "") + "）", tool="task_detail", meta={"id": tid, "done": dn, "total": len(subs)}); return st["id"] + "：" + st["result"][:150]
    with ThreadPoolExecutor(max_workers=max(1, min(3, len(subs)))) as ex: res = list(ex.map(one, subs))
    chains.record("event", "task " + tid + " 收口 " + str(len(subs)) + " 子任务", [[chains.ACTIVE["conv"] or "", "ref", 1], [chains.cur_sess(), "member", 1]])
    return "任务 " + tid + " 完成（" + str(len(subs)) + " 子任务）：\n" + "\n".join(res)
def task_detail(tid=""):
    d = os.path.join(SMS, "tasks"); ids = sorted(x[:-5] for x in (os.listdir(d) if os.path.isdir(d) else []))
    if not tid: return "任务清单：" + ("、".join(ids[-5:]) or "（无）")
    try: doc = json.load(open(_tf(tid), encoding="utf-8"))
    except Exception: return "无任务：" + tid
    dn = sum(1 for x in doc["subtasks"] if x.get("status") == "done")
    at.emit("task", "任务 " + tid + " " + str(dn) + "/" + str(len(doc["subtasks"])), tool="task_detail", meta={"id": tid, "done": dn, "total": len(doc["subtasks"]), "subtasks": doc["subtasks"]})
    return json.dumps({k: doc[k] for k in ("id", "intent", "conv", "sess", "subtasks")}, ensure_ascii=False)[:1500]
if __name__ == "__main__":
    a = sys.argv[1:]
    print(task(" ".join(a[1:])) if a and a[0] == "run" and len(a) > 1 else task_detail(a[1] if a and a[0] == "detail" else "") if a and a[0] == "detail" else (__doc__.strip().splitlines()[-1]))
