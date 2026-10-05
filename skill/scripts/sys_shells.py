#!/usr/bin/env python3
"""sys_shells.py — 基本 shell 指令与系统 shell 联动：detect 检出 powershell/pwsh/cmd/bash/zsh；批6 关键优化：detect 拒认 WSL/商店 bash 桩（System32\\bash.exe·WindowsApps\\bash.exe——它使每条 unix 命令冷启 WSL VM 实测 ~32s，是 skill/子skill exec 卡顿主因），只认真身 Git-Bash；run 对 powershell/pwsh 加 -NoProfile -NonInteractive、cmd 加 /d（免档案/AutoRun 拖慢）；unix 风格命令仅在有真 bash 时改道，否则 powershell 直跑（echo/ls/cat/git/python 在 PS 原生可用）。选择持久 <SMS_HOME>/shell/shell_kind；git 写操作（add/commit/reset…）恒门禁（红线2）；cwd＝SMS_WORKSPACE、env 注入 SMS_HOME/SMS_WORKSPACE/SMS_TMP，输出逐行回显并记 tool_call 链；export() 打印联动片段。壳内 `!命令`、`:sh`、F7 直通与 gateway exec 同一入口；manual/register-manual 出三平台命令手册（shell_commands 子技能·登记 <SMS_HOME>/shell/manual.json）。
批29 性能：detect/current 走 TTL 缓存（免每条命令重复全 PATH 扫描）；朴素单命令（无 shell 元字符
且首 token 是 .exe 真身）免 PowerShell 冷启直跑（tools.exec_direct，实测冷启 0.73-0.88s→0.02s 级）；
进程探测默认 tasklist（0.37s）、确需命令行才查 CIM 全表且按 TTL 缓存（procs/shell_pids/cim_cmdline）。
用法：python -B sys_shells.py list|select <kind>|run <命令>|export|manual [kind|all]|register-manual"""
import no_window  # 静默子进程：前台运行任务不弹命令行窗口
import os, sys, re, time, shutil, subprocess, threading
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import resolve_home, chains, settings, stop_channel as stop, run_watch as rw
SMS = resolve_home.ensure(); SD = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sub_skills", "shell_commands"); MDS = ("powershell.md", "bash.md", "zsh.md", "platform_map.md")
KNOWN = {"pwsh": ["pwsh"], "powershell": ["powershell"], "cmd": ["cmd"], "bash": ["bash", r"C:\Program Files\Git\bin\bash.exe", r"C:\Program Files (x86)\Git\bin\bash.exe"], "zsh": ["zsh"]}
WSL = re.compile(r"(?i)\\system32\\bash(\.exe)?$|\\windowsapps\\")
UNIX = re.compile(r"^\s*(?:sudo\s+)?(?:ls|ll|cat|grep|egrep|rg|sed|awk|find|touch|mkdir|cp|mv|rm|df|du|ps|kill|chmod|chown|ln|head|tail|wc|sort|uniq|which|whoami|pwd|echo|printf|tree|diff|tar|zip|unzip|curl|wget|open|date|env|history|less|more|basename|dirname|xargs|seq|tr|cut|jq|make|python|pip|node|npm|git|ssh|scp|ping|ip|netstat)\b")
def _rp(c):
    p = (c if os.path.isabs(c) else (shutil.which(c) or "")); return p if (p and os.path.isfile(p) and not WSL.search(p)) else ""
_TTL = {}
def cached(key, ttl, fn):
    """TTL 缓存（批29·exec 冷启治理）：只给幂等系统探测（shell 检出/进程表）用；
    用户命令一律每次真跑，run() 常规路径不经此缓存——绝不拿旧输出冒充执行结果。"""
    now = time.time(); e = _TTL.get(key)
    if e is not None and now - e[0] < max(0.0, float(ttl)): return e[1]
    v = fn(); _TTL[key] = (now, v); return v

def _ttl(key, default):
    try:
        import settings; v = settings.get("tools." + key)
    except Exception: v = None
    try: return float(v)
    except Exception: return float(default)

def _flag(key, default):
    try:
        import settings; v = settings.get("tools." + key)
    except Exception: v = None
    return default if v is None else bool(v)

def _detect_raw():
    return {k: next((r for r in map(_rp, cs) if r), None) for k, cs in KNOWN.items()}

