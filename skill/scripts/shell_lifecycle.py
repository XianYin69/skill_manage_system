#!/usr/bin/env python3
"""shell_lifecycle.py — SMS 壳生命周期（2026-09-29 用户「菜单里加入 重启SMS 和 关闭SMS」）：restart(sms)＝写 <SMS_HOME>/shell/restart.json 旗标＋分离式拉起 bin/sms-shell.py（Windows CREATE_NEW_CONSOLE 新窗·posix start_new_session）＋回 "exit" 让当前壳收口退出，旗标供新实例 startup_block 提示「已重启」；shutdown(sms)＝收 HUD 查看进程（hud._stop）＋尽力停 tts 后台＋落 event 链并即时 flush（壳将退出，收口链缓冲不能留）＋回 "exit"（不拉起新实例）；pending(sms)＝读并清重启旗标。入口＝F1 主菜单「系统」组 :restart / :shutdown 与 shell_core._meta 路由，readline 兜底壳与 TUI 同径。用法：python -B shell_lifecycle.py restart|shutdown|status"""
import os, sys, json, time, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import resolve_home, chains, chain_timing
S = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.join(os.path.dirname(os.path.dirname(S)), "bin", "sms-shell.py")
def _p(sms): return os.path.join(sms, "shell", "restart.json")
def _flag(sms, on):
    os.makedirs(os.path.dirname(_p(sms)), exist_ok=True)
    json.dump({"at": time.strftime("%Y-%m-%d %H:%M:%S"), "relaunched": bool(on)}, open(_p(sms), "w", encoding="utf-8"))
def pending(sms=None):
    sms = sms or resolve_home.ensure()
    try: d = json.load(open(_p(sms), encoding="utf-8"))
    except Exception: return None
    try: os.remove(_p(sms))
    except Exception: pass
    return d if d.get("relaunched") else None
def _spawn(sms):
    if not os.path.isfile(BIN): return "启动器缺失：" + BIN
    kw = {"creationflags": 0x00000010, "stdin": subprocess.DEVNULL} if os.name == "nt" else {"start_new_session": True, "stdin": subprocess.DEVNULL}
    try:
        subprocess.Popen([sys.executable, "-B", BIN], cwd=os.path.dirname(BIN), env=dict(os.environ, SMS_SESSION=chains.cur_sess()), **kw)
    except Exception as e:
        import chain_error; chain_error.record("shell", "shell_lifecycle._spawn", str(e))
        return "拉起失败：" + str(e)[:120]
    return "已拉起新实例（" + BIN + "）"
def _bye(sms, tag):
    chains.record("event", tag + " " + time.strftime("%Y-%m-%dT%H:%M:%S"))
    try: chain_timing.flush()
    except Exception: pass
def restart(sms=None):
    sms = sms or resolve_home.ensure(); _flag(sms, True); _bye(sms, "shell-restart"); r = _spawn(sms)
    return "exit" if r.startswith("已拉起") else r
def shutdown(sms=None):
    sms = sms or resolve_home.ensure(); _flag(sms, False)
    try:
        import hud; hud._stop()
    except Exception: pass
    try:
        import tts; hasattr(tts, "stop") and tts.stop()
    except Exception: pass
    _bye(sms, "shell-shutdown"); return "exit"
def cmd(m, sms=None, on_line=None):
    r = restart(sms) if m == "restart" else shutdown(sms)
    on_line and on_line(("已拉起新实例（新窗口），本壳收口退出＝重启SMS 完成" if m == "restart" else "已关闭SMS：HUD/后台查看进程已收，本壳退出") if r == "exit" else r)
    return r
if __name__ == "__main__":
    c = sys.argv[1] if len(sys.argv) > 1 else "status"
    print(restart() if c == "restart" else shutdown() if c == "shutdown" else json.dumps({"launcher": BIN, "exists": os.path.isfile(BIN), "pending": pending()}, ensure_ascii=False) if c == "status" else "用法：restart|shutdown|status")
