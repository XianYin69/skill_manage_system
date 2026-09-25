#!/usr/bin/env python3
"""settings.py — 配置系统：dot-path get/set <SMS_HOME>/config/config.json（DEFAULTS=config/settings.default.json 深合并保旧配置兼容）；段＝llm_gateway（api_key/base_url/model/温度·top_p）· model_meta（上游模型 Token·上下文·RPM 抓取）· chains（各链启用/修剪/合并）· dream（做梦开关·时间）· web_shell（本地加密网页壳）· external（对外端口）。api_key 恒掩码；变更记 event 链。用法：python -B settings.py status|show|get <path>|set <path> <json>|unset <path>|schema。"""
import os, sys, json
from functools import reduce
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import resolve_home, chains
DEFAULTS = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "settings.default.json"), encoding="utf-8"))
CH = [c for c in chains.CHAINS if c != "knowledge"]
def _dm(a, b):
    for k, v in b.items():
        if k != "comment": a[k] = _dm(a.get(k, {}) if isinstance(a.get(k), dict) else {}, v) if isinstance(v, dict) else v
    return a
def eff(sms=None):
    c = resolve_home.conf(sms or resolve_home.ensure())
    if "dream_interval_min" in c: c.setdefault("dream", {})["interval_min"] = c["dream_interval_min"]
    return _dm(json.loads(json.dumps(DEFAULTS)), c)
def _walk(d, path): return reduce(lambda a, k: a.get(k) if isinstance(a, dict) else None, path.split("."), d)
def get(path, default=None, sms=None):
    v = _walk(eff(sms), path); return default if v is None else v
def maskv(k, v): return "***" if k == "api_key" and v else v
def mask(d): return {k: (mask(v) if isinstance(v, dict) else maskv(k, v)) for k, v in d.items() if k != "comment"}
def flat(d=None, pre=""):
    d = eff() if d is None else d
    return [x for k, v in d.items() if k != "comment" for x in (flat(v, pre + k + ".") if isinstance(v, dict) else [{"path": pre + k, "value": maskv(k, v), "default": _walk(DEFAULTS, pre + k)}])]
def set(path, value, sms=None):
    sms = sms or resolve_home.ensure(); p = os.path.join(sms, "config", "config.json"); ks = path.split(".")
    doc = json.load(open(p, encoding="utf-8-sig")) if os.path.exists(p) else {}
    cur = reduce(lambda a, k: a.setdefault(k, {}), ks[:-1], doc)
    cur.update({ks[-1]: value}) if value is not None else cur.pop(ks[-1], None)
    json.dump(doc, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    chains.record("event", "config set " + path + "=" + str(maskv(ks[-1], value))[:80]); return get(path, sms=sms)
def status(sms=None):
    import model_meta, dream, net_util, ext_net
    sms = sms or resolve_home.ensure(); e = eff(sms); g = e["llm_gateway"]; base = e["chains"].get("default", {})
    key = os.environ.get(g.get("api_key_env") or "", "") or g.get("api_key")
    return {"gateway": {"enabled": g.get("enabled"), "base_url": g.get("base_url"), "model": g.get("model"), "api_key": "set" if key else "missing", "temperature": g.get("temperature"), "top_p": g.get("top_p"), "max_tokens": g.get("max_tokens")},
     "model_meta": model_meta.summary(), "dream": {"enabled": e["dream"]["enabled"], "interval_min": e["dream"]["interval_min"], "due": dream.due(sms)},
     "chains": {c: {**base, **(e["chains"].get(c) or {})} for c in CH},
     "web_shell": {**e["web_shell"], "running": net_util.running("web_shell")},
     "external": {**e["external"], "running": net_util.running("external"), "backend": ext_net.backend()}}
if __name__ == "__main__":
    a = sys.argv[1:] or ["status"]; cmd = a[0]; pj = lambda o, i=None: print(json.dumps(o, ensure_ascii=False, default=str, indent=i))
    if cmd == "status": pj(status(), 1)
    elif cmd == "show": pj(mask(eff()), 1)
    elif cmd == "get": pj(get(a[1]))
    elif cmd == "set" and len(a) > 2: pj(set(a[1], json.loads(a[2])))
    elif cmd == "unset": pj(set(a[1], None))
    elif cmd == "schema": pj(flat(DEFAULTS))
    else: print(__doc__.strip().splitlines()[-1])
