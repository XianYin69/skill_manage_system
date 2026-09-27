#!/usr/bin/env python3
"""agent_task.py — 任务工具 task/task_detail（诉求拆分·按技能实例并行子会话·合并）：tsk.decompose 拆子任务→逐笔 skill_route 路由，同一技能多次命中编号为实例（skill 两派＝sk_1/sk_2·各开独立子会话·流前缀 ⧉实例▸·agent_ctx 线程隔离防串台）→ThreadPool 并行（settings task.max_parallel 默认 3·全部子任务同时跑可加大）；子任务异常记 error 不中断其余；每完成一笔经 atomic_io 落 <SMS_HOME>/tasks/<id>.json＋msg_flow task 进度信封（meta.done/total→顶栏实时）；subsession/skill_call 链在 run_skill 内按实例名记；收口生成合并报告（逐实例状态＋全结果＋技能×次数统计），task_detail 复算并再发进度信封（模型/顶栏共用同一进度真源）。用法：python -B agent_task.py run "<诉求>" | detail [task-id]"""
import os, sys, json, time, threading
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import resolve_home, chains, skill_route, task as tsk, agent_tools as at, agent_ctx as ac, atomic_io, settings, stop_channel as stop
SMS = resolve_home.ensure()
def _tf(tid): return os.path.join(SMS, "tasks", tid + ".json")
def _save(doc): os.makedirs(os.path.join(SMS, "tasks"), exist_ok=True); atomic_io.wjson(_tf(doc["id"]), doc)
def task(intent):
    from concurrent.futures import ThreadPoolExecutor
    subs = tsk.decompose(str(intent)); tid = "task-" + time.strftime("%Y%m%d-%H%M%S") + "-" + "%03d" % (time.time() * 1000 % 1000)  # 毫秒后缀：同秒连发两任务不再互相覆盖 tasks/<id>.json（实测 task2 撞名 IndexOverwrite）
    doc = {"id": tid, "intent": str(intent), "conv": chains.ACTIVE["conv"], "sess": chains.cur_sess(), "created": time.strftime("%Y-%m-%d %H:%M:%S"), "subtasks": subs}; _save(doc)
    at.emit("task", "任务 " + tid + "：拆出 " + str(len(subs)) + " 子任务并行派发", tool="task", meta={"id": tid, "done": 0, "total": len(subs)})
    lk = threading.Lock(); cnt = {}; parent = ac.cur()
    def one(st):
        ac.adopt(parent); stop.check(); sid, _ = skill_route.route(st["goal"]); sk = (sid or "").split(",")[0] or None
        with lk:
            if sk: cnt[sk] = cnt.get(sk, 0) + 1
            st["skill"] = sk; st["inst"] = (sk + "_" + str(cnt.get(sk, 0))) if sk else st["id"]; st["status"] = "running"
        try: st["result"] = str(at.run_skill(sk, st["goal"], tag=st["inst"]) if sk else at.ask(st["goal"]))[:600]; st["status"] = "done"
        except stop.Stopped: st["result"] = "用户停止（stop）——子任务在检查点收口"; st["status"] = "stopped"
        except Exception as e: st["result"] = "执行失败：" + str(e)[:180]; st["status"] = "error"
        with lk: dn = sum(1 for x in subs if x["status"] == "done"); _save(doc)
        at.emit("task", "任务 " + tid + " 进度 " + str(dn) + "/" + str(len(subs)) + "（" + st["inst"] + " " + st["goal"][:30] + (" " + st["status"] if st["status"] != "done" else "") + "）", tool="task_detail", meta={"id": tid, "done": dn, "total": len(subs)})
        return st
    with ThreadPoolExecutor(max_workers=max(1, min(max(1, int(settings.get("task.max_parallel", 3))), len(subs)))) as ex: res = list(ex.map(one, subs))
    stat = "、".join(k + "×" + str(v) for k, v in sorted(cnt.items())) or "无技能命中（子问答作答）"
    merged = "任务 " + tid + " 完成（" + str(len(subs)) + " 子任务 · " + stat + " · 成功 " + str(sum(1 for r in res if r["status"] == "done")) + "/" + str(len(res)) + "）：\n" + "\n".join("[" + r["status"] + "] " + r["inst"] + " · " + r["goal"][:40] + " → " + r["result"] for r in res)
    chains.record("event", "task " + tid + " 收口 " + str(len(subs)) + " 子任务（" + stat + "）", [[chains.ACTIVE["conv"] or "", "ref", 1], [chains.cur_sess(), "member", 1]])
    _save(doc); return merged[:6000]
def task_detail(tid=""):
    d = os.path.join(SMS, "tasks"); ids = sorted(x[:-5] for x in (os.listdir(d) if os.path.isdir(d) else []))
    if not tid: return "任务清单：" + ("、".join(ids[-5:]) or "（无）")
    try: doc = atomic_io.rjson(_tf(tid))
    except Exception: return "无任务：" + tid
    dn = sum(1 for x in doc["subtasks"] if x.get("status") == "done")
    at.emit("task", "任务 " + tid + " " + str(dn) + "/" + str(len(doc["subtasks"])), tool="task_detail", meta={"id": tid, "done": dn, "total": len(doc["subtasks"]), "subtasks": doc["subtasks"]})
    return json.dumps({k: doc[k] for k in ("id", "intent", "conv", "sess", "subtasks")}, ensure_ascii=False)[:1500]
if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "run" and len(a) > 1: at.bind(on_line=lambda s: print(s, file=sys.stderr)); print(task(" ".join(a[1:])))
    elif a and a[0] == "detail": print(task_detail(a[1] if len(a) > 1 else ""))
    else: print(__doc__.strip().splitlines()[-1])
