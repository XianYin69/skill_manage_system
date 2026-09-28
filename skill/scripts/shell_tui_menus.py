#!/usr/bin/env python3
"""shell_tui_menus.py — sms-shell TUI 菜单/补全/历史 mixin（被 shell_tui_textual.ShellApp 混入·与 shell_tui_index.Index/shell_tui_ws.Ws 组合）：META 元指令表（含 :index/:skills/:workspace）·Tab 补全（元指令＋个性化指令＋「/」索引令牌）·上下历史·F1/Alt+M 主菜单·Ctrl+K 托管技能菜单（skill_route 活跃技能）·Shift+Tab agent 菜单·pick 派发（":" 直接执行·"call:" 填调用语句·"#" 转 action·"tok:" 以 /名称 插入输入行·"ws:" 切工作区·"path:" 弹路径输入经 :index 按路径加入 skill·其余填输入框待确认）·帮助/清屏/退出 action；F1 主菜单＝分组浮层（MAIN·技能派发/文件工作区/配置权限/会话数据流/系统·进入子组后「← 返回上一级」）；组件 Menu/Path 见 shell_tui_menu；SKILL.md 技能索引/文件索引/工作区菜单见 shell_tui_index/shell_tui_ws。"""
import os
import shell_core as core, skill_route, user_index
from rich.text import Text
from shell_tui_menu import Menu, MAIN, Path
META = [":" + m for m in ("agents","use","skill","cmds","intent","index","skills","workspace","debug","mode","dispatch","sh","edit","view","alias","unalias","hud","deploy","session","grant","perms","tools","api","config","web","ext","net","tts","learn","file","path","dream","image","help","quit")]
class Menus:
    def complete(self, ta):
        try: names = [c["name"] for c in core.user_commands.load(core.SMS)["commands"]]
        except Exception: names = []
        w = (ta.text or "").split()
        if w and w[-1].startswith("/") and len(w[-1]) > 1:
            hits = ["/" + k + " " for k in user_index.refs() if ("/" + k).startswith(w[-1])]
            if hits: ta.text = " ".join(w[:-1] + [hits[0]]); return
        hits = [m + " " for m in META + names if m.startswith(ta.text)]
        if hits: ta.text = hits[0]
    def history(self, ta, key):
        if not self.hist: return False
        self.hi = min(len(self.hist), max(0, self.hi + (-1 if key == "up" else 1))); ta.text = self.hist[self.hi] if self.hi < len(self.hist) else ""; return True
    def menu(self, title, items): self.push_screen(Menu(title, items), self.pick)
    def pick(self, sel):
        if not sel: return
        ta = self.query_one("#input")
        if sel.startswith("call:"): ta.text = ":dispatch " + sel[5:] + " "; ta.focus()
        elif sel.startswith("tok:"): user_index.fill(ta, sel[4:]); ta.focus()
        elif sel.startswith("ws:"): self.ws_switch(sel[3:])
        elif sel.startswith("mode:"): self.set_mode(sel[5:])
        elif sel.startswith("grantp:"): self.grant_perm(sel[7:])
        elif sel.startswith("tool:"): self.tool_toggle(sel[5:])
        elif sel.startswith("path:"): self.ask_path()
        elif sel.startswith("#"): getattr(self, "action_" + sel[1:])()
        elif sel.startswith(":"): self.submit(sel)
        else: ta.text = sel + " "; ta.focus()
    def action_config(self):
        from shell_tui_config import Config
        self.push_screen(Config(), self._cfg_picked)
    def _cfg_picked(self, path):
        if path: self.query_one("#input").text = ":config get " + path; self.query_one("#input").focus()
    def action_menu_main(self): self.menu("sms-shell 菜单（↑↓ 选择 · Enter 执行 · ▸＝分组进入·「← 返回上一级」回退 · Esc 关闭）", MAIN)
    def action_menu_skill(self): self.menu("托管技能（Enter＝填入调用语句，回车经路由真调 skill_call）", [("path:skill","➕ 按路径输入加入 skill（登记扫描根＋重建注册表）")] + ([("call:" + str(s.get("id")), "%s｜%s" % (s.get("id"), str(s.get("description") or "")[:24])) for s in skill_route.skills()] or [(":cmds","注册表为空：先跑 register.py 或按路径加入")]))
    def ask_path(self): self.push_screen(Path("按路径加入 skill：输入含 SKILL.md 的技能目录（或其待扫描父目录）·Enter＝:index 登记扫描根＋重建注册表＋加入文件索引"), lambda p: p and p.strip() and self.submit(":index " + p.strip()))
    def agents_menu(self): self.menu("数据流 agent（Enter 切换）", [(":use " + n, "切到 " + n) for n in core.ag.detected()] or [(":agents","未检出 agent（:agents 查看）")])
    def action_agents_menu(self): self.agents_menu()
    def action_help_cmd(self): self.log_line(Text(core.HELP))
    def action_clear_log(self): r = self.query_one("#log"); r.clear(); self.log_line(Text(core.banner(), style="bold cyan"))
    def action_exit_app(self): self.exit()
