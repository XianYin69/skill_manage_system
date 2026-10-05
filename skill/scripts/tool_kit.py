#!/usr/bin/env python3
"""tool_kit.py — 工具件精准高速内核（批27·用户「write/read/network_fetch 等工具使用更精准和高速的算法及命令执行步骤、更清晰准确的工具命令执行范式」）：
① read_window＝流式窗口读（islice 只取所需行，大文件不再整读进内存；带 offset/总行数/截断标记）；
② grep_walk＝剪枝目录＋二进制/超大文件跳过＋逐行流式＋命中即止（旧版整文件 read().splitlines() 且无体积闸）；
③ glob_fast＝目录剪枝＋扫描上限＋墙钟 deadline 早停，status 如实标注「未扫全」（批29·旧版 iglob 无剪枝无时限，实测中位 36.7s/p90 72s）；
④ grep_walk＝同闸（墙钟 deadline＋文件上限）；
⑤ fetch＝Accept-Encoding gzip/deflate＋响应头 charset＋字节上限＋retry_io 有限重试＋html_to_text 正文抽取（旧版整页原样吐 HTML 给模型，白烧 token）；
⑥ adapt＝命令执行范式适配（PowerShell 顶层 && → ;、cmd 内建重定向 2>nul → 2>$null、dir /b → Get-ChildItem -Name），改写即回说明行，杜绝「一条命令因分隔符语法报错再试一轮」。
本模块只做算法与文案，权限/门禁/信封仍归 agent_tools*。用法：python -B tool_kit.py selftest。"""
import os, re, sys, time, gzip, zlib, fnmatch, io as _io
from itertools import islice
PRUNE = {".git", "__pycache__", "node_modules", ".venv", "venv", "dist", "build", ".pytest_cache", ".idea", ".kilocode_cache"}
BIN_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf", ".zip", ".gz", ".7z", ".exe", ".dll", ".pyc", ".mp4", ".mp3", ".woff", ".woff2", ".ttf", ".bak"}
MAXF = 8_000_000
BIG = 2_000_000

def read_window(path, max_lines=120, offset=0, chars=4000):
    """流式窗口读：只缓存 [offset, offset+max_lines) 行；>2MB 文件取满窗口即早停（总行数回 None）。"""
    n = int(max_lines or 120); n = n if n >= 1 else 1; off = max(0, int(offset or 0))
    size = os.path.getsize(path); buf = []; total = 0; early = False
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for i, ln in enumerate(f):
            if off <= i < off + n: buf.append(ln.rstrip("\n"))
            elif i >= off + n and size > BIG: early = True; break
            total = i + 1
    txt = "\n".join(buf); cut = len(txt) > chars
    if cut: txt = txt[:chars]
    return txt, (None if early else total), (cut or early or total > off + len(buf))
def _keep(ns):
    ns[:] = [x for x in ns if x not in PRUNE and (not x.startswith(".") or x in (".github", ".vscode"))]
def _scan_file(p, rel_root, rx, lim):
    """单文件逐行流式扫描：跳二进制扩展名与 >MAXF，命中即止。回 (命中行, 是否截断)。"""
    out = []
    if os.path.splitext(p)[1].lower() in BIN_EXT: return out, False
    try:
        if os.path.getsize(p) > MAXF: return out, False
        with open(p, encoding="utf-8", errors="replace") as f:
            for i, ln in enumerate(f, 1):
                if rx.search(ln):
                    out.append(os.path.relpath(p, rel_root) + ":" + str(i) + ":" + ln.rstrip("\n").strip()[:200])
                    if len(out) >= lim: return out, True
    except Exception:
        return out, False
    return out, False

