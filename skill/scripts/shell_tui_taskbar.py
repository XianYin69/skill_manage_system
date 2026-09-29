#!/usr/bin/env python3
"""shell_tui_taskbar.py — sms-shell TUI 底栏任务控制 mixin（2026-09-29 批26 用户诉求）：
① action_copy_log＝主输出窗口内容可复制（Ctrl+Shift+C：全文进剪贴板＋落盘 <SMS_HOME>/log/last_output.txt；所选片段复制仍用 Textual 原生 Ctrl+C，RichLog 本身 allow_select）；
② action_stop_task / action_continue_task＝底栏「⏸ 停止 / ▶ 继续」按钮的功能本体（停止＝置 stop_channel 旗标并在提问时以停止语应答唤醒；继续＝清旗标并把最后一张未完成计划表交回数据流续推）；
③ taskbar_refresh＝按钮条可见性＝存在未完成计划表（有非 done 行＝尚未生成最终输出）；
④ plan_tick＝计划任务（各技能 planned_tasks/*.json）到点自动触发；
⑤ _dispatch_action 兜底＝任何底栏动作抛异常只报红不掀壳（修「点了会闪退」）。"""
import io
from rich.text import Text
import stop_channel as stop
import task_table as tt

import os
from rich.text import Text
import stop_channel as stop
import task_table as tt


class Taskbar:
    def log_copy(self, t):
        """累积主输出纯文本（供「复制全部输出」）。"""
        try:
            buf = getattr(self, "logbuf", None)
            if buf is None:
                buf = self.logbuf = []
            buf.append(t.plain if isinstance(t, Text) else str(t))
            del buf[:-2000]
        except Exception:
            pass

    def action_copy_log(self):
        txt = "\n".join(getattr(self, "logbuf", []) or [])
        if not txt.strip():
            self.log_line(Text("（输出为空·无可复制内容）", style="dim")); return
        try:
            self.copy_to_clipboard(txt)
            ok = "已进剪贴板"
        except Exception:
            ok = "剪贴板失败"
        p = "(落盘失败)"
        try:
            import resolve_home
            d = os.path.join(resolve_home.ensure(), "log"); os.makedirs(d, exist_ok=True)
            p = os.path.join(d, "last_output.txt")
            io.open(p, "w", encoding="utf-8").write(txt)
        except Exception:
            pass
        self.log_line(Text("⧉ %s·主输出 %d 字（全文另存 %s）" % (ok, len(txt), p), style="bold cyan"))

    # ── 停止 / 继续（功能＝名字） ─────────────────────────
    def action_stop_task(self):
        stop.request("底栏停止按钮")
        if getattr(self, "awaiting", None):
            import ask_channel
            ask_channel.reply("用户已请求停止任务（底栏停止）")
            self.awaiting = None
        self.log_line(Text("⏸ 已请求停止：在途输出于下一检查点收口；计划表未完成行保留，按「▶ 继续」续推", style="bold yellow"))
        self.taskbar_refresh()

    def action_continue_task(self):
        stop.clear()
        un = tt.unfinished()
        if not un:
            self.log_line(Text("▶ 无未完成计划表（停止旗标已清）", style="dim")); return
        if self.busy:
            self.log_line(Text("▶ 停止旗标已清·当前任务继续推进", style="yellow")); return
        tid, dn, tot = un[-1]
        self.log_line(Text("▶ 续推计划表 %s（%d/%d）" % (tid[-14:], dn, tot), style="bold green"))
        self.submit("继续推进任务表 " + tid + " 的未完成行")

    # ── 按钮条可见性：有计划表且未生成最终输出 ────────────
    def taskbar_refresh(self):
        try:
            from shell_tui_widgets import TaskBar
            bar = self.query_one("#taskbar", TaskBar)
            un = tt.unfinished()
            show = bool(un)
            bar.display = show
            if show:
                tid, dn, tot = un[-1]
                bar.query_one("#btn_stop").label = "⏸ 停止（%d/%d）" % (dn, tot)
        except Exception:
            pass

    # ── 计划任务到点自动触发 ──────────────────────────────
    def plan_tick(self):
        try:
            import planned_tasks as pt
            for r in pt.tick():
                self.log_line(Text("⏱ 计划任务触发 %s → %s" % (r[0], r[1]), style="bold magenta"))
        except Exception:
            pass
        self.taskbar_refresh()

    # ── 防闪退：动作异常只报不掀壳 ────────────────────────
    async def _dispatch_action(self, namespace, action_name, params):
        try:
            return await super()._dispatch_action(namespace, action_name, params)
        except Exception as e:
            try:
                import debug
                self.log_line(Text("底栏操作异常（壳继续运行）：" + str(e)[:160], style="red"))
                debug.enabled() and debug.log("ACTION " + action_name + " " + debug.tb())
            except Exception:
                pass
            return False
