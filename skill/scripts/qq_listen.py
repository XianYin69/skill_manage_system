#!/usr/bin/env python3
"""qq_listen.py — QQ 入站常驻监听器（2026-09-29 用户「我要发消息给你」；「该机器人未连接灵魂」＝本机没有常驻消费进程，本模块就是那个「灵魂」）：仿 dream_bg 后台范式——spawn 起分离子进程 `python -B qq_listen.py run`（DETACHED·stdout/stderr→<SMS_HOME>/qq/listen.log·不随壳退出而亡·防重复拉起），run 内写 pid 文件后跑 qq_session.Session(on_event=qq_inbound.handle).loop()，每次状态变化经 qq_watch.beat 续心跳＋qq_watch.log 记流水（identified/live/down），断线指数退避自动重连；stop 读 pid 用 taskkill 终止并清 pid/心跳文件；status/badge 转调 qq_watch（判活与顶栏徽标同口径）。启动前置校验＝qq_push.ready（未绑定/未启用直接拒绝并提示 :qq bind / :qq on），intents 无权限（4013/4014）时自动降级只订 1<<25 重试一次，仍失败则记 error 链并提示去开放平台补权限。用法：python -B qq_listen.py spawn|run|stop|status|badge|tail [n]。"""
import os, sys, time, json, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import resolve_home, qq_push as qp, qq_watch as W
HERE = os.path.dirname(os.path.abspath(__file__))
def _w(n, v, sms=None):
    os.makedirs(W._d(sms), exist_ok=True); open(W._f(n, sms), "w", encoding="utf-8").write(v)
def run(sms=None):
    import qq_session as S, qq_inbound as I
    c = qp.conf(sms)
    if not qp.ready(c): W.log("拒绝启动：未绑定或未启用（:qq bind / :qq on）", sms); return "未绑定或未启用 QQ——监听器不启动"
    _w("listen.pid", "%d|%d" % (os.getpid(), time.time()), sms); W.log("启动 pid=%d" % os.getpid(), sms)
    for it, last in ((S.I_MSG | S.I_INT, False), (S.I_MSG, True)):
        st = {"bad": 0}
        def on_state(s, x="", st=st):
            W.beat(s, sms); W.log(s + ((" " + x) if x else ""), sms)
            if s == "down" and any(k in x for k in ("Invalid Session", "4013", "4014", "intent")): st["bad"] += 1
            elif s == "identified": st["bad"] = 0
        S.Session(lambda m: I.handle(m), c, intents=it).loop(alive=lambda: last or st["bad"] < 3, on_state=on_state)
        if last: break
        W.log("intents=%d 连续被拒，降级只订 1<<25 重试" % it, sms)
    return "监听循环退出"
def spawn(sms=None):
    if W.alive(sms): d = W.status(sms); return "已在监听（pid=%d·%s）" % (d["pid"], d["state"] or "?")
    if not qp.ready(qp.conf(sms)): return "未绑定或未启用 QQ（:qq bind / :qq on）——监听器不启动"
    os.makedirs(W._d(sms), exist_ok=True)
    f = open(os.path.join(W._d(sms or resolve_home.ensure()), "listen.log"), "ab")
    subprocess.Popen([sys.executable, "-B", os.path.join(HERE, "qq_listen.py"), "run"], stdin=subprocess.DEVNULL, stdout=f, stderr=f, cwd=HERE,
                     creationflags=(0x00000008 | 0x00000200) if os.name == "nt" else 0)
    time.sleep(2.0); d = W.status(sms)
    return "已拉起（pid=%s·running=%s·state=%s·ready=%s）" % (d["pid"], d["running"], d["state"] or "-", d["ready"])
def stop(sms=None):
    p = W._pid(sms)
    if not p: return "未在监听（无 pid 记录）"
    try: subprocess.run((["taskkill", "/PID", str(p), "/F"] if os.name == "nt" else ["kill", str(p)]), capture_output=True, timeout=15)
    except Exception as e: return "终止失败：" + str(e)[:120]
    for n in ("listen.pid", "listen.heartbeat"):
        try: os.remove(W._f(n, sms))
        except OSError: pass
    W.log("已停止 pid=%d" % p, sms); return "已停止 QQ 入站监听（pid=%d）" % p
if __name__ == "__main__":
    a = sys.argv[1:] or ["status"]
    if a[0] == "run": print(run())
    elif a[0] == "spawn": print(spawn())
    elif a[0] == "stop": print(stop())
    elif a[0] == "tail": print(W.tail(a[1] if len(a) > 1 else 12))
    elif a[0] == "badge": print(W.badge())
    else: print(json.dumps(W.status(), ensure_ascii=False, indent=1))
