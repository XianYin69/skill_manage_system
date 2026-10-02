#!/usr/bin/env python3
"""shell_lifecycle.py — SMS 壳生命周期（2026-09-29 用户「菜单里加入 重启SMS 和 关闭SMS」；2026-09-30 三条升级：① 手动 :restart/:shutdown 与关窗口/Ctrl+C 一律二次确认；② 关闭/重启前向远端推送「SMS关闭中」；③ 大模型可依任务要求重启，重启后继续执行任务，且重启完只保留新实例——旧进程必须死）。
restart＝通报→写旗标→落链→分离式拉起 bin/sms-shell.py（新窗）→kill_others 清掉所有旧壳（含本进程，os._exit 硬退，杜绝新旧并存）；
shutdown＝通报＋收 HUD/TTS＋清旧壳＋落链；
request(action,why)＝大模型侧入口（exec 跑 `python -B shell_lifecycle.py request restart 原因`）：只写 <SMS_HOME>/shell/lifecycle.json，由壳在本轮数据流收口时经 run_pending() 自己执行——当前对话先把话说完、任务表先落盘，再重启；
cmd(m,sms,on_line)＝手动入口（F1 菜单与 readline 兜底壳同径）：15 秒内连点两次才真做；
resume(sms)＝重启后「继续执行任务」单一入口（回 (提示文案, 续跑话语或 None)·旗标一次性消费并留档；resume_hint/auto_resume 为委托它的兼容壳，不再二次消费旗标；开关 settings shell.auto_resume 默认开）。
用法：python -B shell_lifecycle.py restart|shutdown|status|request <action> [原因]"""
import os, sys, json, time, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import resolve_home, chains, chain_timing, close_guard as cg
S = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.join(os.path.dirname(os.path.dirname(S)), "bin", "sms-shell.py")
PATTERNS = ("shell_tui_textual.py", "shell_tui.py", "shell_console.py", "shell_gui.py", "sms-shell.py")
CONF = {"m": "", "at": 0.0}
def _p(sms): return os.path.join(sms, "shell", "restart.json")
def _flag(sms, on):
    os.makedirs(os.path.dirname(_p(sms)), exist_ok=True)
    json.dump({"at": time.strftime("%Y-%m-%d %H:%M:%S"), "relaunched": bool(on)}, open(_p(sms), "w", encoding="utf-8"))
def pending(sms=None):
    """读并清重启旗标（新实例 startup 用）。"""
    sms = sms or resolve_home.ensure()
    try: d = json.load(open(_p(sms), encoding="utf-8"))
    except Exception: return None
    try: os.remove(_p(sms))
    except Exception: pass
    return d if d.get("relaunched") else None
def _shell_pids(exclude=()):
    """按命令行特征列出其它 SMS 壳进程（排除自己与 exclude 里的新实例）。"""
    keep = set([os.getpid()] + [int(x) for x in exclude if x])
    q = "Get-CimInstance Win32_Process -Filter \"Name like '%python%'\" | ForEach-Object { \"$($_.ProcessId)`t$($_.CommandLine)\" }"
    try:
        # 实测一次 PowerShell 查询约 1.1s：25s 上限＝网关/PS 卡住时，用户点「确认关闭」最长干等 25 秒，
        # 正是「点了没关」的观感来源。5s 足够；超时回 [] 由 kill_services 的 ctypes 路径兜底。
        out = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", q], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=5).stdout
    except Exception: return []
    hits = []
    for ln in out.splitlines():
        pid, _, cl = ln.partition("\t")
        if cl and any(pt in cl for pt in ("shell_tui_textual.py", "shell_tui.py", "shell_console.py", "shell_gui.py", "sms-shell.py")) and pid.strip().isdigit() and int(pid) not in keep:
            hits.append(int(pid))
    return hits

def kill_others(exclude=(), why=""):
    """清掉旧壳进程——重启后只保留新实例（2026-09-30 用户「重启完 SMS 会有两个进程，只保留重启之后的」）。"""
    gone = []
    for pid in _shell_pids(exclude):
        try:
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, timeout=15)
            gone.append(pid)
        except Exception: pass
    gone and chains.record("event", "shell-kill-others %s（%s）" % (",".join(map(str, gone)), why or "restart"))
    return gone
SVC = (("web_shell", ("shell", "web_shell.pid")), ("planned", ("planned", "serve.pid")),
       ("hud", ("hud", "state.json.pid")), ("qq_listen", ("qq", "listen.pid")))