def detect(ttl=None):
    """shell 真身检出（批29）：按 PATH 指纹 TTL 缓存（默认 300s·tools.shell_detect_ttl），
    PATH 变化自动失效——旧版每条命令都重跑一遍全 PATH 扫描（shutil.which×多候选）。"""
    return cached(("detect", os.environ.get("PATH", "")),
                  _ttl("shell_detect_ttl", 300) if ttl is None else float(ttl), _detect_raw)

def kinds(): return [k for k, v in detect().items() if v]

def _cap(argv, timeout=10):
    """探测专用静默捕获（失败回空串·不抛，调用方按空结果自行降级）。"""
    try:
        return (no_window.run(argv, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=int(timeout)).stdout or "")
    except Exception:
        return ""

def _csv_rows(txt):
    import csv as _c, io as _i
    return [r for r in _c.reader(_i.StringIO(txt)) if r and len(r) >= 2]

def cim_cmdline(name=None, ttl=None):
    """CIM 全表（pid→命令行）唯一入口＋TTL 缓存（默认 15s·tools.probe_ttl）：
    同窗口内多次判活/找壳进程只冷启一次 PowerShell（实测单次 1.2s）。回 {pid: cmdline}。"""
    f = "Name='%s'" % name if name else "Name like '%'"
    q = ('Get-CimInstance Win32_Process -Filter "%s" '
         '| ForEach-Object { "$($_.ProcessId)`t$($_.CommandLine)" }') % f
    def _once():
        d = {}
        argv = ["powershell", "-NoProfile", "-NonInteractive", "-Command", q]
        for ln in _cap(argv, 8).splitlines():
            pid, _, cl = ln.partition("\t")
            if pid.strip().isdigit(): d[int(pid.strip())] = cl.strip()
        return d
    return cached(("cim", name or "*"), _ttl("probe_ttl", 15) if ttl is None else float(ttl), _once)
def procs(name=None, want_cmdline=False, ttl=None, status=None):
    """进程探测轻量替代（批29·用户「CIM 全表查询加 TTL 缓存与轻量替代」）：Windows 默认 tasklist
    （实测 0.37s）取 pid+名，免 PowerShell 冷启（实测 0.73-0.88s）；确需命令行才查 CIM 并按 TTL 缓存。
    非 Windows 走 ps -eo。回 [(pid, name, cmdline)]，status["src"] 记实际来源（如实标注）。"""
    st = status if isinstance(status, dict) else {}
    if os.name != "nt":
        rows = []
        for ln in _cap(["ps", "-eo", "pid=,comm=,args="], 8).splitlines():
            pid, _, rest = ln.strip().partition(" ")
            nm, _, cl = rest.strip().partition(" ")
            if pid.isdigit() and (not name or name in nm):
                rows.append((int(pid), nm, cl if want_cmdline else ""))
        st["src"] = "ps(%d)" % len(rows); return rows
    argv = ["tasklist", "/FO", "CSV", "/NH"]
    if name: argv[1:1] = ["/FI", "IMAGENAME eq " + _exe_name(name)]
    def _tl():
        out = []
        for r in _csv_rows(_cap(argv, 10)):
            try: pid = int(str(r[1]).strip())
            except Exception: continue
            out.append((pid, r[0], ""))
        return out
    rows = cached(("tasklist", name or "*"),
                  _ttl("probe_ttl", 15) if ttl is None else float(ttl), _tl)
    st["src"] = "tasklist(%d)" % len(rows)
    if want_cmdline:
        if not rows: st["src"] += "·无候选免CIM"
        else:
            d = cim_cmdline(_exe_name(name), ttl)
            rows = [(p, n, d.get(p, "")) for p, n, _ in rows]
            st["src"] += "+CIM(%d)" % len(d)
    return rows

def shell_pids(match=(), name="python", exclude=(), ttl=None, status=None):
    """按命令行特征找进程 pid（重启/关闭路径·批29）：先 tasklist 预筛同名进程——无候选直接回空；
    有候选才查 CIM（TTL 缓存）。旧版每次无条件冷启壳全表扫（实测 1.2s，p90 拖到 10s 级）。"""
    keep = {int(x) for x in exclude if str(x).isdigit()} | {os.getpid()}
    rows = procs(name=name, want_cmdline=True, ttl=ttl, status=status)
    return [p for p, _n, cl in rows if p not in keep and cl and any(m in cl for m in match)]

