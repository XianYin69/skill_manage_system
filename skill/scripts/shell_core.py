#!/usr/bin/env python3
"""shell_core.py — sms-shell 共享路由（与 bin ps1 同套确定性路由）：quit·`sms/sms-shell` 前缀剥离·裸内置词零模型直达（批22 收窄＝仅整行显式命令，自然语言一律走数据流交模型裁决意图）·`:dispatch` 真派发（批23 对等对话）·`:sh`/`!命令` 系统 shell 联动·`:edit/:view` 返回编辑器令牌（TUI F8）·`:session new|list|use|current|overview|conflicts` 会话层（新建会话＝新 session·conv 每输入/派发自动开收·拓扑与跨会话冲突经 sessions_view）。其余话语经 shell_mode.utter（含 F7 三态 gate）→ data flow；agent_stream 批16 LLM 主导：路由打分仅作〔参考〕注入，直答/派发由模型在 gateway 工具循环内自主决定。st 上报步骤、ev 收 msg_flow 信封供顶栏进度。"""
import no_window  # 静默子进程：前台运行任务不弹命令行窗口
import os, sys, subprocess, re; S = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, S)
import web_banner as wb, agent_stream as ag, settings, user_commands, skill_route, user_index, debug, chains, resolve_home, sys_shells, shell_resume as sr, stop_channel as stop, chain_error; from shell_help import HELP, SHORT; SMS = ag.SMS; IMG = []; BUILD = "b97"; os.environ["SMS_TMP"] = resolve_home.wtmp(); os.environ.setdefault("SMS_SESSION", __import__("session_reg").current())
def _solo():
    """SOLO 模块安全取用（solo.py 缺失/依赖异常＝None·绝不阻断启动）。"""
    try:
        import solo; return solo
    except Exception: return None
def _soloflag():
    s = _solo()
    try:
        return bool(s and s.enabled())
    except Exception: return False
def _parflag():
    try:
        import settings as _s
        if not bool(_s.get("shell.parallel", True)): return "off（排队续发）"
        c = int(_s.get("shell.max_parallel", 4) or 0)
        return "on·无限" if not c else ("on·≤%d" % c)
    except Exception: return "on"
def _busflag():
    try:
        import settings as _s, msg_flow as _mf
        return "on（他会话推导/工具/命令行输出并入 F9）" if bool(_s.get("shell.detail_bus", True)) and _mf._bus_on() else "off"
    except Exception: return "on"
def banner(): return "sms-shell·build=" + BUILD + " · SMS_HOME=" + SMS + " · session=" + chains.cur_sess() + " · conv 每输入自动开（:session overview 看拓扑） · 数据流：" + (ag.current() or "未检出（:agents 查看）") + " · 技能前缀：" + ("on" if ag.prefix_on() else "off") + " · 接续前对话：" + ("on" if sr.flag() else "off（:resume on 开启）") + " · 帮助 :help（含 :dispatch/:sh/!命令/:resume/:edit/F8 编辑器/F4 debug 开关）" + " · 并行输入：" + _parflag() + " · 跨会话明细：" + _busflag() + " · SOLO：" + ("on" if _soloflag() else "off") + "\n" + wb.line()
def startup_block():
    parts = []
    n = sr.note()
    if n: parts.append("── 接续上次关闭前的对话 ──\n" + n)
    try:
        import net_util as nu
        w = settings.get("web_shell") or {}
        if w.get("enabled", True):
            host = w.get("host", "127.0.0.1"); port = w.get("port", 8737); pid = nu.running("web_shell")
            parts.append("── 网页端 WEB SHELL ──\n地址 https://%s:%s/ · 密钥 %s\n状态：%s（开关 :config set web_shell.enabled true|false）" % (host, port, wb.token_display(), ("运行中 pid=" + str(pid)) if pid else "未运行（:web start 开启）"))
        else:
            parts.append("── 网页端已禁用（:config set web_shell.enabled true 开启）──")
    except Exception: pass
    s = _solo()
    if s:
        try:
            if s.enabled():
                stt = s.status(SMS)
                parts.append("── SOLO 模式已开启 ──\n缺权限不再向用户确认，由大模型自审决定是否授予（关闭：:solo off／F10 权限面板）\n" + s.banner_lines() + "\n当日已放行 " + str(stt.get("granted_today", 0)) + " 项 · 自审网关" + ("可用" if stt.get("gateway_ok") else "未启用") + " · allow_danger=" + str(stt.get("allow_danger")) + " · 永不自审：" + "、".join(stt.get("never") or []) + "（:solo status）")
        except Exception: pass
    return "\n\n".join(parts)
