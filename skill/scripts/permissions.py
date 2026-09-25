#!/usr/bin/env python3
"""permissions.py — 权限：grant/deny/check/audit + 角色批量 + TTL 自动到期；vault/verify 敏感键控凭据与验证协助；danger 键控高危（skill/SMS_HOME 外递归删除、向用户目录复制覆盖）——默认拒绝、不随角色批量，须用户当轮确认后单独 grant（红线 16）。"""
import os, sys, json, time
from datetime import datetime, timedelta
KEYS = ("read", "write", "execute", "network", "privacy", "vault", "verify", "danger")
ROLES = {"readonly": ["read"], "worker": ["read", "write", "execute"], "net": ["read", "write", "execute", "network"],
         "privacy": ["read", "privacy"], "secrets": ["read", "vault", "verify"], "admin": [k for k in KEYS if k != "danger"]}
DEFAULT_GRANTS = dict(zip(KEYS, [True, False, False, False, False, False, False, False]))
DATE = time.strftime("%Y-%m-%d")
def _path(sms): return os.path.join(sms, "sessions", DATE, "permissions.json")
def _doc(path):
    if os.path.exists(path): return json.load(open(path, encoding="utf-8"))
    return {"date": DATE, "audit": [], "grants": dict(DEFAULT_GRANTS)}
def check(doc, key):
    v = doc["grants"].get(key)
    if isinstance(v, dict): return bool(v.get("on")) and time.strftime("%Y-%m-%dT%H:%M:%S") < str(v.get("until", ""))
    return bool(v)
def allow(sms, key): return check(_doc(_path(sms)), key)
def apply(sms, cmd, target, dry, ttl=0):
    path, doc = _path(sms), _doc(_path(sms))
    if cmd == "check":
        keys = ROLES.get(target, [target])
        return {"target": target, "allowed": {k: check(doc, k) for k in keys}}
    on = cmd == "grant"
    for k in ROLES.get(target, [target]):
        doc["grants"][k] = {"on": True, "until": (datetime.now() + timedelta(minutes=ttl)).strftime("%Y-%m-%dT%H:%M:%S")} if on and ttl else on
        doc.setdefault("audit", []).append({"ts": time.strftime("%H:%M:%S"), "action": cmd, "key": k, "ttl_min": ttl})
    if dry: return {"dry_run": True, "grants": doc["grants"]}
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(doc, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return {"grants": doc["grants"]}
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import resolve_home
    sms = resolve_home.ensure()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    target = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else "write"
    ttl = next((int(x) for x in sys.argv[3:] if x.isdigit()), 0)
    print(json.dumps(apply(sms, cmd, target, "--write" not in sys.argv, ttl), ensure_ascii=False))
