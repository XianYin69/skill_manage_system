#!/usr/bin/env python3
"""shell_tui_edit.py — TUI 配置值编辑子面板（被 shell_tui_config 引用）：Edit＝任意 dot-path 值文本编辑（list/dict 以 JSON 呈现·Enter 写入·Esc 取消）；Bool＝True/False 项专用选择器——无需键盘输入 True/False/T/F：↑↓ 方向键在 T/F 两项间选择、Enter 确认、Esc 取消，当前值预置光标并标注 ◀。"""
import json
from rich.text import Text
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Label, ListView, ListItem, Static
class Edit(ModalScreen[str]):
    CSS = "Edit{align:center middle} Edit>Vertical{width:92%;max-width:104;padding:1 2;background:#181825;border:round #89b4fa} #ebt{color:#f9e2af}"
    BINDINGS = [("escape", "cancel", "取消")]
    def __init__(self, path, cur): self.p = path; self.c = cur; super().__init__()
    def compose(self): yield Vertical(Static(Text("编辑 " + self.p + "（Enter 写入 · Esc 取消）"), id="ebt"), Input(value="" if str(self.c) == "***" else (json.dumps(self.c, ensure_ascii=False) if isinstance(self.c, (list, dict)) else str(self.c)), placeholder="新值：JSON 或字面文本", id="ebi"))
    def on_mount(self): self.query_one("#ebi", Input).focus()
    def on_input_submitted(self, m): self.dismiss(m.value)
    def action_cancel(self): self.dismiss(None)
class Bool(ModalScreen[bool]):
    CSS = "Bool{align:center middle} Bool>Vertical{width:64;height:12;padding:1 2;background:#181825;border:round #89b4fa} #blt{color:#f9e2af} ListView{background:#181825}"
    BINDINGS = [("escape", "cancel", "取消")]
    def __init__(self, path, cur): self.p = path; self.cur = bool(cur); super().__init__()
    def compose(self):
        a = ListItem(Label(Text("T · True（开）" + ("　◀ 当前" if self.cur else ""))), id="bt")
        b = ListItem(Label(Text("F · False（关）" + ("　◀ 当前" if not self.cur else ""))), id="bf")
        yield Vertical(Static(Text("布尔 " + self.p + "　↑↓ 选择 · Enter 确认 · 不用输入 True/False"), id="blt"), ListView(a, b, id="blv"))
    def on_mount(self): lv = self.query_one("#blv", ListView); lv.index = 0 if self.cur else 1; lv.focus()
    def on_list_view_selected(self, m): self.dismiss(self.query_one("#blv", ListView).index == 0)
    def action_cancel(self): self.dismiss(None)
