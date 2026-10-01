#!/usr/bin/env python3
"""shell_tui_flow.py — sms-shell TUI 交互流 mixin（被 ShellApp 混入）：
① 批27 并行提交（用户「当有多个用户输入输入到 sms 时，输入的会话无需排队等待·全部并行处理」）：busy 不再是全局闸门——每条输入各起一个 worker 线程（self.running{tid}）同屏并发跑，多任务时输出行按任务打 [tid] 标互不混淆；仅当 shell.parallel=false 或并发已达 shell.max_parallel（0＝无限）才退回旧的 pend 排队续发。任务隔离三件套＝stop_channel.bind／ask_channel.bind／chains.ACTIVE 线程本地：停一个任务不牵连其余、A 任务的提问不吃掉 B 任务的输入、A 的 conv 不被 B 覆写。stop 词支持「stop <tid>」只停指定任务，裸 stop 停全部在跑任务。
② 详细细节跨会话合并（用户「其他会话任务的详细信息（推导·工具使用·命令行输出）也应该写在主 shell 的详细细节里」）：bus_poll 每秒按字节偏移增量消费 detail_bus（web/remote/cron/bg/其他壳进程投递的明细），以〔sess·kind〕前缀并入 app.details（F9＋右栏同口径）；本会话自身行由 split 实时入册，故按 sess 去重不重复。
③ 能回答大模型提问：worker 线程 ask_user 阻塞时主线程每 0.4s ask_poll 经 poll_any 取问题（含所属 tid）置 self.awaiting 高亮显示，用户下一条输入经 ask_channel.reply(text, tid) 回灌继续该任务。
④ 新启动接续：on_mount 预热链缓存并 log core.startup_block。
⑤ 退出/配置/编辑器令牌仍由 _done 分发（多任务时令牌在该任务收口时生效）。submit/_oline/_work/_done 从主类迁入此，主类不再定义这些（否则类自身 dict 覆盖 mixin）。"""
import time as _t
from rich.text import Text
from textual.widgets import ProgressBar
from shell_tui_widgets import Input, StatusBar
from shell_tui_detail import split, _push
import shell_core as core
import stop_channel as stop
import settings as st
def _par():
    try: return bool(st.get("shell.parallel", True))
    except Exception: return True
def _cap():
    try: return int(st.get("shell.max_parallel", 4) or 0)
    except Exception: return 4
