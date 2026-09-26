#!/usr/bin/env python3
"""shell_core.py — sms-shell 共享路由引擎（Textual/readline TUI 与 GUI 前端通用，与 bin 原生 ps1 入口同套确定性路由）：quit·`sms/sms-shell` 前缀剥离重路由·裸内置词（help/?/config/状态/cmds/命令）零模型直达·问 SMS 自身设置/命令/提示词自管理·`:` 元指令仅治理（切回退 agent、api/deploy/session/grant/config 等）·个性化指令（user_commands）命中展开·其余话语默认直达原生网关（先经 agent_stream→skill_route registry 技能路由再 gateway，OpenAI 兼容直连·流式、不经外部 CLI；本体不作答；st 回调上报每步名称供 TUI 进度显示）。"""
import os, sys, subprocess, shlex, re
S = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, S)
import agent_stream as ag, settings, user_commands, skill_route, user_index, debug, resolve_home
SMS = ag.SMS; IMG = []; os.environ["SMS_TMP"] = resolve_home.wtmp()
HELP = ("直接输入任何话语＝交给系统（默认原生网关直连·流式）· 命中个性化指令名则展开执行\n"
        ":agents 看/选回退 CLI · :use <name> · :skill on|off 技能前缀 · :cmds [name] · :intent <话语> · :alias/:unalias 个性化指令 · :hud session|step|alert|hide · :deploy <dir|--Path P --FolderName F>（部署＝仅复制 bin 文件） · :session \"<任务>\" · :workspace current|list|add <路径>|switch <路径>|remove|use-virtual|repair-home（SMS_WORKSPACE＝智能体操作的真实工作区·与数据根 SMS_HOME 分离·清单/切换/添加改路径/回虚拟/修残留·即时生效不动配置·真实/虚拟工作区均自动建 tmp\ 收生成文件〔env SMS_TMP〕·大模型/技能配置直读 SMS 不落工作区） · :grant <键|角色> [分钟] · :api formats|detect|show|validate|export（格式 API·原 sms-api） · :dream status|run · :debug on|off|status|tail [n]|path（调试模式：路由/脚本执行/异常 traceback 全记 <SMS_HOME>/logs/debug.log·启动器 --debug 或 env SMS_DEBUG=1 亦可·顶栏显 DEB） · :image <文件> 附下一话语图片 · :config status|show|get|set 设置系统（模型参数 config.json 与技能列表 skills.json 视图统一·按属主路由写回·每次读写即时重读无缓存） · :web start|stop|token · :ext status|enable|enroll · :net search|fetch|download|status（firefox lite 内核·须 grant net）· :tts say|test|on|off|voices（阿林娜 alina 朗读）· :learn from-url|note|recall|distill|stats · :file read|write|list|copy|move|delete|stat · :path resolve|which|glob|tree|env · :skills 托管技能清单 · :index [<路径>] 看/登记扫描根＋用户「/」索引并重建注册表 · :quit · 系统原生用法：sms-shell <话语|:元指令> 单发执行即退 · Textual TUI：左右分屏（右栏显工作区/修改文件/链会话/步骤类型/会话总览〔创建时间＋简略〕）· F1/Alt+M 主菜单 · Ctrl+K 托管技能菜单 · F2/「/」SKILL.md 技能索引（名称＋SKILL.md 介绍·Enter 插 /技能名）· F5 文件索引（用户索引项·Enter 插 /名称·＋可选文件夹中的文件/文件夹·提交时 /令牌就地展开）· F6 工作区切换（SMS_WORKSPACE：清单切换/＋添加更改路径/◎内置虚拟工作区〔每对话自动建·收口即删〕——不动 SMS_HOME 配置零影响）· F3/Alt+H 帮助 · F4/Alt+C 图形化配置编辑（行＝简写＋注释·↑↓方向键·字母过滤·空格布尔·Enter 布尔＝T/F 方向键选择器免打字·写回即时重读并刷新顶栏）· 技能路由命中时主输出自动给出「链接子对话」提示并备好调用语句（空输入自动填入·回车确认开子对话·或输入 /技能名） · Shift+Tab agent 菜单 · Tab 补全（元指令＋/令牌） · 上下历史 · Ctrl+Enter 提交 · Ctrl+L 清屏 · Ctrl+Q 退出（注：VS Code 等终端会截获 Alt+字母作窗口菜单——「/」/F1-F6/Ctrl+K 恒可达）\n裸词直达（不经大模型）：help/配置/config · 状态/status · 命令/cmds；裸 `config get|set|show <dot.path> <json>`（不带冒号同 :config）；`技能列表`/`哪些技能`/`skills list` 列可调用托管技能")
def banner():
    return "sms-shell · SMS_HOME=" + SMS + " · 当前 agent：" + (ag.current() or "未检出（:agents 查看）") + " · 技能前缀：" + ("on" if ag.prefix_on() else "off") + " · 设置系统：:config status|show|get <dot.path>|set <path> <json> · 原生用法：系统 shell 里 sms-shell <话语|:元指令> 单发执行即退"
def run_script(name, args):
    p = subprocess.run([sys.executable, "-B", os.path.join(S, name)] + list(args), capture_output=True, text=True, encoding="utf-8", errors="replace")
    return (debug.log("exec " + name + " rc=" + str(p.returncode) + ("" if p.returncode == 0 and not p.stderr else " STDERR:" + (p.stderr or p.stdout or "")[:500])) if debug.enabled() else None) or (p.stdout or p.stderr).strip() or "(无输出)"
