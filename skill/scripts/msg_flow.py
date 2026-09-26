#!/usr/bin/env python3
"""msg_flow.py — 用户↔大模型↔客户端 JSON 传输信封（v1.1）：一笔输入/输出＝ {v,kind,ts,conv,sess,skill,tool,chain,ok,text,meta}——kind＝user_in/llm_out/tool/skill/task/step/notice/err/edit/sh/tts；ts 恒 ISO 本地时间；conv/sess 对话与会话归属（隔离审计）；skill/tool/chain 记录技能名与工具链路径；meta 装进度（task done/total、edit 路径、sh 退出码…）。分类（2026-09-26 用户「按类型判断是否隐藏长信息」）——CLASS 把 kind 归入 body 正文（llm_out·永不折叠）/echo 回显（user_in）/alert 告警（err·不折叠）/status 状态（step/task·常显短行）/detail 明细（tool/skill/edit/sh/notice·超长折叠进「详细细节」）/quiet 静默（tts），FOLD 集合＋foldable() 供前端与 ps1 壳同口径分流。make() 产 dict、dumps() 产行、parse() 判信封（非信封返回 None，前端按原文渲染）、brief() 产人读一行（TUI/ps1 显示用，信封原样经 ev 回调交上层做进度/审计）。本模块零依赖零链写。"""
import json, time
KINDS = ("user_in", "llm_out", "tool", "skill", "task", "step", "notice", "err", "edit", "sh", "tts")
CLASS = {"llm_out": "body", "user_in": "echo", "err": "alert", "step": "status", "task": "status", "tts": "quiet",
         "tool": "detail", "skill": "detail", "edit": "detail", "sh": "detail", "notice": "body"}
FOLD = frozenset(k for k, c in CLASS.items() if c == "detail")
def cls(kind): return CLASS.get(kind, "detail")
def foldable(kind): return kind in FOLD
def make(kind, text, conv="", sess="", skill="", tool="", chain=(), ok=None, meta=None):
    return {"v": 1, "kind": kind if kind in KINDS else "notice", "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "conv": conv, "sess": sess, "skill": skill, "tool": tool, "chain": list(chain),
            "ok": ok, "text": str(text), "meta": dict(meta or {})}
def dumps(e): return json.dumps(e, ensure_ascii=False, default=str)
def parse(s):
    s = str(s).strip()
    if not (s.startswith("{") and '"v": 1' in s[:24]): return None
    try: e = json.loads(s)
    except Exception: return None
    return e if isinstance(e, dict) and e.get("v") == 1 and e.get("kind") in KINDS else None
def brief(e, jsonline=False):
    if jsonline: return dumps(e)
    m = e.get("meta") or {}; tag = {"task": "≡ %s %s/%s" % (e.get("skill") or e.get("tool"), m.get("done", 0), m.get("total", 0))}.get(e["kind"])
    if not tag:
        head = {"user_in": "✎ ", "llm_out": "", "tool": "$ ", "skill": "⧉ ", "step": "▸ ", "notice": "• ", "err": "✗ ", "edit": "✎ ", "sh": "! ", "tts": "♪ "}.get(e["kind"], "")
        bits = [x for x in ((("技能:" + e["skill"]) if e.get("skill") else ""), (("工具:" + e["tool"]) if e.get("tool") else "")) if x]
        tag = head + (("〔" + "→".join(bits) + "〕") if bits else "") + str(e.get("text") or "")
    pre = "" if e.get("ok") is not False else "失败 "
    return tag if not (e.get("ts") and jsonline) else tag
