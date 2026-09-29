#!/usr/bin/env python3
"""qq_dispatch.py — QQ 入站派发队列（2026-09-29 真根因修复：qq_listen 曾把 qq_inbound.handle 直接挂在 WS 循环线程上同步跑，deliver 里 agent_stream.ask 一阻塞就把续心跳、看门狗、退避重连全拖死——表现为 pid 假活、listen.heartbeat 停更、且无一条 down 日志。本模块＝纯 stdlib queue＋单工作线程的解耦层：submit(m) 只做非阻塞入队（队列满即丢弃并记审计，绝不反压 WS 线程，也不做磁盘写），worker 线程串行跑 qq_inbound.handle（QQ 侧本就逐条到达，串行还顺带防被动回复上下文 CTX 被并发写串台），WS 循环从此永不被 ask 阻塞，心跳与自愈各自独立。depth()/stats() 供 qq_watch/qq_cli 观测积压，ensure() 幂等起线程（daemon·随进程亡），stop() 投毒枚领取消。用法：python -B qq_dispatch.py stats|test [每条耗时秒]。"""
import os, sys, json, time, queue, threading
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
Q = queue.Queue(maxsize=64)
ST = {"in": 0, "drop": 0, "done": 0, "err": 0, "last": 0.0}
_T = [None]; LK = threading.Lock()
def _log(msg, chain=False):
    try: import qq_watch as W; W.log("派发 " + str(msg)[:160])
    except Exception: pass
    if chain:
        try: import chain_error; chain_error.hook("gate", "qq_dispatch", str(msg)[:200])
        except Exception: pass
def _work():
    while True:
        m = Q.get()
        if m is None: return
        try:
            import qq_inbound as I; r = I.handle(m); ST["done"] += 1
            if r: _log("done " + str(r)[:100])
        except Exception as e:
            ST["err"] += 1; _log("worker 异常 " + str(e)[:160], True)
        finally: ST["last"] = time.time(); Q.task_done()
def ensure():
    with LK:
        t = _T[0]
        if t and t.is_alive(): return t
        _T[0] = t = threading.Thread(target=_work, name="qq-dispatch", daemon=True); t.start(); return t
def submit(m, c=None):
    ensure()
    try: Q.put_nowait(m); ST["in"] += 1; return "queued·depth=%d" % Q.qsize()
    except queue.Full:
        ST["drop"] += 1; _log("队列满丢弃 msg_id=%s" % str(((m or {}).get("d") or {}).get("id"))[:24])
        return "drop·队列满"
def depth(): return Q.qsize()
def stats(): return dict(ST, depth=Q.qsize(), maxlen=Q.maxsize, thread=bool(_T[0] and _T[0].is_alive()))
def stop():
    try: Q.put_nowait(None)
    except queue.Full: pass
if __name__ == "__main__":
    a = sys.argv[1:] or ["stats"]
    if a[0] == "test":
        import qq_inbound as I; old = I.handle; dur = float(a[1]) if len(a) > 1 else 0.01
        I.handle = lambda m, c=None: time.sleep(dur); ensure()
        t0 = time.time(); [submit({"d": {"id": "p%d" % i}}) for i in range(3)]; enq = time.time() - t0; Q.join(); d0 = ST["drop"]
        [submit({"d": {"id": "o%d" % i}}) for i in range(Q.maxsize + 10)]; Q.join(); I.handle = old
        print(json.dumps({"入队3条耗时": round(enq, 4), "不阻塞WS": enq < 0.05, "消费done": ST["done"], "溢出丢弃": ST["drop"] - d0, "残留深度": depth(), "线程存活": stats()["thread"]}, ensure_ascii=False))
    elif a[0] == "stats": print(json.dumps(stats(), ensure_ascii=False))
    else: print(__doc__.strip()[:300])
