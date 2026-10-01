#!/usr/bin/env python3
"""run_watch.py — 程序运行计时器＋反馈器（2026-09-30 用户「添加程序运行计时器和反馈器，防止大模型写的程序/脚本运行异常导致任务卡住；异常要关闭该程序并把最后时刻的输出附给大模型」）。三层防线：① 总预算 budget＝墙钟上限（shell.exec_timeout）到点强杀；② 静默看门狗 stall＝连续无输出即判卡死（shell.stall_timeout，旧版只算总时长——真死锁要白等满预算）；③ 进程树强杀 kill_tree＝Windows taskkill /T /F（只 p.kill() 会留孙进程占着管道＝上一版「杀了还卡」的真凶）。feedback() 产出一段给大模型的话：异常原因＋已跑多久＋上限＋最后时刻输出末段，并落 runtime_rec（phase=exec）供看门狗/顶栏回溯。另 run_with_timeout(fn,secs)＝把任意阻塞调用（QQ 入站派发、技能对话）挂墙钟上限：超时先 stop_channel 协作收口＋杀在途子进程树，再放弃该线程回一句异常——单 worker 线程被一条消息永久拖死正是本次「QQ 发进去没回复」的根因。2026-10-01 分级修复（做梦审计错误1·error 链 2ab90541b9·freq=5）：一档平铺静默值把「慢但活着」的深层链路（网关 LLM 请求／技能对话期间不打活动戳）在 240s 就误杀——现分三档：T1 网络/网关单请求（net_call 自计时即抛）／T2 阶段静默（按 set_stage 阶段取阈值，长等待阶段走宽档 qq.handle_stall_llm）／T3 总预算（qq.handle_timeout／shell.exec_timeout），反馈文本必带级别名与建议（阈值真源 timeout_tiers.py＋tier_feedback.py）。用法：python -B run_watch.py status|test"""
import os, sys, time, threading, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import settings, runtime_rec as rr, timeout_tiers as tiers, tier_feedback as fb

ACT = {}; STAGE = {}  # STAGE＝线程当前阶段（T2 阈值档据此选）

def beat():
    """在途调用打活动戳（按线程）：QQ 入站派发／技能对话每出一行就调一次——
    看门狗只杀「静默卡死」，不杀「慢但一直在推进」的长任务（2026-09-30 用户诉求「防卡住」的正解）。"""
    ACT[threading.get_ident()] = time.time()

def set_stage(s):
    """声明本线程当前阶段（inbound/llm/gateway/skill/push…）并顺手打活动戳：
    长等待处（网关 LLM 请求／技能对话）拿不到逐行输出时靠这里把 T2 阈值提到宽档
    （qq.handle_stall_llm），绝不允许「活着却被杀」（error 2ab90541b9）。"""
    STAGE[threading.get_ident()] = str(s or ""); beat()

def clear_stage():
    STAGE.pop(threading.get_ident(), None)

def net_call(fn, *args, **kwargs):
    """T1＝网络/网关单请求自计时（urlopen 等）：到点即抛 TimeoutError（文本带级别名），
    绝不把在途 worker 拖到 T2/T3 被当成卡死；kind/timeout 两个参数由本函数消化、不外传。"""
    kind = str(kwargs.pop("kind", "net")); to = max(1, tiers._i(kwargs.pop("timeout", 0) or tiers.t1(kind)))
    box = {}; ev = threading.Event()
    def go():
        try: box["v"] = fn(*args, **kwargs)
        except BaseException as e: box["e"] = e
        finally: ev.set()
    beat(); threading.Thread(target=go, name="rw-T1", daemon=True).start()
    if not ev.wait(to):
        beat(); raise TimeoutError(fb.report("T1", to))
    beat()
    if "e" in box: raise box["e"]
    return box.get("v")

def budget(kind="shell"): return max(5, int(settings.get(kind + ".exec_timeout", 600)))
def stall(kind="shell"): return max(15, int(settings.get(kind + ".stall_timeout", 120)))

