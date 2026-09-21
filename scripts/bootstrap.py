#!/usr/bin/env python3
"""bootstrap.py — 确保 Skill_Generator 可用：查技能目录与配置；缺失则从 GitHub 拉取。"""
import os, sys, json, glob

ID = "skill_generator"
REPO = "https://github.com/XianYin69/Skill_Generator.git"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOTS = [os.path.join(ROOT, "sub_skills"), os.path.expanduser("~/.kilocode/skills")]
CONFIGS = ("config/config.json", "config/config.example.json")

def _hit(s):
    return ID.replace("_", "") in str(s).lower().replace("_", "")

def in_folders():
    for r in ROOTS:
        for d in glob.glob(os.path.join(r, "*")):
            if _hit(os.path.basename(d)) and os.path.isfile(os.path.join(d, "SKILL.md")):
                return d
    return None

def in_config():
    for c in CONFIGS:
        p = os.path.join(ROOT, c)
        if os.path.exists(p):
            sg = json.load(open(p, encoding="utf-8")).get("skill_generator") or {}
            path = os.path.expanduser(sg.get("path") or "")
            if sg.get("repo") or (path and os.path.isdir(path)):
                return {"repo": sg.get("repo"), "path": path or None}
    return {}

def acquire(sms, dry):
    cfg, folder = in_config(), in_folders()
    if folder or cfg.get("path"):
        return {"found": True, "folder": folder, "config_path": cfg.get("path")}
    repo, dest = cfg.get("repo") or REPO, os.path.join(ROOTS[1], "Skill_Generator")
    if dry:
        return {"found": False, "action": "would clone", "repo": repo, "target": dest}
    import permissions, subprocess
    if not (permissions.allow(sms, "network") and permissions.allow(sms, "write")):
        return {"found": False, "action": "DENIED: 拉取需授予 network + write"}
    r = subprocess.run(["git", "clone", "--depth", "1", repo, dest], capture_output=True, text=True)
    if r.returncode == 0: import trust; trust.mark(sms, os.path.basename(dest), "pending_review", "cloud", "bootstrap")
    return {"found": False, "cloned": r.returncode == 0, "target": dest, "detail": (r.stderr or r.stdout).strip()[:200]}

if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import resolve_home
    sms = resolve_home.ensure()
    print(json.dumps(acquire(sms, "--write" not in sys.argv), ensure_ascii=False, indent=2))