#!/usr/bin/env python3
"""permissions.py — 权限管理：grant/deny/check/audit，维护 sessions/<日期>/permissions.json（含 privacy，默认拒绝）。"""
import os, sys, json, time

KEYS = ("read", "write", "execute", "network", "privacy")
DEFAULT_GRANTS = {"read": True, "write": False, "execute": False, "network": False, "privacy": False}
DATE = time.strftime("%Y-%m-%d")


def _path(sms):
    return os.path.join(sms, "sessions", DATE, "permissions.json")


def _doc(path):
    if os.path.exists(path):
        return json.load(open(path, encoding="utf-8"))
    return {"date": DATE, "audit": [], "grants": dict(DEFAULT_GRANTS)}


def check(doc, key):
    return bool(doc["grants"].get(key))


def allow(sms, key):
    return check(_doc(_path(sms)), key)


def apply(sms, cmd, key, dry):
    path = _path(sms)
    doc = _doc(path)
    if cmd == "check":
        return {"allowed": check(doc, key)}
    doc["grants"][key] = (cmd == "grant")
    doc.setdefault("audit", []).append({"ts": time.strftime("%H:%M:%S"), "action": cmd, "key": key})
    if dry:
        return {"dry_run": True, "grants": doc["grants"]}
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(doc, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return {"grants": doc["grants"]}


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import resolve_home
    sms = resolve_home.ensure()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    key = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else "write"
    print(json.dumps(apply(sms, cmd, key, "--write" not in sys.argv), ensure_ascii=False))