def run_script(name, args):
    try: p = no_window.run([sys.executable, "-B", os.path.join(S, name) if os.path.isfile(os.path.join(S, name)) else os.path.join(S, "..", "sub_skills", name.replace("/", os.sep))] + list(args), capture_output=True, text=True, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL, timeout=max(10, int(settings.get("shell.exec_timeout", 600))))
    except subprocess.TimeoutExpired as te:
        chain_error.hook("script", name, "timeout")
        import run_watch as rw
        lim = max(10, int(settings.get("shell.exec_timeout", 600)))
        dec = lambda v: (v.decode("utf-8", "replace") if isinstance(v, bytes) else (v or ""))
        lines = [x for x in (dec(te.stdout) + "\n" + dec(te.stderr)).splitlines() if x.strip()]
        return rw.feedback(name, "子脚本超时被中止", lim, lim, lines)
    return (lambda p: (p.returncode and chain_error.hook("script", name, "rc=" + str(p.returncode) + " " + (p.stderr or p.stdout or "")[:200])) or (debug.enabled() and debug.log("exec " + name + " rc=" + str(p.returncode) + ("" if p.returncode == 0 and not p.stderr else " STDERR:" + (p.stderr or p.stdout or "")[:500])) or (p.stdout or p.stderr).strip() or "(无输出)"))(p)
def _meta(m, a, on_line, st):
    if m == "dispatch":
        import agent_tools as at; st("技能派发：" + a[0]) if len(a) > 1 else None; r = stop.guard(lambda: at.run_skill(a[0], " ".join(a[1:]))) if len(a) > 1 else "用法 :dispatch <技能id> <诉求>（技能对等对话派发·批23 各派发独立 conv·:skills 查清单）"; on_line("派发对话 " + a[0] + " 已形式收口·控制权回本对话（正文如上·⧉ 前缀·任务表未完行请继续推进或 :dispatch 重派）" if r.startswith(at.WRAP) else r); return None
    if m == "sh": st("系统 shell"); on_line(stop.guard(lambda: sys_shells.run(" ".join(a), on_line=on_line)) if a and a[0] not in ("list", "select", "export") else (sys_shells.select(a[1]) if a and a[0] == "select" and len(a) > 1 else sys_shells.export() if a and a[0] == "export" else sys_shells.listtext())); return None
    if m in ("restart", "shutdown"): return __import__("shell_lifecycle").cmd(m, SMS, on_line)
    if m == "solo":
        s = _solo()
        if not s: on_line("SOLO 模块不可用（solo.py 缺失或依赖异常·已降级：权限仍走用户确认）"); return None
        c = (a[0] or "").lower() if a else "status"
        if c in ("on", "off"): st("SOLO 开关"); on_line(stop.guard(lambda: s.set(c == "on"))); return None
        if c == "banner": on_line(s.banner_lines()); return None
        on_line(run_script("solo.py", a or ["status"])); return None
    if m in ("edit", "view"): return (on_line("用法 :" + m + " <路径>（TUI F8 或主菜单·查看器 :view）") and None) if not a else m + ":" + os.path.abspath(os.path.expanduser(" ".join(a)))
    if m == "session":
        try:
            import session_cli as _sc
            on_line(_sc.main(list(a) or ['current'])); return None
        except Exception:
            pass
    if m == "agents": on_line("检出：" + ("、".join(ag.detected()) or "无") + " · 当前：" + (ag.current() or "-") + " · 技能前缀：" + ("on" if ag.prefix_on() else "off") + "\n可用适配器（含未装）：" + "、".join(ag.adapters()))
    elif m == "image" and a: p = " ".join(a); IMG[:] = [p] if os.path.isfile(p) else []; on_line(("已附图（下一句生效）：" if IMG else "图片不存在：") + p)
    elif m == "use" and a: on_line(ag.use(a[0]))
    elif m == "skill": on_line(ag.skill(not (a and a[0] == "off")))
    elif m in ("hud", "deploy", "workspace", "resume", "qq", "plan", "dep"): on_line(run_script({"resume": "shell_resume", "qq": "qq_cli", "plan": "planned_tasks", "dep": "dep_fetch"}.get(m, m) + ".py", a))
    elif m in ("config", "web", "ext", "debug", "mode"): m == "debug" and a and a[0] in ("on", "off") and settings.set("debug.enabled", a[0] == "on"); on_line(run_script({"config": "settings", "web": "web_shell", "ext": "external", "mode": "shell_mode"}.get(m, m) + ".py", a or ["status"]))
    elif m in ("net", "tts", "learn", "file", "path", "detail"): on_line(run_script({"net": "ff_lite", "file": "file_ops/scripts/file_ops.py", "path": "file_ops/scripts/path_ops.py", "detail": "shell_console"}.get(m, m) + (".py" if m not in ("file", "path") else ""), (a if a and a[0] in ("tail", "bus", "clear", "status") else (["tail"] + a)) if m == "detail" else (a or (["status"] if m in ("tts", "net") else []))))
    elif m == "api": on_line(run_script("api.py", a or ["formats"]))
    elif m == "grant": on_line(run_script("permissions.py", (a + (["--write"] if a[0] in ("grant", "deny", "unbind", "revoke") else [])) if a and a[0] in ("ids", "status", "check", "unbind", "revoke", "resolve") else ["grant"] + a + ["--write"]))
    elif m in ("dream", "repair"): on_line(run_script("dream.py" if m == "dream" else "dream_pending.py", a or ["status" if m == "dream" else "list"]))
    elif m in ("cmds", "intent"): on_line(run_script("commands.py", ["help"] if (m == "cmds" and not a) else (["show"] + a if m == "cmds" else ["intent"] + a)))
    elif m in ("tools", "task", "manual"): on_line(run_script("agent_dispatch.py", ["tools"] + a) if m == "tools" else run_script("task_table.py", a or ["show"]) if m == "task" else run_script("sys_shells.py", ["manual"] + a))
    elif m == "perms": on_line(run_script("permissions.py", ["status"] + a))
    elif m in ("index", "skills"): on_line(run_script("register.py" if (m == "index" and a) else ("skills_config.py" if m == "index" else "skill_route.py"), (["--add-root"] + a + ["--write"]) if (m == "index" and a) else (["roots"] if m == "index" else ["list"])) + (("\n" + user_index.add(" ".join(a), SMS)) if m == "index" and a else ""))
    elif m in ("alias", "unalias"): on_line(run_script("user_commands.py", [("add" if m == "alias" else "rm")] + a + ["--write"]))
    else: on_line(HELP if m in ("help", "?") else "未知元指令 :" + m + "（:help）")
