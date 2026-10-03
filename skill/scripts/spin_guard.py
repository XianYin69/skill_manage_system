#!/usr/bin/env python3
"""spin_guard.py — 壳自身「空转卡死」哨兵（2026-10-03 用户「解决卡死问题」）。

现场：sess-20261003-133957 的 Textual 壳 pid 14052 单线程 95% CPU 连烧 76 分钟、零输出
零产物，任务表 134231-131 余 3/5、135023-493 余 7/9 永不推进。机制＝自增强死循环：
某轮 worker 未收口 → busy 恒真 → ProgressBar(total=None) 常显 → Textual Bar.auto_refresh
=1/15 每帧整屏重绘 → RichLog 未设 max_lines、logbuf 无上限（该会话抽帧/OCR 海量输出）
→ 重绘代价爆炸 → UI 消息泵被自己饿死 → 收口消息再也处理不掉 → busy 永不清、条永不藏。
旧盲区：proc_guard/stall_class 只盯子进程且把 CPU 高一律判 computing（勿误杀），壳自身
空转在监控里隐形；全 scripts 无 faulthandler＝抓不到栈。

本模块补壳自身：① faulthandler 全程开（dump_traceback_later 独立线程，GIL 被死循环攥着
也能抓栈）；② 活性只认真进展（输出行/产物落盘/任务表行 done），UI 定时器自转不算进展；
③ 判自旋即分级：抓栈→藏 #prog 停动画（立刻还核子）→stop_channel 停在轮→仍不止则
shell_lifecycle.restart 自愈。零焦点侵入：不动前台窗口/不动光标/不激活窗口。
用法：python -B spin_guard.py status|probe <pid>|arm-test"""
import os, sys, time, json, ctypes, threading
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
SMS = None
def _home():
    global SMS
    if not SMS:
        import resolve_home; SMS = resolve_home.ensure()
    return SMS
def _cfg(k, d):
    try:
        import settings; return float(settings.get("shell." + k, d))
    except Exception: return float(d)
ST = {"beat": time.time(), "bkind": "boot", "app": None, "cpu": 0.0, "silent": 0.0,
      "verdict": "ok", "hits": 0, "armed": False, "hide_req": False, "last_ext": 0.0, "tid": ""}
class _FT(ctypes.Structure):
    """FILETIME（lo/hi 两个 DWORD）——进程 CPU 时间戳载体。"""
    _fields_ = [("lo", ctypes.c_uint32), ("hi", ctypes.c_uint32)]
def _cpu_ms(pid=0):
    """本进程（pid=0）或指定 pid 的 kernel+user CPU 毫秒；取不到回 -1。纯 ctypes，零依赖。
    64 位实测坑：GetCurrentProcess 的伪句柄 (HANDLE)-1 取回是 18446744073709551615，不给
    GetProcessTimes 声明 argtypes 就按 C int 回传 → OverflowError → 自测恒 -1 → rate 恒 0
    → 壳自身空转永远检不出（正是本修复要治的盲区）；故 argtypes 必声明＋伪句柄兜底。"""
    try:
        k = ctypes.windll.kernel32
        import ctypes.wintypes as wt
        LP = ctypes.POINTER(_FT)
        k.GetCurrentProcess.restype = wt.HANDLE; k.OpenProcess.restype = wt.HANDLE
        k.GetProcessTimes.restype = wt.BOOL
        k.GetProcessTimes.argtypes = [wt.HANDLE, LP, LP, LP, LP]
        own = (not pid) or int(pid) == os.getpid()
        h = k.GetCurrentProcess() if own else k.OpenProcess(0x1000, False, int(pid))
        if not h and own:
            h = k.OpenProcess(0x1000, False, os.getpid())   # 伪句柄不可用时的兜底
        if not h: return -1.0
        c, e, kr, us = _FT(), _FT(), _FT(), _FT()
        ok = k.GetProcessTimes(h, ctypes.byref(c), ctypes.byref(e), ctypes.byref(kr), ctypes.byref(us))
        if not own: k.CloseHandle(h)
        _v = lambda f: (f.hi << 32) | f.lo
        return (_v(kr) + _v(us)) / 10000.0 if ok else -1.0
    except Exception: return -1.0
def beat(kind="out", tid=""):
    """壳在「真进展」处调用：输出行 / 产物落盘 / 任务表行 done。UI 定时器自转绝不可调本函数。"""
    ST["beat"] = time.time(); ST["bkind"] = str(kind)[:24]
    if tid: ST["tid"] = str(tid)
def _ext_new(since):
    """外部进展证据：工作区 tmp 最新 mtime、runtime/procs.json mtime、tasks/*.json 最新 mtime。
    取不到一律回 0（宁缺勿误杀）。"""
    best = 0.0
    try:
        h = _home()
        for pat, root in ((None, os.path.join(h, "runtime")), ("*.json", os.path.join(h, "tasks"))):
            if not os.path.isdir(root): continue
            if pat is None:
                p = os.path.join(root, "procs.json")
                if os.path.isfile(p): best = max(best, os.path.getmtime(p))
            else:
                import glob as G
                for p in G.glob(os.path.join(root, pat)):
                    try: best = max(best, os.path.getmtime(p))
                    except Exception: pass
    except Exception: pass
    try:
        ws = os.environ.get("SMS_TMP") or ""
        for root, dirs, files in (os.walk(ws, topdown=True) if ws else []):
            dirs[:] = dirs[:8]
            for f in files[:200]:
                try: best = max(best, os.path.getmtime(os.path.join(root, f)))
                except Exception: pass
            break
    except Exception: pass
    return best
