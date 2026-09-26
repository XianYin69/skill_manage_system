#!/usr/bin/env python3
"""shell_tui_mode.py — sms-shell Textual TUI 界面模式菜单 mixin（被 ShellApp 混入·F7/主菜单入口·顶栏与右栏显示当前模式）：三态 view 查看（只读旁观·话语不发送）／chat 对话（默认·经路由与网关流式）／exec 直通（免冒号输入即 :元指令 命令）；菜单行 ✓ 标当前模式，Enter 经 shell_tui_menus.pick("mode:<x>") 回 set_mode → shell_mode.set 唯一写 settings ui.mode（记 event 链·非法值回落 chat）；F7 随时重开菜单·Esc 一键回对话模式（action_mode_chat）；真正的发送门在 shell_core 话语派发点（shell_mode.utter）——故查看模式只拦发送，`:` 元指令与内置词仍可浏览诊断；模式即时生效无内存缓存（F4 改 ui.mode 同径）；readline 兜底壳与单发 CLI 走 `:mode`，bin 原生 ps1 壳无模式面恒 chat。"""
import shell_mode
ROWS = (("view", "只读旁观：话语不发送·仅看日志/链/右栏"), ("chat", "默认：话语经路由→托管技能→原生网关流式"), ("exec", "直通：输入即命令·免冒号按 :元指令 执行"))
class Mode:
    def mode_badge(self): return shell_mode.badge()
    def action_menu_mode(self):
        cur = shell_mode.current()
        self.menu("界面模式（Enter 切换 · F7 随时重开 · Esc 回对话模式）",
                  [("mode:" + k, ("✓ " if k == cur else "○ ") + shell_mode.MODES[k] + "模式｜" + d) for k, d in ROWS])
    def set_mode(self, m): self.log_line(shell_mode.set(m))
    def action_mode_chat(self):
        self.log_line("已是对话模式（F7 可切 查看/直通）" if shell_mode.current() == "chat" else shell_mode.set("chat"))