HELPW = ("help", "?", "h", "帮助", "用法"); CFGW = ("config", "设置", "配置", "状态", "status", "修改配置", "打开设置", "查看配置", "如何修改配置", "怎么修改配置", "如何查看配置", "修改配置文件", "打开配置", "进入配置", "配置编辑器", "图形化配置"); CMDW = ("cmds", "命令", "指令", "命令表"); METAS = frozenset(("agents","use","skill","image","dispatch","sh","edit","view","session","hud","deploy","workspace","resume","config","web","ext","debug","detail","mode","net","tts","learn","file","path","api","grant","solo","dream","cmds","intent","index","skills","alias","unalias","help","?","quit","tools","perms","stop","task","manual"))
def _cfgline(): g = settings.status()["gateway"]; return "gateway: enabled=%s base_url=%s model=%s api_key=%s max_tokens=%s 推理=%s · 文件=<SMS_HOME>/config/config.json\n改配置：:config set <path> <json> · 全量：:config show · TUI F4 图形化（debug 开关/输出路径同处）· 推理等级 :config set llm_gateway.reasoning_effort \"high\"（low|medium|high·null 不发送）" % (g["enabled"], g["base_url"], g["model"], g["api_key"], g["max_tokens"], g.get("reasoning", "-"))
def _lc_pending(on_line):
    """批32 R1：quit/exit 也消费大模型登记的 restart/shutdown（旧版直接 return "exit"＝请求残留无人执行）。
    壳内＝真执行（restart 拉起新实例并硬退本进程）；异常不静默（记 error 链＋一行告知·文件保留）。"""
    try:
        import shell_lifecycle as lc
        r = lc.run_pending(SMS, on_line=on_line)
        if isinstance(r, str) and "待壳执行" in r:
            on_line(r)  # R2：取不到执行者＝明确告知＋文件保留，不静默
        return r
    except Exception as e:
        try:
            import chain_error
            chain_error.record("shell", "shell_core.quit_pending", str(e)[:160])
        except Exception as e2:
            on_line("!lifecycle▸ 退出前消费登记请求异常且记链失败：" + repr(e2)[:100])
        on_line("!lifecycle▸ 退出前消费 restart/shutdown 登记异常（请求文件保留·已记 error 链）：" + str(e)[:120])
        return None
def handle(line, on_line, st=lambda n: None, ev=None):
    if not (t := line.strip()): return None
    if t.lower() in ("quit", "exit", ":quit", ":q", ":exit"):
        _lc_pending(on_line)  # 批32 R1：退出路径也消费登记请求（壳内 restart 拉起新实例后硬退，走不到下一行）
        return "exit"
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

import runtime_bind as _rb; _rb.set_runner(handle)  # 批27 接缝登记（core 侧经 runtime_bind 调壳，不再反向 import）