# cmd/PowerShell 内建与别名：这些名字直跑会撞上 PATH 里的同名 exe（Git coreutils 的 dir/ls/cat/rm、
# system32 的 find），语义就变了——一律交回原壳。
BUILTIN = set(
    "cd dir echo set path type more cls del erase ren rename move md mkdir rd rmdir ver vol "
    "date time prompt start assoc ftype call shift for if goto rem pause pushd popd exit "
    "logout ls cat cp mv rm pwd ps kill sleep man history source alias find sort where "
    "write gci gc gps sls select foreach format ogv iwr irm iex gwmi gm ni ci ri rni sp ft "
    "fl h diff cmp clhy gl mo sal sch select-string".split())
def _exe_name(name):
    """tasklist/CIM 统一口径：进程名补 .exe（CIM 的 Name='python' 匹配不到 python.exe）。"""
    if not name: return None
    return name if name.lower().endswith(".exe") else name + ".exe"

SAFE = re.compile(r"^[\w.\-+/\\:@=,~ ]+$")
def _direct(cmd):
    """朴素单命令免壳直跑（批29·exec 冷启主因＝PowerShell 进程本身 0.73-0.88s）：
    命令＝「一个可执行文件＋无元字符参数」且首 token 解析到 .exe 真身（非 WSL 桩）时直接 Popen argv；
    含任何 shell 语法（; | & < > $ 引号 通配 换行）即回 [] 走原壳——语义零变化。tools.exec_direct 可关。"""
    if os.name != "nt" or not _flag("exec_direct", True): return []
    s = str(cmd).strip()
    if not s or "\n" in s or not SAFE.match(s): return []
    toks = s.split()
    head = toks[0].lower().rsplit(".", 1)[0]
    if head in BUILTIN: return []  # 内建/别名名＝交回原壳，绝不拿 PATH 里的同名 exe 顶替
    exe = _rp(toks[0])
    if not exe or not exe.lower().endswith(".exe"): return []
    return [exe] + toks[1:]

def kind_for(cmd, kind=None):
    k = kind if kind in kinds() else current()
    if k in ("powershell", "cmd") and UNIX.match(str(cmd or "").strip()):
        return next((b for b in ("bash", "zsh") if b in kinds()), k)
    return k
def _current_raw(f):
    try: c = open(f, encoding="utf-8").read().strip()
    except Exception: c = ""
    ks = kinds(); return c if c in ks else next((k for k in ("pwsh", "powershell", "cmd", "bash", "zsh") if k in ks), "")

def current():
    """当前选定壳（批29）：以 shell_kind 文件 mtime＋检出结果为缓存键（默认 60s·tools.shell_current_ttl），
    免每条命令重复读盘＋全 PATH 扫描；select() 换壳即清缓存。"""
    f = os.path.join(SMS, "shell", "shell_kind")
    try: mt = os.path.getmtime(f)
    except Exception: mt = 0
    return cached(("current", mt, tuple(kinds())), _ttl("shell_current_ttl", 60),
                  lambda: _current_raw(f))

def select(k):
    if k not in kinds(): return "未检出 shell：" + str(k) + "（:sh list 看可用）"
    os.makedirs(os.path.join(SMS, "shell"), exist_ok=True)
    open(os.path.join(SMS, "shell", "shell_kind"), "w", encoding="utf-8").write(k)
    _TTL.clear(); return "系统 shell 选定：" + k + "（sms-shell `!命令`/`:sh <命令>` 与 gateway exec 之外的手动入口）"
def listtext(): cur = current(); return "可检出系统 shell：" + ("、".join(kinds()) or "（无）") + " · 当前：" + cur + " · 用法：`!dir`/`:sh <命令>` 单发执行（cwd＝工作区 tmp 收产物）· `:sh <kind>` 选定 · `:sh export` 打印联动片段 · `sys_shells.py manual [kind|all]` 查三平台手册（shell_commands）"
def manual(k=None): p = os.path.join(SD, {"pwsh": "powershell.md", "powershell": "powershell.md", "cmd": "platform_map.md", "bash": "bash.md", "zsh": "zsh.md"}.get(k or current(), "platform_map.md")); return "shell_commands 三平台手册：\n  " + "\n  ".join(os.path.join(SD, x) for x in MDS) if k == "all" else (p if os.path.isfile(p) else "手册目录缺失：" + SD)
def reg_manual():
    import atomic_io; d = {x[:-3]: os.path.join(SD, x) for x in MDS}; ok = all(os.path.isfile(v) for v in d.values()); os.makedirs(os.path.join(SMS, "shell"), exist_ok=True); ok and atomic_io.wjson(os.path.join(SMS, "shell", "manual.json"), {"skill": "shell_commands", "manuals": d}); return ("已登记手册 %d 篇 → <SMS_HOME>/shell/manual.json（:cmds/F2/派发对话可读取）" % len(d)) if ok else "手册不全：" + "、".join(x for x in d.values() if not os.path.isfile(x))
