#!/usr/bin/env python3
"""locate.py — bin 启动定位器：部署＝把 bin 内文件复制到任意指定路径后，本文件负责找回源安装的 skill_manage_system——1) 相邻安装（../skill/scripts/shell.py，兼容旧 ../scripts/shell.py）2) env SMS_SKILL 3) <SMS_HOME>/config/config.json 的 sms_skill（SMS_HOME：env → %LOCALAPPDATA%|~/Library/Caches|~/.cache 下 SMS → ~/SMS）；定位成功即以 shell.py 为 __main__ 运行，参数原样透传。"""
import os, sys, json, runpy
HERE = os.path.dirname(os.path.abspath(__file__))
def _shell_in(base):
    for rel in ("skill" + os.sep, ""):
        p = os.path.normpath(os.path.join(base, rel, "scripts", "shell.py"))
        if os.path.isfile(p): return p
    return None
def _sms_home():
    h = os.environ.get("SMS_HOME")
    if h: return h
    home = os.path.expanduser("~")
    c = os.environ.get("LOCALAPPDATA") or (os.path.join(home, "Library", "Caches") if sys.platform == "darwin" else os.path.join(home, ".cache"))
    for cand in (os.path.join(c, "SMS"), os.path.join(home, "SMS")):
        if os.path.isfile(os.path.join(cand, "config", "config.json")): return cand
    return os.path.join(c, "SMS")
def _shell():
    env = os.environ.get("SMS_SKILL") or ""
    cands = [os.path.normpath(os.path.join(HERE, ".."))]
    if env: cands.append(env)
    conf = os.path.join(_sms_home(), "config", "config.json")
    if os.path.isfile(conf):
        try: cands.append(json.load(open(conf, encoding="utf-8-sig")).get("sms_skill") or "")
        except Exception: pass
    for base in cands:
        if base:
            p = _shell_in(base)
            if p: return p
    print("未定位到 skill_manage_system：运行过 deploy.py 会登记 sms_skill 到 <SMS_HOME>/config/config.json；也可设 env SMS_SKILL=<skill 绝对路径>", file=sys.stderr)
    sys.exit(1)
if __name__ == "__main__":
    runpy.run_path(_shell(), run_name="__main__")
