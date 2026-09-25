# shell_tests.ps1 — sms-shell 原生入口冒烟测试：确定性路由（零模型）逐断言 · 托管引擎透传 · 可选活网关话语（-Offline 跳过）；结果写 UTF-8 报告
param([switch]$Offline, [switch]$SkipEngine)
$ErrorActionPreference = 'Continue'
$root = Split-Path (Split-Path $PSScriptRoot)
$bin = Join-Path $root 'bin\sms-shell.cmd'
$rep = Join-Path $root 'tmp\shell_tests_report.txt'
$fail = 0; $lines = @()
function RunOne([string[]]$argvs) { (& $bin @argvs 2>&1 | Out-String) }
function T([string]$desc, [string[]]$argvs, [string[]]$expects) {
  $out = RunOne $argvs
  $miss = @($expects | Where-Object { $out -notlike ('*' + $_ + '*') })
  if ($miss.Count -eq 0) { $script:lines += ('PASS ' + $desc) } else { $script:fail++; $e = ($out -replace '\s+', ' '); if ($e.Length -gt 260) { $e = $e.Substring(0, 260) }; $script:lines += ('FAIL ' + $desc + ' 缺[' + ($miss -join ';') + '] 实际: ' + $e) }
}
T '裸 help＝内置元指令表' @('help') @('元指令', '单发执行即退')
T '裸 ?＝内置' @('?') @('元指令')
T ':help 单发' @(':help') @(':config', ':quit')
T '前缀剥离＋meta' @('sms_shell :config get llm_gateway.model') @('auto')
T 'sms-shell 单词＝帮助' @('sms-shell') @('元指令')
T '裸 config＝网关摘要' @('config') @('base_url', 'api_key=')
T '裸 状态＝网关摘要' @('状态') @('enabled=')
T '打开sms shell设置＝确定性路由' @('打开sms shell设置') @('元指令')
$show = RunOne @(':config show')
if (($show -like '*"***"*') -and ($show -notmatch 'freellmapi-a923')) { $lines += 'PASS api_key 恒掩码（show 不出真实值）' } else { $fail++; $lines += 'FAIL api_key 掩码' }
T '未知元指令报错不崩' @(':nosuch') @('未知元指令')
T ':agents 治理原生' @(':agents') @('检出', 'gateway')
if (-not $SkipEngine) { T '托管引擎透传 :cmds' @(':cmds') @('shell') }
if (-not $Offline) {
  $t2 = RunOne @('用中文只回复两个字：收到')
  $ok2 = ($t2.Trim().Length -ge 2) -and ($t2 -notmatch '网关错误|拒绝：|无法连接')
  if ($ok2) { $lines += ('PASS 活网关流式回复: ' + ($t2 -replace '\s+', ' ').Trim()) } else { $fail++; $t3 = ($t2 -replace '\s+', ' '); if ($t3.Length -gt 260) { $t3 = $t3.Substring(0, 260) }; $lines += ('FAIL 活网关: ' + $t3) }
}
$lines += ('TOTAL fail=' + $fail)
[IO.File]::WriteAllLines($rep, [string[]]$lines, (New-Object Text.UTF8Encoding $true))
exit $fail
