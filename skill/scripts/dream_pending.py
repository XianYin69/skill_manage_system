#!/usr/bin/env python3
"""dream_pending.py — 做梦受阻待批队列（2026-09-29 用户「做梦遇到需权限或其他原因无法后台操作时，空闲时以前台提示提醒用户，征得同意后继续修复」）：台账 <SMS_HOME>/dream/pending.json＝[{id,kind,target,reason,how,first,last,count,status}]；add() 幂等合并计数（同 kind+target+reason）并落 error 链；due() 空闲判定＝做梦未在跑（dream_watch.state.running 假）且有 open 项，供顶栏徽标/右栏提示；take/drop 供 :repair go|skip 消费；badge()＝「⚠修复待批N」。前台续跑由 dream_repair.resume() 执行（用户当轮 :repair go＝同意，权限齐备当场修，修好 chain_error.resolve）；auto_solo()＝SOLO 自动同意版（solo.auto_pending 为真时对 due() 每条 open 项逐条 resume 并回汇总串，为假回 None 与今天逐字一致，空闲收口处由 shell_tui_flow 调用）。用法：python -B dream_pending.py list|add <kind> <target> <reason>|drop <id> [status]"""
import os, sys, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import resolve_home, atomic_io, chains
def _d(sms): return os.path.join(sms, "dream")
def _p(sms): return os.path.join(_d(sms), "pending.json")
def _doc(sms): return atomic_io.rjson(_p(sms), default=[]) or []
def _save(sms, rows): os.makedirs(_d(sms), exist_ok=True); atomic_io.wjson(_p(sms), rows)
def add(kind, target, reason, how=None, sms=None):
    sms = sms or resolve_home.ensure(); rows = _doc(sms); now = time.strftime("%Y-%m-%dT%H:%M:%S")
    try:
        import chain_error
        if chain_error.selffix(reason): return "selffix"
    except Exception: pass
    r = next((x for x in rows if x["kind"] == kind and x["target"] == target and x["reason"] == reason and x["status"] == "open"), None)
    if r: r["last"] = now; r["count"] += 1
    else: rows.append({"id": "%s-%d" % (kind, int(time.time())), "kind": kind, "target": str(target)[:80], "reason": str(reason)[:160],
                       "how": how or {}, "first": now, "last": now, "count": 1, "status": "open"})
    _save(sms, rows); __import__("qq_flow").fire("pending", rows[-1]); chains.record("event", "做梦待批登记·%s·%s：%s" % (kind, str(target)[:40], str(reason)[:100])); return rows[-1]["id"]
def open_rows(sms=None): return [x for x in _doc(sms or resolve_home.ensure()) if x.get("status") == "open"]
def due(sms=None):
    sms = sms or resolve_home.ensure()
    try:
        import dream_watch
        if dream_watch.state(sms)["running"]: return []
    except Exception: pass
    return open_rows(sms)
def take(fid, sms=None):
    r = next((x for x in _doc(sms or resolve_home.ensure()) if x["id"] == fid), None)
    return r or "无此项：" + str(fid)
def drop(fid, status="skipped", sms=None):
    sms = sms or resolve_home.ensure(); rows = _doc(sms); n = 0
    for x in rows:
        if x["id"] == fid: x["status"] = status; x["last"] = time.strftime("%Y-%m-%dT%H:%M:%S"); n += 1
    _save(sms, rows); return "已置 %s：%s" % (status, fid) if n else "无此项"
def badge(sms=None):
    d = due(sms); return ("⚠修复待批%d" % len(d)) if d else ""
def auto_solo(sms=None):
    """SOLO 自动同意并续跑修复待批（solo.auto_pending() 为假直接回 None＝零回归）：
    为真则对 due() 的每条 open 项调 dream_repair.resume(id) 逐条续跑，回汇总串（成功几条/失败几条）；
    每条与总结均经 chains.record("event",…) 留痕，末尾由 qq_flow 通报一句结果。"""
    sms = sms or resolve_home.ensure()
    try:
        import solo
        if not solo.auto_pending(): return None
    except Exception: return None
    rows = due(sms)
    if not rows: return None
    ok = bad = 0; notes = []
    for r in rows:
        fid = r.get("id")
        try:
            import dream_repair
            out = str(dream_repair.resume(fid, sms))
        except Exception as e:
            out = "续跑异常：" + str(e)[:80]
        if out.startswith("已续跑修复"): ok += 1
        else: bad += 1
        notes.append("%s→%s" % (str(fid), out[:60]))
        chains.record("event", "SOLO自动同意待批·%s：%s" % (str(fid), out[:120]))
    msg = "SOLO 自动同意并续跑修复待批：成功%d·未成%d（%s）" % (ok, bad, "；".join(notes)[:200])
    chains.record("event", msg)
    try: __import__("qq_flow").fire("SOLO待批", msg)
    except Exception: pass
    return msg
if __name__ == "__main__":
    a = sys.argv[1:] or ["list"]; sms = resolve_home.ensure()
    if a[0] == "add" and len(a) > 2: print(add(a[1], a[2], " ".join(a[3:]) or "未说明"))
    elif a[0] in ("plan", "fix"): 
        import dream_repair; print(json.dumps(dream_repair.plan(sms) if a[0] == "plan" else dream_repair.fix(sms), ensure_ascii=False, indent=1))
    elif a[0] == "go" and len(a) > 1:
        import dream_repair; print(dream_repair.resume(a[1], sms))
    elif a[0] == "drop" and len(a) > 1: print(drop(a[1], a[2] if len(a) > 2 else "skipped"))
    else:
        d = due(sms); print(json.dumps(d, ensure_ascii=False, indent=1) if d else "（空闲无待批修复·做梦受阻项已清零）")