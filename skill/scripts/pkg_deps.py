#!/usr/bin/env python3
"""pkg_deps.py — 技能包 dependence/ 目录检查与净化（install.py 安装时调用·与技能包同一口径）：子包须含 SKILL.md 并按来源标 trust（cloud→pending_review、local→trusted_local），quarantine 拒整包；非包条目（软件/仓库地址/杂项）标 dep:<名> pending_review 留人工 review，绝不自动下载或执行，URL 抽出留档。"""
import os, re

URL_RE = re.compile(r"(?:gh:|https?://)[\w./:@~+%#\-]+")
TEXT = (".md", ".txt", ".json", ".yaml", ".yml", ".list", ".csv")

def _kind(p): return "pkg" if os.path.isdir(p) and os.path.isfile(os.path.join(p, "SKILL.md")) else "item"

def _urls(p):
    if os.path.isdir(p) or not p.endswith(TEXT): return []
    try: return URL_RE.findall(open(p, encoding="utf-8", errors="ignore").read(20000))[:8]
    except OSError: return []

def check(sms, src, source, write):
    dep = os.path.join(src, "dependence")
    if not os.path.isdir(dep): return None
    import trust
    rep = {"checked": 0, "entries": [], "rejected": []}
    for n in sorted(os.listdir(dep)):
        p = os.path.join(dep, n); k = _kind(p); rep["checked"] += 1
        if trust.label_of(sms, "dep:" + n) == "quarantine" or (k == "pkg" and trust.label_of(sms, n) == "quarantine"):
            rep["rejected"].append(n + ":quarantine"); continue
        if k == "pkg":
            lb = "pending_review" if source == "cloud" else "trusted_local"
            trust.mark(sms, n, lb, source, "install:dep", write)
            rep["entries"].append({"name": n, "kind": k, "label": lb})
        else:
            trust.mark(sms, "dep:" + n, "pending_review", source, "install:dep", write)
            rep["entries"].append({"name": n, "kind": k, "label": "pending_review", "urls": _urls(p),
                                   "note": "软件/仓库地址先 trust review 再单独安装，不自动下载执行"})
    return rep

if __name__ == "__main__":
    import sys, json
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import resolve_home
    a = sys.argv[1:]; src = a[0] if a else "."
    d = os.path.abspath(src)
    print(json.dumps(check(resolve_home.ensure(), os.path.dirname(d) if os.path.isfile(src) else d,
                           "cloud" if "--cloud" in a else "local", "--write" in a), ensure_ascii=False, indent=2))
