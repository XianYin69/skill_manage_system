#!/usr/bin/env python3
"""permissions.py — 权限：grant/deny/check/status/audit + 角色批量 + TTL 自动到期；生效优先级＝今日显式授予（audit 记过的键·含 TTL）＞ 配置默认 skills.json permissions_default（danger 不随默认）＞ 内置默认——F4 改 permissions_default 即与运行时一致（修复「是否启用与配置文件不一致」）；danger 键控高危（红线16）：默认拒绝、不随角色批量、须当轮单独 grant。用法：python -B permissions.py status | check <键|角色> | grant|deny <键|角色> [分钟] [--write]"""
import os, sys, json, time
from datetime import datetime, timedelta
KEYS = ("read", "write", "execute", "network", "privacy", "vault", "verify", "danger")
ROLES = {"readonly": ["read"], "worker": ["read", "write", "execute"], "net": ["read", "write", "execute", "network"],
         "privacy": ["read", "privacy"], "secrets": ["read", "vault", "verify"], "admin": [k for k in KEYS if k != "danger"]}
DEFAULT_GRANTS = dict(zip(KEYS, [True, False, False, False, False, False, False, False]))
DATE = time.strftime("%Y-%m-%d")
def _path(sms): return os.path.join(sms, "sessions", DATE, "permissions.json")
def check(doc, key):
    v = doc["grants"].get(key)
    if isinstance(v, dict): return bool(v.get("on")) and time.strftime("%Y-%m-%dT%H:%M:%S") < str(v.get("until", ""))
    if isinstance(v, str): return v.strip().lower() in ("true", "1", "on", "yes", "开")
    return bool(v)
def _seed(sms=None):
    d = dict(DEFAULT_GRANTS)
    try:
        import skills_config
        for k, v in (skills_config.get("permissions_default", {}, sms) or {}).items():
            if k in KEYS and k != "danger": d[k] = check({"grants": {k: v}}, k)
    except Exception: pass
    return d
def _doc(path, sms=None):
    if not os.path.exists(path): return {"date": DATE, "audit": [], "grants": _seed(sms)}
    doc = json.load(open(path, encoding="utf-8")); doc.setdefault("grants", {}); doc.setdefault("audit", []); return doc
def _eff(sms):
    doc = _doc(_path(sms), sms); ex = {a.get("key") for a in doc["audit"] if a.get("action") in ("grant", "deny")}
    e = _seed(sms); src = {k: "配置默认" for k in KEYS}
    for k in KEYS:
        if k in ex and k in doc["grants"]: e[k] = check(doc, k); src[k] = "今日授予" + ("（TTL）" if isinstance(doc["grants"][k], dict) else "")
    src["danger"] = "仅今日单独 grant（红线16）" if e.get("danger") or "danger" in ex else "恒默认拒绝"
    return {"effective": e, "source": src, "grants": doc["grants"], "config_default": _seed(sms)}
def allow(sms, key): return _eff(sms)["effective"].get(key, False)
def apply(sms, cmd, target, dry, ttl=0):
    path, doc = _path(sms), _doc(_path(sms), sms)
    if cmd == "status": return _eff(sms)
    if cmd == "check": keys = ROLES.get(target, [target]); return {"target": target, "allowed": {k: allow(sms, k) for k in keys}}
    on = cmd == "grant"
    for k in ROLES.get(target, [target]):
        doc["grants"][k] = {"on": True, "until": (datetime.now() + timedelta(minutes=ttl)).strftime("%Y-%m-%dT%H:%M:%S")} if on and ttl else on
        doc.setdefault("audit", []).append({"ts": time.strftime("%H:%M:%S"), "action": cmd, "key": k, "ttl_min": ttl})
    if dry: return {"dry_run": True, "grants": doc["grants"]}
    os.makedirs(os.path.dirname(path), exist_ok=True); import atomic_io; atomic_io.wjson(path, doc)
    return {"grants": doc["grants"], "note": "未显式授予的键恒随配置 permissions_default（F4 可改）"}
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import resolve_home
    sms = resolve_home.ensure(); a = sys.argv[1:] or ["status"]
    cmd = a[0]; target = a[1] if len(a) > 1 and not a[1].startswith("--") else "write"; ttl = next((int(x) for x in a[2:] if x.isdigit()), 0)
    print(json.dumps(apply(sms, cmd, target, "--write" not in a, ttl), ensure_ascii=False, indent=2))
