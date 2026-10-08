#!/usr/bin/env python3
"""tests/test_lifecycle_allow.py — 批33 回归：常驻宿主（allow=True）必须真执行，不得把请求退回重登记。

复现的用户原话：「子代理请求重启测试功能时不会重启」。旧缺陷两处：
① restart/shutdown 内部无条件 `if not _is_shell(): return request(...)`——
   run_pending 已判定 allow 宿主可以代执行，调进去却又被退回登记，请求被壳消费后
   立刻重生成＝永远原地打转，谁都不执行；
② 退回时漏传 sms（`request("restart", why)`）——临时/镜像 home 里的测试请求
   被写进真实 <SMS_HOME>/shell/lifecycle.json，真壳下一轮收口就真重启（实测踩过）。
两条都在这里钉死。跑法：pytest tests -q。
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = os.path.join(ROOT, "skill", "scripts")
sys.path.insert(0, S)

import close_guard as cg          # noqa: E402
import shell_lifecycle as lc      # noqa: E402


def _home(tmp_path):
    h = os.path.join(str(tmp_path), "sms")
    os.makedirs(os.path.join(h, "shell"), exist_ok=True)
    return h


def _isolate(monkeypatch):
    """绝不真开窗、绝不真杀进程：spawn/reclaim/通报全桩掉。"""
    monkeypatch.setattr(lc, "reclaim", lambda *a, **k: ([], []))
    monkeypatch.setattr(lc, "_bye", lambda s, t: None)
    monkeypatch.setattr(cg, "push", lambda t: None)
    monkeypatch.setattr(lc, "BIN", os.path.join(str(os.getcwd()), "__no_such_launcher__.py"))
    # 批34：模拟失败的请求绝不可经 _note→chain_error 落进真实 <SMS_HOME> 的 error 链
    # （否则每跑一次 pytest 就多一条「启动器缺失 __no_such_launcher__.py」，做梦把它当生产故障反复登记）
    monkeypatch.setattr(lc, "_note", lambda e, src: None)


def test_allow_host_performs_instead_of_bouncing(monkeypatch, tmp_path):
    home = _home(tmp_path)
    _isolate(monkeypatch)
    spawned = []
    monkeypatch.setattr(lc, "_spawn",
                        lambda sms: (spawned.append(1) or ("已拉起新实例 pid=FAKE(1)", 1)))
    cg.request("restart", "常驻宿主代执行", home)
    out = lc.run_pending(sms=home, allow=True, hard=False)
    assert spawned, "allow 宿主没有执行＝请求仍被退回登记（批33 缺陷①）"
    assert not os.path.exists(cg._f(home)), "执行成功后请求文件必须被消费"
    assert "FAKE" in str(out), out


def test_failed_perform_keeps_the_request(monkeypatch, tmp_path):
    """执行失败（启动器缺失）＝退回登记而不是静默丢失——下次收口还会重试。"""
    home = _home(tmp_path)
    _isolate(monkeypatch)
    cg.request("restart", "启动器缺失场景", home)
    out = lc.run_pending(sms=home, allow=True, hard=False)
    assert "启动器缺失" in str(out) and "退回登记" in str(out), out
    assert os.path.exists(cg._f(home)), "失败即丢请求＝用户再也等不到重启"


def test_non_shell_without_allow_defers_and_never_touches_real_home(monkeypatch, tmp_path):
    home = _home(tmp_path)
    _isolate(monkeypatch)
    real = cg._f()                       # 真实 <SMS_HOME>/shell/lifecycle.json
    had = os.path.exists(real)
    cg.request("restart", "只登记不执行", home)
    out = lc.run_pending(sms=home, allow=False)
    assert "待壳执行" in str(out), out
    assert os.path.exists(cg._f(home)), "非壳宿主不得删除请求文件"
    assert os.path.exists(real) == had, "非壳路径把请求写进了真实 SMS_HOME（批33 缺陷②）"


def test_request_forwards_sms_home(monkeypatch, tmp_path):
    """restart()/shutdown() 在纯登记模式下必须把 sms 透传给 request()。"""
    home = _home(tmp_path)
    _isolate(monkeypatch)
    seen = {}
    monkeypatch.setattr(lc, "_is_shell", lambda: False)
    monkeypatch.setattr(lc, "request",
                        lambda a, w="", s=None: seen.update(a=a, s=s) or "已登记")
    lc.restart(sms=home, why="x")
    assert seen.get("s") == home, "restart 未透传 sms＝镜像测试会污染真实壳（缺陷②）"
    seen.clear()
    lc.shutdown(sms=home, why="y")
    assert seen.get("s") == home, "shutdown 未透传 sms"