def grep_walk(root, rx, include="*", max=60, deadline=None, max_files=None, status=None):
    """剪枝＋流式＋命中即止＋墙钟 deadline/文件上限早停（批29 加闸·旧版无时限可整树扫到分钟级）：
    跳 .git/__pycache__/node_modules 等与二进制/超 8MB 文件，逐行扫不整读。status 回扫描量与早停原因；
    时限/上限触发的截断同样回 True 并在 status["note"] 点名「未扫全」。回 (命中行, 是否截断)。"""
    rx = rx if hasattr(rx, "search") else re.compile(str(rx))
    lim = int(max or 60); lim = lim if lim >= 1 else 1
    dl = _num(deadline, "grep_deadline", 8.0)
    capf = int(_num(max_files, "grep_max_files", 20000.0))
    st = status if isinstance(status, dict) else {}
    st.update(files=0, lines=0, deadline=False, cap=False, limit=False, pruned=0)
    if os.path.isfile(root):  # 单文件路径直扫（旧版 os.walk 遇文件静默返回空＝精准度缺陷）
        out, tr = _scan_file(root, os.path.dirname(os.path.abspath(root)) or ".", rx, lim)
        st.update(files=1, limit=tr, mode="单文件")
        _note(st, "单文件扫描", 1, len(out), lim, dl, capf)
        return out, tr
    out = []; t0 = time.time(); stop_ = ""
    for dp, ns, fs in os.walk(root):
        _keep2(ns, st)
        for fn in fs:
            st["files"] += 1
            if capf and st["files"] > capf: stop_ = "cap"; break
            if dl and (st["files"] & 127) == 0 and time.time() - t0 >= dl: stop_ = "deadline"; break
            if include != "*" and not fnmatch.fnmatch(fn, str(include)): continue
            if os.path.splitext(fn)[1].lower() in BIN_EXT: continue
            p = os.path.join(dp, fn)
            try:
                if os.path.getsize(p) > MAXF: continue
                with open(p, encoding="utf-8", errors="replace") as f:
                    for i, ln in enumerate(f, 1):
                        st["lines"] += 1
                        if rx.search(ln):
                            out.append(os.path.relpath(p, root) + ":" + str(i) + ":"
                                       + ln.rstrip("\n").strip()[:200])
                            if len(out) >= lim: stop_ = "limit"; break
            except Exception: continue
            if stop_: break
        if stop_: break
    st["deadline"] = stop_ == "deadline"; st["cap"] = stop_ == "cap"; st["limit"] = stop_ == "limit"
    st["mode"] = "grep 剪枝扫描"
    _note(st, st["mode"], st["files"], len(out), lim, dl, capf)
    return out, bool(stop_)

def _num(v, key, default):
    """数值闸：显式参数 > settings(tools.<key>) > 默认；<=0＝不设限（批29 性能闸）。"""
    if v is None:
        try:
            import settings; v = settings.get("tools." + key)
        except Exception: v = None
    try: v = float(v)
    except Exception: v = float(default)
    return v if v > 0 else 0.0

def _keep2(ns, st):
    """剪枝并计数（供如实标注）。"""
    b = len(ns); _keep(ns); st["pruned"] = st.get("pruned", 0) + b - len(ns)

def _seg_rx(s):
    """单层 glob → 正则片段（* 与 ? 不跨分隔符·[seq] 支持 ! 取反）。"""
    out = []; i = 0; n = len(s)
    while i < n:
        ch = s[i]
        if ch == "*": out.append("[^/]*")
        elif ch == "?": out.append("[^/]")
        elif ch == "[":
            j = s.find("]", i + 1)
            if j < 0: out.append(re.escape(ch))
            else:
                cls = s[i + 1:j]
                if cls[:1] in ("!", "^"): cls = "^" + cls[1:]
                out.append("[" + cls.replace("\\", "\\\\") + "]"); i = j
        else: out.append(re.escape(ch))
        i += 1
    return "".join(out)

def _glob_rx(pattern):
    """glob 模式 → 编译正则（反斜杠归一为 /·** 跨目录·Windows 大小写不敏感）。"""
    segs = [x for x in str(pattern).replace("\\", "/").split("/") if x not in ("", ".")]
    parts = []
    for i, s in enumerate(segs):
        if s == "**":
            parts.append(".*" if i == len(segs) - 1 else "(?:[^/]+/)*")
        else:
            parts.append(_seg_rx(s))
            if i < len(segs) - 1: parts.append("/")
    return re.compile("".join(parts), re.IGNORECASE if os.name == "nt" else 0)

def _note(st, mode, scanned, nhits, limit, dl, cap):
    """如实标注：模式/扫描量/命中数＋早停原因（时限/上限/命中截断），绝不假装结果完整。"""
    bits = [mode, "扫描 %d 项" % scanned, "命中 %d" % nhits]
    if st.get("pruned"): bits.append("剪枝 %d 目录" % st["pruned"])
    if st.get("deadline"): bits.append("⚠墙钟 %.1fs 早停·未扫全" % dl)
    if st.get("cap"): bits.append("⚠扫描上限 %d 早停·未扫全" % cap)
    if st.get("limit"): bits.append("⚠命中达 %d 截断" % limit)
    st["note"] = "·".join(bits); return st["note"]

