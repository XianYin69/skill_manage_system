#!/usr/bin/env python3
"""shell_tui_menus.py — sms-shell TUI 菜单/补全/历史 mixin（被 shell_tui_textual.ShellApp 混入）：META 元指令表（含 :index/:skills）·Tab 补全（元指令＋个性化指令）·上下历史·F1/Alt+M 主菜单·Ctrl+K 托管技能菜单（skill_route 活跃技能）·「/」或 Alt+K 打开 SKILL.md 索引 action_menu_skill_index（id→SKILL.md 路径·首项索引本地文件→文件选择菜单 shell_tui_files→回填 :index <目录> 登记 scan_roots 重建注册表）·Shift+Tab agent 菜单·pick 派发（":" 直接执行·"call:" 填调用语句·"#" 转 action·其余填输入框待确认）·帮助/清屏/退出 action。"""
import os
import shell_core as core, skill_route
from rich.text import Text
from shell_tui_widgets import Menu
META = [":" + m for m in ("agents","use","skill","cmds","intent","index","skills","alias","unalias","hud","deploy","session","grant","api","config","web","ext","net","tts","learn","file","path","dream","image","help","quit")]
class Menus:
    def complete(self, ta):
        try: names = [c["name"] for c in core.user_commands.load(core.SMS)["commands"]]
        except Exception: names = []
        hits = [m + " " for m in META + names if m.startswith(ta.text)]
        if hits: ta.text = hits[0]
    def history(self, ta, key):
        if not self.hist: return False
        self.hi = min(len(self.hist), max(0, self.hi + (-1 if key == "up" else 1))); ta.text = self.hist[self.hi] if self.hi < len(self.hist) else ""; return True
    def menu(self, title, items): self.push_screen(Menu(title, items), self.pick)
    def pick(self, sel):
        if not sel: return
        ta = self.query_one("#input")
        if sel.startswith("call:"): ta.text = "请经 SMS 调用技能 " + sel[5:] + " 处理："; ta.focus()
        elif sel.startswith("#"): getattr(self, "action_" + sel[1:])()
        elif sel.startswith(":"): self.submit(sel)
        else: ta.text = sel + " "; ta.focus()
    def action_config(self):
        from shell_tui_config import Config
        self.push_screen(Config(), self._cfg_picked)
    def action_menu_skill_index(self):
        rows = [("#pick_file", "＋ 索引本地文件：选目录/SKILL.md 加入 scan_roots 并重建注册表")]
        for s in skill_route.skills():
            rows.append(("call:" + str(s.get("id", "")), "%s → %s" % (s.get("id", ""), os.path.join(str(s.get("install_path", "")), str(s.get("entry", "SKILL.md"))))))
        self.menu("SKILL.md 索引（Enter：技能＝填调用语句·首项＝打开文件选择 · / 或 F2 打开）", rows)
    def action_pick_file(self):
        from shell_tui_files import Files
        self.push_screen(Files(), self._file_picked)
    def _file_picked(self, path):
        if not path: return
        d = path if os.path.isdir(path) else os.path.dirname(path)
        self.log_line(core.run_script("register.py", ["--add-root", d, "--write"]))
    def _cfg_picked(self, path):
        if path: self.query_one("#input").text = ":config get " + path; self.query_one("#input").focus()
    def action_menu_main(self): self.menu("sms-shell 菜单（↑↓ 选择 · Enter 执行 · Esc 关闭）", [("#config","图形化配置：方向键·字母过滤·空格改值·Shift+Tab 编辑"),("#menu_skill_index","SKILL.md 索引：托管技能→路径·首项索引本地文件"),(":agents","查看/选择数据流 agent"),(":config status","配置状态（文本）"),(":cmds","命令总表"),(":session list","会话任务"),(":deploy ","部署＝仅复制 bin 到目录"),(":grant ","权限授予 <键|角色>"),(":api formats","格式 API"),(":dream run","做梦整理链"),(":hud session","HUD 浮窗"),(":tts status","TTS 朗读状态"),(":help","全部元指令说明")])
    def action_menu_skill(self): self.menu("托管技能（Enter＝填入调用语句，回车经路由真调 skill_call）", [("call:" + str(s.get("id")), "%s｜%s" % (s.get("id"), str(s.get("description") or "")[:24])) for s in skill_route.skills()] or [(":cmds","注册表为空：先跑 register.py")])
    def agents_menu(self): self.menu("数据流 agent（Enter 切换）", [(":use " + n, "切到 " + n) for n in core.ag.detected()] or [(":agents","未检出 agent（:agents 查看）")])
    def action_agents_menu(self): self.agents_menu()
    def action_help_cmd(self): self.log_line(Text(core.HELP))
    def action_clear_log(self): r = self.query_one("#log"); r.clear(); self.log_line(Text(core.banner(), style="bold cyan"))
    def action_exit_app(self): self.exit()
