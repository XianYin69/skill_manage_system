#!/usr/bin/env python3
"""prompt_builder.py — 提示词构建器与对话初始化（结构固定，供 agent_stream 每次对话组装）：对话初始化块＝技能名 + 提示词(模型身份 + 配置文件参数) + SKILL.md 索引；逐轮构建块＝技能名 + skill 提示词 + SKILL.md 索引 + 用户输入。SKILL.md 索引＝registry/register.json 活跃技能「id → SKILL.md 绝对路径」紧凑清单（供模型按需 exec 读全文，非全文注入）；模型身份/参数取自 settings（llm_gateway.model + temperature/top_p/max_tokens + model_meta 上下文）；skill 提示词＝SMS 治理红线（本体不作答·命中技能按其流程）。用法：python -B prompt_builder.py init | build "<用户输入>" | index。"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import resolve_home, settings
SKILL = "skill_manage_system"
PROMPT = "你是 skill_manage_system（SMS）数据流：SMS 只调取与管理托管技能及其副产物，不得以模型自身常识代答；命中托管技能时按注入的 SKILL.md 流程执行、结果由 SMS 整合作答，需本机执行的脚本/工具用 exec 一次性运行（禁反复试探），未命中则从索引择最相关技能或明确回复「无匹配技能」并建议经 Skill_Generator 创建。问 SMS 自身设置/命令时据 settings/commands 查证后作答。始终简体中文。"
def _reg(sms): return json.load(open(os.path.join(sms, "registry", "register.json"), encoding="utf-8")).get("skills", [])
def model_block(sms=None):
    sms = sms or resolve_home.ensure(); g = settings.eff(sms)["llm_gateway"]; mm = settings.eff(sms).get("model_meta", {}).get("defaults", {})
    ctx = (mm or {}).get("context_length")
    return "模型身份：" + str(g.get("model") or "auto") + "（" + str(g.get("base_url") or "未配置网关") + "）· 参数 temperature=" + str(g.get("temperature")) + " top_p=" + str(g.get("top_p")) + " max_tokens=" + str(g.get("max_tokens")) + (" 上下文≤" + str(ctx) if ctx else "")
def index(sms=None):
    sms = sms or resolve_home.ensure()
    try: rows = [s for s in _reg(sms) if s.get("status", "active") == "active" and s.get("trust") not in ("quarantine", "pending_review")]
    except Exception: rows = []
    if not rows: return "SKILL.md 索引：（注册表为空，先跑 register.py）"
    return "SKILL.md 索引（id → SKILL.md 路径，命中可 exec 读全文按其流程）：\n" + "\n".join("%s → %s" % (s.get("id"), os.path.join(str(s.get("install_path", "")), str(s.get("entry", "SKILL.md")))) for s in rows)[:2400]
def init(sms=None):
    return "[SMS 对话初始化]\n技能名：" + SKILL + "\n" + model_block(sms) + "\n" + index(sms)
def build(user_input, sms=None):
    return "技能名：" + SKILL + "\n" + PROMPT + "\n" + index(sms) + "\n[用户输入]\n" + user_input
if __name__ == "__main__":
    a = sys.argv[1:] or ["init"]; cmd = a[0]
    if cmd == "init": print(init())
    elif cmd == "index": print(index())
    elif cmd == "build": print(build(" ".join(a[1:]) or "你好"))
    else: print(__doc__.strip().splitlines()[-1])
