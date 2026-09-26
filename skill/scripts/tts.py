#!/usr/bin/env python3
"""tts.py — 朗读引擎「阿林娜（alina）」开关与挂钩（合成后端 tts_say.py）：开关单一真源＝settings tts.enabled（:tts on|off 直接写配置——修复旧 shell/tts.state 运行时文件与配置文件双源不一致：文件一旦为 off，配置开 true 也永远无声）。模型输出经 agent_stream 调 hook() 逐句读出：msg_flow JSON 信封行只朗读其 text 字段；步骤/命令/提示回显（$ ▸ ⧉ ≡ 注意： 拒绝： 网关错误 sms> •）不朗读；markdown 符号/URL 剥净；长段按句切 ≤tts.max_chars 连续朗读；⧉技能▸ 前缀剥后朗读子会话正文。用法：python -B tts.py say "<文本>" | test | on | off | toggle | status | voices。"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import resolve_home, settings, chains, msg_flow, tts_say
SMS = resolve_home.ensure()
NAME = lambda: settings.get("tts.profile_name", "阿林娜")
CAP = lambda: max(60, int(settings.get("tts.max_chars", 400)))
def on(): return bool(settings.get("tts.enabled", False))
def set_on(v):
    settings.set("tts.enabled", bool(v)); v or tts_say.stop()
    return NAME() + "：" + ("开" if v else "关") + "（写配置 tts.enabled·即时生效·关即清队列）"
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
    return json.dumps({"profile": NAME() + "（alina）", "engine": "SAPI5", "on": on(),
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
