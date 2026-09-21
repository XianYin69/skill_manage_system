#!/usr/bin/env python3
"""register.py — 扫描技能安装位置与所用工具，生成 registry/register.json。"""
import os, sys, time, glob

TOOLS = ["read", "write", "edit", "glob", "grep", "bash", "task", "skill", "websearch", "webfetch"]
DEFAULT_ROOTS = [os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sub_skills"), os.path.expanduser("~/.kilocode/skills")]

def find_skills(roots):
    out = []
    for root in roots:
        for d in sorted(glob.glob(os.path.join(root, "*"))):
            sk = os.path.join(d, "SKILL.md")
            if os.path.isfile(sk):
                out.append((os.path.basename(d), d, sk))
    return out

def meta(sk):
    rows = open(sk, encoding="utf-8", errors="ignore").read().splitlines()
    low = "\n".join(rows).lower()
    i = next((i for i, l in enumerate(rows) if l.strip().startswith("description:")), -1)
    v = rows[i].split(":", 1)[1].strip() if i >= 0 else ""
    d = v.strip("\"'") if v and v[0] not in ">|" else (rows[i + 1].strip() if 0 <= i < len(rows) - 1 else "")
    return [t for t in TOOLS if t in low], d[:100]

def build(sms, roots):
    rows = []
    import trust
    for n, d, sk in find_skills(roots):
        tools, desc = meta(sk)
        rows.append({"id": n, "name": n, "install_path": d, "entry": "SKILL.md",
                     "kind": "sub_skill" if "sub_skills" in d else "skill",
                     "tools": tools, "description": desc,
                     "status": "active", "updated_at": time.strftime("%Y-%m-%d"),
                     "trust": trust.label_of(sms, n)})
    doc = {"schema": "skill_register", "version": "1.0.0",
           "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
           "scan_roots": roots, "skills": rows}
    return os.path.join(sms, "registry", "register.json"), doc

if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import resolve_home
    sms = resolve_home.ensure()
    roots = [a for a in sys.argv[1:] if not a.startswith("--")] or DEFAULT_ROOTS
    out, doc = build(sms, roots)
    import emit
    print(emit.write_json(out, doc, sms, "--write" not in sys.argv))