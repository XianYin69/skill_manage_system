#!/usr/bin/env python3
"""shell_tui_config.py — sms-shell TUI 图形化配置编辑（F4/Alt+C 或主菜单「图形化配置」）：settings.flat() 全 dot-path 项（api_key 掩码·含 skills.json 技能列表段）——每行＝简写＋注释（shell_tui_label·源自 settings 段 comment）＋原路径＋当前值（默认值）·↑↓ 选择·可打印字符增量过滤（命中简写/注释/路径/值）·空格＝布尔项取反即写回／其余项 ● 多选标记·Enter＝当前项编辑（布尔项弹 T/F 方向键选择器 shell_tui_edit.Bool——免键盘输入 True/False；其余弹 Edit 面板·list/dict 以 JSON 呈现）·Shift+Tab＝直接进 Edit·Esc 关面板；写回一律经 settings.set（模型参数落 config.json·技能键按属主路由 skills_config 落 skills.json·记 event 链）；配置无内存缓存——每次读写即时读文件，写回后经 app.on_config_change 即时刷新顶栏数据流，并上报 app.touched 供右侧栏显示。子面板 Edit/Bool 见 shell_tui_edit.py。"""
import json
from rich.text import Text
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, ListItem, ListView, Static
import settings
from shell_tui_edit import Edit, Bool
import shell_tui_label
class Config(ModalScreen[str]):
    CSS = "Config{align:center middle} Config>Vertical{width:92%;max-width:118;height:88%;background:#181825;border:round #89b4fa;padding:1 2} #ebt{color:#f9e2af}"
    BINDINGS = [("escape", "cm_close", "关闭")]
    def __init__(self): super().__init__(); self.q = ""; self.sel = set()
    def compose(self): yield Vertical(Static("配置编辑：↑↓选择 · 字母数字过滤（简写/注释/路径） · 空格＝取反/多选 · Enter＝编辑（布尔＝T/F 方向键选） · Shift+Tab＝编辑 · Esc 关闭", id="ebt"), ListView(id="ebl"))
    def on_mount(self): self.rebuild(); self.query_one("#ebl", ListView).focus()
    def items(self): return [e for e in settings.flat() if self.q.lower() in (shell_tui_label.search(e["path"]) + " " + str(e["value"])).lower()]
    def row(self, e): return "%s %s｜%s ＝ %s（默认 %s）" % ("●" if e["path"] in self.sel else "·", shell_tui_label.label(e["path"]), e["path"], e["value"], e["default"])
    def rebuild(self):
        lv = self.query_one("#ebl", ListView); idx = lv.index if lv.index is not None else 0; es = self.items(); lv.clear()
        lv.extend(ListItem(Label(Text(self.row(e)))) for e in es); lv.index = min(idx, max(0, len(es) - 1))
    def cur(self): es = self.items(); i = self.query_one(ListView).index; return es[i] if i is not None and 0 <= i < len(es) else None
    def wr(self, path, v):
        settings.set(path, v); hasattr(self.app, "touched") and self.app.touched.append("config:" + path)
        getattr(self.app, "on_config_change", lambda p: None)(path); self.rebuild()
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
        if not (c := self.cur()): return
        def got(v):
            if v is None or (not str(v).strip() and str(c["value"]) == "***"): return
            try: val = json.loads(str(v))
            except Exception: val = str(v)
            self.wr(c["path"], val)
        self.app.push_screen(Edit(c["path"], c["value"]), got)
    def choose(self):
        if (c := self.cur()) and isinstance(c["value"], bool): self.app.push_screen(Bool(c["path"], c["value"]), lambda b: b is not None and self.wr(c["path"], b))
        elif c: self.edit_cur()
    def on_list_view_selected(self, m): self.choose()
    def action_cm_close(self): self.dismiss(None)
