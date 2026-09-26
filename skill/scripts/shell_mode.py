#!/usr/bin/env python3
"""shell_mode.py — sms-shell 界面模式（三态·唯一持久经 settings.set("ui.mode")→<SMS_HOME>/config/config.json·非法值回落 chat）：chat 对话＝默认·话语经 agent_stream→skill_route→原生网关流式；view 查看＝只读旁观·话语不发送（`:` 元指令与内置词仍可浏览诊断）；exec 直通＝输入即命令·无冒号输入自动补 ":" 转元指令治理（不经大模型）。utter() 是 shell_core.handle 话语派发点的模式门（view 拦截提示·exec 改道·chat 原样发网关），故模式只管「发送话语」这一件事，治理面不受影响；set()/current()/badge() 供 F7 菜单、顶栏与右栏即时读取（无内存缓存·F4 改 ui.mode 同径生效）；入口＝F7/主菜单＋`:mode chat|view|exec|status`（readline 兜底壳与单发 CLI 同用），bin 原生 ps1 壳无模式面恒 chat。"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import settings
MODES = {"chat": "对话", "view": "查看", "exec": "直通"}
DESC = {"chat": "默认：话语经路由→托管技能→原生网关流式作答",
        "view": "只读旁观：话语不发送·仅看日志/链/右栏（元指令仍可浏览）",
        "exec": "直通：输入即系统 shell 命令（unix 命令自动走 bash·!同义）·`:` 开头仍走 :元指令 治理·不经大模型"}
def norm(v): return v if v in MODES else "chat"
def current(): return norm(settings.get("ui.mode"))
def label(m=None): return MODES[norm(m or current())]
def badge(m=None): return label(m) + "模式"
def set(m):
    k = norm(m); settings.set("ui.mode", k); return "界面模式 → " + badge(k) + "｜" + DESC[k] + ("" if m in MODES else "（非法值已回落 chat）")
def utter(line, img, on_line, st, ev=None):
    m = current()
    if m == "view": st("界面模式：查看（拦截发送）"); on_line(DESC[m] + "｜:mode chat 或 F7 切回对话"); return None
    if m == "exec":
        import shell_core as core; t = line.strip()
        if t and t[0] not in ":：":
            import sys_shells; st("直通→系统 shell"); on_line(sys_shells.run(t, on_line=on_line)); return None
        st("界面模式：直通（转元指令）"); return core.handle(t, on_line, st, ev)
    import agent_stream as ag; _hud(line); ag.ask(line + ("\n[图:" + img + "]" if img else ""), on_line, st, ev); return None
def _hud(text):
    import settings, hud
    settings.get("hud.enabled") and settings.get("hud.auto", True) and hud._set("session", text[:48], 300)
if __name__ == "__main__":
    a = (sys.argv[1] if len(sys.argv) > 1 else "status").lower()
    if a in MODES: print(set(a))
    elif a == "status": print(badge() + "（可切 " + "·".join(k + "＝" + v for k, v in MODES.items()) + "）· 存 settings ui.mode")
    else: print("用法：:mode chat|view|exec|status")
