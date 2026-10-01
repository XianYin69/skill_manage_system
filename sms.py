#!/usr/bin/env python3
"""sms.py — 根入口（Windows/macOS/Linux，纯标准库）：①开箱即用：解析/创建 SMS_HOME、播种用户配置、红线自检（失败即停）；②依赖嗅探与修补：python/PySide6/textual/git/agent CLI 逐项报告（缺 dep 不自动安装，--install-deps 经同意才 pip 装 PySide6；textual 仅报告）；注册表产物缺失或 --rebuild 时重建；③引导至 CLI：交棒 bin/sms-shell（Textual TUI 优先，ps1 原生 DOS TUI 回退）。用法：python sms.py [doctor|shell] [--rebuild] [--install-deps] [shell 参数…]。"""
import importlib.util, json, os, shutil, subprocess, sys, time
ROOT = os.path.dirname(os.path.abspath(__file__))
S = os.path.join(ROOT, "skill", "scripts")
sys.path.insert(0, S)
import resolve_home, agent_stream, chains, dream
def run(script, *a):
    return subprocess.run([sys.executable, "-B", os.path.join(S, script), *a], cwd=ROOT, capture_output=True, text=True)
def sniff(argv, say):
    say("python %d.%d%s" % (*sys.version_info[:2], "" if sys.version_info >= (3, 9) else " —— 过低（需≥3.9）"))
    have_py = True
    say("GUI 依赖 PySide6：%s" % ("可用" if importlib.util.find_spec("PySide6") else "缺失→sms-shell 回退 TUI；同意安装请加 --install-deps"))
    if "--install-deps" in argv and not importlib.util.find_spec("PySide6"):
        subprocess.run([sys.executable, "-m", "pip", "install", "PySide6"])
        say("GUI 依赖 PySide6：%s" % ("可用" if importlib.util.find_spec("PySide6") else "安装失败"))
    say("TUI 增强依赖 textual：%s" % ("可用" if importlib.util.find_spec("textual") else "缺失→sms-shell 回退旧 readline TUI（pip install textual 可启用增强 TUI）"))
    say("git：%s" % ("可用" if shutil.which("git") else "缺失→sync_skills/trust 不可用，请安装并加入 PATH"))
    ags = sorted(agent_stream.detected())
    say("agent CLI：%s" % ("、".join(ags) if ags else "未检出→shell 拒绝派发；装任一 agent 或在 <SMS_HOME>/config/config.json 配 agent_cli {bin,args}"))
    st = json.loads(run("dream.py", "status").stdout); frags = chains.store().all_frags()
    say("做梦机制：间隔 %d 分（用户设置·时间戳程序按间隔算）·上次 %s%s；链碎片 %d 条（%d 链）" % (st["interval_min"], time.strftime("%m-%d %H:%M", time.localtime(st["last_run"])) if st["last_run"] else "从未", "（已到期待跑）" if st["due"] else "（未到期）", len(frags), len(chains.CHAINS)))
    reg = os.path.join(resolve_home.resolve(), "registry", "register.json")
    if os.path.exists(reg) and "--rebuild" not in argv:
        return say("注册表：已存在（register/interfaces/connections/deps）")
    r = run("init_registry.py", "--write")
    say("注册表重建：%s" % ("成功" if r.returncode == 0 else "失败→先 python -B skill/scripts/permissions.py grant write --write 再试"))
def main():
    argv = sys.argv[1:]
    print("[1/3 开箱即用] SMS_HOME=%s（<SMS_HOME>/config/config.json 首读自动播种）" % resolve_home.ensure())
    try: chk = json.loads(run("redlines.py", "check").stdout)
    except Exception as e: print("[1/3] 红线自检异常：%s" % e); sys.exit(1)
    sp = run("sep_audit.py")
    if sp.returncode != 0 and "COUPLED" in (sp.stdout or ""): print("[1/3] 壳/核分离体检未通过——core 侧存在 shell_* 反向 import，禁止继续：%s" % json.dumps(json.loads(sp.stdout).get("violations"), ensure_ascii=False)); sys.exit(1)
    print("[1/3] 壳/核分离体检：%s" % ("SEPARATED（core→shell 0·seam=runtime_bind）" if sp.returncode == 0 else "跳过（sep_audit 不可用）"))
    if not chk.get("ok"): print("[1/3] 红线自检未通过，按治理禁止绕过：%s" % json.dumps(chk, ensure_ascii=False)); sys.exit(1)
    print("[1/3] 红线自检：通过；[2/3 依赖嗅探与修补]")
    out = []; sniff(argv, out.append)
    for ln in out: print("[2/3]", ln)
    if "doctor" in argv: sys.exit(0)
    print("[3/3 引导至 CLI] 启动 sms-shell（Textual TUI 优先·ps1 原生 DOS TUI 回退·缺 python 时 api 路由至 locate.py）…")
    args = [a for a in argv if a not in ("doctor", "--rebuild", "--install-deps")]
    e = os.path.join(ROOT, "bin", "sms-shell.cmd" if os.name == "nt" else "sms-shell")
    sys.exit(subprocess.call(subprocess.list2cmdline([e] + args), cwd=ROOT, shell=True) if os.name == "nt" else subprocess.call(["sh", e, *args], cwd=ROOT))
if __name__ == "__main__":
    main()
