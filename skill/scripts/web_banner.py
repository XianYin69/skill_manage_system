#!/usr/bin/env python3
"""web_banner.py — 网页壳（web_shell）状态一行化公共件（供 shell_core.banner 与 TUI 菜单复用·新建以零增行完成 t3/t4，不再把既有文件推高）：enabled/host/port 取真实配置 settings.eff()（真源键＝config.json 的 web_shell.enabled，与 web_shell.serve 的拒启判定同源，不新造键）；运行状态取 net_util.running("web_shell")；token 只给掩码前缀——绝不打印完整明文，也不写进链/日志，明文一律经 :web token 或 python -B web_shell.py token 走既有审计。开关：开＝settings.set 落盘并在未运行时按 net_util.spawn 后台拉起；关＝提示可 :web stop。本模块任何异常都降级为文字，不得让 banner／菜单抛错。"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
NAME = "web_shell"; DEF = {"host": "127.0.0.1", "port": 8737}
def cfg():
    try:
        import settings
        return settings.eff().get(NAME) or {}
    except Exception: return {}
def enabled(c=None): return bool((c or cfg()).get("enabled", True))
def running():
    try:
        import net_util
        return net_util.running(NAME)
    except Exception: return None
def url(c=None):
    c = c or cfg(); return "https://%s:%s" % (c.get("host", DEF["host"]), c.get("port", DEF["port"]))
def token_mask():
    try:
        import resolve_home
        p = os.path.join(resolve_home.ensure(), "shell", "web.token")
        t = open(p, encoding="utf-8").read().strip() if os.path.exists(p) else ""
        return (t[:6] + "…") if t else "未生成（:web token）"
    except Exception: return "不可读"
def status():
    c = cfg(); en = enabled(c); pid = running() if en else None
    return {"enabled": en, "url": url(c), "pid": pid, "run": ("运行中 pid=%s" % pid if pid else ("已启用·未运行" if en else "未启用")), "mask": (token_mask() if en else "—")}

def line():
    """banner 末尾一行网页端提示（URL＋运行状态＋掩码 token＋取明文方式；未启用＝提示而非报错）。"""
    try:
        s = status()
        if not s["enabled"]: return "网页壳：未启用（:config set web_shell.enabled true）"
        return "网页壳：网页端 %s（HTTPS 自签）· %s · token %s（明文：:web token 或 python -B web_shell.py token）" % (s["url"], s["run"], s["mask"])
    except Exception as e: return "网页壳：状态不可读（%s）" % str(e)[:40]
def toggle():
    """开/关 web_shell.enabled（settings.set 落盘）＋即时反馈：开且未运行→net_util.spawn 后台拉起；关→提示 :web stop。"""
    want = not enabled()
    try:
        import settings
        settings.set(NAME + ".enabled", want)
    except Exception as e: return "切换失败（settings.set web_shell.enabled）：" + str(e)[:60]
    if not want: return "网页壳：web_shell.enabled → 关（在跑的壳可 :web stop 停止·:web status 查看）"
    s = status()
    if s["pid"]: return "网页壳：web_shell.enabled → 开（已在运行 pid=%s·%s）" % (s["pid"], s["url"])
    try:
        import net_util
        return "网页壳：web_shell.enabled → 开·" + net_util.spawn(NAME) + "（%s·HTTPS 自签·token 明文 :web token）" % s["url"]
    except Exception as e: return "网页壳：web_shell.enabled → 开，拉起失败（%s）——可 :web start" % str(e)[:60]