def _alive(pid):
    """ctypes 真判活（GetExitCodeProcess==259·绝不用 os.kill 防误杀）。"""
    try:
        import ctypes
        k = ctypes.windll.kernel32
        h = k.OpenProcess(0x1004, False, int(pid))
        if not h: return False
        c = ctypes.c_ulong(); ok = k.GetExitCodeProcess(h, ctypes.byref(c)); k.CloseHandle(h)
        return bool(ok) and c.value == 259
    except Exception: return True
def kill_services(exclude=(), sms=None, budget=1.5, why=None):
    """回收壳自己拉起的一切后台进程——DETACHED 子进程不随 os._exit 而亡，正是「点了确认关闭程序还在」的真根因。
    两路取 pid：① SVC pid 文件表（web_shell/planned/hud/qq_listen·不活只清文件绝不误杀）② 本进程全部后代
    （proc_guard ctypes Toolhelp32·零 PowerShell）。taskkill /T /F 逐个杀，总预算 budget 秒，异常一律静默。
    why＝调用场景（close_guard._bye 按规格传「窗口/控制事件」·缺省按 close 记链）。"""
    t0 = time.time(); sms = sms or resolve_home.ensure()
    keep = set([os.getpid()] + [int(x) for x in exclude if x]); pids = []
    for _name, rel in SVC:
        try:
            p = os.path.join(sms, *rel)
            if not os.path.exists(p): continue
            pid = int((open(p, encoding="utf-8").read() or "0").split("|")[0].strip() or 0)
            if pid and pid not in keep and _alive(pid): pids.append(pid)
            else:
                try: os.remove(p)
                except Exception: pass
        except Exception: pass
    try:
        import proc_guard as pg
        for d in pg.descendants(os.getpid()):
            if d not in keep and d not in pids and _alive(d): pids.append(d)
    except Exception: pass
    for pid in pids:
        if time.time() - t0 > budget: break
        try: subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, timeout=3)
        except Exception: pass
    pids and chains.record("event", "shell-kill-services %s（%s）" % (",".join(map(str, pids)), why or "close"))
    return pids
def _push_async(text, wait=1.2):
    """远端通报挪到 daemon 线程（旧版同步 urlopen timeout=8s＝确认关闭后干等 8 秒＝「没关」错觉）。"""
    import threading
    try:
        t = threading.Thread(target=cg.push, args=(text,), daemon=True); t.start(); t.join(wait)
    except Exception: pass
def _bye(sms, tag):
    chains.record("event", tag + " " + time.strftime("%Y-%m-%dT%H:%M:%S"))
    try: chain_timing.flush()
    except Exception: pass
def _spawn(sms):
    if not os.path.isfile(BIN): return ("启动器缺失：" + BIN, None)
    kw = {"creationflags": 0x00000010, "stdin": subprocess.DEVNULL} if os.name == "nt" else {"start_new_session": True, "stdin": subprocess.DEVNULL}
    try:
        pr = subprocess.Popen([sys.executable, "-B", BIN], cwd=os.path.dirname(BIN), env=dict(os.environ, SMS_SESSION=chains.cur_sess()), **kw)
    except Exception as e:
        import chain_error; chain_error.record("shell", "shell_lifecycle._spawn", str(e))
        return ("拉起失败：" + str(e)[:120], None)
    return ("已拉起新实例 pid=%s（%s）" % (pr.pid, BIN), pr.pid)

def restart(sms=None, why="", hard=True):
    """重启：通报远端→写旗标→拉起新实例→清旧壳（含本进程）。非壳进程（exec 子进程）调用＝只登记请求，交壳收口时执行。"""
    sms = sms or resolve_home.ensure()
    if not _is_shell(): return request("restart", why)
    cg.push("SMS 重启中（%s）· %s" % (why or "restart", time.strftime("%H:%M:%S")))
    _flag(sms, True); _bye(sms, "shell-restart")
    r, newpid = _spawn(sms)
    if not newpid: return r
    time.sleep(1.0)
    # 先收用户看得见的服务，再跑慢的 PowerShell 清旧壳；新实例 on_mount 会重拉服务
    kill_services(exclude=[newpid], why="restart")
    kill_others(exclude=[newpid], why=why or "restart")
    if hard:
        try: chain_timing.flush()
        except Exception: pass
        os._exit(0)   # 本进程必死——旧实例不留（用户「只保留重启之后的」）
    return r