def kill_tree(p):
    """强杀整棵进程树（孙进程一个不留）；失败退 p.kill()。回手段名供反馈措辞。"""
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(p.pid), "/T", "/F"], capture_output=True, timeout=15)
            return "taskkill /T /F"
        import signal
        os.killpg(os.getpgid(p.pid), signal.SIGKILL); return "killpg SIGKILL"
    except Exception:
        try:
            p.kill(); return "p.kill()"
        except Exception:
            return "杀失败"

def tail(buf, n=30, cap=3000):
    """最后时刻的输出末段（剥 !sh▸ 前缀·去空行·限长）——直接喂给大模型。"""
    L = [str(x).split("▸ ", 1)[-1].rstrip() for x in (buf or []) if str(x).strip()]
    s = "\n".join(L[-n:])
    return s[-cap:] if len(s) > cap else s

def feedback(name, why, secs, limit, buf=None, n=30):
    """给大模型的异常提示（计时器/反馈器的「反馈」半边）：原因＋计时＋末段输出＋下一步建议。"""
    t = tail(buf, n); rr.rec("exec", err=why, sms=None)
    return ("⚠ 程序运行异常：%s ——「%s」已被计时器强制关闭（已跑 %.0fs／上限 %ds）。"
            "最后时刻该程序的输出（末 %d 行）：\n%s\n"
            "请勿原样重跑：先判读上面输出定位卡点（等输入／死循环／等网络／等子进程），"
            "改成带超时与非交互参数的写法、或拆小步再执行。") % (
        why, name, float(secs), int(limit), min(n, len((buf or []))), t or "（无任何输出——多半卡在启动或等 stdin）")

def watchdog(p, buf, limit=None, stall_s=None, name="命令", on_kill=None):
    """计时器本体（守护线程）：每 0.5s 巡检——总预算到点／静默（无新输出行）到点／用户 stop 请求，
    任一命中即 kill_tree 整棵树并置 p._rw_reason。mark() 由读循环在每行输出后调用续表活。
    返回 stop()：跑完取消巡检（回命中原因或 None）。"""
    t0 = time.time(); box = {"last": time.time(), "done": False, "why": "", "n": len(buf)}
    def spin():
        while not box["done"] and p.poll() is None:
            now = time.time()
            if len(buf) != box["n"]: box["n"] = len(buf); box["last"] = now
            idle = now - box["last"]
            if limit and now - t0 >= limit: box["why"] = "超总预算 %ds" % int(limit)
            elif stall_s and idle >= stall_s: box["why"] = "静默 %ds 无任何输出（判为卡死）" % int(stall_s)
            else:
                try:
                    import stop_channel as sc
                    if sc.stopped(): box["why"] = "用户请求停止"
                except Exception: pass
            if box["why"]:
                kill_tree(p); p._rw_reason = box["why"]
                try:
                    on_kill and on_kill(box["why"])
                except Exception: pass
                return
            time.sleep(0.5)
    th = threading.Thread(target=spin, name="run_watch", daemon=True); th.start()
    return lambda: (box.__setitem__("done", True), th.join(timeout=2), box["why"] or getattr(p, "_rw_reason", ""))[2]

