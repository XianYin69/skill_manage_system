#!/usr/bin/env python3
"""shell_core.py — sms-shell 共享路由引擎（TUI/GUI 前端通用）：像对 agent 说话一样——任意话语默认经数据流交给已安装 agent CLI 执行（agent_stream，前置 skill_manage_system 指令）；输入命中个性化指令名（user_commands）则展开执行；`:` 元指令仅做治理（切 agent、开关技能前缀、指令系统、hud/deploy/session/grant）；本体不作答。"""
import os, sys, subprocess, shlex
S = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, S)
import agent_stream as ag
SMS = ag.SMS
HELP = ("直接输入任何话语＝交给当前 agent（默认带 skill_manage_system 指令）· 命中个性化指令名则展开执行\n"
        ":agents 看/选 · :use <name> · :skill on|off 技能前缀 · :cmds [name] · :intent <话语> · :alias/:unalias 个性化指令\n"
        ":hud session|step|alert|hide · :deploy <dir|--Path P --FolderName F>（部署＝仅复制 bin 文件） · :session \"<任务>\" · :grant <键|角色> [分钟] · :dream status|run · :image <文件> 附下一话语图片 · :config status|get|set · :web start|stop|token · :ext status|enable|enroll · :quit")
def banner():
    return "sms-shell · SMS_HOME=" + SMS + " · 当前 agent：" + (ag.current() or "未检出（:agents 查看）") + " · 技能前缀：" + ("on" if ag.prefix_on() else "off")
def run_script(name, args):
    p = subprocess.run([sys.executable, "-B", os.path.join(S, name)] + list(args), capture_output=True, text=True, encoding="utf-8", errors="replace")
    return (p.stdout or p.stderr).strip() or "(无输出)"
IMG = []
def _meta(m, a, on_line):
    if m == "agents": on_line("检出：" + ("、".join(ag.detected()) or "无") + " · 当前：" + (ag.current() or "-") + " · 技能前缀：" + ("on" if ag.prefix_on() else "off") + "\n可用适配器（含未装）：" + "、".join(ag.adapters()))
    elif m == "image" and a:
        p = " ".join(a); IMG[:] = [p] if os.path.isfile(p) else []
        on_line(("已附图（下一句生效）：" if IMG else "图片不存在：") + p)
    elif m == "use" and a: on_line(ag.use(a[0]))
    elif m == "skill": on_line(ag.skill(not (a and a[0] == "off")))
    elif m in ("hud", "deploy", "session"): on_line(run_script(m + ".py", a))
    elif m in ("config", "web", "ext"): on_line(run_script({"config": "settings", "ext": "external"}.get(m, m) + ".py", a or ["status"]))
    elif m == "grant": on_line(run_script("permissions.py", ["grant"] + a + ["--write"]))
    elif m == "dream": on_line(run_script("dream.py", a or ["status"]))
    elif m == "cmds": on_line(run_script("commands.py", ["help"] if not a else ["show"] + a))
    elif m == "intent": on_line(run_script("commands.py", ["intent"] + a))
    elif m == "alias": on_line(run_script("user_commands.py", ["add"] + a))
    elif m == "unalias": on_line(run_script("user_commands.py", ["rm"] + a))
    elif m in ("help", "?"): on_line(HELP)
    else: on_line("未知元指令 :" + m + "（:help）")
def handle(line, on_line):
    if not line.strip(): return None
    if line.strip() in ("quit", "exit", ":quit", ":q", ":exit"): return "exit"
    if line.startswith(":"):
        p = line[1:].split(); _meta(p[0], p[1:], on_line); return None
    import user_commands
    try: parts = shlex.split(line)
    except ValueError: parts = line.split()
    if user_commands.find(user_commands.load(SMS), parts[0]):
        on_line(run_script("user_commands.py", ["run"] + parts)); return None
    line2 = line + ("\n[图:" + IMG[0] + "]" if IMG else "")
    if IMG: IMG.clear()
    ag.ask(line2, on_line); return None
if __name__ == "__main__":
    print(banner() + "\n" + HELP)