def dump_stack(why=""):
    """把全线程栈写 logs/spin.log（faulthandler 独立线程，死循环攥着 GIL 也能抓）。"""
    try:
        import faulthandler
        p = os.path.join(_home(), "logs"); os.makedirs(p, exist_ok=True)
        with open(os.path.join(p, "spin.log"), "a", encoding="utf-8") as f:
            f.write("\n==== spin dump %s %s ====\n" % (time.strftime("%H:%M:%S"), why))
            f.flush(); faulthandler.dump_traceback(file=f, all_threads=True); f.write("\n")
        return True
    except Exception: return False
def arm(app=None, tick_s=None):
    """壳启动时调一次：开 faulthandler（含 dump_traceback_later——GIL 被 C 调用攥死也能抓栈）
    ＋起守护线程。app 可空（无 UI 时只观测不处置）。"""
    if ST["armed"]: return status()
    ST["armed"] = True
    if app is not None: ST["app"] = app
    try:
        import faulthandler
        p = os.path.join(_home(), "logs"); os.makedirs(p, exist_ok=True)
        _fh = open(os.path.join(p, "spin.log"), "a", encoding="utf-8")
        faulthandler.enable(file=_fh, all_threads=True)
        faulthandler.dump_traceback_later(max(60.0, _cfg("spin_dump_s", 120)), repeat=True, file=_fh)
    except Exception: pass
    threading.Thread(target=_watch, args=(tick_s or _cfg("spin_tick_s", 5.0),), daemon=True, name="spin-guard").start()
    return status()
def _escalate(s):
    """分级处置：①抓栈＋记链＋通报 ②藏 #prog 停 15fps 动画 ③停在轮 ④重启自愈。"""
    n = int(s.get("hits") or 0)
    cpu = float(s.get("cpu_ms_per_s") or 0.0); sil = float(s.get("silent_s") or 0.0)
    bk = str(s.get("last_beat") or "")   # 键名以 status() 为准（旧代码 s["cpu"]/s["silent"]/s["bkind"] 必 KeyError）
    dump_stack("hit#%d cpu=%.0fms/s silent=%.0fs" % (n, cpu, sil))
    try:
        import chains; chains.record("event", "spin-detect hit=%d cpu_ms_s=%.0f silent=%.0fs beat=%s" % (n, cpu, sil, bk))
    except Exception: pass
    if n == 1:
        try:
            import qq_push; qq_push.push("⚠ 壳空转检出（CPU %.0f%%·%.0fs 无进展）：已停进度条动画回收核子，栈存 logs/spin.log" % (cpu / 10.0, sil))
        except Exception: pass
        ST["hide_req"] = True                       # UI tick 消费→藏 #prog（跨线程只置标志）
    if n >= 2:
        try:
            import stop_channel; stop_channel.request("spin-guard 空转自愈")
        except Exception: pass
    if n >= 3 and _cfg("spin_selfheal", 1) >= 1:
        try:
            import shell_lifecycle; shell_lifecycle.request("restart", "spin-selfheal cpu=%.0fms/s silent=%.0fs" % (cpu, sil))
        except Exception: pass
def _watch(tick_s):
    prev = _cpu_ms(); pts = time.time(); ext = 0.0
    while True:
        time.sleep(tick_s)
        now = time.time(); c = _cpu_ms()
        rate = (c - prev) / max(0.2, now - pts) if c >= 0 and prev >= 0 else 0.0   # ms CPU / s 墙钟
        prev, pts = c, now
        ext = max(ext, _ext_new(ext))
        silent = now - max(ST["beat"], ext or 0.0)
        ST["cpu"], ST["silent"] = rate, silent
        thr_c = _cfg("spin_cpu_ms_per_s", 600); thr_s = _cfg("spin_after_s", 60)
        if rate >= thr_c and silent >= thr_s:
            ST["hits"] += 1; ST["verdict"] = "spin"
            try:
                _escalate(status())      # 处置链任何异常都不得打死守护线程
            except Exception:
                dump_stack("escalate-error hit=%d" % ST["hits"])
        elif ST["verdict"] == "spin" and silent < thr_s:
            ST["verdict"] = "ok"; ST["hits"] = 0
        else:
            ST["verdict"] = "busy" if rate >= thr_c else "ok"
def tick(app=None):
    """UI 定时器调（1s）：消费 hide_req 藏掉不确定进度条——这是本次空转的放大器，
    藏下即停 15fps 整屏重绘，核子当场归还。绝不可在此调 beat()（自转不算进展）。"""
    a = app or ST["app"]
    if not ST["hide_req"] or a is None: return ST["verdict"]
    ST["hide_req"] = False
    try:
        from textual.widgets import ProgressBar
        a.query_one("#prog", ProgressBar).display = False
    except Exception: pass
    return ST["verdict"]
def stalled(): return ST["verdict"] == "spin"
def status():
    return {"pid": os.getpid(), "armed": ST["armed"], "verdict": ST["verdict"],
            "cpu_ms_per_s": round(ST["cpu"], 1), "silent_s": round(ST["silent"], 1),
            "hits": ST["hits"], "last_beat": ST["bkind"], "beat_age": round(time.time() - ST["beat"], 1),
            "thr": {"cpu_ms_per_s": _cfg("spin_cpu_ms_per_s", 600), "after_s": _cfg("spin_after_s", 60),
                    "selfheal": _cfg("spin_selfheal", 1)}}
def probe(pid):
    c = _cpu_ms(int(pid)); return {"pid": int(pid), "cpu_ms_total": c, "alive": c >= 0}
if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "probe" and len(a) > 1: print(json.dumps(probe(a[1]), ensure_ascii=False))
    elif a and a[0] == "test":
        arm(); t0 = time.time()
        while time.time() - t0 < 200: pass
    else:
        print(json.dumps(status(), ensure_ascii=False))
