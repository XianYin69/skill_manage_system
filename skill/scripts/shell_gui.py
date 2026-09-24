#!/usr/bin/env python3
"""shell_gui.py — sms-shell GUI 前端（PySide6 窗口终端，shell.py 探测可用后启动）：QTextEdit 只读输出＋QLineEdit 输入；话语经 shell_core/agent_stream 在 QThread 后台流式执行、逐行回填不卡窗；个性化指令与 `:` 元指令行为同 TUI；关闭窗口即退出。"""
import os, sys, html, subprocess
S = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, S)
import shell_core as core
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QLineEdit, QMainWindow, QTextEdit, QVBoxLayout, QWidget

class Worker(QThread):
    line, bye = Signal(str), Signal()
    def __init__(self, text):
        super().__init__(); self.text = text
    def run(self):
        if core.handle(self.text, lambda s: self.line.emit(str(s))) == "exit": self.bye.emit()

class Shell(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("sms-shell — agent 数据流（默认 skill_manage_system）")
        self.resize(920, 560); self.workers = []
        box = QVBoxLayout(); central = QWidget(); central.setLayout(box); self.setCentralWidget(central)
        self.out = QTextEdit(); self.out.setReadOnly(True)
        self.ent = QLineEdit(); self.ent.setPlaceholderText("话语回车→当前 agent · :help 元指令 · quit 退出")
        f = QFont("Consolas", 10); self.out.setFont(f); self.ent.setFont(f)
        box.addWidget(self.out); box.addWidget(self.ent); self.ent.setFocus()
        self.setStyleSheet("QMainWindow,QWidget{background:#1e1e2e}"
                           "QTextEdit{background:#1e1e2e;color:#cdd6f4;border:0}"
                           "QLineEdit{background:#181825;color:#89b4fa;border:0;padding:4px}")
        self.ent.returnPressed.connect(self.submit)
        self.echo(core.banner() + "\n" + core.HELP)
    def echo(self, s):
        self.out.append("<pre>%s</pre>" % html.escape(str(s)))
        self.out.verticalScrollBar().setValue(self.out.verticalScrollBar().maximum())
    def submit(self):
        line = self.ent.text().strip(); self.ent.clear()
        if not line: return
        self.echo("sms> " + line)
        if line == "tui":
            subprocess.Popen([sys.executable, "-B", os.path.join(S, "shell_tui.py")]); self.echo("已另起 TUI 终端壳"); return
        if line.strip() in ("quit", "exit", ":quit", ":q", ":exit"): self.close(); return
        wk = Worker(line); wk.line.connect(self.echo); wk.bye.connect(self.close)
        wk.start(); self.workers.append(wk)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = Shell(); win.show(); sys.exit(app.exec())
