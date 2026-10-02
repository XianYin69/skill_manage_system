#!/usr/bin/env python3
"""qq_watch.py — QQ 入站监听器「真在后台跑」判活＋顶栏徽标（2026-09-29·与做梦 dream_watch 同范式）：pid 文件 <SMS_HOME>/qq/listen.pid（pid|ts）＋心跳文件 qq/listen.heartbeat（pid|ts|state）双证——① 纯进程判活 pid_alive()（OpenProcess＋GetExitCodeProcess==259，绝不用 os.kill(pid,0)，Windows 下会误杀）② 心跳新鲜（窗口 HB=180s·重连退避最长 60s）；alive()＝「真在听」＝pid 文件有 pid＋心跳新鲜＋心跳里的 pid 与 pid 文件里的 pid 相符（pid 被别的程序复用时句柄仍成功，旧口径恒真致 qq_boot/qq_listen 拒绝重拉、僵尸永不自愈）；status() 回 running（纯进程）/listening（真在听）/pid/hb_pid/beat_age/state/fresh/zombie/ready，僵尸＝记了 pid 但进程已死或心跳过期（:qq lstatus 据此报「后台未真执行」）；badge() 供顶栏：在听＝「◌QQ入站·<state>」、僵尸＝「⚠QQ监听中断」、未启＝空串；log() 追加 qq/listen.log 业务流水，tail() 取末 n 行。用法：python -B qq_watch.py status|badge|beat <状态>|tail [n]。"""
import os, sys, time, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import resolve_home, qq_push as qp
HB = 180.0
def _d(sms=None): return os.path.join(sms or resolve_home.ensure(), "qq")
def _f(n, sms=None): return os.path.join(_d(sms), n)
def _rd(n, sms=None):
    try: return open(_f(n, sms), encoding="utf-8").read().strip()
    except Exception: return ""
def _pid(sms=None):
    try: return int(_rd("listen.pid", sms).split("|")[0])
    except Exception: return 0
def pid_alive(p):
    """纯进程判活（保留原 ctypes OpenProcess＋GetExitCodeProcess==259 逻辑·非 nt 退 os.kill）：
    pid 可能被别的程序复用，句柄成功≠监听还活着，故只供 status() 区分「进程死」与「心跳过期」。"""
    p = int(p or 0)
    if not p: return False
    if os.name != "nt":
        try: os.kill(p, 0); return True
        except Exception: return False
    import ctypes; k = ctypes.windll.kernel32; h = k.OpenProcess(0x1000, False, p); c = ctypes.c_ulong()
    r = bool(h) and k.GetExitCodeProcess(h, ctypes.byref(c)) and c.value == 259
    if h: k.CloseHandle(h)
    return bool(r)
def _hbrow(sms=None):
    """心跳行拆成 (pid, age, state)；无文件/解不出＝(0, 1e9, "")。"""
    try:
        q = _rd("listen.heartbeat", sms).split("|")
        hp = int(q[0]) if q and q[0].strip().isdigit() else 0
        return hp, time.time() - float(q[1]), (q[2] if len(q) > 2 else "")
    except Exception: return 0, 1e9, ""
def alive(sms=None):
    """「真在听」判活（QQ 无法连接的真根因修复：pid 被别的程序复用→OpenProcess 仍成功→旧 alive 恒真→
    qq_boot.autostart 与 qq_listen.spawn 都拒绝重拉、僵尸永不自愈）。nt 口径＝①pid 文件有 pid
    ②心跳存在且新鲜（age<HB）③心跳里的 pid == pid 文件里的 pid，三条同时满足；
    非 nt 保持原语义（进程探活）但同样要求心跳新鲜。"""
    p = _pid(sms)
    if not p: return False
    hp, age, _st = _hbrow(sms)
    if os.name != "nt": return bool(pid_alive(p) and age < HB)
    return bool(age < HB and hp and hp == p)
def beat(state, sms=None):
    try: open(_f("listen.heartbeat", sms), "w", encoding="utf-8").write("%d|%d|%s" % (os.getpid(), time.time(), str(state)[:60])); return True
    except Exception: return False
def _hb(sms=None):
    _hp, age, st = _hbrow(sms); return age, st
def status(sms=None):
    """running＝纯进程判活（pid_alive·pid 可能被复用故不等于在监听），listening＝真在听（alive），
    zombie 口径不变＝记了 pid 且（进程已死或心跳过期）。"""
    pid = _pid(sms); hp, age, st = _hbrow(sms); fresh = age < HB; pa = pid_alive(pid)
    return {"running": pa, "pid": pid, "hb_pid": hp, "beat_age": None if age > 1e8 else round(age, 1),
            "state": st, "fresh": fresh, "listening": alive(sms),
            "zombie": bool(pid) and (not pa or not fresh), "ready": qp.ready()}
def badge(sms=None):
    d = status(sms)
    if d["zombie"]: return "⚠QQ监听中断"
    return ("◌QQ入站·" + (d["state"] or "?")) if d["running"] and d["fresh"] else ""
def log(txt, sms=None):
    try: os.makedirs(_d(sms), exist_ok=True); open(_f("listen.log", sms), "a", encoding="utf-8").write(time.strftime("%m-%d %H:%M:%S ") + str(txt) + "\n")
    except Exception: pass
def tail(n=12, sms=None):
    try: return "\n".join(open(_f("listen.log", sms), encoding="utf-8", errors="replace").read().splitlines()[-int(n):]) or "（日志空）"
    except Exception: return "（无日志）"
if __name__ == "__main__":
    a = sys.argv[1:] or ["status"]
    print(json.dumps(status(), ensure_ascii=False, indent=1) if a[0] == "status" else badge() if a[0] == "badge"
          else str(beat(" ".join(a[1:]) or "manual")) if a[0] == "beat" else tail(a[1] if len(a) > 1 else 12) if a[0] == "tail" else __doc__.strip()[:260])
