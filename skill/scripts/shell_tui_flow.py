#!/usr/bin/env python3
"""shell_tui_flow.py — sms-shell TUI 交互流 mixin（被 ShellApp 混入·解决三报障）：①任务进行中可输入——busy 时不再吞输入而是 self.pend 排队、上条完成自动依序提交；②能回答大模型提问——worker 线程调 ask_user 阻塞时主线程每 0.4s _ask_poll 取问题置 self.awaiting 并高亮显示，用户下一条输入即作答复经 ask_channel.reply 回灌继续任务；③新启动接续——on_mount 预热链缓存并 log core.startup_block（上次关闭前对话尾部）。submit/_oline/_work/_done 从主类迁入此，主类不再定义这些（否则类自身 dict 覆盖 mixin）。④任务中输 stop/停止/:stop 等词＝请求停止当前任务（stop_channel 置旗标·worker 在流式/工具/子进程检查点收口·ask_user 提问时先以停止语应答唤醒阻塞线程·排队 pend 保留照常续发）。退出/配置/编辑器令牌仍由 _done 分发。"""
from rich.text import Text
from textual.widgets import ProgressBar
from shell_tui_widgets import Input, StatusBar
from shell_tui_detail import split, _push
import shell_core as core
import stop_channel as stop
class Flow:
    def submit(self, text):
        if not (text := (text or "").strip()): return
        if stop.is_stop_word(text):
            self._clear(); getattr(self, "awaiting", None) and (__import__("ask_channel").reply("用户已请求停止任务（stop）"), setattr(self, "awaiting", None))
            if self.busy: stop.request("输入：" + text); self.log_line(Text("⛔ 已请求停止当前任务——流式/工具/子进程下一检查点收口" + ("·已排队 %d 条完成后照常续发" % len(self.pend) if self.pend else ""), style="bold yellow")); return
            self.log_line(Text("空闲：无进行中任务·停止状态已清", style="dim")); return
        if getattr(self, "awaiting", None):
            import ask_channel; ask_channel.reply(text); self.awaiting = None
            self.log_line(Text("sms> （答复）", style="bold blue") + Text(text)); self._clear(); return
        if self.busy:
            self.pend.append(text); self._clear()
            self.log_line(Text("已排队 %d 条 · 当前任务仍在进行（见状态栏计时），完成后自动依序发送" % len(self.pend), style="yellow")); return
        self.log_line(Text("sms> ", style="bold blue") + Text(text)); self._clear()
        self.hist.append(text); self.hi = len(self.hist); self.steps = []; self.touched = []; self.busy = True
        self.query_one("#prog", ProgressBar).display = True; self.query_one("#status", StatusBar).begin(); self.run_worker(lambda: self._work(text), thread=True)
    def _clear(self): self.query_one("#input", Input).text = ""
    def warm(self):
        try: import chain_store as cs; cs.Store(core.SMS).all_frags()
        except Exception: pass
    def ask_poll(self):
        if self.awaiting: return
        import ask_channel; q = ask_channel.poll()
        if q: self.awaiting = q; self.log_line(Text("❓ 大模型提问（直接输入即答复·任务将据你的回答继续）：", style="bold magenta")); self.log_line(Text(q, style="magenta"))
    def _oline(self, s):
        s2 = str(s)
        ("$ " in s2 or "config:" in s2 or ".py" in s2 or ".md" in s2) and self.touched.append(s2[:200])
        r = split(self, s2); r is not None and self.call_from_thread(self.log_line, r)
    def _work(self, text):
        done = None
        def _st(n): self.steps.append(n); _push(self, "▸ " + str(n))
        try: done = core.handle(text, self._oline, _st, self._ev)
        except Exception as e: import debug; done = None; core.debug.enabled() and core.debug.log("EXC " + core.debug.tb()); self.call_from_thread(self.log_line, Text("处理异常：" + (core.debug.tb()[-900:] if core.debug.enabled() else repr(e)[:200]), style="red"))
        finally:
            import ask_channel; ask_channel.flush()
        self.call_from_thread(self._done, done)
    def _done(self, done):
        self.busy = False; self.awaiting = None; self.task_prog = ""; self.query_one("#prog", ProgressBar).display = False; self.query_one("#status", StatusBar).end(); self.subconv_hint()
        if isinstance(done, str) and done.startswith(("edit:", "view:")): self._open_editor(done.split(":", 1)[1], done.startswith("view:")); return
        if done == "exit": self.exit(); return
        if done == "config": self.action_config()
        if self.pend: nxt = self.pend.pop(0); self.submit(nxt)