def glob_fast(pattern, root, limit=200, deadline=None, max_scan=None, status=None):
    """剪枝＋扫描上限＋墙钟 deadline 早停（批29·用户实测旧版 iglob 无剪枝无时限：中位 36.7s/p90 72s）：
    含 ** 的递归模式走自研匹配器（跳 .git/__pycache__/node_modules/venv/dist/build 等，旧版 glob 模块
    不剪枝＝垃圾目录全进）；单层模式仍走 glob.iglob＋islice 早停。status 回实际扫描量与早停原因，
    到 limit/时限/上限即停并如实标注「未扫全」——不假装找全。回 (匹配相对路径≤limit, 是否截断)。"""
    import glob as _g
    st = status if isinstance(status, dict) else {}
    limit = max(1, int(limit or 200)); dl = _num(deadline, "glob_deadline", 6.0)
    cap = int(_num(max_scan, "glob_max_scan", 150000.0))
    st.update(scanned=0, deadline=False, cap=False, limit=False, pruned=0)
    pat = str(pattern)
    if "**" not in pat:
        it = islice(_g.iglob(pat, root_dir=root, recursive=True), limit + 1)
        rows = sorted(list(it)); more = len(rows) > limit
        st.update(mode="iglob", scanned=len(rows), limit=more)
        _note(st, "单层匹配(iglob)", len(rows), len(rows[:limit]), limit, dl, cap)
        return rows[:limit], more
    rx = _glob_rx(pat); root = str(root)
    pre = len(root.rstrip("\\/")) + 1
    hits = []; t0 = time.time(); stop_ = ""
    for dp, ns, fs in os.walk(root):
        _keep2(ns, st)
        for name in ns:
            st["scanned"] += 1
            rel = os.path.join(dp, name)[pre:].replace("\\", "/")
            if rx.fullmatch(rel):
                hits.append(rel)
                if len(hits) > limit: stop_ = "limit"; break
        if stop_: break
        for fn in fs:
            st["scanned"] += 1
            if cap and st["scanned"] > cap: stop_ = "cap"; break
            if dl and (st["scanned"] & 255) == 0 and time.time() - t0 >= dl:
                stop_ = "deadline"; break
            rel = os.path.join(dp, fn)[pre:].replace("\\", "/")
            if rx.fullmatch(rel):
                hits.append(rel)
                if len(hits) > limit: stop_ = "limit"; break
        if stop_: break
    st["deadline"] = stop_ == "deadline"; st["cap"] = stop_ == "cap"
    st["limit"] = stop_ == "limit"
    rows = sorted(hits[:limit]); st["mode"] = "剪枝递归匹配"
    _note(st, st["mode"], st["scanned"], len(rows), limit, dl, cap)
    return rows, bool(stop_)

_TAG = re.compile(r"(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>|<[^>]+>")
_SP = re.compile(r"[ \t]{2,}|(?:\r?\n){3,}")
def html_to_text(h):
    """正文抽取：去 script/style/标签＋实体还原＋空行折叠（省 token 的主因）。"""
    import html as H
    t = _TAG.sub(" ", str(h or "")); t = H.unescape(t).replace("\xa0", " ")
    return _SP.sub(lambda m: "\n" if "\n" in m.group(0) else " ", t).strip()
def decode(raw, hdr):
    enc = (hdr.get("Content-Encoding") or "").lower()
    if "gzip" in enc:
        try: raw = gzip.decompress(raw)
        except Exception: pass
    elif "deflate" in enc:
        try: raw = zlib.decompress(raw)
        except Exception:
            try: raw = zlib.decompressobj(-zlib.MAX_WBITS).decompress(raw)
            except Exception: pass
    cs = (hdr.get("Content-Type") or "").lower(); m = re.search(r"charset=([\w\-]+)", cs)
    for c in ([m.group(1)] if m else []) + ["utf-8"]:
        try: return raw.decode(c), cs
        except Exception: continue
    return raw.decode("utf-8", "replace"), cs