def shutdown(sms=None, why="", hard=True):
    """关闭：通报远端→收 HUD/TTS→清所有壳进程。非壳进程调用＝只登记请求。"""
    sms = sms or resolve_home.ensure()
    if not _is_shell(): return request("shutdown", why)
    _push_async("SMS 关闭中（%s）· %s" % (why or "shutdown", time.strftime("%H:%M:%S")))
    _flag(sms, False)
    try:
        import hud; hud._stop()
    except Exception: pass
    try:
        import tts; hasattr(tts, "stop") and tts.stop()
    except Exception: pass
    # 先收用户看得见的置顶 HUD/网页壳，再跑慢的 PowerShell 清其它实例（kill_others→_shell_pids）
    kill_services(why="shutdown")  # 关壳必清后台＝批29 真根因（DETACHED 不随 os._exit 而亡）
    _bye(sms, "shell-shutdown"); kill_others(why=why or "shutdown")
    if hard:
        try: kill_services(budget=0.4, why="shutdown-hard")
        except Exception: pass
        try: chain_timing.flush()
        except Exception: pass
        os._exit(0)
    return "已关闭SMS：HUD/后台已收，本壳退出"

def _is_shell():
    """本进程是不是壳：argv 命中 PATTERNS 即真（旧版跑 PowerShell 查自身命令行＝实测 2.24s 白等，
    点「确认关闭」后数秒无反馈正是「看起来没关」的成因之一）。取不到一律按壳处理＝宁硬退不误登记。"""
    try:
        cl = " ".join([os.path.basename(sys.executable)] + sys.argv)
    except Exception:
        return True
    return any(pt in cl for pt in PATTERNS)
def request(action, why="", sms=None):
    """大模型侧入口：登记 restart/shutdown，本轮数据流收口时由壳自己执行（先说完话、先落任务表）。"""
    return cg.request(action, why, sms)
def run_pending(sms=None, allow=False):
    """壳在每轮数据流收口处调用：有登记的请求就真执行（壳自己＝含 os._exit 硬退；
    allow=True 的宿主（QQ 监听器这类常驻非壳进程）也可代为执行——拉起新实例＋清掉旧壳，宿主自己不死、通道不断。"""
    d = cg.peek(sms)
    if not d: return None
    if not (_is_shell() or allow): return None
    cg.pending(sms)
    a = str(d.get("action") or "")
    return restart(sms, "大模型请求·" + str(d.get("why") or ""), hard=_is_shell()) if a == "restart" else shutdown(sms, "大模型请求·" + str(d.get("why") or ""), hard=_is_shell()) if a == "shutdown" else None
def cmd(m, sms=None, on_line=None, force=False):
    """手动入口（F1 菜单 :restart/:shutdown·readline 兜底壳同径）：15 秒内连点两次才真做＝二次确认（settings close_guard.enabled=false 时首枪即真做，restart/shutdown 内部仍向远端通报）。"""
    now = time.time()
    if not force and cg.enabled() and not (CONF["m"] == m and now - CONF["at"] < 15):
        CONF.update(m=m, at=now)
        msg = ("⚠ 二次确认：%s 已收到第一次——再执行一次 :%s（15 秒内）才真%s；任务进行中建议先 F11 停止。" % ("重启SMS" if m == "restart" else "关闭SMS", m, "重启" if m == "restart" else "关闭"))
        on_line and on_line(msg)
        return msg
    CONF.update(m="", at=0.0)
    on_line and on_line(("已拉起新实例并清掉旧壳＝重启SMS 完成" if m == "restart" else "已关闭SMS：HUD/后台已收·远端已通报"))
    return restart(sms, "用户手动 :restart") if m == "restart" else shutdown(sms, "用户手动 :shutdown")

_LAST = None
def resume(sms=None):
    """重启后唯一入口：一次性算出（提示文案, 自动续跑话语或 None）——旗标只消费一次，结果留档 _LAST 供 resume_hint/auto_resume 兼容壳复用。"""
    global _LAST
    if not pending(sms):
        _LAST = ("", None); return _LAST
    try:
        import task_table as tt, settings
        un = tt.unfinished(); auto = bool(settings.get("shell.auto_resume", True))
    except Exception:
        _LAST = ("已重启（上一实例退出）。", None); return _LAST
    if not un:
        _LAST = ("已重启（上一实例退出·无未完成任务表）。", None); return _LAST
    top = "；".join("%s（%d/%d）" % (t[-14:], d, n) for t, d, n in un[:3])
    hint = "⟳ 重启完成：检测到未完成任务表 %d 张（%s）——%s" % (
        len(un), top, "本轮自动续跑（:config set shell.auto_resume false 可关）" if auto else "按 F12／输「继续任务」续跑")
    _LAST = (hint, "继续任务（重启后自动续跑·见〔任务表〕未完成行）" if auto else None)
    return _LAST
