#!/usr/bin/env python3
"""shell_tui_editor.py — sms-shell TUI 内置文本编辑器/查看器（ModalScreen·F8 或 :edit/:view 令牌进入）：用户亲编辑≠模型写盘——载入按 utf-8→utf-8-sig→gbk 多编码嗅探（旧版 utf-8 失败即置只读＝用户「文件编辑器没法编辑文件」根因），新建/不存在文件也可编辑保存；Ctrl+S 直写目标路径（记 event 链审计·skill 本体目录仍拒写＝红线8/16），只读态（:view）禁存；Esc/Ctrl+Q 关闭回传路径；标题行显示路径、编码与状态。与文件索引（F5）/右栏修改文件联动使用。"""
import os
from rich.text import Text
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Static, TextArea
import chains
class Editor(ModalScreen):
    CSS = "Editor{align:center middle} Editor>Vertical{width:92%;max-width:160;height:90%;background:#181825;border:round #89b4fa} #eh{color:#f9e2af}"
    BINDINGS = [("ctrl+s", "save", "保存"), ("escape", "close", "关闭"), ("ctrl+q", "close", "关闭")]
    ENC = ("utf-8", "utf-8-sig", "gbk")
    def __init__(self, path, ro=False):
        self.p = os.path.abspath(os.path.expanduser(str(path))); self.ro = bool(ro); self.enc = "utf-8"; self._txt = ""
        if not os.path.exists(self.p): pass  # 不存在＝新建空文件，保持可编辑
        else:
            for e in self.ENC:
                try: self._txt = open(self.p, encoding=e).read(); self.enc = e; break
                except UnicodeDecodeError: continue
                except Exception: self.ro = True; break
        super().__init__()
    def compose(self): yield Vertical(Static(self._head(), id="eh"), TextArea(self._txt, show_line_numbers=True, language=None))
    def _head(self, msg=""): return Text((msg + " · " if msg else "") + "编辑 " + self.p + "〔" + self.enc + "〕" + ("（只读查看 · Esc 关闭）" if self.ro else "（Ctrl+S 保存 · Esc 关闭）"), style="bold #f9e2af")
    def on_mount(self): self.query_one("#eh", Static).update(self._head()); self.query_one(TextArea).focus()
    def action_save(self):
        if self.ro: return
        try:
            os.makedirs(os.path.dirname(self.p) or ".", exist_ok=True)
            open(self.p, "w", encoding=self.enc if self.enc != "utf-8-sig" else "utf-8").write(self.query_one(TextArea).text)
            chains.record("event", "编辑器保存 " + self.p); msg = "已保存"
        except Exception as e: msg = "保存失败：" + str(e)[:140]
        self.query_one("#eh", Static).update(self._head(msg))
    def action_close(self): self.dismiss(self.p)
