#!/usr/bin/env python3
"""shell_gui.py — sms-shell GUI 前端（需图形服务器，由 shell.py 自动检测后启动）：tkinter 窗口终端，输出区+输入行，共享 shell_core 引擎；输入 tui 可另起终端壳。"""
import os, sys, subprocess
S = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, S)
import shell_core as core
def main():
    import tkinter as tk
    r = tk.Tk(); r.title("sms-shell — SMS 指令壳（GUI）"); r.configure(bg="#1e1e2e"); r.geometry("880x540")
    txt = tk.Text(r, bg="#1e1e2e", fg="#cdd6f4", font=("Consolas", 10), relief="flat", state="disabled")
    ent = tk.Entry(r, bg="#181825", fg="#89b4fa", insertbackground="#89b4fa", font=("Consolas", 10), relief="flat")
    txt.pack(fill="both", expand=True, padx=8, pady=(8, 0)); ent.pack(fill="x", padx=8, pady=8); ent.focus_set()
    txt.tag_config("cmd", foreground="#89b4fa"); txt.tag_config("out", foreground="#cdd6f4"); txt.tag_config("err", foreground="#f38ba8")
    def echo(s, tag="out"):
        txt.config(state="normal"); txt.insert("end", s + "\n", tag); txt.config(state="disabled"); txt.see("end")
    def submit(_e=None):
        line = ent.get().strip(); ent.delete(0, "end")
        if not line: return
        echo("sms> " + line, "cmd")
        c = line.split()[0]
        if c in ("quit", "exit"): r.destroy(); return
        if c == "help": echo(core.HELP)
        elif c == "tui": subprocess.Popen([sys.executable, "-B", os.path.join(S, "shell_tui.py")])
        elif c == "gui": echo("已在 GUI 模式")
        else:
            out = core.exec_line(line)
            echo("未知命令：" + c + "（help）" if out is None else out, "err" if out is None else "out")
    ent.bind("<Return>", submit)
    echo(core.BANNER.replace("\n", " ") + "（GUI·图形服务器模式）\nhelp 看命令 · tui 起终端壳 · quit 关窗")
    r.mainloop()
if __name__ == "__main__":
    main()