def run_with_timeout(fn, secs, name="调用", args=(), kwargs=None, stall=None, stage=None):
    """给任意阻塞调用挂分级墙钟（QQ 入站派发／技能对话靠它兜底）。
    分级（2026-10-01 做梦审计错误1·error 链 2ab90541b9·freq=5 修复）：
    ① T3 总预算＝secs（qq.handle_timeout／shell.exec_timeout）；
    ② T2 阶段静默＝被观察线程多久没打活动戳，阈值按该线程 set_stage() 声明的阶段动态取——
       已知长等待阶段（llm/gateway/skill…）走宽档 qq.handle_stall_llm（默认 600s），
       普通阶段沿用显式 stall（qq.handle_stall 240s）。旧版只有一档平铺 240s，深层链路在网关
       合法长等待期间不打戳 → 240s 早于 900s 触发，把「慢但活着」的调用误杀成卡死；
    ③ T1 网络/网关单请求＝net_call() 自计时即抛，本就不该走到 T2/T3。
    stall=None＝不挂 T2（保持旧调用方语义）；qq.tiered_timeout=false＝退回旧一档平铺。
    命中＝先 stop_channel 协作收口再放弃该线程，回 (False, 反馈)；反馈文本必带级别名与建议。"""
    kwargs = kwargs or {}; box = {}; ev = threading.Event(); t0 = time.time()
    def go():
        wid = threading.get_ident(); ACT[wid] = time.time()
        if stage: STAGE[wid] = str(stage)
        try:
            box["v"] = fn(*args, **kwargs)
        except BaseException as e:
            box["e"] = e
        finally:
            ACT.pop(wid, None); STAGE.pop(wid, None); ev.set()
    th = threading.Thread(target=go, name="rw-" + str(name)[:20], daemon=True); th.start(); wid = th.ident
    base = max(30, int(stall)) if stall else 0
    tier = ""; band = ""; lim = 0
    while not ev.wait(0.5):
        el = time.time() - t0
        if el >= max(5, int(secs)): tier, band, lim = "T3", "", max(5, int(secs)); break
        if base:
            sl, band = tiers.t2(STAGE.get(wid, stage or ""), base) if tiers.tiered() else (base, "平铺档")
            if (time.time() - ACT.get(wid, t0)) >= sl: tier, lim = "T2", sl; break
    if not tier:
        try:
            import stop_channel as sc; sc.clear()
        except Exception: pass
        if "e" in box: raise box["e"]
        return True, box.get("v")
    try:
        import stop_channel as sc; sc.request("run_watch 超时收口：" + str(name))
        threading.Timer(60.0, sc.clear).start()  # 60s 后自动复位：被放弃线程在此窗口内拿旗标自行收口，也不把旗标永久留给下一个任务
    except Exception: pass
    why = fb.report(tier, lim, STAGE.get(wid) or stage, band) + "（线程已放弃·随进程退出而亡）"
    return False, feedback(name, why, time.time() - t0, secs,
                           ["（该调用无末段输出可附；活动戳 " + str(round(time.time() - ACT.get(wid, t0), 1)) + "s 前）"], n=1)


def status():
    import json
    return json.dumps({"exec_timeout_s": budget(), "stall_timeout_s": stall(), "tiers": fb.snapshot(),
                       "note": "分级超时：T1＝网络/网关单请求（qq.net_timeout／llm_gateway.timeout）·T2＝阶段静默（普通档 qq.handle_stall·长等待阶段宽档 qq.handle_stall_llm）·T3＝总预算（qq.handle_timeout／shell.exec_timeout）；子进程仍按 shell.exec_timeout 总预算＋shell.stall_timeout 静默；改：:config set qq.handle_stall_llm 600",
                       "runtime": rr.read()}, ensure_ascii=False)

if __name__ == "__main__":
    a = sys.argv[1:] or ["status"]
    if a[0] == "test":
        import sys_shells
        print("① 静默看门狗（应 ~3s 内判卡并杀掉）：", sys_shells.run("Start-Sleep -Seconds 30")[:200])
        print("② 有输出后卡死：", sys_shells.run("1..3 | %{ \"line$_\"; Start-Sleep -Seconds 30 }")[:200])
        print("③ 超时孙进程残留检查：taskkill 树杀后 Get-Process sleep 计数=", end=" ")
        print(subprocess.run(["powershell", "-NoProfile", "-Command", "(Get-Process -Name sleep -ErrorAction SilentlyContinue).Count"], capture_output=True, text=True).stdout.strip())
    else:
        print(status())
