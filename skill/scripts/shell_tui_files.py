#!/usr/bin/env python3
"""shell_tui_files.py — sms-shell TUI 本地文件/文件夹选择菜单（F5 文件索引首项＋工作区「＋添加/更改路径」共用）：浏览文件系统——↑ 上级 · ✔ 选定当前目录 · 目录项进入 · 文件（任意类型·可插入文件夹中的文件）直接选定其路径，Enter 经 dismiss(str) 回 shell_tui_index._file_picked（目录→register --add-root 登记 scan_roots＋user_index 索引项；文件→user_index 索引项→「/名称」令牌）；工作区模式（_ws_pick）回 shell_tui_ws.ws_indexed 登记并切换；Esc 关闭。默认起始＝skills_config.roots() 内最新存在根，否则用户主目录。"""
import os
from rich.text import Text
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, ListView, ListItem, Static
import skills_config
def _start():
    try:
        for r in reversed(skills_config.roots()):
            if r and os.path.isdir(r): return r
    except Exception: pass
    return os.path.expanduser("~")
class Files(ModalScreen[str]):
    CSS = "Files{align:center middle} Files>Vertical{width:92%;max-width:112;height:86%;background:#181825;border:round #89b4fa;padding:1 2} #fh{color:#f9e2af}"
    BINDINGS = [("escape", "close", "关闭")]
    def __init__(self, start=None): self.cwd = os.path.abspath(start or _start()); super().__init__()
    def compose(self): yield Vertical(Static(id="fh"), ListView(id="fl"))
    def on_mount(self): self._reload()
    def listing(self):
        out = []
        try: names = sorted(os.listdir(self.cwd))
        except Exception: return out
        for n in names:
            p = os.path.join(self.cwd, n)
            try:
                if os.path.isdir(p): out.append((n + "/", p))
                elif os.path.isfile(p): out.append((n, p))
            except Exception: pass
        return out
    def _reload(self):
        self.items = [("↑ 上级目录", os.path.dirname(self.cwd)), ("✔ 选定当前目录（登记为扫描根）", self.cwd)] + self.listing()
        lv = self.query_one("#fl", ListView); lv.clear(); lv.extend(ListItem(Label(Text(l))) for l, _ in self.items)
        self.query_one("#fh", Static).update(Text("索引目录：" + self.cwd + "\n↑↓ 浏览 · Enter 进入/选定（目录或任意文件） · Esc 关闭"))
    def on_list_view_selected(self, m):
        l, p = self.items[m.index or 0]
        if l.startswith("✔"): self.dismiss(p)
        elif l.startswith("↑"):
            up = os.path.dirname(self.cwd)
            if up and up != self.cwd: self.cwd = up; self._reload()
        elif os.path.isdir(p): self.cwd = p; self._reload()
        else: self.dismiss(p)
    def action_close(self): self.dismiss(None)
