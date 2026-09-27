#!/usr/bin/env python3
"""agent_tools.py — 网关大模型可用的 agent 工具核心（SMS 本体的手和脚，红线：不作答只执行）：command(=exec)/read/write/ask/skill/user_send/thinking_chain。每笔调用经 msg_flow 信封上报客户端（技能名＋工具链＋输出＋ts＋conv/sess 归属；on_line 人读行供显示·ev 回调结构化供顶栏进度/审计），task/task_detail 在 agent_task.py、schema 与派发在 agent_dispatch.py。skill＝托管技能真派发（红线17）：记 skill_call＋subsession 链→SKILL.md 全文＋用户诉求→嵌套 gateway 工具循环（前缀 ⧉技能▸ 回显）→收口子会话返回整合结果（批7④：正文已经⧉前缀实时显示给用户时返回改 WRAP 首尾片段包装·防主模型整段复读·:dispatch 见 WRAP 打收口行）；深度≤2 防子对话自路由死循环（修复用户追责「无法使用Skill完成需求」：旧版命中技能只注入 1400 字截断 SKILL.md 让网关空转、subconv 提示回填自引用致连开 8 个空对话）。write 守卫：工作区/SMS 默认可写；其余路径需 :grant write；skill 目录需 :grant danger。用法：python -B agent_tools.py（常规经网关工具调用；单跑见 agent_dispatch.py）"""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import resolve_home, chains, msg_flow, skill_route, permissions, agent_ctx as ac
SMS = resolve_home.ensure(); SKROOT = os.path.realpath(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))); WRAP = "【子会话正文·已经⧉前缀实时显示给用户·最终回复禁止复述引用】\n"; _in = lambda p, base: p == _r(base) or p.startswith(_r(base) + os.sep)
def bind(on_line=None, ev=False):
    c = ac.cur()
    if on_line: c["on_line"] = on_line
    if ev is not False: c["ev"] = ev; return c
def emit(kind, text, tool="", skill="", ok=None, meta=None):
    c = ac.cur(); e = msg_flow.make(kind, text, conv=chains.ACTIVE["conv"], sess=chains.cur_sess(), skill=skill, tool=tool, ok=ok, meta=meta)
    c["ev"] and c["ev"](e); return c["on_line"](msg_flow.brief(e))
def _r(p): return os.path.realpath(os.path.abspath(os.path.expanduser(str(p))))
def read(path, max_lines=120):
    try: t = open(_r(path), encoding="utf-8", errors="replace").read().splitlines()
    except Exception as e: return "读失败：" + str(e)[:150]
    out = "\n".join(t[:max_lines])[:4000]; emit("tool", str(path) + "（%d 行）" % len(t), tool="read", ok=True); return out + ("" if len(t) <= max_lines else "\n…共 %d 行截断" % len(t))
def write(path, content, append=False):
    p = _r(path)
    if _in(p, SKROOT) and not permissions.allow(SMS, "danger"): return "拒绝：skill 目录写入需 :grant danger（" + p + "）"
    if not (_in(p, resolve_home.workspace()) or _in(p, SMS)) and not permissions.allow(SMS, "write"): return "拒绝：工作区/SMS 外写入需 :grant write（" + p + "）"
    os.makedirs(os.path.dirname(p) or ".", exist_ok=True); open(p, "a" if append else "w", encoding="utf-8").write(str(content))
    emit("edit", ("追加 " if append else "写入 ") + p + "（" + str(len(str(content))) + " 字）", tool="write", ok=True); return "已写入 " + p
def command(cmd):
    import sys_shells; buf = []; rc = str(sys_shells.run(str(cmd), on_line=buf.append)); out = ("\n".join(str(x).split("▸ ", 1)[-1] for x in buf) or "(无输出)")[:4000]
    chains.log("tool", "cmd:" + str(cmd)[:60]); emit("tool", "$ " + str(cmd) + "\n" + out, tool="command", ok=rc.startswith("rc=0"), meta={"rc": rc})
    return (("rc≠0 " if not rc.startswith("rc=0") else "") + out)
def ask(question):
    import agent_tools2; return agent_tools2.ask_sub(question)