class Flow:
    def _init_par(self):
        if not hasattr(self, "running"): self.running = {}
        if not hasattr(self, "_seq"): self._seq = 0
        if not hasattr(self, "_bus_off"): self._bus_off = None
    def _room(self):
        """还能不能立刻起一条新输入：并行开＝未达 shell.max_parallel（0＝无限）；并行关＝旧语义，无在跑任务才起下一条（其余排队）。"""
        if not _par(): return not getattr(self, "running", {})
        cap = _cap()
        return not cap or len(getattr(self, "running", {})) < cap
    def _tag(self, tid=""):
        return ("[%s] " % tid) if tid and len(getattr(self, "running", {})) > 1 else ""
    def submit(self, text):
        self._init_par()
        if not (text := (text or "").strip()): return
        w = text.split(" ", 1); one = w[1].strip() if len(w) > 1 else ""
        if stop.is_stop_word(text) or (stop.is_stop_word(w[0]) and one in getattr(self, "running", {})):
            self._clear(); self._stop(one); return
        if getattr(self, "awaiting", None):
            import ask_channel; ask_channel.reply(text, self.awaiting[0]); self.awaiting = None
            self.log_line(Text("sms> （答复）", style="bold blue") + Text(text)); self._clear(); return
        self._clear()
        if not self._room():
            self.pend.append(text)
            self.log_line(Text("已排队 %d 条 · %s" % (len(self.pend), ("并发已达上限 %d 个任务" % _cap()) if _par() else "并行已关闭（:config set shell.parallel false）"), style="yellow") + Text("·有空位即自动续发")); return
        self._start(text)
    def _stop(self, one=""):
        """stop 词收口：带 tid＝只停该任务，裸 stop＝停全部在跑任务（并行时代语义·旧版单任务行为不变）。"""
        if getattr(self, "awaiting", None):
            import ask_channel; ask_channel.reply("用户已请求停止任务（stop）", self.awaiting[0]); self.awaiting = None
        if one and one in self.running:
            stop.request("输入：stop " + one, one)
            self.log_line(Text("⛔ 已请求停止任务 %s——该任务在流式/工具/子进程下一检查点收口（其余 %d 个不受影响）" % (one, len(self.running) - 1), style="bold yellow")); return
        if one and one not in self.running:
            self.log_line(Text("无此在跑任务：%s（现行 %s）" % (one, "、".join(sorted(self.running)) or "无"), style="yellow")); return
        if self.running:
            for tid in list(self.running): stop.request("输入：stop（全部）", tid)
            self.log_line(Text("⛔ 已请求停止全部 %d 个在跑任务——各任务在下一检查点收口" % len(self.running), style="bold yellow")); return
        stop.clear(); self.log_line(Text("空闲：无进行中任务·停止状态已清", style="dim"))
    def _start(self, text):
        self._seq += 1; tid = "t%d" % self._seq
        stop.clear()
        self.log_line(Text("sms> ", style="bold blue") + Text(text) + (Text("   〔并行第 %d 个任务〕" % (len(self.running) + 1), style="dim cyan") if self.running else Text(""))); self.hist.append(text); self.hi = len(self.hist)
        self.running[tid] = {"text": text, "t0": _t.time(), "steps": []}
        self.busy = True; self.query_one("#prog", ProgressBar).display = True
        if len(self.running) == 1: self.query_one("#status", StatusBar).begin()
        self.run_worker(lambda: self._work(text, tid), thread=True, name="sms-task-" + tid)
    def _clear(self): self.query_one("#input", Input).text = ""
    def warm(self):
        try: import chain_store as cs; cs.Store(core.SMS).all_frags()
        except Exception: pass
    def ask_poll(self):
        if getattr(self, "awaiting", None): return
        import ask_channel; r = ask_channel.poll_any()
        if not r: return
        tid, q = r; self.awaiting = (tid, q)
        self.log_line(Text("❓ 大模型提问%s（直接输入即答复·该任务据你的回答继续·stop %s 只停它）：" % ((" 〔任务 %s〕" % tid) if tid else "", tid or ""), style="bold magenta")); self.log_line(Text(q, style="magenta"))
    def _oline(self, s, tid=""):
        s2 = str(s)
        ("$ " in s2 or "config:" in s2 or ".py" in s2 or ".md" in s2) and self.touched.append(s2[:200])
        r = split(self, s2, self._tag(tid)); r is not None and self.call_from_thread(self.log_line, r)
    def _work(self, text, tid=""):
        stop.bind(tid)
        try: __import__("ask_channel").bind(tid)
        except Exception: pass
        done = None
        def _st(n):
            self.steps.append((self._tag(tid) or "") + str(n)); _push(self, self._tag(tid) + "▸ " + str(n))
        try:
            done = core.handle(text, (lambda s: self._oline(s, tid)), _st, self._ev)
        except stop.Stopped as e:
            done = None; self.call_from_thread(self.log_line, Text("⛔ 任务 %s 已停止（%s）——在途输出中断·旗标已复位" % (tid, str(e)[:80]), style="bold yellow"))
        except Exception as e:
            done = None; core.debug.enabled() and core.debug.log("EXC " + core.debug.tb())
            self.call_from_thread(self.log_line, Text("处理异常：" + (core.debug.tb()[-900:] if core.debug.enabled() else repr(e)[:200]), style="red"))
        finally:
            import ask_channel
            try: ask_channel.flush(tid)
            except Exception: pass
        self.call_from_thread(self._done, tid, done)
    def _done(self, tid="", done=None):
        info = self.running.pop(tid, None) or {}
        el = _t.time() - float(info.get("t0") or _t.time())
        stop.clear(tid)
        if getattr(self, "awaiting", None) and self.awaiting[0] == tid: self.awaiting = None
        if self.running:
            self.log_line(Text("✔ 任务 %s 收口（%.1fs）·仍在并行跑 %d 个：%s" % (tid, el, len(self.running), "、".join(sorted(self.running))), style="dim"))
        else:
            self.busy = False; self.task_prog = ""; self.query_one("#prog", ProgressBar).display = False; self.query_one("#status", StatusBar).end(); self.subconv_hint()
            (b := __import__("dream_pending").badge()) and self.log_line(Text("⚑ 做梦有 " + b + "（后台缺权限/高危不可自动修）—— :repair list 看详情 · :repair go <id> 你同意后当场续跑"))
        if isinstance(done, str) and done.startswith(("edit:", "view:")): self._open_editor(done.split(":", 1)[1], done.startswith("view:")); return
        if done == "exit": self.exit(); return
        if done == "config": self.action_config()
        while self.pend and self._room(): self._start(self.pend.pop(0))
    def bus_poll(self):
        """跨会话明细合并（批27②）：按字节偏移增量取 detail_bus 新行，别的会话（web/remote/cron/bg/其他壳）的推导·工具·命令行输出进本壳 F9/右栏；本会话自身行已由 split 实时入册故按 sess 跳过。"""
        self._init_par()
        try:
            import detail_bus as db, chains
            own = chains.cur_sess()
            if self._bus_off is None:
                for e in db.recent(20):
                    e.get("sess") != own and _push(self, db.label(e) + " " + str(e.get("text"))[:600])
                self._bus_off = db.size(); return
            self._bus_off, ents = db.tail(self._bus_off)
            for e in ents:
                e.get("sess") == own or _push(self, db.label(e) + " " + str(e.get("text"))[:600])
        except Exception: pass
