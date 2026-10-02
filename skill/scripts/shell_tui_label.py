#!/usr/bin/env python3
"""shell_tui_label.py — 配置项简写与注释（供 shell_tui_config 列表行与过滤）：简写＝ALI 别名表逐段缩写（未收录段原样）；注释＝沿 settings.DEFAULTS 就近段的 comment 字段（技能列表段回落 skills_config.DEFAULT），截 46 字；label(p)＝「简写｜注释」，search(p)＝路径＋简写＋注释小写串（输入字母数字可命中简写/注释词）。"""
import settings, skills_config
ALI = {"llm_gateway": "网关", "model_meta": "元数据", "chains": "链", "dream": "做梦", "web_shell": "网页壳", "external": "对外", "ff_lite": "FF内核", "tts": "朗读",
       "scan_roots": "扫描根", "skill_generator": "SG源", "sync_clients": "同步", "Source_Remote": "远程源", "permissions_default": "默认权限", "index_items": "索引项",
       "enabled": "启用", "disable": "禁用", "base_url": "地址", "api_key": "密钥", "api_key_env": "密钥env", "model": "模型", "max_tokens": "上限", "timeout": "超时", "timeout_s": "超时秒",
       "temperature": "温度", "top_p": "topP", "interval_min": "间隔分", "refresh_interval_min": "刷新分", "auto_refresh": "自刷新", "host": "主机", "port": "端口", "interface": "网卡",
       "pq_mode": "PQ模式", "session_ttl_min": "会话分", "max_fail_per_min": "封禁阈", "engine": "引擎", "profile_name": "名", "voice": "音色", "rate": "语速", "pitch": "音高", "volume": "音量",
       "max_chars": "字数限", "max_page_chars": "页字限", "max_download_mb": "下载限M", "download_dir": "下载目录", "headless": "无头", "defaults": "默认", "context_length": "上下文",
       "max_output_tokens": "输出限", "rpm": "RPM", "default": "默认", "merge_thr": "合并阈", "prune_days": "修剪天", "min_freq": "最小频", "comment": "注释", "sms_home": "数据根", "agent_cli": "CLI", "sms_skill": "回源", "repo": "仓库", "install_syntax": "装法",
         "debug": "调试", "path": "输出路径", "ui": "界面", "mode": "模式", "sms_workspace": "工作区", "workspaces": "工作区清单", "next_run": "下次做梦", "tmp": "临时", "tasks": "任务",
          "caps": "上限", "gateway_rounds": "工具轮", "skill_rounds": "派技轮", "ask_rounds": "子问答轮",
          "task": "任务表", "auto_table": "自动建表", "auto_continue": "主流程守卫", "max_continue": "续推上限", "max_parallel": "并发上限", "solo": "SOLO自审", "allow_danger": "自审放行danger", "auto_pending": "待批自动同意", "never": "永不自审", "ttl_min": "授予分", "max_ttl_min": "授予分上限", "review_max_tokens": "自审字限", "analyze_retry": "错误先分析", "max_same_error": "同错上限", "retry_backoff_cap": "退避封顶秒", "analyze_max_tokens": "分析字限", "notify": "放行告知", "granted_today": "今日已放行"}
def _walk_comment(p):
    node = settings.DEFAULTS; c = ""
    for k in p.split("."):
        node = node.get(k) if isinstance(node, dict) else None
        if not isinstance(node, dict): break
        if node.get("comment"): c = node["comment"]
    if not c and p.split(".")[0] in skills_config.SKILL_KEYS and skills_config.DEFAULT.get("comment"): c = skills_config.DEFAULT["comment"]
    return c
def short(p): return "·".join(ALI.get(x, x) for x in p.split("."))
SECT = ["solo", "llm_gateway", "model_meta", "chains", "dream", "tts", "debug", "ui", "hud", "sms_workspace", "workspaces", "web_shell", "external", "ff_lite", "agent_tools", "scan_roots", "skill_generator", "sync_clients", "Source_Remote", "permissions_default"]
def order(keys): return [s for s in SECT if s in keys] + sorted(k for k in keys if k not in SECT)
def label(p):
    c = _walk_comment(p); return short(p) + ("｜" + c[:24] if c else "")
def search(p): return (p + " " + label(p)).lower()
