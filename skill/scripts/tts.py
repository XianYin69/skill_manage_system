#!/usr/bin/env python3
"""tts.py — 朗读引擎「阿林娜（alina）」开关与挂钩（合成后端 tts_say.py）：模型输出经 agent_stream 调 hook() 逐句读出——2026-09-26 修复（用户「修复TTS阅读问题」）：msg_flow JSON 信封行只朗读其 text 字段；步骤/命令/提示回显（$ ▸ ⧉ ≡ 注意： 拒绝： 网关错误 sms> •）不朗读；markdown 符号/URL 剥净；长段按句切 ≤tts.max_chars 连续朗读（旧版整段截 400 字致只读半句）；⧉技能▸ 前缀剥后朗读子会话正文；here-string 定界独立成行防文本含 '@ 崩溃。运行时开关只存 <SMS_HOME>/shell/tts.state，默认关闭；持久默认经 settings tts.enabled。用法：python -B tts.py say "<文本>" | test | on | off | toggle | status | voices。"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import resolve_home, settings, chains, msg_flow, tts_say
SMS = resolve_home.ensure(); ST = os.path.join(SMS, "shell", "tts.state")
NAME = lambda: settings.get("tts.profile_name", "阿林娜")
CAP = lambda: max(60, int(settings.get("tts.max_chars", 400)))
def on(): return os.path.isfile(ST) and open(ST).read().strip() == "on" or bool(settings.get("tts.enabled", False)) and not os.path.isfile(ST)
def set_on(v): os.makedirs(os.path.dirname(ST), exist_ok=True); open(ST, "w").write("on" if v else "off"); return NAME() + "：" + ("开" if v else "关")
def speak(text, wait=False): return tts_say.speak(tts_say.clean(text), wait)
def voices(): return tts_say.voices()
def hook(on_line):
    if not on(): return on_line
    def w(ln):
        on_line(ln); s = str(ln).strip()
        if not s or s.startswith(("注意：", "拒绝：", "网关错误", "!", "•")): return
        e = msg_flow.parse(s)
        if e: s = str(e.get("text") or "")
        if e is None and s.startswith("⧉"): s = s.split("▸", 1)[-1]
        t = tts_say.clean(s)
        if t and not t.startswith(("$", "▸", "sms>", "≡")):
            for ch in tts_say.chunks(t, CAP()): tts_say.speak(ch)
    return w
def status():
    return json.dumps({"profile": NAME() + "（alina）", "engine": "SAPI5", "runtime_on": os.path.isfile(ST), "effective_on": on(),
                       "voice": settings.get("tts.voice", ""), "rate_pct": int(float(settings.get("tts.rate", -1)) * 10), "pitch": settings.get("tts.pitch", "+0st"), "volume_pct": int(settings.get("tts.volume", 100)), "max_chars": CAP(), "gender": "female-mechanical", "platform": "windows"}, ensure_ascii=False)
if __name__ == "__main__":
    a = sys.argv[1:] or ["status"]; c = a[0]
    if c == "say" and len(a) > 1: print(speak(" ".join(a[1:]), True))
    elif c == "test": print(speak("你好，我是" + NAME() + "，很高兴为你朗读。", True))
    elif c == "voices": print(voices())
    elif c == "on": print(set_on(True))
    elif c == "off": print(set_on(False))
    elif c == "toggle": print(set_on(not on()))
    else: chains.log("tool", "tts:status"); print(status())
