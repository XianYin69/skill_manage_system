#!/usr/bin/env python3
"""tts_say.py — 阿林娜（alina）SAPI5 合成后端（被 tts.py 引用·文本不出本机）：voices 枚举系统语音；speak 逐段 PowerShell Add-Type System.Speech 播报（SSML rate/pitch/volume 由 settings 取值·here-string 定界独立成行防 '@ 文本崩溃·wait 模式供 CLI）；clean 去 markdown/控制前缀（** ` # 链接 URL $ ▸ ⧉ ≡ sms> 等）；chunks 按句切 ≤cap 段（修复旧版整段截 400 字朗读不完整与噪音符号）。"""
import os, sys, re, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import settings
_MD = re.compile(r"\$[^\s]*|▸|⧉|≡|sms>|●|◀|\*\*|__|`{1,3}|~~|#{1,6}\s+|\((?=[^\)]*https?://)|https?://\S+|!\[[^\]]*\]|\[[^\]]*\]\([^)]*\)|\[\d+\]")
def clean(s): return re.sub(r"\s+", " ", _MD.sub(" ", str(s))).strip()
def chunks(s, cap):
    out, buf = [], ""
    for sent in re.split(r"(?<=[。！？；!?;\n])", str(s)):
        buf += sent
        if len(buf) >= cap: out.append(buf.strip()); buf = ""
    return out + ([buf.strip()] if buf.strip() else [])
def voices():
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command",
              "Add-Type -AssemblyName System.Speech;(New-Object System.Speech.Synthesis.SpeechSynthesizer).GetInstalledVoices()|ForEach-Object{$_.VoiceInfo.Name}"],
              capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
        return "\n".join(x for x in (r.stdout or "").splitlines() if x.strip()) or (r.stderr or "无")
    except Exception as e: return "ERR 枚举语音失败：" + str(e)[:150]
def _ssml(text):
    t = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return "<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis'><prosody rate='%s%%' pitch='%s' volume='%s%%'>%s</prosody></speak>" % (int(float(settings.get("tts.rate", -1)) * 10), settings.get("tts.pitch", "+0st"), int(settings.get("tts.volume", 100)), t)
def speak(text, wait=False):
    if not (text or "").strip(): return ""
    cmd = "\n".join(["Add-Type -AssemblyName System.Speech", "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer",
        "try{$s.SelectVoice('%s')}catch{}" % settings.get("tts.voice", "Microsoft Huihui Desktop - Chinese (China)").replace("'", "''"),
        "$x=@'", _ssml(text[:600]), "'@;$s.SpeakSsml($x)"])
    try:
        p = subprocess.Popen(["powershell", "-NoProfile", "-Command", cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if wait: p.wait(timeout=120)
        return p.pid if not wait else "done"
    except Exception as e: return "ERR 朗读失败：" + str(e)[:150]
