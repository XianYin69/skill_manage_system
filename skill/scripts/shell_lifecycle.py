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
        out = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", q], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=25).stdout
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
    cg.push("SMS 关闭中（%s）· %s" % (why or "shutdown", time.strftime("%H:%M:%S")))
    _flag(sms, False)
    try:
        import hud; hud._stop()
    except Exception: pass
    try:
        import tts; hasattr(tts, "stop") and tts.stop()
    except Exception: pass
    _bye(sms, "shell-shutdown"); kill_others(why=why or "shutdown")
    if hard:
        try: chain_timing.flush()
        except Exception: pass
        os._exit(0)
    return "已关闭SMS：HUD/后台已收，本壳退出"

def _is_shell():
    """本进程是不是壳进程（壳自己执行重启/关闭才允许硬退；exec 派生的子进程只登记请求，交壳在收口时执行——否则子进程会把正在对话的壳当场打死）。"""
    me = os.getpid()
    try:
        q = "Get-CimInstance Win32_Process -Filter \"ProcessId=%d\" | ForEach-Object { $_.CommandLine }" % me
        cl = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", q], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20).stdout
    except Exception: return True
    return any(pt in cl for pt in ("shell_tui_textual.py", "shell_tui.py", "shell_console.py", "shell_gui.py", "sms-shell.py"))
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
    else:
        print(json.dumps({"launcher": BIN, "exists": os.path.isfile(BIN), "is_shell": _is_shell(),
                          "pending_restart": cg.peek(), "others": _shell_pids()}, ensure_ascii=False))