GITW = re.compile(r"(?:^|[;&|]\s*)(?:git\s+(?:-[^\s]+\s+)*?(add|commit|merge|rebase|reset|checkout|switch|restore|push|rm|mv|stash|clean|tag|cherry-pick|apply|am|revert|worktree|gc)\b)|git\s+branch\s+-[dD]\b")
def guarded(cmd): m = GITW.search(str(cmd or "")); import permissions; return None if not m or permissions.allow(SMS, "danger", ctx={"tool": "exec", "target": str(cmd or "")[:60], "intent": "用户要求的 git 写操作"}) else "拒绝：git 写操作（" + (m.group(1) or "branch -d") + "）改动仓库历史须用户当轮确认＋:grant danger（红线2·实测有对话自行 commit 致误提交）"
def run(cmd, kind=None, on_line=lambda s: None):
    k = kind_for(cmd, kind)
    if (g := guarded(cmd)): on_line(g); return g
    binp = ""; argv = _direct(cmd) if k in ("powershell", "cmd") else []
    lab = "direct"
    if not argv:
        binp = (detect().get(k) or "") if k else ""
        if not binp: return "未检出可用系统 shell（:sh list）"
        lab = k
        argv = [binp, "/d", "/c", str(cmd)] if k == "cmd" else (
            [binp, "-NoProfile", "-NonInteractive", "-Command", str(cmd)]
            if k in ("powershell", "pwsh") else [binp, "-c", str(cmd)])

    p = no_window.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL, env=dict(os.environ, PYTHONIOENCODING="utf-8", SMS_HOME=SMS, SMS_WORKSPACE=resolve_home.workspace(), SMS_TMP=resolve_home.wtmp()), cwd=resolve_home.workspace())  # stdin=DEVNULL：命令误读输入直接 EOF 而非挂住壳（批12 卡死根治）
    tl = rw.budget("shell"); sl = rw.stall("shell"); buf = []; t0 = time.time()
    done = rw.watchdog(p, buf, tl, sl, str(cmd)[:40], on_warn=lambda n, m: on_line("!watch▸ ⚠ " + m))
    ok, dwhy = rw.pump(p, buf, on_line, "!" + lab + "▸ ", str(cmd)[:40])
    stop.kill_if(p)
    try:
        rc = p.wait(timeout=10)
    except Exception:
        rc = -1
    why = done() or ("" if ok else dwhy); chains.log("tool", "sh:" + lab + ":" + str(cmd)[:60])
    if why: return rw.feedback(str(cmd)[:60], why, time.time() - t0, tl, buf)
    return "rc=" + str(rc)
def export():
    return ("$env:SMS_HOME='%s'; $env:SMS_WORKSPACE='%s'; $env:SMS_TMP='%s'; Set-Location $env:SMS_WORKSPACE\n" % (SMS, resolve_home.workspace(), resolve_home.wtmp()) + "export SMS_HOME='%s' SMS_WORKSPACE='%s' SMS_TMP='%s'; cd \"$SMS_WORKSPACE\"（pwsh/cmd 用首行·bash/zsh 用次行）" % (SMS, resolve_home.workspace(), resolve_home.wtmp()))
if __name__ == "__main__":
    a = sys.argv[1:] or ["list"]
    if a[0] == "list": print(listtext())
    elif a[0] == "select" and len(a) > 1: print(select(a[1]))
    elif a[0] == "run" and len(a) > 1: print(run(" ".join(a[1:]), on_line=print))
    elif a[0] == "procs":
        st = {}; rows = procs(a[1] if len(a) > 1 else None, want_cmdline=(len(a) > 2), status=st)
        print("%s · %d 项 · %s" % (st.get("src"), len(rows), str(rows[:6])))
    elif a[0] == "export": print(export())
    elif a[0] in ("manual", "register-manual"): print(reg_manual() if a[0] == "register-manual" else manual(a[1] if len(a) > 1 else None))
    else: print(__doc__.strip().splitlines()[-1])
