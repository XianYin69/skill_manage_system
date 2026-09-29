#!/usr/bin/env python3
"""qq_stall.py — QQ 来源任务表的「卡住」看门狗（2026-09-29 用户「QQ 发起的会话其任务表因网络问题停滞时，主动推一条 ⚠任务表卡住 到我的 QQ」；后台范式照抄 qq_watch：daemon 线程＋节流＋异常全静默，绝不影响数据流）：判据＝<SMS_HOME>/tasks/*.json 里 src=="qq" 且仍有 pending/running 行的表，age＝now－文件 mtime（每次改表都 atomic_io.wjson 落盘→mtime 即「最后一次有进展」的时刻），age>stall_after（默认 180s）即卡住→qq_push.push「⚠任务表卡住 <tid尾14> <done>/<total> ▶<running行>（无 running 则 ▽）已 <N>s 无进展（疑似网络/网关中断）」tag=QQ·卡住；去重＝<SMS_HOME>/qq/stall.json{tid:{sig,last}}，sig＝尾14|done/total|running 行，同 sig 在 stall_repeat（默认 600s）内不重发（表真挪动→sig 变→可再报，进度未死则安静）；tick() 按 stall_tick（默认 30s）节流，start() 起 daemon 线程循环（qq_listen.run 进 Session 循环前调用，与监听器同生共死）；来源标记＝task_table._mkdoc 与 agent_task.task 建表时调 src() 写 doc["src"]，qq_inbound.deliver 在调 agent_stream.ask 前落 qq/active.json{conv,ts}，30min 内建的表判 qq 否则 shell（ask 内部才新建 conv、与派发时 conv 不同，故按时间窗判不按 conv 匹配）；开关阈值＝config/qq.json 的 stall/stall_after/stall_repeat/stall_tick（qq_cli conf k=v 改，本模块绝不写用户实值）。用法：python -B qq_stall.py check|tick|status。"""
import os, sys, time, json, threading
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import resolve_home, qq_push as qp; _last = {"t": 0.0}
def _td(sms=None): return os.path.join(sms or resolve_home.ensure(), "tasks")
def src(conv="", sms=None):
    """建表侧来源标记：qq/active.json 的 ts 距今 <1800s＝qq 否则 shell（读不到回 shell 保守不误报；ask 内才新建 conv、与派发时 conv 不同，故按时间窗判不按 conv 匹配）。"""
    try: return "qq" if time.time() - float((qp._ld(qp._f(sms or resolve_home.ensure(), "active.json"), {}) or {}).get("ts") or 0) < 1800 else "shell"
    except Exception: return "shell"
def _stat(s): return (sum(1 for x in s if x.get("status") == "done"), len(s), next((str(x.get("id")) for x in s if x.get("status") == "running"), ""))
def stalled(sms=None, c=None):
    """卡住表清单 [(doc,(done,total,running行),age_s)]：只认 src=="qq" 且仍有 pending/running 行的表，mtime＝最后一次改表（进展）时刻。"""
    c = c or qp.conf(sms); after = float(c.get("stall_after", 180)); now = time.time(); out = []; d = _td(sms)
    for fn in sorted(x for x in (os.listdir(d) if os.path.isdir(d) else []) if x.endswith(".json")):
        try: doc = qp._ld(os.path.join(d, fn), {}) or {}; subs = doc.get("subtasks") or []
        except Exception: continue
        if doc.get("src") != "qq" or not any(x.get("status") in ("pending", "running") for x in subs): continue
        try: age = int(now - os.path.getmtime(os.path.join(d, fn)))
        except OSError: continue
        if age > after: out.append((doc, _stat(subs), age))
    return out
def check(sms=None, c=None):
    """扫一遍并按需推送；同 sig 在 stall_repeat 内不重发，去重状态落 qq/stall.json{tid:{sig,last}}；返回已推文本列表。"""
    try:
        c = c or qp.conf(sms)
        if not c.get("stall", True) or not qp.ready(c): return []
        st = qp._ld(qp._f(c["sms"], "stall.json"), {}) or {}; hits = []
        for doc, (dn, tot, run), age in stalled(sms, c):
            tid = str(doc.get("id")); sig = "%s|%d/%d|%s" % (tid[-14:], dn, tot, run); v = st.get(tid) or {}
            if v.get("sig") == sig and time.time() - float(v.get("last") or 0) < float(c.get("stall_repeat", 600)): continue
            txt = "\u26a0任务表卡住 %s %d/%d %s 已 %ds 无进展（疑似网络/网关中断）" % (tid[-14:], dn, tot, ("\u25b6" + run) if run else "\u25bd", age)
            qp.push(txt, "QQ·卡住", c); hits.append(txt); st[tid] = {"sig": sig, "last": time.time()}
        qp._wj(qp._f(c["sms"], "stall.json"), st); return hits
    except Exception: return []
def tick(sms=None):
    """节流入口（stall_tick 默认 30s）：监听线程每轮调一次，未到窗口回「节流」。"""
    c = qp.conf(sms); now = time.time()
    if now - _last["t"] < float(c.get("stall_tick", 30)): return "节流"
    _last["t"] = now; return check(sms, c) or "无卡住"
def start(sms=None):
    """起 daemon 线程循环（幂等·qq_listen.run 进 Session 循环前调用）：每 5s 醒一次，tick 自按 stall_tick 节流；线程随进程亡，绝不拖住退出。"""
    if getattr(start, "_t", None): return start._t
    def loop():
        while True:
            try: time.sleep(5); tick(sms)
            except Exception: pass
    start._t = threading.Thread(target=loop, daemon=True, name="qq-stall"); start._t.start(); return start._t
def status(sms=None, c=None): c = c or qp.conf(sms); return {"stall": bool(c.get("stall", True)), "after": c.get("stall_after"), "repeat": c.get("stall_repeat"), "tick": c.get("stall_tick"), "watching": len(stalled(sms, c)), "thread": bool(getattr(start, "_t", None)), "src": src(sms=sms), "state": qp._ld(qp._f(c["sms"], "stall.json"), {}) or {}}
if __name__ == "__main__":
    a = sys.argv[1:] or ["status"]; print(json.dumps(status(), ensure_ascii=False, indent=1) if a[0] == "status" else json.dumps(check(), ensure_ascii=False) if a[0] == "check" else str(tick()) if a[0] == "tick" else __doc__.strip()[:300])
