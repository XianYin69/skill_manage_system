#!/usr/bin/env python3
"""tts.py — 朗读引擎「阿林娜（alina）」：Windows SAPI5 机械女声（导航/屏幕阅读器腔，平调·可配语速音高），文本不出本机；模型输出经 agent_stream 调 hook() 逐句读出。运行时开关只存 <SMS_HOME>/shell/tts.state，默认关闭；持久默认经 settings tts.enabled。用法：python -B tts.py say "<文本>" | test | on | off | toggle | status | voices。"""
import os, sys, json, subprocess, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import resolve_home, settings, chains
SMS = resolve_home.ensure(); ST = os.path.join(SMS, "shell", "tts.state")
V = lambda: settings.get("tts.voice", "Microsoft Huihui Desktop - Chinese (China)")
RATE = lambda: float(settings.get("tts.rate", -1))
PITCH = lambda: settings.get("tts.pitch", "+0st")
NAME = lambda: settings.get("tts.profile_name", "阿林娜")
VOL = lambda: int(settings.get("tts.volume", 100))
def on(): return os.path.isfile(ST) and open(ST).read().strip() == "on" or bool(settings.get("tts.enabled", False)) and not os.path.isfile(ST)
def set_on(v): os.makedirs(os.path.dirname(ST), exist_ok=True); open(ST, "w").write("on" if v else "off"); return NAME() + "：" + ("开" if v else "关")
def voices():
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command",
              "Add-Type -AssemblyName System.Speech;(New-Object System.Speech.Synthesis.SpeechSynthesizer).GetInstalledVoices()|ForEach-Object{$_.VoiceInfo.Name}"],
              capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
        return "\n".join(x for x in (r.stdout or "").splitlines() if x.strip()) or (r.stderr or "无")
    except Exception as e: return "ERR 枚举语音失败：" + str(e)[:150]
def _ssml(text):
    t = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return "<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis'><prosody rate='%s%%' pitch='%s' volume='%s%%'>%s</prosody></speak>" % (int(RATE() * 10), PITCH(), VOL(), t)
def speak(text, wait=False):
    if not text or not text.strip(): return ""
    cmd = "Add-Type -AssemblyName System.Speech;$s=New-Object System.Speech.Synthesis.SpeechSynthesizer;try{$s.SelectVoice('%s')}catch{};$x=@'%s'@;$s.SpeakSsml($x)" % (V().replace("'", "''"), _ssml(text[:400]))
    try:
        p = subprocess.Popen(["powershell", "-NoProfile", "-Command", cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if wait: p.wait(timeout=120)
        return p.pid if not wait else "done"
    except Exception as e: return "ERR 朗读失败：" + str(e)[:150]
def hook(on_line):
    if not on(): return on_line
    def w(ln):
        on_line(ln)
        s = str(ln).strip()
        if s and not s.startswith(("$", "注意：", "拒绝：", "网关错误")): speak(s)
    return w
def status():
    return json.dumps({"profile": NAME() + "（alina）", "engine": "SAPI5", "runtime_on": os.path.isfile(ST), "effective_on": on(),
                       "voice": V(), "rate_pct": int(RATE() * 10), "pitch": PITCH(), "volume_pct": VOL(), "gender": "female-mechanical", "platform": "windows"}, ensure_ascii=False)
if __name__ == "__main__":
    a = sys.argv[1:] or ["status"]; c = a[0]
    if c == "say" and len(a) > 1: print(speak(" ".join(a[1:]), True))
    elif c == "test": print(speak("你好，我是" + NAME() + "，很高兴为你朗读。", True))
    elif c == "voices": print(voices())
    elif c == "on": print(set_on(True))
    elif c == "off": print(set_on(False))
    elif c == "toggle": print(set_on(not on()))
    else: chains.log("tool", "tts:status"); print(status())
