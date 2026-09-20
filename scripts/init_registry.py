#!/usr/bin/env python3
"""init_registry.py — 初始设置：register → pack → connect 一次跑通。"""
import os, sys, json


def run(sms, roots, dry):
    import resolve_home, register, pack, connect
    _, reg = register.build(sms, roots)
    out1 = os.path.join(sms, "registry", "register.json")
    _, itf = pack.pack(sms, reg)
    out2 = os.path.join(sms, "registry", "interfaces.json")
    _, con = connect.build(sms, reg, itf)
    out3 = os.path.join(sms, "registry", "connections.json")
    trio = ((out1, reg), (out2, itf), (out3, con))
    if dry:
        return {os.path.basename(o): d for o, d in trio}
    for o, d in trio:
        json.dump(d, open(o, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return {"OK": [out1, out2, out3]}


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import resolve_home, register
    sms = resolve_home.ensure()
    roots = [a for a in sys.argv[1:] if not a.startswith("--")] or register.DEFAULT_ROOTS
    res = run(sms, roots, "--dry-run" in sys.argv)
    print(json.dumps(res, ensure_ascii=False, indent=2))