#!/usr/bin/env python3
"""deploy.py — 把 SMS 与托管 skills 部署到其他目录/agent 客户端：默认预览，--write 且已授予 write 才执行；复制排除 .git/.kilo/__pycache__/tmp；目标=位置参数目录或 --clients a,b；--skills a,b|all 附带部署 hub/客户端目录中的 skill；--launcher 在目标根生成 sms-shell(.cmd) 可执行启动器——部署后其他路径直接运行该文件即可起 GUI/TUI 壳。"""
import os, sys, json, shutil
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXCL = shutil.ignore_patterns(".git", ".kilo", "__pycache__", "*.pyc", "tmp", "SMS")
def _clients(): import sync_skills; return sync_skills.clients()
def _roots(sms): return [os.path.join(sms, "skills")] + sorted(_clients().values())
def _pick(sms, name):
    for r in _roots(sms):
        if os.path.isfile(os.path.join(r, name, "SKILL.md")): return os.path.join(r, name)
    return None
def _names(sms, spec):
    if spec != "all": return [n.strip() for n in spec.split(",") if n.strip()]
    return sorted({n for r in _roots(sms) if os.path.isdir(r) for n in os.listdir(r) if os.path.isfile(os.path.join(r, n, "SKILL.md"))})
def deploy(sms, targets, with_sms, skills, write):
    acts = []
    items = ([("skill_manage_system", HERE)] if with_sms else []) + [(n, _pick(sms, n)) for n in skills]
    for d in targets:
        for n, src in items:
            if not src: acts.append("MISS " + n + "（hub/客户端目录未找到，先 sync pull 或 install）"); continue
            dst = os.path.join(d, n)
            acts.append(("deploy " if write else "would deploy ") + n + " -> " + dst)
            if write:
                os.makedirs(d, exist_ok=True); shutil.copytree(src, dst, dirs_exist_ok=True, ignore=EXCL)
    return acts
def launcher(d, write):
    files = {"sms-shell.cmd": b'@echo off\r\npython -B "%~dp0skill_manage_system\\scripts\\shell.py" %*\r\n',
             "sms-shell": b'#!/bin/sh\nexec python3 -B "$(dirname "$0")/skill_manage_system/scripts/shell.py" "$@"\n'}
    acts = []
    for name, data in files.items():
        acts.append(("launcher " if write else "would launcher ") + os.path.join(d, name))
        if write: os.makedirs(d, exist_ok=True); open(os.path.join(d, name), "wb").write(data); os.chmod(os.path.join(d, name), 0o755)
    return acts
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import resolve_home, permissions
    sms = resolve_home.ensure(); raw = sys.argv[1:]; w = "--write" in raw; skip = set()
    for i, x in enumerate(raw):
        if x in ("--clients", "--skills") and i + 1 < len(raw) and not raw[i + 1].startswith("--"): raw[i] = x + "=" + raw[i + 1]; skip.add(i + 1)
    kv = dict(x[2:].split("=", 1) for i, x in enumerate(raw) if x.startswith("--") and "=" in x and i not in skip)
    dirs = [os.path.expandvars(os.path.expanduser(x)) for i, x in enumerate(raw) if not x.startswith("--") and i not in skip]
    cls = _clients()
    for c in (kv.get("clients") or "").replace(",", " ").split():
        if c not in cls: print("未知客户端（未检出该 agent 目录；可先设 env SMS_CLIENTS=\"name=path;...\"）: " + c); sys.exit(1)
        dirs.append(cls[c])
    if not dirs: print("用法: deploy.py <dir...> | --clients a,b [--skills a,b|all] [--no-sms] [--launcher] --write"); sys.exit(1)
    if w and not permissions.allow(sms, "write"): print("DENIED: 会话未授予 write 权限（permissions.json）"); sys.exit(1)
    skills = _names(sms, kv["skills"]) if "skills" in kv else []
    acts = deploy(sms, dirs, "--no-sms" not in raw, skills, w) + ([l for d in dirs for l in launcher(d, w)] if "--launcher" in raw else [])
    print(json.dumps({"targets": dirs, "actions": acts}, ensure_ascii=False, indent=2))
