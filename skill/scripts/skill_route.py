#!/usr/bin/env python3
"""skill_route.py — 数据流 SMS 技能路由（路由-派发-整合链，红线 4/7）：读 registry/register.json 活跃技能（quarantine/pending_review 信任级跳过）＋ interfaces.json 接口词，与输入打分匹配（阈值 4：技能id 子串命中或分词＋接口词双证据——修复旧阈值 2 让 skill_connector 蹭「skill」子串误命中）；命中→chains.log("skill") 记 skill_call 链并返回命中 id——由 agent_stream 直接经 agent_tools.run_skill 开子会话真派发（SKILL.md 全文由派发注入，不再截 1400 字塞父提示词）；未命中→附技能全表供父模型择 skill 工具调用，确无则声明无匹配并提示经 Skill_Generator 创建。用法：python -B skill_route.py match "<话语>" | list"""
import os, sys, json, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import resolve_home, chains
def _load(sms, rel):
    try: return json.load(open(os.path.join(sms, rel), encoding="utf-8"))
    except Exception: return {}
def skills(sms=None):
    sms = sms or resolve_home.ensure()
    return [s for s in _load(sms, "registry/register.json").get("skills", []) if s.get("status", "active") == "active" and s.get("trust") not in ("quarantine", "pending_review")]
def _terms(sms):
    t = {}
    for it in _load(sms, "registry/interfaces.json").get("skills", []):
        ws = [str(i.get("name", "")) for i in it.get("interfaces", [])] + [str(c) for c in (it.get("capabilities") or [])]
        t.setdefault(it.get("skill_id") or "", []).extend(w for w in ws if 1 < len(w) <= 12)
    return t
def _score(s, u, terms):
    sid = str(s.get("id", "")).lower()
    return (4 if sid and sid in u else 0) + 2 * sum(1 for x in re.split(r"[-_.]+", sid) if len(x) >= 4 and x in u) + sum(1 for w in terms.get(s.get("id"), []) if w.lower() in u)
def match(text, sms=None):
    sms = sms or resolve_home.ensure(); terms = _terms(sms); u = text.lower(); ss = skills(sms)
    ranked = sorted(((_score(s, u, terms), i) for i, s in enumerate(ss)), key=lambda x: -x[0])
    return [ss[i] for sc, i in ranked[:2] if sc >= 4]
def catalog(sms=None, cap=620):
    return ("技能全表：" + "；".join("%s（%s）" % (s.get("id"), re.sub(r"\s+", "", str(s.get("description") or ""))[:26]) for s in skills(sms)))[:cap]
def listtext(sms=None):
    ss = skills(sms); return ("技能注册表为空：先运行 register.py 扫描安装根（config.scan_roots），或经 Skill_Generator 创建后重装。" if not ss else "可调用托管技能 %d 个（说法即自动路由，Ctrl+K 选填）：" % len(ss) + "；".join("%s（%s）" % (s.get("id"), re.sub(r"\s+", "", str(s.get("description") or ""))[:26]) for s in ss) + "。命中技能由 SMS 开子会话真派发执行（skill 工具），结果整合作答；需本机真跑脚本/调设备时以 :use 切 agent CLI 承接。")[:1400]
def route(text, sms=None):
    hs = match(text, sms)
    for s in hs: chains.log("skill", "路由命中:" + str(s.get("id")))
    if hs:
        g = "；".join("%s→%s" % (s.get("id"), os.path.join(str(s.get("install_path", "")), str(s.get("entry", "SKILL.md")))) for s in hs)
        return ",".join(str(s.get("id")) for s in hs), "[SMS 路由] 命中托管技能（" + g + "）：由 SMS 经 skill 工具开子会话按其 SKILL.md 全文派发执行（本消息为父对话时勿重复读 SKILL.md、勿以常识代答）；子会话不可用时如实说明并提示 :dispatch <技能id> <诉求>。"
    return None, "[SMS 路由] 未命中托管技能，但必须优先从下表择最相关技能并调 skill 工具真执行；确无可用时明确回复「无匹配技能」并建议调整话语或经 Skill_Generator 创建，禁止常识代答。" + catalog(sms)
if __name__ == "__main__":
    a = sys.argv[1:] or ["list"]
    if a[0] == "list": print(listtext())
    elif a[0] == "match" and len(a) > 1:
        sid, inj = route(" ".join(a[1:])); print(json.dumps({"hit": sid, "inject": inj[:220]}, ensure_ascii=False))
    else: print(__doc__.strip().splitlines()[1]); sys.exit(1)
