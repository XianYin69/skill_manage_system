#!/usr/bin/env python3
"""shell_tui_sessions.py — 会话总览数据（供右栏「会话总览」区）：从 <SMS_HOME>/chains 读 session 链 open:/close: 碎片得各对话创建/收口时间，配 dialogue 链 user@<conv> 首条话语作简略信息；overview() 按创建时间倒序返回 [(conv, 创建时间, 简略)]，纯读不落盘。"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import chain_store, resolve_home
def overview(sms=None, n=6):
    st = chain_store.Store(sms or resolve_home.ensure()); conv = {}
    for f in st.all_frags("session"):
        t = str(f.get("text", ""))
        if t.startswith("open:"): conv.setdefault(t[5:], {"ts": f.get("ts", ""), "brief": ""})
        elif t.startswith("close:"):
            e = conv.setdefault(t[6:], {"ts": f.get("ts", ""), "brief": ""}); e["end"] = f.get("ts", "")
    for f in sorted(st.all_frags("dialogue"), key=lambda x: x.get("ts", "")):
        t = str(f.get("text", ""))
        if (m := _user(t)):
            cid, brief = m
            if cid in conv and not conv[cid]["brief"]: conv[cid]["brief"] = brief[:38]
    rows = sorted(conv.items(), key=lambda kv: kv[1]["ts"], reverse=True)[:n]
    return [(k, str(v["ts"])[5:16].replace("T", " "), v["brief"] or "（无话语）") for k, v in rows]
def _user(t):
    if not t.startswith("user@"): return None
    rest = t[5:]; cid, _, brief = rest.partition(" "); return (cid, brief.strip()) if cid else None
