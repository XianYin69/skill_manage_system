#!/usr/bin/env python3
"""shell_core.py — sms-shell 共享路由（与 bin ps1 同套确定性路由）：quit·`sms/sms-shell` 前缀剥离·裸内置词零模型直达（批22 收窄＝仅整行显式命令，自然语言一律走数据流交模型裁决意图）·`:dispatch` 真派发（批23 对等对话）·`:sh`/`!命令` 系统 shell 联动·`:edit/:view` 返回编辑器令牌（TUI F8）·`:session new|list|use|current|overview|conflicts` 会话层（新建会话＝新 session·conv 每输入/派发自动开收·拓扑与跨会话冲突经 sessions_view）。其余话语经 shell_mode.utter（含 F7 三态 gate）→ data flow；agent_stream 批16 LLM 主导：路由打分仅作〔参考〕注入，直答/派发由模型在 gateway 工具循环内自主决定。st 上报步骤、ev 收 msg_flow 信封供顶栏进度。"""
import os, sys, subprocess, re; S = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, S)
import agent_stream as ag, settings, user_commands, skill_route, user_index, debug, chains, resolve_home, sys_shells, shell_resume as sr, stop_channel as stop, chain_error; from shell_help import HELP, SHORT; SMS = ag.SMS; IMG = []; BUILD = "b95"; os.environ["SMS_TMP"] = resolve_home.wtmp(); os.environ.setdefault("SMS_SESSION", __import__("session_reg").current())
def banner(): return "sms-shell·build=" + BUILD + " · SMS_HOME=" + SMS + " · session=" + chains.cur_sess() + " · conv 每输入自动开（:session overview 看拓扑） · 数据流：" + (ag.current() or "未检出（:agents 查看）") + " · 技能前缀：" + ("on" if ag.prefix_on() else "off") + " · 接续前对话：" + ("on" if sr.flag() else "off（:resume on 开启）") + " · 帮助 :help（含 :dispatch/:sh/!命令/:resume/:edit/F8 编辑器/F4 debug 开关）"
def startup_block(): n = sr.note(); return ("── 接续上次关闭前的对话 ──\n" + n) if n else ""
def run_script(name, args):
    try: p = subprocess.run([sys.executable, "-B", os.path.join(S, name) if os.path.isfile(os.path.join(S, name)) else os.path.join(S, "..", "sub_skills", name.replace("/", os.sep))] + list(args), capture_output=True, text=True, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL, timeout=max(10, int(settings.get("shell.exec_timeout", 600))))
    except subprocess.TimeoutExpired: chain_error.hook("script", name, "timeout"); return "子脚本超时（" + name + "·>" + str(max(10, int(settings.get("shell.exec_timeout", 600)))) + "s）已中止——:config set shell.exec_timeout <秒> 可调"
    return (lambda p: (p.returncode and chain_error.hook("script", name, "rc=" + str(p.returncode) + " " + (p.stderr or p.stdout or "")[:200])) or (debug.enabled() and debug.log("exec " + name + " rc=" + str(p.returncode) + ("" if p.returncode == 0 and not p.stderr else " STDERR:" + (p.stderr or p.stdout or "")[:500])) or (p.stdout or p.stderr).strip() or "(无输出)"))(p)
