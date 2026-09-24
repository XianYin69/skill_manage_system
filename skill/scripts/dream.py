#!/usr/bin/env python3
"""dream.py — 做梦机制（惰性触发，红线 17）：距上次超过间隔（config dream_interval_min，默认 360 分钟）即在入口/写盘/派发时后台运行——跨链合并近义碎片、修剪陈旧低频（knowledge 钉选除外）、重建 <SMS_HOME>/chains/retrieval.md、高频 knowledge 同步 memory.json 钉选、审计对话开-收口与子会话悬挂（violations.md）、skill_errors 未解决≥3 记升级事件（经 user_commands skill-update→Skill_Generator 修改路径）、事件入 event 链。用法：python dream.py run|maybe|status [--sync]。"""
import os, sys, json, time, threading
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import resolve_home, chain_store as cs, chains
def _last(sms):
    try: return float(open(os.path.join(sms, "chains", "last_run")).read())
    except Exception: return 0.0
def due(sms): return time.time() - _last(sms) >= resolve_home.conf(sms).get("dream_interval_min", 360) * 60
def maybe(sms):
    if due(sms):
        threading.Thread(target=run, args=(sms,), daemon=True).start(); return True
    return False
def run(sms):
    st = cs.Store(sms); r = {"merged": st.merge_near(), "pruned": st.prune()}
    top = sorted(st.all_frags(), key=lambda f: -f.get("freq", 1))[:40]
    os.makedirs(os.path.join(sms, "chains"), exist_ok=True)
    open(os.path.join(sms, "chains", "retrieval.md"), "w", encoding="utf-8").write("\n".join("[%s·f%d] %s" % (f["id"], f["freq"], f["text"]) for f in top) or "（暂无）\n")
    r["pinned"] = _mem(sms, top); _audit(sms, r); _escalate(sms, r)
    open(os.path.join(sms, "chains", "last_run"), "w").write(str(time.time()))
    st.add("event", "做梦完成：合并%d 修剪%d 钉选%d 违规%d 升级%d" % (r["merged"], r["pruned"], r["pinned"], len(r["violations"]), r["escalated"]))
    return r
def _ld(p): return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None
def _wj(p, d): json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
def _mem(sms, top):
    p = os.path.join(sms, "memory.json"); doc = _ld(p) or {"updated": time.strftime("%Y-%m-%d"), "entries": []}
    have = {e["note"] for e in doc["entries"]}; nid = max([e["id"] for e in doc["entries"]], default=0); n = 0
    for f in [x for x in top if x["chain"] == "knowledge" and x["freq"] >= 3][:10]:
        if f["text"] not in have:
            nid += 1; doc["entries"].append({"id": nid, "date": f["ts"][:10], "path": "chains/knowledge/" + f["id"], "note": f["text"]}); n += 1
    if n: doc["updated"] = time.strftime("%Y-%m-%d"); _wj(p, doc)
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
            e["escalated"] = time.strftime("%Y-%m-%dT%H:%M:%S"); r["escalated"] += 1
            chains.record("event", "dream 升级：%s 错误≥3 → user_commands run skill-update %s（Skill_Generator 修改路径）" % (e.get("skill"), e.get("skill")))
    if r["escalated"]: _wj(p, doc)
if __name__ == "__main__":
    sms = resolve_home.ensure(); cmd = sys.argv[1] if len(sys.argv) > 1 else "status"; _m = (run(sms), True)[1] if "--sync" in sys.argv else maybe(sms)
    print(json.dumps(run(sms), ensure_ascii=False) if cmd == "run" else "spawned" if cmd == "maybe" and _m else
          json.dumps({"last_run": _last(sms), "due": due(sms), "interval_min": resolve_home.conf(sms).get("dream_interval_min", 360)}))
