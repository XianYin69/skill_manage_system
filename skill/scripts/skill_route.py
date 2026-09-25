#!/usr/bin/env python3
"""skill_route.py — 数据流 SMS 技能路由（路由-派发-整合链，红线 4/7）：读 registry/register.json 活跃技能（quarantine/pending_review 信任级跳过）＋ interfaces.json 接口词，与输入打分匹配；命中→chains.log("skill") 记 skill_call 链，返回 (命中id串, 治理注入段)——注入段随话语送网关，强制模型先 exec 读该技能 SKILL.md 全文按其流程执行、结果由 SMS 整合作答，禁止绕过技能以常识代答；未命中→附技能全表供择优，确无则声明无匹配并提示经 Skill_Generator 创建。用法：python -B skill_route.py match "<话语>" | list"""
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
    return [ss[i] for sc, i in ranked[:2] if sc >= 2]
def catalog(sms=None, cap=620):
    return ("技能全表：" + "；".join("%s（%s）" % (s.get("id"), re.sub(r"\s+", "", str(s.get("description") or ""))[:26]) for s in skills(sms)))[:cap]
def listtext(sms=None):
    ss = skills(sms); return ("技能注册表为空：先运行 register.py 扫描安装根（config.scan_roots），或经 Skill_Generator 创建后重装。" if not ss else "可调用托管技能 %d 个（说法即自动路由，Ctrl+K 选填）：" % len(ss) + "；".join("%s（%s）" % (s.get("id"), re.sub(r"\s+", "", str(s.get("description") or ""))[:26]) for s in ss) + "。命中技能将注入其 SKILL.md 流程按其执行·结果由 SMS 整合作答；需本机真跑脚本/调设备时以 :use 切 agent CLI 承接。")[:1400]
def _doc(s, cap=1400):
    try: return open(os.path.join(str(s.get("install_path", "")), str(s.get("entry", "SKILL.md"))), encoding="utf-8", errors="ignore").read()[:cap]
    except Exception: return ""
def route(text, sms=None):
    hs = match(text, sms)
    for s in hs: chains.log("skill", "路由命中:" + str(s.get("id")))
    if hs:
        g = "；".join("%s→%s" % (s.get("id"), os.path.join(str(s.get("install_path", "")), str(s.get("entry", "SKILL.md")))) for s in hs)
        docs = "\n".join("【%s SKILL.md】\n%s" % (s.get("id"), _doc(s)) for s in hs)
        return ",".join(str(s.get("id")) for s in hs), "[SMS 路由] 本输入命中托管技能（" + g + "）：以下为其 SKILL.md 全文，请严格按其流程整合执行与作答；若流程含需本机执行的脚本/工具步骤，用 exec 工具一次性运行再据结果作答（禁止反复试探），无 exec 能力时如实说明并提示 :use 切 agent CLI 承接；禁止绕过技能以常识代答。\n" + docs
    return None, "[SMS 路由] 未命中托管技能，但必须优先从下表择最相关技能（exec 读其 SKILL.md 按其流程执行）；确无可用时明确回复「无匹配技能」并建议调整话语或经 Skill_Generator 创建，禁止常识代答。" + catalog(sms)
if __name__ == "__main__":
    a = sys.argv[1:] or ["list"]
    if a[0] == "list": print(listtext())
    elif a[0] == "match" and len(a) > 1:
        sid, inj = route(" ".join(a[1:])); print(json.dumps({"hit": sid, "inject": inj[:220]}, ensure_ascii=False))
    else: print(__doc__.strip().splitlines()[1]); sys.exit(1)