def resume_hint(sms=None):
    """兼容壳（旧入口·新代码请直接用 resume）：文案取 resume()，旗标已被 resume 消费过则复用留档，绝不二次消费。"""
    return (resume(sms) if _LAST is None else _LAST)[0]
def auto_resume(sms=None):
    """兼容壳（旧入口·新代码请直接用 resume）：续跑话语取 resume()[1]（同上·不二次消费旗标）。"""
    return (resume(sms) if _LAST is None else _LAST)[1]
def _selftest():
    """批29 回归（python -B shell_lifecycle.py selftest）：① _is_shell 零 PowerShell ② kill_services 真收
    DETACHED 后代 ③ 死 pid 只清文件不误杀。回收只在 tmp 镜像根里跑＝真服务进程不受扰；真实 pid 文件先备份后还原。"""
    import shutil, tempfile
    t = time.time(); assert not _is_shell(), "直跑本文件应判非壳（argv 不含 PATTERNS）"
    dt = time.time() - t
    assert dt < 0.2, "_is_shell 耗时 %.3fs＝仍在跑 PowerShell（旧版实测 2.24s）" % dt
    sms = resolve_home.ensure(); bak = {}
    for _n, rel in SVC:  # 真实 pid 文件先备份（测试全程不写它们＝兜底防污染）
        p = os.path.join(sms, *rel)
        bak[p] = open(p, "rb").read() if os.path.exists(p) else None
    root = tempfile.mkdtemp(prefix="lc_selftest_"); pr = None
    try:
        pr = subprocess.Popen([sys.executable, "-B", "-c", "import time;time.sleep(60)"],
                              creationflags=0x08000000 | 0x8)
        time.sleep(0.4)
        import proc_guard as pg
        assert pr.pid in pg.descendants(os.getpid()), "Toolhelp32 后代枚举未命中测试孙进程 %s" % pr.pid
        got = kill_services(sms=root, budget=2.0)
        assert pr.pid in got, "kill_services 未收到后代（got=%s）" % got
        time.sleep(1.2)
        assert not _alive(pr.pid), "DETACHED 孙进程仍活着＝真根因未修"
        dead = os.getpid() + 10 ** 6
        pf = os.path.join(root, "planned", "serve.pid")
        os.makedirs(os.path.dirname(pf), exist_ok=True)
        open(pf, "w", encoding="utf-8").write("%d|%d" % (dead, time.time()))
        got2 = kill_services(sms=root, budget=1.0)
        assert dead not in got2, "死 pid 进了回收表＝pid 复用会误杀（got=%s）" % got2
        assert not os.path.exists(pf), "死 pid 文件未被清（残留＝下次误判在跑）"
        assert not _alive(dead), "死 pid 竟判活"
    finally:
        try:
            pr and pr.kill()
        except Exception: pass
        shutil.rmtree(root, ignore_errors=True)
        for p, data in bak.items():  # 还原真实 pid 文件
            try:
                if data is None:
                    os.path.exists(p) and os.remove(p)
                else:
                    os.makedirs(os.path.dirname(p), exist_ok=True)
                    open(p, "wb").write(data)
            except Exception: pass
    print("selftest OK（_is_shell %.3fs·零 PowerShell）" % dt)
if __name__ == "__main__":
    a = sys.argv[1:] or ["status"]
    if a[0] in ("restart", "shutdown"):
        print(restart(why="CLI " + a[0]) if _is_shell() else request(a[0], "CLI " + a[0]))
    elif a[0] == "request":
        print(request(a[1] if len(a) > 1 else "restart", " ".join(a[2:]) or "大模型请求"))
    elif a[0] == "force":
        print(restart(why="CLI force") if a[1] != "shutdown" else shutdown(why="CLI force"))
    elif a[0] == "pending":
        print(run_pending() or "无待执行请求")
    elif a[0] == "selftest":
        _selftest()
    else:
        print(json.dumps({"launcher": BIN, "exists": os.path.isfile(BIN), "is_shell": _is_shell(),
                          "pending_restart": cg.peek(), "others": _shell_pids()}, ensure_ascii=False))

import runtime_bind as _rb; _rb.set_pending(run_pending)  # 批27 接缝登记
