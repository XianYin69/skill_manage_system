#!/usr/bin/env python3
"""sys_shells.py — 基本 shell 指令与系统 shell 联动：detect 检出 powershell/pwsh/cmd/bash/zsh；批6 关键优化：detect 拒认 WSL/商店 bash 桩（System32\\bash.exe·WindowsApps\\bash.exe——它使每条 unix 命令冷启 WSL VM 实测 ~32s，是 skill/子skill exec 卡顿主因），只认真身 Git-Bash；run 对 powershell/pwsh 加 -NoProfile -NonInteractive、cmd 加 /d（免档案/AutoRun 拖慢）；unix 风格命令仅在有真 bash 时改道，否则 powershell 直跑（echo/ls/cat/git/python 在 PS 原生可用）。选择持久 <SMS_HOME>/shell/shell_kind；git 写操作（add/commit/reset…）恒门禁（红线2）；cwd＝SMS_WORKSPACE、env 注入 SMS_HOME/SMS_WORKSPACE/SMS_TMP，输出逐行回显并记 tool_call 链；export() 打印联动片段。壳内 `!命令`、`:sh`、F7 直通与 gateway exec 同一入口。用法：python -B sys_shells.py list|select <kind>|run <命令>|export"""
import os, sys, re, shutil, subprocess, threading
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import resolve_home, chains, settings
SMS = resolve_home.ensure()
KNOWN = {"pwsh": ["pwsh"], "powershell": ["powershell"], "cmd": ["cmd"], "bash": ["bash", r"C:\Program Files\Git\bin\bash.exe", r"C:\Program Files (x86)\Git\bin\bash.exe"], "zsh": ["zsh"]}
WSL = re.compile(r"(?i)\\system32\\bash(\.exe)?$|\\windowsapps\\")
UNIX = re.compile(r"^\s*(?:sudo\s+)?(?:ls|ll|cat|grep|egrep|rg|sed|awk|find|touch|mkdir|cp|mv|rm|df|du|ps|kill|chmod|chown|ln|head|tail|wc|sort|uniq|which|whoami|pwd|echo|printf|tree|diff|tar|zip|unzip|curl|wget|open|date|env|history|less|more|basename|dirname|xargs|seq|tr|cut|jq|make|python|pip|node|npm|git|ssh|scp|ping|ip|netstat)\b")
def _rp(c):
    p = (c if os.path.isabs(c) else (shutil.which(c) or "")); return p if (p and os.path.isfile(p) and not WSL.search(p)) else ""
def detect(): return {k: next((r for r in map(_rp, cs) if r), None) for k, cs in KNOWN.items()}
def kinds(): return [k for k, v in detect().items() if v]
def kind_for(cmd, kind=None):
    k = kind if kind in kinds() else current()
    if k in ("powershell", "cmd") and UNIX.match(str(cmd or "").strip()):
        return next((b for b in ("bash", "zsh") if b in kinds()), k)
    return k
def current():
    try: c = open(os.path.join(SMS, "shell", "shell_kind"), encoding="utf-8").read().strip()
    except Exception: c = ""
    ks = kinds(); return c if c in ks else next((k for k in ("pwsh", "powershell", "cmd", "bash", "zsh") if k in ks), "")
def select(k):
    if k not in kinds(): return "未检出 shell：" + str(k) + "（:sh list 看可用）"
    os.makedirs(os.path.join(SMS, "shell"), exist_ok=True); open(os.path.join(SMS, "shell", "shell_kind"), "w", encoding="utf-8").write(k)
    return "系统 shell 选定：" + k + "（sms-shell `!命令`/`:sh <命令>` 与 gateway exec 之外的手动入口）"
def listtext(): cur = current(); return "可检出系统 shell：" + ("、".join(kinds()) or "（无）") + " · 当前：" + cur + " · 用法：`!dir`/`:sh <命令>` 单发执行（cwd＝工作区 tmp 收产物）· `:sh <kind>` 选定 · `:sh export` 打印系统 shell 联动片段"
GITW = re.compile(r"(?:^|[;&|]\s*)(?:git\s+(?:-[^\s]+\s+)*?(add|commit|merge|rebase|reset|checkout|switch|restore|push|rm|mv|stash|clean|tag|cherry-pick|apply|am|revert|worktree|gc)\b)|git\s+branch\s+-[dD]\b")
def guarded(cmd): m = GITW.search(str(cmd or "")); import permissions; return None if not m or permissions.allow(SMS, "danger") else "拒绝：git 写操作（" + (m.group(1) or "branch -d") + "）改动仓库历史须用户当轮确认＋:grant danger（红线2·实测有对话自行 commit 致误提交）"
def run(cmd, kind=None, on_line=lambda s: None):
    k = kind_for(cmd, kind); binp = (detect().get(k) or "") if k else ""
    if not binp: return "未检出可用系统 shell（:sh list）"
    if (g := guarded(cmd)): on_line(g); return g
    argv = [binp, "/d", "/c", str(cmd)] if k == "cmd" else ([binp, "-NoProfile", "-NonInteractive", "-Command", str(cmd)] if k in ("powershell", "pwsh") else [binp, "-c", str(cmd)])
    p = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", env=dict(os.environ, PYTHONIOENCODING="utf-8", SMS_HOME=SMS, SMS_WORKSPACE=resolve_home.workspace(), SMS_TMP=resolve_home.wtmp()), cwd=resolve_home.workspace())
    killed = []; tl = max(5, int(settings.get("shell.exec_timeout", 600)))
    tk = threading.Timer(tl, lambda: p.poll() is None and (killed.append(1), p.kill())); tk.daemon = True; tk.start()
    for ln in iter(p.stdout.readline, ""):
        if ln.strip(): on_line(("!" + k + "▸ ") + ln.rstrip())
    rc = p.wait(); tk.cancel(); chains.log("tool", "sh:" + k + ":" + str(cmd)[:60])
    return "rc=" + str(rc) + ("（超时 %ds 已中止）" % tl if killed else "")
def export():
    return ("$env:SMS_HOME='%s'; $env:SMS_WORKSPACE='%s'; $env:SMS_TMP='%s'; Set-Location $env:SMS_WORKSPACE\n" % (SMS, resolve_home.workspace(), resolve_home.wtmp()) + "export SMS_HOME='%s' SMS_WORKSPACE='%s' SMS_TMP='%s'; cd \"$SMS_WORKSPACE\"（pwsh/cmd 用首行·bash/zsh 用次行）" % (SMS, resolve_home.workspace(), resolve_home.wtmp()))
if __name__ == "__main__":
    a = sys.argv[1:] or ["list"]
    if a[0] == "list": print(listtext())
    elif a[0] == "select" and len(a) > 1: print(select(a[1]))
    elif a[0] == "run" and len(a) > 1: print(run(" ".join(a[1:]), on_line=print))
    elif a[0] == "export": print(export())
    else: print(__doc__.strip().splitlines()[-1])
