#!/usr/bin/env python3
"""shell_tui_sessions.py — 对话一览数据（供右栏「对话一览 conv」区·批23 对等对话：每用户输入
与每技能派发各成一个 conv——派发 conv 由 run_skill 记 session 链 open:/close: 故同样入列）：
从 <SMS_HOME>/chains 读 session 链 open:/close: 碎片得各对话创建/收口时间，配 dialogue 链
user@<conv> 首条话语作简略信息；overview() 按创建时间倒序返回 [(conv, 创建时间, 简略)]，
纯读不落盘。

性能（2026-10-02 治 sms_shell 卡顿·规格 perf_spec.md·输出零回归）：overview 可接收调用方
（右栏 _heavy 线程）传入的 session/dialogue 碎片复用同一次链扫描，不再与 sessions_view 各扫
一遍；不传时自取（sessions_view 的 TTL 快照兜底），行为不变。
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import chain_store, resolve_home, sessions_view


def _sess_frags(sms):
    if sms: return chain_store.Store(sms).all_frags("session")
    return sessions_view.session_frags()


def _dial_frags(sms):
    if sms: return chain_store.Store(sms).all_frags("dialogue")
    return sessions_view.dialogue_frags()


def overview(sms=None, n=6, frags=None, dial=None):
    conv = {}
    for f in (frags if frags is not None else _sess_frags(sms)):
        t = str(f.get("text", ""))
        if t.startswith("open:"): conv.setdefault(t[5:], {"ts": f.get("ts", ""), "brief": ""})
        elif t.startswith("close:"):
            e = conv.setdefault(t[6:], {"ts": f.get("ts", ""), "brief": ""})
            e["end"] = f.get("ts", "")
    for f in sorted(dial if dial is not None else _dial_frags(sms),
                    key=lambda x: x.get("ts", "")):
        t = str(f.get("text", ""))
        if (m := _user(t)):
            cid, brief = m
            if cid in conv and not conv[cid]["brief"]: conv[cid]["brief"] = brief[:38]
    rows = sorted(conv.items(), key=lambda kv: kv[1]["ts"], reverse=True)[:n]
    return [(k, str(v["ts"])[5:16].replace("T", " "), v["brief"] or "（无话语）") for k, v in rows]


def _user(t):
    if not t.startswith("user@"): return None
    rest = t[5:]; cid, _, brief = rest.partition(" ")
    return (cid, brief.strip()) if cid else None