def _meta(m, a, on_line, st):
    if m == "dispatch":
        import agent_tools as at; st("技能派发：" + a[0]) if len(a) > 1 else None; r = stop.guard(lambda: at.run_skill(a[0], " ".join(a[1:]))) if len(a) > 1 else "用法 :dispatch <技能id> <诉求>（技能对等对话派发·批23 各派发独立 conv·:skills 查清单）"; on_line("派发对话 " + a[0] + " 已形式收口·控制权回本对话（正文如上·⧉ 前缀·任务表未完行请继续推进或 :dispatch 重派）" if r.startswith(at.WRAP) else r); return None
    if m == "sh": st("系统 shell"); on_line(stop.guard(lambda: sys_shells.run(" ".join(a), on_line=on_line)) if a and a[0] not in ("list", "select", "export") else (sys_shells.select(a[1]) if a and a[0] == "select" and len(a) > 1 else sys_shells.export() if a and a[0] == "export" else sys_shells.listtext())); return None
    if m in ("restart", "shutdown"): return __import__("shell_lifecycle").cmd(m, SMS, on_line)
    if m in ("edit", "view"): return (on_line("用法 :" + m + " <路径>（TUI F8 或主菜单·查看器 :view）") and None) if not a else m + ":" + os.path.abspath(os.path.expanduser(" ".join(a)))
    if m == "session": c = a[0] if a else "current"; import sessions_view as sv; on_line(chains.new_sess(" ".join(a[1:])) if c == "new" else chains.list_sess() if c == "list" else sv.overview(chains.cur_sess()) if c == "overview" else sv.conflicts(chains.cur_sess()) or "（无跨会话未完成·各会话任务表均已收口）" if c == "conflicts" else chains.use_sess(a[1]) if c == "use" and len(a) > 1 else ("当前会话（session）" + chains.cur_sess() + "·新建会话＝新 session 非 conv·conv 每输入/派发自动开收" if c == "current" else run_script("chains.py", ["session"] + a))); return None
    if m == "agents": on_line("检出：" + ("、".join(ag.detected()) or "无") + " · 当前：" + (ag.current() or "-") + " · 技能前缀：" + ("on" if ag.prefix_on() else "off") + "\n可用适配器（含未装）：" + "、".join(ag.adapters()))
    elif m == "image" and a: p = " ".join(a); IMG[:] = [p] if os.path.isfile(p) else []; on_line(("已附图（下一句生效）：" if IMG else "图片不存在：") + p)
    elif m == "use" and a: on_line(ag.use(a[0]))
    elif m == "skill": on_line(ag.skill(not (a and a[0] == "off")))
    elif m in ("hud", "deploy", "workspace", "resume", "qq"): on_line(run_script({"resume": "shell_resume", "qq": "qq_cli"}.get(m, m) + ".py", a))
    elif m in ("config", "web", "ext", "debug", "mode"): m == "debug" and a and a[0] in ("on", "off") and settings.set("debug.enabled", a[0] == "on"); on_line(run_script({"config": "settings", "web": "web_shell", "ext": "external", "mode": "shell_mode"}.get(m, m) + ".py", a or ["status"]))
    elif m in ("net", "tts", "learn", "file", "path", "detail"): on_line(run_script({"net": "ff_lite", "file": "file_ops/scripts/file_ops.py", "path": "file_ops/scripts/path_ops.py", "detail": "shell_console"}.get(m, m) + (".py" if m not in ("file", "path") else ""), (["tail"] + a) if m == "detail" else (a or (["status"] if m in ("tts", "net") else []))))
    elif m == "api": on_line(run_script("api.py", a or ["formats"]))
    elif m == "grant": on_line(run_script("permissions.py", ["grant"] + a + ["--write"]))
    elif m in ("dream", "repair"): on_line(run_script("dream.py" if m == "dream" else "dream_pending.py", a or ["status" if m == "dream" else "list"]))
    elif m in ("cmds", "intent"): on_line(run_script("commands.py", ["help"] if (m == "cmds" and not a) else (["show"] + a if m == "cmds" else ["intent"] + a)))
    elif m in ("tools", "task", "manual"): on_line(run_script("agent_dispatch.py", ["tools"] + a) if m == "tools" else run_script("task_table.py", a or ["show"]) if m == "task" else run_script("sys_shells.py", ["manual"] + a))
    elif m == "perms": on_line(run_script("permissions.py", ["status"] + a))
    elif m in ("index", "skills"): on_line(run_script("register.py" if (m == "index" and a) else ("skills_config.py" if m == "index" else "skill_route.py"), (["--add-root"] + a + ["--write"]) if (m == "index" and a) else (["roots"] if m == "index" else ["list"])) + (("\n" + user_index.add(" ".join(a), SMS)) if m == "index" and a else ""))
    elif m in ("alias", "unalias"): on_line(run_script("user_commands.py", [("add" if m == "alias" else "rm")] + a + ["--write"]))
    else: on_line(HELP if m in ("help", "?") else "未知元指令 :" + m + "（:help）")
