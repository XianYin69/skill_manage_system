#!/usr/bin/env python3
"""shell_tui_perms.py — sms-shell TUI「权限与工具」菜单 mixin（F10/主菜单·修复：大模型工具权限进菜单＋权限启用与配置文件一致可见）：menu_perms＝系统权限总览（permissions.py status：每键 生效值/来源=配置默认|今日授予·Enter＝今日 :grant 30 分钟·danger 不进菜单须当轮 :grant danger）；menu_tools＝大模型工具开关（agent_dispatch.NAMES·Enter 写 settings agent_tools.<name>·gateway 只暴露启用工具·execute 拒调禁用）；menu_hud＝HUD 浮窗启用/状态/隐藏。写回即时生效，右栏/顶栏无需重启；menu_remote＝远程会话权限授予（按 id 分配 remote·TTL 到期自动失效·数据源 ids.json＋session_reg＋qq.json）。menu_solo＝SOLO 模式面板（solo.set 开/关·solo.status 状态·banner_lines 风险行·granted_today 当日放行计数；solo 不可用＝降级提示不抛异常）。"""
import json
import shell_core as core, settings
PKEYS = ("read", "write", "execute", "network", "privacy", "vault", "verify")
class Perms:
    def action_menu_perms(self):
        try: d = json.loads(core.run_script("permissions.py", ["status"]))
        except Exception: d = {}
        eff, src = d.get("effective") or {}, d.get("source") or {}
        self.menu("系统权限（✓＝生效·来源随配置 permissions_default／今日授予·Enter＝授予 30 分钟·danger 须 :grant danger）",
                  [("grantp:" + k, ("✓ " if eff.get(k) else "✗ ") + k + "｜" + str(src.get(k, ""))) for k in PKEYS] + [("#menu_solo", "▶ SOLO 模式（权限免用户确认·大模型自审授予·风险须知）"), ("#menu_remote", "▶ 远程会话权限授予（按 id 分配·TTL 到期自动失效）"), ("#menu_tools", "▶ 大模型工具权限（哪些工具可被调用）"), ("#menu_hud", "▶ HUD 浮窗（启用/隐藏/状态）")])
    def grant_perm(self, k): self.submit(":grant " + k + " 30")
    def action_menu_remote(self):
        """远程会话权限授予（按 id 分配）：ids.json 已绑定＋session_reg 的 qq/web 会话＋qq.json openid/allow，Enter＝授予 remote 30 分钟。"""
        ids = {}
        try: ids = (json.loads(core.run_script("permissions.py", ["ids"])) or {}).get("ids") or {}
        except Exception: pass
        rows = {}
        try:
            import session_reg
            for sid, v in (session_reg.list_() or {}).items():
                if v.get("kind") in ("qq", "web"): rows[sid] = (str(v.get("name") or ""), v.get("kind"))
        except Exception: pass
        try:
            import qq_push; c = qq_push.conf()
            for x in [str(c.get("openid") or "")] + [str(y) for y in (c.get("allow") or [])]:
                if x: rows.setdefault(x, ("", "qq"))
        except Exception: pass
        for rid, v in ids.items(): rows.setdefault(rid, (str(v.get("name") or ""), v.get("kind") or "session"))
        try:
            import permissions as P
            for rid in list(rows):
                try: r = P.resolve(rid, None)
                except Exception: r = rid
                if r and r != rid and r in rows: rows.pop(rid)
        except Exception: pass
        items = []
        for rid, (nm, kd) in rows.items():
            g = list(((ids.get(rid) or {}).get("grants") or {}).keys())
            items.append(("grantid:" + rid, ("✓ " if "remote" in g else "✗ ") + str(nm or rid)[:12] + "｜" + str(kd) + "｜" + ("、".join(g) or "-")))
        self.menu("远程会话权限授予（按 id 分配·Enter＝授予 remote 30 分钟·TTL 到期自动失效）",
                  items + [("#ask_remote_id", "➕ 按 id 名授予（输入 openid/会话名）"), (":grant ids", "≡ 查看全部已绑定 id（文本）"), ("#menu_perms", "← 返回权限与工具")])
    def action_ask_remote_id(self):
        from shell_tui_menu import Path
        self.push_screen(Path("远程会话授权：输入 openid／会话 sid／友好名 · Enter＝授予 remote 30 分钟"), lambda p: p and p.strip() and self.submit(":grant remote 30 --id " + p.strip()))
    def action_menu_tools(self):
        try: import agent_dispatch as ad; names = ad.NAMES
        except Exception: names = []
        self.menu("大模型工具权限（Enter 开/关·即时生效·写 config agent_tools.*）", [("tool:" + n, ("✓ " if settings.get("agent_tools." + n, True) else "✗ ") + n) for n in names])
    def tool_toggle(self, n): settings.set("agent_tools." + n, not settings.get("agent_tools." + n, True)); self.log_line("工具权限：" + n + " → " + ("启用" if settings.get("agent_tools." + n, True) else "禁用")); self.action_menu_tools()
    def action_menu_hud(self):
        self.menu("HUD 顶面浮窗（需 settings hud.enabled＝true·置顶/穿透/不抢焦点·F10→权限总览可开）", [(":hud start", "▶ 启用并显示当前任务"), (":hud status", "状态"), (":hud hide", "隐藏（关窗）")])
    def action_menu_solo(self):
        """SOLO 模式面板（真源 solo.py·降级安全：import/调用失败只提示不抛）：开/关＝solo.set，状态＝solo.status，风险＝banner_lines。"""
        try:
            import solo
        except Exception:
            self.menu("SOLO 模式不可用（solo.py 缺失/依赖异常·权限仍走用户确认）", [("#menu_perms", "← 返回权限与工具")]); return
        try:
            st = solo.status(); on = bool(st.get("enabled"))
        except Exception:
            st, on = {}, False
        self.log_line("SOLO 模式：" + ("已开启" if on else "已关闭") + "｜当日自审放行 " + str(st.get("granted_today", 0)) + " 项｜allow_danger=" + str(st.get("allow_danger")) + "｜自审网关=" + ("可用" if st.get("gateway_ok") else "未启用") + "｜永不自审：" + ("、".join(st.get("never") or []) or "-") + "\n风险须知：\n" + solo.banner_lines())
        self.menu("SOLO 模式（Enter 切换·关闭＝权限回到用户确认·单项收回 :grant revoke <键>）",
                  [("solo:toggle", ("✓ " if on else "✗ ") + "SOLO 自审授予（免用户确认）"),
                   ("solo:danger", ("✓ " if st.get("allow_danger") else "✗ ") + "allow_danger（自审可放行 skill 目录写·红线16）"),
                   (":solo status", "状态（文本）"), (":grant ", "手工授予某键 <键> [分钟]"),
                   ("#menu_perms", "← 返回权限与工具")])
    def solo_toggle(self, what):
        """开/关切换（写 config solo.enabled／solo.allow_danger）·失败仅提示，随后回面板刷新。"""
        try:
            import solo
        except Exception:
            self.log_line("SOLO 模块不可用（已降级：权限仍走用户确认）"); return
        try:
            if what == "danger":
                cur = bool(solo.cfg().get("allow_danger")); settings.set("solo.allow_danger", not cur)
                self.log_line("SOLO allow_danger → " + ("开（自审可放行 skill 目录写）" if not cur else "关（danger 仍须当轮 :grant danger）"))
            else:
                self.log_line(solo.set(not solo.enabled()))
        except Exception as e:
            self.log_line("SOLO 切换失败：" + str(e)[:120])
        self.action_menu_solo()