MAXB = 2_000_000
def fetch(url, chars=4000, as_text=True, call=None, retries=2):
    """精准取文：Accept-Encoding gzip/deflate＋字节上限 2MB＋charset 优先响应头＋HTML 抽正文＋瞬时错有限重试。
    call 由调用方注入（SMS 传 run_watch.net_call 走 T1 超时分级），缺省 urllib.urlopen。回 (正文, 说明)。"""
    import urllib.request
    req = urllib.request.Request(str(url), headers={"User-Agent": "sms-shell/1.0",
        "Accept-Encoding": "gzip, deflate", "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8"})
    def _once():
        r = call(req) if call else urllib.request.urlopen(req, timeout=30)
        with r: raw, hdr = r.read(MAXB + 1), r.headers
        txt, ct = decode(raw[:MAXB], hdr)
        big = len(raw) > MAXB
        if as_text and ("html" in ct or txt.lstrip()[:1] == "<"):
            t2 = html_to_text(txt); txt = t2 or txt
        note = "%s·%d 字节→%d 字%s" % (ct.split(";")[0] or "?", len(raw[:MAXB]), len(txt), "·已截 2MB" if big else "")
        return txt, note
    try:
        import retry_io as rio
        return rio.call(_once, max(0, int(retries)), base=1.0, cap=5.0)
    except Exception as e: return None, net_err(e)

def net_err(e):
    """批29 P3-10：网络失败分类——域名不可达/DNS、连接被拒/超时＝环境抖动（提示查代理或跳过该项调研，非技能缺陷）；
    401/403＝站点拒绝（需登录/反爬）；404＝资源不存在；T1/T2＝超时分级。回带类别前缀的可读一句。"""
    import socket, urllib.error
    t = str(e) or e.__class__.__name__
    if isinstance(e, socket.gaierror) or "getaddrinfo" in t or "Name or service" in t:
        return "〔网络·域名不可达〕%s——查 DNS/代理，或跳过该项调研（非技能缺陷）" % t[:90]
    if isinstance(e, urllib.error.HTTPError):
        if e.code in (401, 403): return "〔站点拒绝·%d〕需登录或被反爬拦截，换来源或带鉴权：%s" % (e.code, t[:80])
        if e.code == 404: return "〔资源不存在·404〕链接失效或路径变更：%s" % t[:80]
        if e.code in (429, 503): return "〔限流/暂不可用·%d〕稍后重试或降频：%s" % (e.code, t[:80])
        return "〔HTTP·%d〕%s" % (e.code, t[:120])
    if isinstance(e, urllib.error.URLError):
        r = str(getattr(e, "reason", e))
        if "10060" in r or "timed out" in r.lower() or "refused" in r.lower():
            return "〔网络·连接超时/被拒〕%s——目标端口未开放或被防火墙拦截，属环境问题（非技能缺陷）" % r[:90]
        return "〔网络·不可达〕%s" % r[:120]
    if isinstance(e, TimeoutError) or "T1" in t or "timeout" in t.lower():
        return "〔超时〕%s——T1 网络单请求到点，可降 chars 或换源" % t[:110]
    return "〔异常·%s〕%s" % (e.__class__.__name__, t[:140])

def _amp(c):
    """引号感知的 && → ; 改写（引号内不动·反斜杠转义按 PS 规则只在双引号内处理）。回 (新命令, 改写处数)。"""
    out = []; q = ""; i = 0; n = 0
    while i < len(c):
        ch = c[i]
        if q:
            out.append(ch)
            if ch == "\\" and q == '"': out.append(c[i + 1:i + 2]); i += 2; continue
            if ch == q: q = ""
            i += 1; continue
        if ch in "\"'": q = ch; out.append(ch); i += 1; continue
        if c.startswith("&&", i): out.append(";"); i += 2; n += 1; continue
        out.append(ch); i += 1
    return "".join(out), n
