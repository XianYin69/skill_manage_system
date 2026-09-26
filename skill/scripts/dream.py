#!/usr/bin/env python3
"""dream.py — 做梦机制（时间戳调度·红线17 审计）：触发时间由程序按链规模自动计算——interval_min()＝max(45,min(720,45＋碎片//20))·用户不可设置（settings 已剔除 interval_min/next_run 配置键）；next_run_ts（chains/）到点触发——合并近义/修剪低频/钉选记忆/审计未收口对话与子会话/升级高频错误 skill 触发 skill-update；maybe 每次数据流输入检查·daemon 线程执行。用法：python -B dream.py status|run [--sync]|schedule（按程序计算值重排·不接受手动分钟）|maybe。"""
import os, sys, json, time, threading
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import resolve_home, chain_store as cs, chains
def _now(): return time.strftime("%Y-%m-%dT%H:%M:%S")
def _read_ts(sms, k):
    try: return float(open(os.path.join(sms, "chains", k)).read())
    except Exception: return 0.0
def _fmt(t): return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(t)) if t else None
def interval_min(sms):
    try: return max(45, min(720, 45 + len(cs.Store(sms).all_frags()) // 20))
    except Exception: return 360
def next_run(sms): return _fmt(_read_ts(sms, "next_run_ts"))
def due(sms): nxt = _read_ts(sms, "next_run_ts"); None if nxt else schedule(sms); return bool(nxt) and time.time() >= float(nxt)
def schedule(sms): open(os.path.join(sms, "chains", "next_run_ts"), "w").write(str(time.time() + interval_min(sms) * 60)); return _now()
def maybe(sms): return due(sms) and bool(threading.Thread(target=run, args=(sms,), daemon=True).start() or True)
def run(sms):
    st = cs.Store(sms); r = {"merged": st.merge_near(), "pruned": st.prune()}; top = sorted(st.all_frags(), key=lambda f: -f.get("freq", 1))[:40]
    os.makedirs(os.path.join(sms, "chains"), exist_ok=True); open(os.path.join(sms, "chains", "retrieval.md"), "w", encoding="utf-8").write("\n".join("[%s·f%d] %s" % (f["id"], f["freq"], f["text"]) for f in top) or "（暂无）\n")
    r["pinned"] = _mem(sms, top); _audit(sms, r); _escalate(sms, r); open(os.path.join(sms, "chains", "last_run"), "w").write(str(time.time()))
    r["task"] = "做梦完成：合并%d 修剪%d 钉选%d 违规%d 升级%d" % (r["merged"], r["pruned"], r["pinned"], len(r.get("violations", [])), r.get("escalated", 0))
    chains.record("event", r["task"]); schedule(sms); return r
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
    elif cmd == "schedule": schedule(sms); print("触发时间由程序计算（间隔 %d 分·随链规模浮动·不可手动设置）：下次 %s" % (interval_min(sms), next_run(sms)))
    elif cmd == "maybe": print("spawned" if maybe(sms) else "未到期")
    else: print(json.dumps({"last_run": _read_ts(sms, "last_run") or None, "next_run_ts": _read_ts(sms, "next_run_ts") or None, "next_run": next_run(sms), "interval_min": interval_min(sms), "computed_by": "program", "due": due(sms)}, ensure_ascii=False))
