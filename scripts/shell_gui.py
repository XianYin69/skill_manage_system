#!/usr/bin/env python3
"""shell_gui.py — sms-shell GUI 前端（需图形服务器，shell.py 自动检测）：窗口终端，话语在后台线程流式送入当前 agent、逐行回填输出区不卡窗；个性化指令与 `:` 元指令同 TUI；tui 命令可另起终端壳。"""
import os, sys, threading, subprocess
S = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, S)
import shell_core as core
def main():
    import tkinter as tk
    r = tk.Tk(); r.title("sms-shell — agent 数据流（默认 skill_manage_system）"); r.configure(bg="#1e1e2e"); r.geometry("920x560")
    txt = tk.Text(r, bg="#1e1e2e", fg="#cdd6f4", font=("Consolas", 10), relief="flat", state="disabled")
    ent = tk.Entry(r, bg="#181825", fg="#89b4fa", insertbackground="#89b4fa", font=("Consolas", 10), relief="flat")
    txt.pack(fill="both", expand=True, padx=8, pady=(8, 0)); ent.pack(fill="x", padx=8, pady=8); ent.focus_set()
    txt.tag_config("cmd", foreground="#89b4fa"); txt.tag_config("out", foreground="#cdd6f4"); txt.tag_config("err", foreground="#f38ba8")
    def echo(s, tag="out"):
        txt.config(state="normal"); txt.insert("end", str(s) + "\n", tag); txt.config(state="disabled"); txt.see("end")
    def submit(_e=None):
        line = ent.get().strip(); ent.delete(0, "end")
        if not line: return
        echo("sms> " + line, "cmd")
        if line == "tui": subprocess.Popen([sys.executable, "-B", os.path.join(S, "shell_tui.py")]); echo("已另起 TUI 终端壳"); return
        def work():
            if core.handle(line, lambda s: r.after(0, echo, s)) == "exit": r.after(0, r.destroy)
        threading.Thread(target=work, daemon=True).start()
    ent.bind("<Return>", submit)
    echo(core.banner() + "\n" + core.HELP)
    r.mainloop()
if __name__ == "__main__":
    main()
