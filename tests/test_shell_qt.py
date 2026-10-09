#!/usr/bin/env python3
"""tests/test_shell_qt.py — PyQt6 图形壳（shell_qt.py）离线回归：文件在场＋零裸子进程＋入口 --qt 接线＋
行分类与上色纯函数口径（不建 QApplication·不连模型网关）。跑法：pytest tests/test_shell_qt.py -q"""
import os
import re
import sys
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = os.path.join(ROOT, "skill", "scripts")
sys.path.insert(0, S)
QT = os.path.join(S, "shell_qt.py")


def _src():
    assert os.path.isfile(QT), "缺 shell_qt.py（PyQt6 图形壳）"
    return open(QT, encoding="utf-8").read()


def test_qt_shell_present_and_quiet():
    src = _src()
    import no_window_audit as aud
    assert aud.hits(src, "shell_qt.py") == [], "GUI 内不得有裸 subprocess/os.system（闪黑框根因）"
    assert "# sms-visible" in src, "GUI 另起 TUI 的可见控制台点必须带标记"


def test_entry_wired_qt_flag():
    sh = open(os.path.join(S, "shell.py"), encoding="utf-8").read()
    assert '--qt' in sh and 'launch("qt")' in sh, "入口须支持 --qt 起 PyQt6 图形壳"
    assert os.path.isfile(os.path.join(S, "shell_tui_textual.py"))
    lc = open(os.path.join(S, "shell_lifecycle.py"), encoding="utf-8").read()
    assert "shell_qt.py" in lc, "壳生命周期回收清单须含 shell_qt.py"


def test_scripts_locator_and_routing():
    src = _src()
    assert "def _scripts()" in src, "GUI 需三级找回壳脚本目录（换目录部署可跑）"
    for call in ("core.handle(", "msg_flow.visible(", "detail_bus.tail(", "stop.bind("):
        assert call in src, "GUI 必须复用壳路由/明细口径/并行隔离：" + call


def test_line_classification_deterministic():
    """不起 QApplication：只测 paint/visible 的纯函数口径（与 Textual split 一致）。"""
    import msg_flow
    assert msg_flow.visible("$ exec ls") is False, "工具行不得进主输出"
    assert msg_flow.visible("这是正文回答") is True
    assert msg_flow.visible("◌ 思考片段") is False
    assert msg_flow.blank("⧉general_answer▸   ") is True


def test_probe_hook_exists():
    src = _src()
    assert "--probe=" in src and "probe_finish" in src, "需保留 --probe 端到端回归钩子"
