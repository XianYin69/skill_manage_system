#!/usr/bin/env python3
"""chain_store.py — 十一链（用户/记忆/逻辑/时间/事件/会话/调用skill/调用工具/子会话/对话/钉选knowledge）碎片存储层：每条链为 JSON 碎片（语句化/最小化），含向量（64 维哈希投影，语句指向）、频次（使用计数）、边（语义/时间/因果/引用，树形·神经网络型）。数据 <SMS_HOME>/chains/<链>/<id>.json；纯标准库、零依赖。"""
import os, sys, json, re, time, math, hashlib; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import chains_git
def _toks(s):
    s = s.lower(); return re.findall(r"[a-z0-9]+", s) + [a + b for a, b in zip(s, s[1:]) if "\u4e00" <= a <= "\u9fff" and "\u4e00" <= b <= "\u9fff"]
def vec(t):
    v = [0.0] * 64
    for x in set(_toks(t)): v[int(hashlib.md5(x.encode()).hexdigest()[:8], 16) % 64] += 1.0
    n = math.sqrt(sum(q * q for q in v)) or 1.0; return [round(q / n, 4) for q in v]
def cos(a, b): return sum(x * y for x, y in zip(a, b))
def _ld(p): return json.load(open(p, encoding="utf-8"))
def _wj(p, d): json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False); chains_git.touch()
class Store:
    def __init__(self, sms): self.root = os.path.join(sms, "chains"); chains_git.ensure(self.root)
    def _p(self, c, fid): return os.path.join(self.root, c, fid + ".json")
    def _cof(self, fid): return next((c for c in (sorted(os.listdir(self.root)) if os.path.isdir(self.root) else []) if os.path.exists(self._p(c, fid))), None)
    def add(self, chain, text, edges=None):
        fid = hashlib.md5((chain + text + str(time.time())).encode()).hexdigest()[:10]
        os.makedirs(os.path.join(self.root, chain), exist_ok=True)
        _wj(self._p(chain, fid), {"id": fid, "chain": chain, "ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "text": text.strip(),
              "vec": vec(text), "freq": 1, "edges": [[e[0], e[1], e[2] if len(e) > 2 else 1.0] for e in edges or []]})
        return fid
    def all_frags(self, chain=None):
        return [f for c in ([chain] if chain else (sorted(os.listdir(self.root)) if os.path.isdir(self.root) else []))
                for p in ([os.path.join(self.root, c)] if os.path.isdir(os.path.join(self.root, c)) else [])
                for x in sorted(os.listdir(p)) if x.endswith(".json") for f in [_ld(os.path.join(p, x))]]
    def bump(self, fid):
        c = self._cof(fid)
        if c: d = _ld(self._p(c, fid)); d["freq"] += 1; _wj(self._p(c, fid), d)
        return bool(c)
    def remove(self, fid):
        return next((os.remove(self._p(c, fid)) or chains_git.touch() or True for c in (self._cof(fid),) if c), None)
    def link(self, a, b, rel="semantic", w=1.0):
        c = self._cof(a)
        if c:
            d = _ld(self._p(c, a)); d["edges"].append([b, rel if self._cof(b) else "ref", round(w, 3)]); _wj(self._p(c, a), d)
    def merge_near(self, chain=None, thr=0.92):
        fs = self.all_frags(chain); n = 0
        for i, a in enumerate(fs):
            for b in fs[i + 1:]:
                if (a.get("dead") or b.get("dead")) or not (a["text"] == b["text"] or cos(a["vec"], b["vec"]) >= thr): continue
                a["freq"] += b.get("freq", 1); a["edges"] += b.get("edges", []); b["dead"] = True
                _wj(self._p(a["chain"], a["id"]), a); _wj(self._p(b["chain"], b["id"]), b); n += 1
        return n
    def prune(self, days=14, min_freq=1):
        cut = time.strftime("%Y-%m-%d", time.localtime(time.time() - days * 86400))
        dead = [(self._wj(self._p(f["chain"], f["id"]), dict(f, dead=True, pruned=cut)) or 1)
                for f in self.all_frags() if f["chain"] != "knowledge" and f["ts"][:10] < cut and f.get("freq", 1) <= min_freq]
        return len(dead)
