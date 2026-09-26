#!/usr/bin/env python3
"""shell_tui_perms.py — sms-shell TUI「权限与工具」菜单 mixin（F10/主菜单·修复：大模型工具权限进菜单＋权限启用与配置文件一致可见）：menu_perms＝系统权限总览（permissions.py status：每键 生效值/来源=配置默认|今日授予·Enter＝今日 :grant 30 分钟·danger 不进菜单须当轮 :grant danger）；menu_tools＝大模型工具开关（agent_dispatch.NAMES·Enter 写 settings agent_tools.<name>·gateway 只暴露启用工具·execute 拒调禁用）；menu_hud＝HUD 浮窗启用/状态/隐藏。写回即时生效，右栏/顶栏无需重启。"""
import json
import shell_core as core, settings
PKEYS = ("read", "write", "execute", "network", "privacy", "vault", "verify")
class Perms:
    def action_menu_perms(self):
        try: d = json.loads(core.run_script("permissions.py", ["status"]))
        except Exception: d = {}
        eff, src = d.get("effective") or {}, d.get("source") or {}
        self.menu("系统权限（✓＝生效·来源随配置 permissions_default／今日授予·Enter＝授予 30 分钟·danger 须 :grant danger）",
                  [("grantp:" + k, ("✓ " if eff.get(k) else "✗ ") + k + "｜" + str(src.get(k, ""))) for k in PKEYS] + [("#menu_tools", "▶ 大模型工具权限（哪些工具可被调用）"), ("#menu_hud", "▶ HUD 浮窗（启用/隐藏/状态）")])
    def grant_perm(self, k): self.submit(":grant " + k + " 30")
    def action_menu_tools(self):
        try: import agent_dispatch as ad; names = ad.NAMES
        except Exception: names = []
        self.menu("大模型工具权限（Enter 开/关·即时生效·写 config agent_tools.*）", [("tool:" + n, ("✓ " if settings.get("agent_tools." + n, True) else "✗ ") + n) for n in names])
    def tool_toggle(self, n): settings.set("agent_tools." + n, not settings.get("agent_tools." + n, True)); self.log_line("工具权限：" + n + " → " + ("启用" if settings.get("agent_tools." + n, True) else "禁用")); self.action_menu_tools()
    def action_menu_hud(self):
        self.menu("HUD 顶面浮窗（需 settings hud.enabled＝true·置顶/穿透/不抢焦点·F10→权限总览可开）", [(":hud start", "▶ 启用并显示当前任务"), (":hud status", "状态"), (":hud hide", "隐藏（关窗）")])
