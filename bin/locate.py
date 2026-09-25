#!/usr/bin/env python3
"""locate.py — bin 统一启动定位器（sms-shell 与格式 API 已合并为本入口）：部署＝把 bin 内文件复制到任意指定路径后，本文件负责找回源安装的 skill_manage_system——1) 相邻安装（../skill/scripts/shell.py，兼容旧 ../scripts/shell.py）2) env SMS_SKILL 3) <SMS_HOME>/config/config.json 的 sms_skill（SMS_HOME：env → %LOCALAPPDATA%|~/Library/Caches|~/.cache 下 SMS → ~/SMS）；首参 api → 格式 API（原 sms-api 命令面），其余以 shell.py 为 __main__ 运行，参数原样透传。"""
import os, sys, json, runpy
for s in (sys.stdout, sys.stderr):
    try: s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass
HERE = os.path.dirname(os.path.abspath(__file__))
def _home():
    h = os.environ.get("SMS_HOME")
    if h: return h
    home = os.path.expanduser("~")
    c = os.environ.get("LOCALAPPDATA") or (os.path.join(home, "Library", "Caches") if sys.platform == "darwin" else os.path.join(home, ".cache"))
    for cand in (os.path.join(c, "SMS"), os.path.join(home, "SMS")):
        if os.path.isfile(os.path.join(cand, "config", "config.json")): return cand
    return os.path.join(c, "SMS")
def _skill_base():
    env = os.environ.get("SMS_SKILL") or ""
    cands = [os.path.normpath(os.path.join(HERE, ".."))]
    if env: cands.append(env)
    conf = os.path.join(_home(), "config", "config.json")
    if os.path.isfile(conf):
        try: cands.append(json.load(open(conf, encoding="utf-8-sig")).get("sms_skill") or "")
        except Exception: pass
    for b in cands:
        if b:
            base = _base_of(b)
            if base: return base
    print("未定位到 skill_manage_system：运行过 deploy.py 会登记 sms_skill 到 <SMS_HOME>/config/config.json；也可设 env SMS_SKILL=<skill 绝对路径>", file=sys.stderr)
    sys.exit(1)
def _base_of(root):
    for rel in ("skill" + os.sep, ""):
        p = os.path.normpath(os.path.join(root, rel))
        if os.path.isfile(os.path.join(p, "scripts", "shell.py")): return p
    return None
def _scripts(): return os.path.join(_skill_base(), "scripts")
def _shell():
    p = os.path.join(_scripts(), "shell.py")
    if not os.path.isfile(p): print("缺失 shell.py：" + p, file=sys.stderr); sys.exit(1)
    return p
if __name__ == "__main__":
    if sys.argv[1:2] == ["api"]:
        sys.argv = ["api.py"] + sys.argv[2:]
        p = os.path.join(_scripts(), "api.py")
        if os.path.isfile(p): runpy.run_path(p, run_name="__main__")
        else: runpy.run_path(os.path.join(HERE, "api.py"), run_name="__main__")
    else:
        sys.exit(runpy.run_path(_shell(), run_name="__main__") or 0)
