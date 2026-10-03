#!/usr/bin/env python3
"""register.py — 扫描技能安装位置与所用工具，生成 registry/register.json。
默认扫描根读 skills_config（<SMS_HOME>/config/skills.json 的 scan_roots），--add-root <path>
登记本地目录/文件为扫描根；根自身含 SKILL.md（或 skill/SKILL.md）时该根即作为一个
技能登记（按路径加入单个 skill），父子根重复命中自动去重。深度 2：候选根下
<skill>/private/* 含 SKILL.md 者同样登记（附属技能必须可被 SMS 索引与派发），
条目附 visibility/parent/publish——publish=false 语义＝永不进 git/远端/GitHub，
注册≠发布。"""
import os, sys, time, glob

TOOLS = ["read", "write", "edit", "glob", "grep", "bash", "task", "skill", "websearch", "webfetch"]
DEFAULT_ROOTS = [os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sub_skills"), os.path.expanduser("~/.kilocode/skills")]
ENTRY_RELS = ("SKILL.md", "skill/SKILL.md")

def candidates(root):
    """深度 1 候选：root 自身 + root/*（与原实现同集合，不过滤文件项）。"""
    return [root] + sorted(glob.glob(os.path.join(root, "*")))

def find_skills(roots):
    """深度 1 全扫后追加深度 2：候选目录下 `private/*` 含 SKILL.md 者也登记（parent＝所属技能名）。"""
    out = []; seen = set(); skill_dirs = []
    for root in roots:
        cands = candidates(root)
        for d in cands:
            for rel in ENTRY_RELS:
                if os.path.isfile(os.path.join(d, rel)) and d not in seen:
                    seen.add(d); skill_dirs.append(d)
                    out.append((os.path.basename(d), d, os.path.join(d, rel), rel, None)); break
        for d in skill_dirs:  # 深度 2：只对真技能目录扫 private/*（附属技能必属某技能）
            for p in sorted(glob.glob(os.path.join(d, "private", "*"))):
                if not os.path.isdir(p):
                    continue
                for rel in ENTRY_RELS:
                    if os.path.isfile(os.path.join(p, rel)) and p not in seen:
                        seen.add(p)
                        out.append((os.path.basename(p), p,
                                    os.path.join(p, rel), rel,
                                    os.path.basename(d)))
                        break
    return out

def meta(sk):
    rows = open(sk, encoding="utf-8", errors="ignore").read().splitlines()
    low = "\n".join(rows).lower()
    i = next((i for i, l in enumerate(rows) if l.strip().startswith("description:")), -1)
    v = rows[i].split(":", 1)[1].strip() if i >= 0 else ""
    d = v.strip("\"'") if v and v[0] not in ">|" else (rows[i + 1].strip() if 0 <= i < len(rows) - 1 else "")
    return [t for t in TOOLS if t in low], d[:100]

def visibility_of(sk, attached):
    """读 SKILL.md frontmatter 顶层 `visibility:`；缺省：附属（private/ 下）＝PRIVATE，普通技能＝PUBLIC。"""
    default = "PRIVATE" if attached else "PUBLIC"
    try:
        rows = open(sk, encoding="utf-8-sig", errors="ignore").read().splitlines()
    except OSError:
        return default
    if not rows or rows[0].strip() != "---":
        return default
    for l in rows[1:]:
        if l.strip() == "---":
            break
        if l[:1].isspace():
            continue
        if l.strip().startswith("visibility:"):
            val = l.split(":", 1)[1].strip().strip("\"'")
            return val.upper() if val else default
    return default

def build(sms, roots):
    rows = []
    import trust
    for n, d, sk, rel, parent in find_skills(roots):
        tools, desc = meta(sk)
        vis = visibility_of(sk, parent is not None)
        rows.append({"id": n, "name": n, "install_path": d, "entry": rel,
                     "kind": "sub_skill" if "sub_skills" in d else "skill",
                     "tools": tools, "description": desc,
                     "status": "active", "updated_at": time.strftime("%Y-%m-%d"),
                     "trust": trust.label_of(sms, n),
                     "visibility": vis, "parent": parent, "publish": vis != "PRIVATE"})
    doc = {"schema": "skill_register", "version": "1.1.0",
           "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
           "scan_roots": roots, "skills": rows}
    return os.path.join(sms, "registry", "register.json"), doc

if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import resolve_home, skills_config
    sms = resolve_home.ensure(); args = sys.argv[1:]
    if "--add-root" in args: v = args[args.index("--add-root") + 1]; print(skills_config.add_root(v, sms)); args = [a for a in args if not a.startswith("--") and a != v]
    roots = [a for a in args if not a.startswith("--")] or skills_config.roots(sms) or DEFAULT_ROOTS  # 批4修复：--write 等旗标曾被当扫描根致注册表刷空
    out, doc = build(sms, roots)
    import emit
    print(emit.write_json(out, doc, sms, "--write" not in sys.argv))
