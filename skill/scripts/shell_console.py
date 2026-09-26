#!/usr/bin/env python3
"""shell_console.py — 无 F9 屏文字前端的输出区门控（批7·用户「思考过程/命令输入/工具调用/skill调用请求/skill调用过程全放详细·输出区只放正文」）：wrap(on_line) 按与 Textual split 同口径的 msg_flow.visible 判每一行——正文/• notice/✗ err 原样透传；◌ 思考、$ 工具、⧉ 技能过程、▸ 步骤、! sh 执行、≡ 任务等过程行不上屏、压入 <SMS_HOME>/shell/detail.json 滚动末 400 条（atomic_io 并发安全写·控制台版 F9·`:detail tail`/本脚本 tail 可读），debug 开启时另记 debug.log。接线面＝shell_tui.py（readline 兜底与单发）·shell_tui_textual 单发 CLI·shell_gui.py GUI——凡无 F9 界面的入口一律经此门控，主输出只留模型非思考非工具调用的文本。用法：python -B shell_console.py [tail n]"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import msg_flow, resolve_home, atomic_io
SMS = resolve_home.ensure()
P = lambda: os.path.join(SMS, "shell", "detail.json")
def record(t):
    try:
        d = atomic_io.rjson(P(), default=[]) if os.path.isfile(P()) else []
        atomic_io.wjson(P(), (list(d) + [str(t)[:2000]])[-400:])
        try:
            import debug; debug.enabled() and debug.log("F9 " + str(t)[:300])
        except Exception: pass
    except Exception: pass
def wrap(on_line):
    def w(s):
        t = str(s)
        if msg_flow.visible(t): on_line(t)
        else: record(t)
    return w
if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "tail":
        d = atomic_io.rjson(P(), default=[])
        print("\n".join(str(x).replace("\n", " ") for x in d[-(int(a[1]) if len(a) > 1 and a[1].isdigit() else 30):]) or "（空——◌思考/$工具/⧉技能/▸步骤/!sh/≡任务过程行收存于此·主输出只留正文）")
    else: print(__doc__.strip())