PS = ("powershell", "pwsh")
def adapt(cmd, kind="powershell"):
    """命令执行范式适配：仅当目标壳为 PowerShell 且命令含已知不兼容语法时改写，回 (新命令, 说明行)。
    目的＝一次成功，杜绝「因分隔符语法报错再试一轮」。"""
    if str(kind) not in PS: return str(cmd), []
    c = str(cmd); notes = []
    if "&&" in c:
        c2, n = _amp(c)
        if n: c = c2; notes.append("PowerShell 5.1 不支持 && 作语句分隔·已按范式改写为 ;（%d 处）" % n)
    if re.search(r"(?i)2>nul\b", c):
        c = re.sub(r"(?i)2>nul\b", "2>$null", c); notes.append("cmd 重定向 2>nul 已改写为 PowerShell 2>$null")
    segs = c.split(";"); hit = False
    for i, s in enumerate(segs):
        if re.match(r"(?i)^\s*dir\s+/b\b", s): segs[i] = re.sub(r"(?i)^(\s*)dir\s+/b\s*", "\\1Get-ChildItem -Name ", s); hit = True
    if hit: c = ";".join(segs); notes.append("cmd 内建 dir /b 已改写为 PowerShell Get-ChildItem -Name")
    if "||" in c:
        _q, n2 = _amp(c.replace("||", "&&")); notes.append("⚠ || 在 Windows PowerShell 5.1 不是语句分隔（pwsh7 才支持）·建议拆步或 if ($LASTEXITCODE -eq 0)")
    return c, notes

if __name__ == "__main__":
    import tempfile, json as _j
    d = tempfile.mkdtemp(); f = os.path.join(d, "a.txt")
    _io.open(f, "w", encoding="utf-8").write("\n".join("line%d hit" % i if i == 900 else "x" * 40 for i in range(2000)))
    txt, tot, more = read_window(f, 5, 0, 4000)
    assert tot == 2000 and len(txt.splitlines()) == 5 and more, (tot, len(txt))
    txt2, tot2, m2 = read_window(f, 3, 1997, 4000); assert tot2 == 2000 and txt2.count("\n") == 2 and not m2, txt2
    hits, tr = grep_walk(d, re.compile("hit"), "*.txt", 3); assert len(hits) == 1 and not tr, hits
    os.makedirs(os.path.join(d, "node_modules", "x"), exist_ok=True)
    _io.open(os.path.join(d, "node_modules", "x", "b.txt"), "w").write("hit")
    assert not any("node_modules" in h for h in grep_walk(d, re.compile("hit"), "*", 9)[0])
    g, tr2 = glob_fast("**/*.txt", d, 200); assert g and not tr2, g
    os.makedirs(os.path.join(d, ".git", "hooks"), exist_ok=True)
    _io.open(os.path.join(d, ".git", "hooks", "c.txt"), "w").write("x")
    st = {}
    g2, _ = glob_fast("**/*.txt", d, 200, status=st)
    assert not any(".git" in x for x in g2), g2
    assert st.get("pruned") and "剪枝" in st.get("note", ""), st
    os.makedirs(os.path.join(d, "sub"), exist_ok=True)
    _io.open(os.path.join(d, "sub", "z.txt"), "w").write("z")
    g3, tr3 = glob_fast("**/*.txt", d, 1); assert tr3 and len(g3) == 1, (g3, tr3)
    if os.name == "nt":
        st2 = {}; _h, tr4 = glob_fast("**/*.ini", r"C:\Windows", 200, deadline=0.01, status=st2)
        assert tr4 and st2.get("deadline") and "未扫全" in st2["note"], st2
        st3 = {}; _h2, tr5 = grep_walk(r"C:\Windows", re.compile("zzz_never"),
                                       "*.ini", 5, deadline=0.01, status=st3)
        assert tr5 and st3.get("deadline"), st3
    assert html_to_text("<html><script>var a=1;</script><style>p{}</style><h1>Hi&nbsp;there</h1><p>x</p></html>") == "Hi there x", html_to_text("<b>x</b>")
    import gzip as _gz
    class _H(dict):
        get = dict.get
    raw = _gz.compress("你好".encode()); txt3, ct = decode(raw, _H({"Content-Encoding": "gzip", "Content-Type": "text/html; charset=utf-8"}))
    assert txt3 == "你好", (txt3, ct)
    c1, n1 = adapt("cd X && dir /b && echo done"); assert "&&" not in c1 and c1.count(";") == 2 and len(n1) == 2, (c1, n1)
    assert adapt("echo 'a && b'")[0] == "echo 'a && b'"
    assert "2>$null" in adapt("python x 2>nul")[0]
    assert adapt("ls -la", "bash")[1] == []
    print(_j.dumps({"selftest": "OK", "read_window": [tot, len(txt.splitlines())], "grep": len(hits), "adapt": c1}, ensure_ascii=False))
