#!/usr/bin/env python3
"""shell_tui_config.py — sms-shell TUI 图形化配置编辑（F4/Alt+C 或主菜单「图形化配置」）：settings.flat() 全 dot-path 项（api_key 掩码·含 skills.json 技能列表段）分组浏览——默认视图＝按段（dot-path 首段·shell_tui_label.order 定序）出组头「▸ 段名（N 项）｜注释」·Enter 进入该组·组内首行「← 返回上一级（全部组）」Enter 回组列表（Esc 整体关闭）；过滤态（打字 q 非空）跨组平铺命中行·退格删过滤·Enter＝当前项——布尔真值与 "True"/"False" 字符串一律弹 T/F 方向键选择器（shell_tui_edit.Bool·免打字写回真实布尔）·其余弹 Edit 面板（list/dict JSON 呈现）·Shift+Tab 直接进 Edit·空格＝布尔取反即写回／非布尔加入 ● 多选；每行＝简写＋注释｜＝值（默认）｜原路径·截断防溢出（总 ≤112·值 40·默认 22·路径 34）；debug.enabled 写回即时 debug.on/off() 生效；写回一律经 settings.set（模型参数 config.json·技能键按属主路由 skills_config·记 event 链）·无内存缓存即时读文件·写回经 app.on_config_change 刷新顶栏＋app.touched 右栏。"""
import json, debug, settings, shell_tui_label
from rich.text import Text
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, ListItem, ListView, Static
from shell_tui_edit import Edit, Bool
class Config(ModalScreen[str]):
    CSS = "Config{align:center middle} Config>Vertical{width:96%;max-width:124;height:88%;background:#181825;border:round #89b4fa;padding:1 2} #ebt{color:#f9e2af}"
    BINDINGS = [("escape", "cm_close", "关闭")]
    def __init__(self): super().__init__(); self.q = ""; self.sel = set(); self.grp = None; self.rows = []
    def compose(self): yield Vertical(Static("配置：默认按段分组（▸ 组名·Enter 进入·组内「← 返回上一级」回组列表）· 打字过滤跨组平铺 · 空格＝取反/多选 · Enter＝编辑（布尔＝T/F 选） · Esc 关闭", id="ebt"), ListView(id="ebl"))
    def on_mount(self): self.rebuild(); self.query_one("#ebl", ListView).focus()
    def items(self): return [e for e in settings.flat() if self.q.lower() in (shell_tui_label.search(e["path"]) + " " + str(e["value"])).lower()]
    @staticmethod
    def _b(v): return v if isinstance(v, bool) else (v.strip().lower() == "true") if isinstance(v, str) and v.strip().lower() in ("true", "false") else None
    @staticmethod
    def _cut(s, n): s = str(s); return s if len(s) <= n else s[:n - 1] + "…"
    def row(self, e): return (("%s %s｜＝%s（默认%s）｜%s" % ("●" if e["path"] in self.sel else "·", shell_tui_label.label(e["path"]), self._cut(e["value"], 40), self._cut(e["default"], 22), self._cut(e["path"], 34))))[:112]
    def groups(self): d = {}; [d.setdefault(e["path"].split(".")[0], []).append(e) for e in self.items()]; return [(s, d[s]) for s in shell_tui_label.order(d)]
    def rebuild(self):
        lv = self.query_one("#ebl", ListView); idx = lv.index if lv.index is not None else 0; gs = self.groups(); self.rows = [("C", e) for _, g in gs for e in g] if self.q else ([("B", None)] + [("C", e) for e in dict(gs).get(self.grp, [])] if self.grp else [("G", s, len(g)) for s, g in gs])
        lv.clear(); lv.extend(ListItem(Label(Text("← 返回上一级（全部 %d 组）" % len(gs) if r[0] == "B" else ("▸ %s（%d 项）" % (shell_tui_label.label(r[1]), r[2]))[:112] if r[0] == "G" else self.row(r[1])))) for r in self.rows); lv.index = min(idx, max(0, len(self.rows) - 1))
    def cur(self): i = self.query_one(ListView).index; return self.rows[i] if i is not None and 0 <= i < len(self.rows) else None
    def cure(self): r = self.cur(); return r[1] if r and r[0] == "C" else None
    def wr(self, path, v):
        settings.set(path, v); path == "debug.enabled" and (v and debug.on() or debug.off())
        hasattr(self.app, "touched") and self.app.touched.append("config:" + path); getattr(self.app, "on_config_change", lambda p: None)(path); self.rebuild()
    async def on_key(self, e):
        if e.key == "space" and (c := self.cure()):
            b = self._b(c["value"]); self.wr(c["path"], not b) if b is not None else (self.sel.symmetric_difference_update({c["path"]}), self.rebuild()); e.stop(); e.prevent_default()
        elif e.key == "backspace": self.q = self.q[:-1]; self.grp = None; self.rebuild(); e.stop(); e.prevent_default()
        elif e.key == "shift+tab": self.edit_cur(); e.stop(); e.prevent_default()
        elif (ch := e.character) and len(ch) == 1 and ch.isprintable() and ch != " ": self.q += ch; self.rebuild(); e.stop(); e.prevent_default()
    def edit_cur(self):
        if not (c := self.cure()): return
        def got(v):
            try: val = json.loads(str(v))
            except Exception: val = str(v)
            if v is not None and (str(v).strip() or str(c["value"]) == "***"): self.wr(c["path"], val)
        self.app.push_screen(Edit(c["path"], c["value"]), got)
    def choose(self):
        r = self.cur(); k = r and r[0]; c = r[1] if k == "C" else None
        if k == "B": self.grp = None; self.rebuild()
        elif k == "G": self.grp = r[1]; self.rebuild()
        elif c is not None and (b := self._b(c["value"])) is not None: self.app.push_screen(Bool(c["path"], b), lambda x: x is not None and self.wr(c["path"], x))
        elif c is not None: self.edit_cur()
    def on_list_view_selected(self, m): self.choose()
    def action_cm_close(self): self.dismiss(None)
