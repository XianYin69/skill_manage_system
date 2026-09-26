#!/usr/bin/env python3
"""sys_shells.py — 基本 shell 指令与系统 shell 联动：detect 检出 powershell/pwsh/cmd/bash/zsh（含 Git-Bash 回退路径）；选择持久 <SMS_HOME>/shell/shell_kind；run(cmd) 以选定 shell 单发执行——cwd＝SMS_WORKSPACE、env 注入 SMS_HOME/SMS_WORKSPACE/SMS_TMP（与工作区/生成文件口径一致），输出逐行回显并记 tool_call 链；export() 打印联动片段（在系统原生 shell 里 set/export 后即与 sms-shell 同工作区同 tmp，双向联动）。壳内 `!命令` 与 `:sh <命令>` 为同一入口。用法：python -B sys_shells.py list|select <kind>|run <命令>|export"""
import os, sys, shutil, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import resolve_home, chains
SMS = resolve_home.ensure()
KNOWN = {"pwsh": ["pwsh"], "powershell": ["powershell"], "cmd": ["cmd"], "bash": ["bash", r"C:\Program Files\Git\bin\bash.exe"], "zsh": ["zsh"]}
def detect(): return {k: next((c for c in cs if shutil.which(c) or os.path.isfile(c or "")), None) for k, cs in KNOWN.items()}
def kinds(): return [k for k, v in detect().items() if v]
def current():
    try: c = open(os.path.join(SMS, "shell", "shell_kind"), encoding="utf-8").read().strip()
    except Exception: c = ""
    ks = kinds(); return c if c in ks else next((k for k in ("pwsh", "powershell", "cmd", "bash", "zsh") if k in ks), "")
def select(k):
    if k not in kinds(): return "未检出 shell：" + str(k) + "（:sh list 看可用）"
    os.makedirs(os.path.join(SMS, "shell"), exist_ok=True); open(os.path.join(SMS, "shell", "shell_kind"), "w", encoding="utf-8").write(k)
    return "系统 shell 选定：" + k + "（sms-shell `!命令`/`:sh <命令>` 与 gateway exec 之外的手动入口）"
def listtext():
    cur = current(); return "可检出系统 shell：" + ("、".join(kinds()) or "（无）") + " · 当前：" + cur + " · 用法：`!dir`/`:sh <命令>` 单发执行（cwd＝工作区 tmp 收产物）· `:sh <kind>` 选定 · `:sh export` 打印系统 shell 联动片段"
def run(cmd, kind=None, on_line=lambda s: None):
    k = kind if kind in kinds() else current(); binp = (detect().get(k) or "") if k else ""
    if not binp: return "未检出可用系统 shell（:sh list）"
    p = subprocess.Popen([binp, "/c" if k == "cmd" else "-c", str(cmd)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", env=dict(os.environ, PYTHONIOENCODING="utf-8", SMS_HOME=SMS, SMS_WORKSPACE=resolve_home.workspace(), SMS_TMP=resolve_home.wtmp()), cwd=resolve_home.workspace())
    for ln in iter(p.stdout.readline, ""):
        if ln.strip(): on_line(("!" + k + "▸ ") + ln.rstrip())
    rc = p.wait(); chains.log("tool", "sh:" + k + ":" + str(cmd)[:60])
    return "rc=" + str(rc)
def export():
    return ("$env:SMS_HOME='%s'; $env:SMS_WORKSPACE='%s'; $env:SMS_TMP='%s'; Set-Location $env:SMS_WORKSPACE\n" % (SMS, resolve_home.workspace(), resolve_home.wtmp())
            + "export SMS_HOME='%s' SMS_WORKSPACE='%s' SMS_TMP='%s'; cd \"$SMS_WORKSPACE\"（pwsh/cmd 用首行·bash/zsh 用次行）" % (SMS, resolve_home.workspace(), resolve_home.wtmp()))
if __name__ == "__main__":
    a = sys.argv[1:] or ["list"]
    if a[0] == "list": print(listtext())
    elif a[0] == "select" and len(a) > 1: print(select(a[1]))
    elif a[0] == "run" and len(a) > 1: print(run(" ".join(a[1:]), on_line=print))
    elif a[0] == "export": print(export())
    else: print(__doc__.strip().splitlines()[-1])
