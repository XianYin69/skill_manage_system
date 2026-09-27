#!/usr/bin/env python3
"""prompt_builder.py — 提示词构建器与对话初始化（结构固定，供 agent_stream 每次对话组装）：对话初始化块＝技能名 + 提示词(模型身份 + 配置文件参数) + SKILL.md 索引；逐轮构建块＝技能名 + skill 提示词 + SKILL.md 索引 + 用户输入。SKILL.md 索引＝registry/register.json 活跃技能「id → SKILL.md 绝对路径」紧凑清单（供模型按需 exec 读全文，非全文注入）；模型身份/参数取自 settings（llm_gateway.model + temperature/top_p/max_tokens + model_meta 上下文）；skill 提示词＝SMS 治理红线（批16 LLM 主导：问答可直答·动手必用工具·路由行仅参考）。用法：python -B prompt_builder.py init | build "<用户输入>" | index。"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import resolve_home, settings
SKILL = "skill_manage_system"
PROMPT = "你是 skill_manage_system（SMS）数据流中的主导决策者（批16 起 LLM 主导·脚本只辅助）：纯知识问答/闲聊/解释可直答（简短·简体中文）；需要本机事实用 read/grep/glob/ls/exec 查证后作答、禁止编造；需要动手执行（写盘/派技能/调脚本）才用工具——命中托管技能时用 skill 工具开子会话按注入的 SKILL.md 真执行、结果收口后由你整合，需本机执行的脚本/工具用 exec 一次性运行（禁反复试探），禁止空口声称已执行；[SMS 路由·参考] 行只是关键词打分提示，采纳与否由你判断；链＝省 token 的记忆介质（批17·相信大模型）——涉既往经验先 chain recall 查证、有价值结论即 chain append 写入 memory/knowledge/logic 链，决策岔路用 debate 正反双链自辩修正路径（人多在回路旁，仅高危节点回人在回路确认）；认为确无可用技能则说明并建议经 Skill_Generator 创建。生成文件一律写入当前工作区 tmp\\ 子目录（env SMS_TMP·壳已自动建），不散落工作区根；目标为工作区文件的 tmp 产物经用户审核先 `python -B ws_release.py diff <tmp相对路径> --to <工作区相对目标>` 预览、当轮同意后 `release … --yes`（须 :grant danger）释放回工作区；大模型与技能配置直接读 SMS 数据根 <SMS_HOME>/config 下 config.json/skills.json，绝不复制或重建到工作区。问 SMS 自身设置/命令时据 settings/commands 查证后作答。始终简体中文。"
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
    sms = sms or resolve_home.ensure(); t = resolve_home.wtmp(); return "[SMS 对话初始化]\n技能名：" + SKILL + "\n" + model_block(sms) + "\n工作区：" + t[: -len(os.sep + "tmp")] + "（生成文件只入 tmp\\＝" + t + "·模型/技能配置直读 " + os.path.join(sms, "config") + "·勿放入工作区·待审产物可 ws_release diff/release 收编）\n" + index(sms)
def build(user_input, sms=None):
    return "技能名：" + SKILL + "\n" + PROMPT + "\n" + index(sms) + "\n[用户输入]\n" + user_input
if __name__ == "__main__":
    a = sys.argv[1:] or ["init"]; cmd = a[0]
    if cmd == "init": print(init())
    elif cmd == "index": print(index())
    elif cmd == "build": print(build(" ".join(a[1:]) or "你好"))
    else: print(__doc__.strip().splitlines()[-1])
