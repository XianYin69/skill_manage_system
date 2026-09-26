#!/usr/bin/env python3
"""shell_tui_editor.py — sms-shell TUI 内置文本编辑器/查看器（ModalScreen·F7 或 :edit/:view 令牌进入）：TextArea 载 utf-8 文本；可编辑态 Ctrl+S 经 agent_tools.write 守卫视（工作区/SMS 默认可写·越界按其规则拒绝并红字提示），只读态（:view/读失败）禁存；Esc/Ctrl+Q 关闭回传路径；标题行显示路径与状态。与文件索引（F5）/右栏修改文件联动使用。"""
import os
from rich.text import Text
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Static, TextArea
import agent_tools as at
class Editor(ModalScreen):
    CSS = "Editor{align:center middle} Editor>Vertical{width:92%;max-width:160;height:90%;background:#181825;border:round #89b4fa} #eh{color:#f9e2af}"
    BINDINGS = [("ctrl+s", "save", "保存"), ("escape", "close", "关闭"), ("ctrl+q", "close", "关闭")]
    def __init__(self, path, ro=False):
        self.p = os.path.abspath(os.path.expanduser(str(path))); self.ro = bool(ro)
        try: self._txt = open(self.p, encoding="utf-8", errors="replace").read()
        except Exception: self._txt = ""; self.ro = True
        super().__init__()
    def compose(self):
        yield Vertical(Static(self._head(), id="eh"), TextArea(self._txt, show_line_numbers=True, language=None))
    def _head(self):
        return Text("编辑 " + self.p + ("（只读查看 · Esc 关闭）" if self.ro else "（Ctrl+S 保存 · Esc 关闭）"), style="bold #f9e2af")
    def on_mount(self): self.query_one("#eh", Static).update(self._head()); self.query_one(TextArea).focus()
    def action_save(self):
        if self.ro: return
        msg = at.write(self.p, self.query_one(TextArea).text)
        self.query_one("#eh", Static).update(Text(msg + " · " + self.p + "（Ctrl+S 再存 · Esc 关闭）", style="green" if msg.startswith("已写入") else "bold red"))
    def action_close(self): self.dismiss(self.p)
