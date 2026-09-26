#!/usr/bin/env python3
"""dream.py — 做梦机制（timestamp 调度，红线 17）：后台常驻守护线程监听 config dream.next_run ISO 时间戳，到时即执行——跨链合并近义碎片、修剪陈旧低频（knowledge 钉选除外）、重建 <SMS_HOME>/chains/retrieval.md、高频 knowledge 同步 memory.json 钉选、审计对话开-收口与子会话悬挂（violations.md）、skill_errors≥3 记升级事件（经 user_commands skill-update→Skill_Generator 修改路径）。用法：python dream.py run|maybe|status|schedule|--sync。"""
import os, sys, json, time, threading
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import resolve_home, chain_store as cs, chains

def _now_iso(): return time.strftime("%Y-%m-%dT%H:%M:%S")
def _last(sms):
    try: return float(open(os.path.join(sms, "chains", "last_run")).read())
    except Exception: return 0.0
def _next_run(sms):
    try: return float(open(os.path.join(sms, "chains", "next_run_ts")).read())
    except Exception: return 0.0
def _interval(sms):
    c = resolve_home.conf(sms); d = c.get("dream") or {}
    return d.get("interval_min", 360) * 60
def due(sms):
    import settings
    next_ts = _next_run(sms) or settings.get("dream.next_run", sms=sms)
    if not next_ts: return False
    try: return time.time() >= float(next_ts)
    except (ValueError, TypeError): return False
def schedule(sms, interval_min=None):
    iv = interval_min or (_interval(sms) // 60)
    nxt = time.time() + iv * 60
    open(os.path.join(sms, "chains", "next_run_ts"), "w").write(str(nxt))
    import settings
    settings.set("dream.next_run", _now_iso(), sms=sms)
    return _now_iso()
def daemon_loop(sms, stop_event=None):
    while not stop_event.is_set() and not _should_stop():
        if due(sms):
            run(sms)
            schedule(sms)
        stop_event.wait(10)
def _should_stop(): return False
def _daemon_thread(sms, stop_event=None):
    t = threading.Thread(target=daemon_loop, args=(sms, stop_event), daemon=True)
    t.start(); return t
def maybe(sms):
    if due(sms):
        threading.Thread(target=run, args=(sms,), daemon=True).start(); return True
    return False
def run(sms):
    st = cs.Store(sms); r = {"merged": st.merge_near(), "pruned": st.prune()}
    top = sorted(st.all_frags(), key=lambda f: -f.get("freq", 1))[:40]
    os.makedirs(os.path.join(sms, "chains"), exist_ok=True)
    open(os.path.join(sms, "chains", "retrieval.md"), "w", encoding="utf-8").write(
        "\n".join("[%s·f%d] %s" % (f["id"], f["freq"], f["text"]) for f in top) or "（暂无）\n")
    r["pinned"] = _mem(sms, top); _audit(sms, r); _escalate(sms, r)
    open(os.path.join(sms, "chains", "last_run"), "w").write(str(time.time()))
    r["task"] = "做梦完成：合并%d 修剪%d 钉选%d 违规%d 升级%d" % (
        r["merged"], r["pruned"], r["pinned"], len(r.get("violations", [])), r.get("escalated", 0))
    chains.record("event", r["task"]); return r
def _ld(p): return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None
def _wj(p, d): json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
def _mem(sms, top):
    p = os.path.join(sms, "memory.json"); doc = _ld(p) or {"updated": _now_iso(), "entries": []}
    have = {e["note"] for e in doc["entries"]}; nid = max([e["id"] for e in doc["entries"]], default=0); n = 0
    for f in [x for x in top if x["chain"] == "knowledge" and x["freq"] >= 3][:10]:
        if f["text"] not in have:
            nid += 1; doc["entries"].append({"id": nid, "date": f["ts"][:10], "path": "chains/knowledge/" + f["id"], "note": f["text"]}); n += 1
    if n: doc["updated"] = _now_iso(); _wj(p, doc)
    return n
def _audit(sms, r):
    fs = cs.Store(sms).all_frags("session"); opens = {f["text"].split(":", 1)[1] for f in fs if f["text"].startswith("open")}
    closes = {f["text"].split(":", 1)[1] for f in fs if f["text"].startswith("close")}
    subs = {f["text"].rsplit("@", 1)[-1] for f in cs.Store(sms).all_frags("subsession")}
    r["violations"] = sorted(opens - closes) + sorted(subs - closes)
    open(os.path.join(sms, "chains", "violations.md"), "w", encoding="utf-8").write("\n".join(r["violations"]))
def _escalate(sms, r):
    r["escalated"] = 0; p = os.path.join(sms, "errors", "skill_errors.json"); doc = _ld(p)
    if not doc: return
    for e in doc.get("errors", []):
        if e.get("count", 0) >= 3 and not (e.get("resolved") or e.get("escalated")):
            e["escalated"] = _now_iso(); r["escalated"] += 1
            chains.record("event", "dream 升级：%s 错误≥3 → user_commands run skill-update %s" % (e.get("skill"), e.get("skill")))
    if r["escalated"]: _wj(p, doc)
if __name__ == "__main__":
    sms = resolve_home.ensure(); cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "run":
        if "--sync" in sys.argv: print(json.dumps(run(sms), ensure_ascii=False, indent=2))
        else: print("spawned" if maybe(sms) else "未到期")
    elif cmd == "status":
        iv = _interval(sms) // 60; nxt = _next_run(sms)
        print(json.dumps({"last_run": _last(sms), "next_run_ts": nxt, "next_run_iso": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(nxt)) if nxt else None, "interval_min": iv, "due": due(sms)}, ensure_ascii=False))
    elif cmd == "schedule":
        iv = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else None
        print("下次做梦：" + schedule(sms, iv))
    elif cmd == "maybe": print("spawned" if maybe(sms) else "未到期")
    else: print(__doc__.strip().splitlines()[-1])
