#!/usr/bin/env python3
"""dream.py — 做梦机制（时间戳调度·红线17 审计）：next_run_ts（chains/）到点触发——合并近义/修剪低频/钉选记忆/审计未收口对话与子会话/升级高频错误 skill 触发 skill-update；maybe 每次数据流输入检查·daemon 线程执行；状态/调度经 settings dream.next_run/interval_min。用法：python -B dream.py status|run [--sync]|schedule [分钟]|maybe"""
import os, sys, json, time, threading
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import resolve_home, chain_store as cs, chains
def _now(): return time.strftime("%Y-%m-%dT%H:%M:%S")
def _read_ts(sms, k):
    try: return float(open(os.path.join(sms, "chains", k)).read())
    except Exception: return 0.0
def _iv(sms):
    c = resolve_home.conf(sms); d = c.get("dream") or {}; return d.get("interval_min", 360) * 60
def due(sms):
    import settings; nxt = _read_ts(sms, "next_run_ts") or settings.get("dream.next_run", sms=sms)
    try: return bool(nxt) and time.time() >= float(nxt)
    except (ValueError, TypeError): return False
def schedule(sms, iv=None):
    iv = iv or (_iv(sms) // 60); nxt = time.time() + iv * 60; open(os.path.join(sms, "chains", "next_run_ts"), "w").write(str(nxt))
    import settings; settings.set("dream.next_run", _now(), sms=sms); return _now()
def maybe(sms): return due(sms) and bool(threading.Thread(target=run, args=(sms,), daemon=True).start() or True)
def run(sms):
    st = cs.Store(sms); r = {"merged": st.merge_near(), "pruned": st.prune()}; top = sorted(st.all_frags(), key=lambda f: -f.get("freq", 1))[:40]
    os.makedirs(os.path.join(sms, "chains"), exist_ok=True); open(os.path.join(sms, "chains", "retrieval.md"), "w", encoding="utf-8").write("\n".join("[%s·f%d] %s" % (f["id"], f["freq"], f["text"]) for f in top) or "（暂无）\n")
    r["pinned"] = _mem(sms, top); _audit(sms, r); _escalate(sms, r); open(os.path.join(sms, "chains", "last_run"), "w").write(str(time.time()))
    r["task"] = "做梦完成：合并%d 修剪%d 钉选%d 违规%d 升级%d" % (r["merged"], r["pruned"], r["pinned"], len(r.get("violations", [])), r.get("escalated", 0))
    chains.record("event", r["task"]); return r
def _ldw(p): import json; return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None
def _wj(p, d): import json; json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
def _mem(sms, top):
    p = os.path.join(sms, "memory.json"); doc = _ldw(p) or {"updated": _now(), "entries": []}
    have = {e["note"] for e in doc["entries"]}; nid = max([e["id"] for e in doc["entries"]], default=0); n = 0
    for f in [x for x in top if x["chain"] == "knowledge" and x["freq"] >= 3][:10]:
        if f["text"] not in have: nid += 1; doc["entries"].append({"id": nid, "date": f["ts"][:10], "path": "chains/knowledge/" + f["id"], "note": f["text"]}); n += 1
    if n: doc["updated"] = _now(); _wj(p, doc); return n
    return 0
def _audit(sms, r):
    fs = cs.Store(sms).all_frags("session"); opens = {f["text"].split(":", 1)[1] for f in fs if f["text"].startswith("open")}; closes = {f["text"].split(":", 1)[1] for f in fs if f["text"].startswith("close")}
    subs = {f["text"].rsplit("@", 1)[-1] for f in cs.Store(sms).all_frags("subsession")}
    r["violations"] = sorted(opens - closes) + sorted(subs - closes)
    open(os.path.join(sms, "chains", "violations.md"), "w", encoding="utf-8").write("\n".join(r["violations"]))
def _escalate(sms, r):
    r["escalated"] = 0; p = os.path.join(sms, "errors", "skill_errors.json"); doc = _ldw(p)
    for e in (doc or {}).get("errors", []):
        if e.get("count", 0) >= 3 and not (e.get("resolved") or e.get("escalated")): e["escalated"] = _now(); r["escalated"] += 1; chains.record("event", "dream 升级：%s 错误≥3 → user_commands run skill-update %s" % (e.get("skill"), e.get("skill")))
    if r["escalated"]: _wj(p, doc)
if __name__ == "__main__":
    sms = resolve_home.ensure(); cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "run": print(json.dumps(run(sms), ensure_ascii=False, indent=2) if "--sync" in sys.argv else ("spawned" if maybe(sms) else "未到期"))
    elif cmd == "status": iv = _iv(sms) // 60; nxt = _read_ts(sms, "next_run_ts"); print(json.dumps({"last_run": _read_ts(sms, "last_run"), "next_run_ts": nxt, "next_run_iso": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(nxt)) if nxt else None, "interval_min": iv, "due": due(sms)}, ensure_ascii=False))
    elif cmd == "schedule": print("下次做梦：" + schedule(sms, int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else None))
    elif cmd == "maybe": print("spawned" if maybe(sms) else "未到期")
