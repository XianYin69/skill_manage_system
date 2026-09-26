#!/usr/bin/env python3
"""agent_tools.py — 网关大模型可用的 agent 工具核心（SMS 本体的手和脚，红线：不作答只执行）：command(=exec)/read/write/ask/skill/user_send/thinking_chain。每笔调用经 msg_flow 信封上报客户端（技能名＋工具链＋输出＋ts＋conv/sess 归属；on_line 人读行供显示·ev 回调结构化供顶栏进度/审计），task/task_detail 在 agent_task.py、schema 与派发在 agent_dispatch.py。skill＝托管技能真派发（红线17）：记 skill_call＋subsession 链→SKILL.md 全文＋用户诉求→嵌套 gateway 工具循环（前缀 ⧉技能▸ 回显）→收口子会话返回整合结果；深度≤2 防子对话自路由死循环（修复用户追责「无法使用Skill完成需求」：旧版命中技能只注入 1400 字截断 SKILL.md 让网关空转、subconv 提示回填自引用致连开 8 个空对话）。write 守卫：工作区/SMS 默认可写；其余路径需 :grant write；skill 目录需 :grant danger。用法：python -B agent_tools.py（常规经网关工具调用；单跑见 agent_dispatch.py）"""
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import resolve_home, chains, msg_flow, skill_route, permissions
SMS = resolve_home.ensure(); SKROOT = os.path.realpath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CTX = {"on_line": lambda s: None, "ev": False, "depth": 0}
def bind(on_line=None, ev=False):
    if on_line: CTX["on_line"] = on_line
    if ev is not False: CTX["ev"] = ev; return CTX
def emit(kind, text, tool="", skill="", ok=None, meta=None):
    e = msg_flow.make(kind, text, conv=chains.ACTIVE["conv"], sess=chains.cur_sess(), skill=skill, tool=tool, ok=ok, meta=meta)
    CTX["ev"] and CTX["ev"](e); return CTX["on_line"](msg_flow.brief(e))
def _r(p): return os.path.realpath(os.path.abspath(os.path.expanduser(str(p))))
def _in(p, base): return p == _r(base) or p.startswith(_r(base) + os.sep)
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
    import gateway; m, err = gateway.chat([{"role": "system", "content": "你是 SMS 数据流的子问答：只据所问简明作答（简体中文≤300字），不确定就说不确定。"}, {"role": "user", "content": str(question)[:4000]}])
    emit("tool", "子问答完成", tool="ask", ok=bool(m)); return (m or {}).get("content") or ("子问答失败：" + err)
def run_skill(name, inp):
    import gateway, skill_doc
    s = next((x for x in skill_route.skills() if str(x.get("id", "")).lower() == str(name).strip().lower()), None)
    if not s: return "无托管技能：" + name + "（:skills 查清单）"
    if CTX["depth"] >= 2: return "拒绝：技能子会话已达 2 层（防自路由死循环）——请直接按已注入的 SKILL.md 用工具执行"
    ip = str(s.get("install_path")); skp = os.path.join(ip, str(s.get("entry", "SKILL.md"))); dst = resolve_home.wtmp()
    doc = skill_doc.package(ip, str(s.get("entry", "SKILL.md")), 60000)
    if not doc: return "SKILL.md 读取失败：" + skp
    chains.log("skill", "%s|src=%s|dst=%s" % (s.get("id"), skp, dst)); chains.log("sub", str(s.get("id"))); emit("skill", "开子会话派发 " + str(s.get("id")) + "（src=" + skp + "｜dst=" + dst + "）", skill=str(s.get("id")), tool="skill", meta={"src_path": skp, "dst_path": dst})
    body = "【子会话·托管技能 " + str(s.get("id")) + " 真派发】红线17：本消息结束即收口子会话。技能启用只以 SKILL.md 为准——下文已按 skill_doc 解释器打包注入 SKILL.md 全文＋明示引用子文档＋脚本调用清单，禁止列举/遍历技能目录或再回读这些文件；按流程执行用户诉求（脚本按清单 exec 一步到位）；生成文件一律入目标目录 dst=" + dst + "（env SMS_TMP）。\n" + doc + "\n\n用户诉求：\n" + str(inp)[:4000] + "\n\n最后输出整合结果（≤600字·附产物绝对路径），结束消息不要携带工具调用。"
    of = CTX["on_line"]; pf = lambda x, _n=str(s.get("id")): of(("⧉" + _n + "▸ ") + str(x)); CTX["on_line"] = pf; CTX["depth"] += 1
    try: out = gateway.run(body, pf) or ""
    finally: CTX["on_line"] = of; CTX["depth"] -= 1
    chains.log("sub", "收口:" + str(s.get("id"))); emit("skill", "子会话收口 " + str(s.get("id")), skill=str(s.get("id")), tool="skill", ok=bool(out))
    return out or ("（技能 " + str(s.get("id")) + " 无输出）")
def user_send(text):
    chains.record("dialogue", "agent@" + (chains.ACTIVE["conv"] or chains.session_id()) + " " + str(text)[:200], [[chains.ACTIVE["conv"] or "", "ref", 1], [chains.cur_sess(), "member", 1]]); emit("notice", str(text)); return "已送达用户"
def thinking_chain(frm, to, why):
    fid = chains.record("logic", str(frm) + "→" + str(to) + "：" + str(why)); emit("step", "逻辑链已记 " + str(frm) + "→" + str(to), tool="thinking_chain"); return "已记逻辑链 " + str(fid)
if __name__ == "__main__": print(__doc__.strip().splitlines()[1][:400])
