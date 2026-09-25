#!/usr/bin/env python3
"""shell_tui_config.py — sms-shell TUI 图形化配置编辑（F4/Alt+C 或主菜单「图形化配置」）：settings.flat() 全 dot-path 项（api_key 掩码·含 skills.json 技能列表段）——↑↓ 选择·可打印字符增量过滤·Backspace 退格·空格＝布尔项取反即写回／其余项 ● 多选标记·Shift+Tab 或 Enter＝编辑当前值（list/dict 值以 JSON 呈现可改·子面板 Enter 确认·JSON 解析失败按原文·Esc 取消）·Esc 关面板；写回一律经 settings.set（模型参数落 config.json·技能列表键按属主路由 skills_config 落 skills.json·记 event 链），并上报 app.touched 供右侧栏显示。"""
import json
from rich.text import Text
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Label, ListView, ListItem, Static
import settings
class Edit(ModalScreen[str]):
    BINDINGS = [("escape", "cancel", "取消")]
    def __init__(self, path, cur): self.p = path; self.c = cur; super().__init__()
    def compose(self): yield Vertical(Static("编辑 " + self.p + "（Enter 写入 · Esc 取消）", id="ebt"), Input(value="" if str(self.c) == "***" else (json.dumps(self.c, ensure_ascii=False) if isinstance(self.c, (list, dict)) else str(self.c)), placeholder="新值：JSON 或字面文本", id="ebi"))
    def on_mount(self): self.query_one("#ebi", Input).focus()
    def on_input_submitted(self, m): self.dismiss(m.value)
    def action_cancel(self): self.dismiss(None)
class Config(ModalScreen[str]):
    CSS = "Config{align:center middle} Config>Vertical{width:92%;max-width:104;height:88%;background:#181825;border:round #89b4fa;padding:1 2} #ebt{color:#f9e2af}"
    BINDINGS = [("escape", "cm_close", "关闭")]
    def __init__(self): super().__init__(); self.q = ""; self.sel = set()
    def compose(self): yield Vertical(Static("配置编辑：↑↓选择 · 输入字母数字过滤 · 空格＝布尔取反/标记多选 · Shift+Tab/Enter＝编辑值 · Esc 关闭", id="ebt"), ListView(id="ebl"))
    def on_mount(self): self.rebuild(); self.query_one("#ebl", ListView).focus()
    def items(self): return [e for e in settings.flat() if self.q.lower() in (e["path"] + " " + str(e["value"])).lower()]
    def rebuild(self):
        lv = self.query_one("#ebl", ListView); idx = lv.index if lv.index is not None else 0; es = self.items(); lv.clear()
        lv.extend(ListItem(Label(Text("%s %s = %s（默认 %s）" % ("●" if e["path"] in self.sel else "·", e["path"], e["value"], e["default"])))) for n, e in enumerate(es))
        lv.index = min(idx, max(0, len(es) - 1))
    def cur(self): es = self.items(); i = self.query_one(ListView).index; return es[i] if i is not None and 0 <= i < len(es) else None
    def wr(self, path, v): settings.set(path, v); hasattr(self.app, "touched") and self.app.touched.append("config:" + path); self.rebuild()
    async def on_key(self, e):
        if e.key == "space":
            c = self.cur()
            if c and isinstance(c["value"], bool): self.wr(c["path"], not c["value"])
            elif c: self.sel ^= {c["path"]}; self.rebuild()
            e.stop(); e.prevent_default()
        elif e.key == "backspace":
            if self.q: self.q = self.q[:-1]; self.rebuild()
            e.stop(); e.prevent_default()
        elif e.key == "shift+tab": self.edit_cur(); e.stop(); e.prevent_default()
        elif (ch := e.character) and len(ch) == 1 and ch.isprintable() and ch != " ": self.q += ch; self.rebuild(); e.stop(); e.prevent_default()
    def edit_cur(self):
        c = self.cur()
        if not c: return
        def got(v):
            if v is None or (not str(v).strip() and str(c["value"]) == "***"): return
            try: val = json.loads(str(v))
            except Exception: val = str(v)
            self.wr(c["path"], val)
        self.app.push_screen(Edit(c["path"], c["value"]), got)
    def on_list_view_selected(self, m): self.edit_cur()
    def action_cm_close(self): self.dismiss(None)