def run_skill(name, inp, tag=""):
    import gateway, skill_doc, latency; c = ac.cur()
    s = next((x for x in skill_route.skills() if str(x.get("id", "")).lower() == str(name).strip().lower()), None)
    if not s: return "无托管技能：" + name + "（:skills 查清单）"
    if c["depth"] >= 2: return "拒绝：技能子会话已达 2 层（防自路由死循环）——请直接按已注入的 SKILL.md 用工具执行"
    nm = str(s.get("id")).lower()
    if nm in (c.get("chain") or []): return "拒绝：" + nm + " 自派发（本技能链已派发过它·防双 ⧉ 前缀复读循环）——请直接按已注入的 SKILL.md 用工具执行"
    ip = str(s.get("install_path")); skp = os.path.join(ip, str(s.get("entry", "SKILL.md"))); dst = resolve_home.wtmp(); tl = str(tag or s.get("id"))
    doc = skill_doc.package(ip, str(s.get("entry", "SKILL.md")), 60000)
    if not doc: return "SKILL.md 读取失败：" + skp
    chains.log("skill", "%s|src=%s|dst=%s" % (tl, skp, dst)); chains.log("sub", tl); emit("skill", "开子会话派发 " + tl + "（src=" + skp + "｜dst=" + dst + "）", skill=tl, tool="skill", meta={"src_path": skp, "dst_path": dst})
    body = "【子会话·托管技能 " + str(s.get("id")) + " 真派发】红线17：本消息结束即收口子会话并返回 SMS 主流程（父对话继续调度·整合·推进任务表，整段对话不因你完成而结束）。技能启用只以 SKILL.md 为准——下文已按 skill_doc 解释器打包注入 SKILL.md 全文＋明示引用子文档＋脚本调用清单，禁止列举/遍历技能目录或再回读这些文件；按流程执行用户诉求（脚本按清单 exec 一步到位）；生成文件一律入目标目录 dst=" + dst + "（env SMS_TMP）。\n" + doc + "\n\n用户诉求：\n" + str(inp)[:4000] + "\n\n最后输出整合结果（≤600字·附产物绝对路径），结束消息不要携带工具调用。"
    of = c["on_line"]; c["streamed"] = False; pf = lambda x, _n=tl: (str(x).strip() and c.__setitem__("streamed", True), of(("⧉" + _n + "▸ ") + str(x)));     c["on_line"] = pf; c["depth"] += 1; ch = c["chain"]; c["chain"] = ch + [nm]
    try: out = latency.wrap("skill", tl, gateway.run, body, pf, max_rounds=int(__import__("settings").get("caps.skill_rounds", 0))) or ""  # 0＝无限（防任务断裂）·>0 强制收口
    finally: c["on_line"] = of; c["depth"] -= 1; c["chain"] = ch
    chains.log("sub", "收口:" + tl); emit("skill", "子会话收口 " + tl, skill=tl, tool="skill", ok=bool(out))
    return (WRAP + out[:120] + "\n……（中间省略·正文已实时显示给用户）……\n" + out[-300:] + "\n（你只看到首尾片段·无法也严禁复述全文·子会话已收口·控制权返回 SMS 主流程：〔任务表〕有未完成行或诉求有后续步骤必须继续推进（续派 skill/执行工具），全部完成后才一句 ≤40 字收尾回报；禁止把子技能完成当作整段对话结束；需数据用 read 读产物路径）") if out and c["streamed"] else (out or ("（技能 " + tl + " 无输出）"))
def user_send(text):
    chains.record("dialogue", "agent@" + (chains.ACTIVE["conv"] or chains.session_id()) + " " + str(text)[:200], [[chains.ACTIVE["conv"] or "", "ref", 1], [chains.cur_sess(), "member", 1]]); emit("notice", str(text)); return "已送达用户"
def thinking_chain(frm, to, why):
    fid = chains.record("logic", str(frm) + "→" + str(to) + "：" + str(why)); emit("step", "逻辑链已记 " + str(frm) + "→" + str(to), tool="thinking_chain"); return "已记逻辑链 " + str(fid)
if __name__ == "__main__": print(__doc__.strip().splitlines()[1][:400])
