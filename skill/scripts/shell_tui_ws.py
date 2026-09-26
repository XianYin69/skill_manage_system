#!/usr/bin/env python3
"""shell_tui_ws.py — sms-shell TUI 工作区切换 mixin（被 ShellApp 混入·F6/主菜单）：行＝登记工作区清单（workspace.py 的 bootstrap workspaces·✓＝当前）；Enter 切换＝workspace.switch（写 bootstrap sms_home＋本进程 env，子脚本即时生效）；「＋ 添加/更改工作区路径」→ Files 目录选择（_ws_pick 旗标复用 shell_tui_files）→ 登记并切换；「⟳ 重启壳」→ os.execv 以当前 argv 重启使全壳换根（失败降级为提示手动重进——切换已持久化不丢）。"""
import os, sys
import shell_core as core, workspace
class Ws:
    def action_menu_ws(self):
        cur = workspace.current()
        rows = [("ws:" + w, ("✓ " if w == cur else "○ ") + w) for w in workspace.list_ws()]
        rows += [("#ws_add", "＋ 添加/更改工作区路径（浏览选目录→登记并切换）"), ("#ws_restart", "⟳ 重启壳使切换完全生效")]
        self.menu("工作区切换（Enter＝切换 · F2 技能索引 · F5 文件索引）", rows)
    def ws_switch(self, p):
        self.log_line(core.run_script("workspace.py", ["switch", p])); os.environ["SMS_HOME"] = os.path.abspath(os.path.expanduser(p))
        self.log_line("提示：壳内点 F6→⟳ 重启完全换根（子脚本已即时生效）")
    def ws_indexed(self, path):
        self.log_line(core.run_script("workspace.py", ["add", path])); self.ws_switch(path)
    def action_ws_add(self):
        from shell_tui_files import Files
        self._ws_pick = True; self.push_screen(Files(), self._file_picked)
    def action_ws_restart(self):
        self.log_line("重启壳以切换工作区…")
        try: self.exit(); os.execv(sys.executable, [sys.executable, "-B"] + sys.argv)
        except Exception: self.log_line("自动重启失败：请手动退出重进 sms-shell（新工作区已持久化）")
