#!/usr/bin/env python3
"""shell_resume.py — 新启动接续前次对话（2026-09-26 用户报障「无法在新启动时接续前次对话」）：原生网关每轮对话收口把 user/agent 轮次写 <SMS_HOME>/shell/last_conv.json（同会话累积末 20 轮·换会话才重置·每条 ≤1200 字；红线17 每输入开新 conv，按 conv 重置会让接续永远只剩一句，故改按 sess 归属）；下次任何输入（含重启壳后）开新对话时把前次轮次作 [上一对话记录] 块前置注入提示词（记忆＝上一对话轮次＋压缩链，不违背红线 17）；TUI 启动时 log 尾部轮次供人读接续。开关＝状态文件 shell/resume（"off" 关闭·默认开·:resume on|off|status·与 skill_prefix 同机制，属壳运行态非模型配置）。用法：python -B shell_resume.py on|off|status"""
import os, sys, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import resolve_home, chains
SMS = resolve_home.ensure()
def _p(n): return os.path.join(SMS, "shell", n)
def flag():
    try: return open(_p("resume"), encoding="utf-8").read().strip() != "off"
    except Exception: return True
def set_flag(on): open(_p("resume"), "w", encoding="utf-8").write("on" if on else "off"); return "接续前次对话：" + ("开（每轮输入自动携带上一对话轮次·重启壳亦接续）" if on else "关（仅压缩链记忆）")
def load():
    import atomic_io
    try: return atomic_io.rjson(_p("last_conv.json"), encoding="utf-8")
    except Exception: return {}
def append(user, agent):
    if not flag(): return
    d = load(); conv = chains.ACTIVE["conv"] or chains.session_id()
    t = d.get("turns", []) if d.get("sess") == chains.cur_sess() else []
    t += [["user", str(user)[:1200]], ["agent", str(agent)[:1200]]]
    import atomic_io; atomic_io.wjson(_p("last_conv.json"), {"conv": conv, "sess": chains.cur_sess(), "ts": time.strftime("%Y-%m-%d %H:%M:%S"), "turns": t[-20:]})
def prefix(sess=None):
    d = load(); t = d.get("turns") or []
    if not t or not flag(): return ""
    rows = "\n".join(("user: " if r == "user" else "agent: ") + x for r, x in t[-12:])
    return "[上一对话记录（" + str(d.get("conv")) + " · " + str(d.get("ts")) + " 接续·勿逐字复读，据此理解指代继续推进）]\n" + rows + "\n[接续结束·以下为当前新对话]\n"
def tail(n=6):
    d = load(); return [] if not (d.get("turns") and flag()) else [("%s｜%s" % (r, x[:110])) for r, x in (d.get("turns") or [])[-n:]]
def note():
    d = load()
    return ("接续上一对话 " + str(d.get("conv")) + "（" + str(d.get("ts")) + " · 末 " + str(len(tail())) + " 条·开关 :resume on|off）\n" + "\n".join(tail())) if (flag() and d.get("turns")) else ""
if __name__ == "__main__":
    a = (sys.argv[1] if len(sys.argv) > 1 else "status").lower()
    print(set_flag(a == "on") if a in ("on", "off") else "resume=" + ("on" if flag() else "off") + " · 上轮 " + str(load().get("conv") or "无") + " · " + str(load().get("ts") or "") + "（:resume on|off）")
