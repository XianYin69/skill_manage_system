#!/usr/bin/env python3
"""shell_tui_ws.py — sms-shell TUI 工作区切换 mixin（被 ShellApp 混入·F6/主菜单·v2 语义）：工作区＝SMS_WORKSPACE（智能体操作文件的真实目录·与数据根 SMS_HOME 分离——切换只写 settings sms_workspace/workspaces＋env，gateway exec/agent CLI 的 cwd 即时生效，配置零重置）；行＝◎虚拟工作区（每对话开建口删·当前则标注）＋登记清单（✓当前）·Enter 切换；「＋ 添加/更改工作区路径」→ Files 选目录（_ws_pick 旗标复用 shell_tui_files）→ 登记并切换；「⚠ 修复 v1 切换残留」→ workspace.repair_home()（bootstrap sms_home 改回初始 SMS 目录＋v1 清单迁入配置）。"""
import shell_core as core, workspace
class Ws:
    def action_menu_ws(self):
        cur = workspace.current()
        rows = [("ws:", "◎ 内置虚拟工作区 " + workspace.vroot() + ("　← 当前（每对话开建口删）" if workspace.is_virtual(cur) else ""))]
        rows += [("ws:" + w, ("✓ " if w == cur else "○ ") + w) for w in workspace.list_ws()]
        rows += [("#ws_add", "＋ 添加/更改工作区路径（选目录→登记并切换）"), ("#ws_repair", "⚠ 修复 v1 切换残留（SMS_HOME 改回初始 SMS 目录）")]
        self.menu("SMS_WORKSPACE 切换（不动 SMS_HOME·配置零影响·即时生效 · F2 技能索引 · F5 文件索引）", rows)
    def ws_switch(self, p):
        self.log_line(workspace.switch(p))
    def ws_indexed(self, path):
        self.log_line(workspace.add(path)); self.ws_switch(path)
    def action_ws_add(self):
        from shell_tui_files import Files
        self._ws_pick = True; self.push_screen(Files(), self._file_picked)
    def action_ws_repair(self):
        self.log_line(workspace.repair_home())
