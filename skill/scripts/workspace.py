#!/usr/bin/env python3
"""workspace.py — SMS 工作区（SMS_HOME 数据根）登记·切换·改路径：清单与当前指针持久化于 bootstrap 配置（缓存目录下 SMS/config/config.json 的 sms_home＋workspaces，env SMS_BOOT 可覆写该文件路径供测试隔离）；switch 先写 bootstrap 再置本进程 env——一切子脚本（run_script 子进程）即时按新根解析，壳前端据此重启完全生效；变更记 event 链。用法：python -B workspace.py current|list|add <path>|switch <path>|remove <path>。"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import resolve_home, chains
def boot():
    return os.environ.get("SMS_BOOT") or os.path.join(resolve_home._cache(), "SMS", "config", "config.json")
def _read():
    try: return json.load(open(boot(), encoding="utf-8-sig"))
    except Exception: return {}
def _write(d):
    p = boot(); os.makedirs(os.path.dirname(p), exist_ok=True); json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
def current(): return resolve_home.resolve()
def list_ws():
    ws = [x for x in (_read().get("workspaces") or []) if isinstance(x, str) and x]; cur = current()
    return ([cur] if cur not in ws else []) + ws
def _abs(p): return os.path.abspath(os.path.expanduser(p))
def add(p):
    p = _abs(p)
    if not os.path.isdir(p): return "拒绝：工作区目录不存在 " + p
    if p in list_ws(): return "已登记工作区：" + p
    d = _read(); d["workspaces"] = list_ws() + [p]; _write(d)
    chains.record("event", "workspace add " + p); return "已登记工作区：" + p
def switch(p):
    if (msg := add(p)).startswith("拒绝"): return msg
    chains.record("event", "workspace switch -> " + _abs(p))
    d = _read(); d["sms_home"] = _abs(p); d["workspaces"] = list_ws(); _write(d)
    os.environ["SMS_HOME"] = d["sms_home"]
    return "已切换工作区 → " + d["sms_home"] + "（子脚本即时生效；退出重进或壳内 F6→⟳ 重启完全生效）"
def remove(p):
    d = _read(); before = d.get("workspaces") or []; ws = [x for x in before if x != _abs(p)]
    if len(ws) == len(before): return "无登记工作区：" + p
    d["workspaces"] = ws; _write(d); chains.record("event", "workspace remove " + p); return "已移除登记：" + p
if __name__ == "__main__":
    a = sys.argv[1:] or ["list"]; cmd = a[0]
    if cmd == "current": print(current())
    elif cmd == "list": print("\n".join(("* " if w == current() else "  ") + w for w in list_ws()))
    elif cmd in ("add", "switch", "remove") and len(a) > 1: print({"add": add, "switch": switch, "remove": remove}[cmd](" ".join(a[1:])))
    else: print(__doc__.strip().splitlines()[-1])