def _meta(m, a, on_line):
    if m == "agents": on_line("检出：" + ("、".join(ag.detected()) or "无") + " · 当前：" + (ag.current() or "-") + " · 技能前缀：" + ("on" if ag.prefix_on() else "off") + "\n可用适配器（含未装）：" + "、".join(ag.adapters()))
    elif m == "image" and a: p = " ".join(a); IMG[:] = [p] if os.path.isfile(p) else []; on_line(("已附图（下一句生效）：" if IMG else "图片不存在：") + p)
    elif m == "use" and a: on_line(ag.use(a[0]))
    elif m == "skill": on_line(ag.skill(not (a and a[0] == "off")))
    elif m in ("hud", "deploy", "session", "workspace"): on_line(run_script(m + ".py", a))
    elif m in ("config", "web", "ext", "debug"): on_line(run_script({"config": "settings", "web": "web_shell", "ext": "external"}.get(m, m) + ".py", a or ["status"]))
    elif m in ("net", "tts", "learn", "file", "path"): on_line(run_script({"net": "ff_lite", "file": "file_ops", "path": "path_ops"}.get(m, m) + ".py", a or (["status"] if m in ("tts", "net") else [])))
    elif m == "api": on_line(run_script("api.py", a or ["formats"]))
    elif m == "grant": on_line(run_script("permissions.py", ["grant"] + a + ["--write"]))
    elif m == "dream": on_line(run_script("dream.py", a or ["status"]))
    elif m in ("cmds", "intent"): on_line(run_script("commands.py", ["help"] if (m == "cmds" and not a) else (["show"] + a if m == "cmds" else ["intent"] + a)))
    elif m in ("index", "skills"): on_line(run_script("register.py" if (m == "index" and a) else ("skills_config.py" if m == "index" else "skill_route.py"), (["--add-root"] + a + ["--write"]) if (m == "index" and a) else (["roots"] if m == "index" else ["list"])) + (("\n" + user_index.add(" ".join(a), SMS)) if m == "index" and a else ""))
    elif m in ("alias", "unalias"): on_line(run_script("user_commands.py", [("add" if m == "alias" else "rm")] + a + ["--write"]))
    elif m in ("help", "?"): on_line(HELP)
    else: on_line("未知元指令 :" + m + "（:help）")
HELPW, CFGW, CMDW = ("help", "?", "h", "帮助", "用法"), ("config", "设置", "配置", "状态", "status", "修改配置", "打开设置", "查看配置", "如何修改配置", "怎么修改配置", "如何查看配置", "修改配置文件", "打开配置", "进入配置", "配置编辑器", "图形化配置"), ("cmds", "命令", "指令", "命令表")
def _cfgline():
    g = settings.status()["gateway"]; return "gateway: enabled=%s base_url=%s model=%s api_key=%s max_tokens=%s · 文件=<SMS_HOME>/config/config.json\n改配置：:config set <path> <json> · 全量：:config show" % (g["enabled"], g["base_url"], g["model"], g["api_key"], g["max_tokens"])
def handle(line, on_line, st=lambda n: None):
    if not (t := line.strip()): return None
    if t.lower() in ("quit", "exit", ":quit", ":q", ":exit"): return "exit"
    m = re.match(r"(?i)^(sms[\s\-_\.]*shell(\.cmd)?|sms)(?=[\s,，:：]|$)[\s,，]*(.*)$", t)
    if m: return handle(m.group(3), on_line, st) if m.group(3).strip() else on_line(HELP)
    if t.startswith((":", "：")): p = t.lstrip(":：").split(); debug.enabled() and debug.log("meta " + " ".join(p)[:200]); st("元指令：" + p[0].lower()); _meta(p[0].lower(), p[1:], on_line); return None
    if (w := t.lower()) in HELPW: st("内置词：帮助"); on_line(HELP); return None
    if w in CFGW: st("内置词：配置状态"); on_line(_cfgline()); return "config" if w in ("打开配置", "进入配置", "配置编辑器", "图形化配置", "打开设置") else None
    if w in CMDW: st("内置词：命令表"); on_line(run_script("commands.py", ["help"])); return None
    if (mc := re.match(r"(?i)^(?:config|设置|配置)[\s,，]+(\S.*)$", t)): st("内置词：配置命令"); _meta("config", mc.group(1).split(None, 2), on_line); return None
    if re.search(r"(哪些|那些|什么|可用|可以|能)[^。！!？?]{0,8}(技能|skills?\b)", t) or re.match(r"(?i)^skills?\s*list[\s!！。？?]*$|^(技能列表|可用技能|可调用技能)[\s!！。？?]*$", t): st("内置词：技能清单"); on_line(skill_route.listtext()); return None
    if (re.search(r"(?i)sms|shell|壳", t) and re.search("设置|配置|命令|指令|config", t)) or w in ("显示提示词", "提示词", "你的提示词"): st("SMS 壳自管理直答"); on_line(HELP + "\n（确定性路由·未经大模型·SMS 壳自身信息即上表）"); return None
    try: parts = shlex.split(line)
    except ValueError: parts = line.split()
    if user_commands.find(user_commands.load(SMS), parts[0]): st("个性化指令展开：" + parts[0]); on_line(run_script("user_commands.py", ["run"] + parts)); return None
    img = IMG[0] if IMG else None; IMG.clear(); debug.enabled() and debug.log("utter> " + line[:300]); st("话语→数据流（agent_stream）"); line = user_index.expand(line, SMS)
    ag.ask(line + ("\n[图:" + img + "]" if img else ""), on_line, st); return None
if __name__ == "__main__": print(banner() + "\n" + HELP)