HELPW = ("help", "?", "h", "帮助", "用法"); CFGW = ("config", "设置", "配置", "状态", "status", "修改配置", "打开设置", "查看配置", "如何修改配置", "怎么修改配置", "如何查看配置", "修改配置文件", "打开配置", "进入配置", "配置编辑器", "图形化配置"); CMDW = ("cmds", "命令", "指令", "命令表"); METAS = frozenset(("agents","use","skill","image","dispatch","sh","edit","view","session","hud","deploy","workspace","resume","config","web","ext","debug","detail","mode","net","tts","learn","file","path","api","grant","dream","cmds","intent","index","skills","alias","unalias","help","?","quit","tools","perms","stop","task","manual"))
def _cfgline(): g = settings.status()["gateway"]; return "gateway: enabled=%s base_url=%s model=%s api_key=%s max_tokens=%s 推理=%s · 文件=<SMS_HOME>/config/config.json\n改配置：:config set <path> <json> · 全量：:config show · TUI F4 图形化（debug 开关/输出路径同处）· 推理等级 :config set llm_gateway.reasoning_effort \"high\"（low|medium|high·null 不发送）" % (g["enabled"], g["base_url"], g["model"], g["api_key"], g["max_tokens"], g.get("reasoning", "-"))
def handle(line, on_line, st=lambda n: None, ev=None):
    if not (t := line.strip()): return None
    if t.lower() in ("quit", "exit", ":quit", ":q", ":exit"): return "exit"
    if (pm := re.match(r"(?i)^(sms[\s\-_\.]*shell(\.cmd)?|sms)(?=[\s,，:：]|$)[\s,，]*(.*)$", t)): return handle(pm.group(3), on_line, st, ev) if pm.group(3).strip() else on_line(HELP)
    if t.startswith(("!", "！")): st("系统 shell 透传"); on_line(sys_shells.run(t[1:].strip(), on_line=on_line)); return None
    if t.startswith((":", "：")): p = t.lstrip(":：").split(); k = p[0].lower(); debug.enabled() and debug.log("meta " + " ".join(p)[:200]); st("元指令：" + k); return (on_line("停止状态：" + stop.status() + "（任务进行中在 TUI/GUI 直接输 stop/停止；readline 兜底壳 Ctrl+C 中断）"), stop.clear(), None)[2] if k == "stop" else _meta(k, p[1:], on_line, st)
    if (w := t.lower()) in HELPW: st("内置词：帮助"); on_line(HELP); return None
    if w in CFGW: st("内置词：配置状态"); on_line(_cfgline()); return "config" if w in ("打开配置", "进入配置", "配置编辑器", "图形化配置", "打开设置") else None
    if w in CMDW: st("内置词：命令表"); on_line(run_script("commands.py", ["help"])); return None
    if (mc := re.match(r"(?i)^(?:config|设置|配置)[\s,，]+(\S.*)$", t)): st("内置词：配置命令"); _meta("config", mc.group(1).split(None, 2), on_line, st); return None
    if re.match(r"(?i)^skills?\s*list[\s!！。？?]*$|^(技能列表|可用技能|可调用技能)[\s!！。？?]*$", t): st("内置词：技能清单"); on_line(skill_route.listtext()); return None
    if w in ("显示提示词", "提示词", "你的提示词"): st("SMS 壳自管理直答"); on_line(SHORT + "（确定性路由·未经大模型）"); return None
    if user_commands.find(user_commands.load(SMS), (parts := t.split())[0]): st("个性化指令展开：" + parts[0]); on_line(run_script("user_commands.py", ["run"] + parts)); return None
    img = IMG[0] if IMG else None; IMG.clear(); debug.enabled() and debug.log("utter> " + line[:300]); st("话语→数据流（agent_stream）"); line = user_index.expand(line, SMS)
    import shell_mode; return shell_mode.utter(line, img, on_line, st, ev) or None
