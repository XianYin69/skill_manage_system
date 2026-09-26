param([switch]$Offline, [switch]$SkipEngine); $ErrorActionPreference = 'Continue'
$root = Split-Path (Split-Path $PSScriptRoot); $bin = Join-Path $root 'bin\sms-shell.cmd'
$rep = Join-Path $root 'tmp\shell_tests_report.txt'; $fail = 0; $lines = @()
function RunOne([string[]]$argvs) { (& $bin @argvs 2>&1 | Out-String) }
function T([string]$desc, [string[]]$argvs, [string[]]$expects) {
  $out = RunOne $argvs
   $miss = @($expects | Where-Object { $out.IndexOf($_, [System.StringComparison]::Ordinal) -lt 0 })
  if ($miss.Count -eq 0) { $script:lines += ('PASS ' + $desc) } else { $script:fail++; $e = ($out -replace '\s+', ' '); if ($e.Length -gt 260) { $e = $e.Substring(0, 260) }; $script:lines += ('FAIL ' + $desc + ' 缺[' + ($miss -join ';') + '] 实际: ' + $e) }
}
T '裸 help＝内置速查表（精简）' @('help') @('元指令', '全量命令表')
T '裸 ?＝内置' @('?') @('元指令')
T ':help 单发' @(':help') @(':config', ':quit', ':dispatch', ':sh', ':mode')
T '前缀剥离＋meta' @('sms_shell :config get llm_gateway.model') @('auto')
T 'sms-shell 单词＝帮助' @('sms-shell') @('元指令')
T '裸 config＝网关摘要' @('config') @('base_url', 'api_key=')
T '裸 状态＝网关摘要' @('状态') @('enabled=')
T '打开sms shell设置＝确定性路由短指引' @('打开sms shell设置') @('确定性路由')
T '裸 config get <dot.path>＝零模型读配置' @('config get llm_gateway.model') @('auto')
T '裸 技能列表＝托管技能清单' @('技能列表') @('可调用托管技能')
T '裸 哪些skill＝技能清单路由' @('你现在可以调用那些skill') @('可调用托管技能')
T ':skills 元指令＝托管技能清单' @(':skills') @('可调用托管技能')
T ':index 无参＝scan_roots 清单' @(':index') @('[')
T 'config get scan_roots＝技能根经统一视图' @('config get scan_roots') @('.kilocode')
$wsd = Join-Path $env:TEMP ('sms_ws_' + (Get-Random)); New-Item -ItemType Directory -Force -Path $wsd | Out-Null
T ':workspace switch＝真实工作区自动建 tmp' @(':workspace', 'switch', $wsd) @('已切换工作区', 'tmp')
T ':workspace tmp＝真实工作区下 tmp 绝对路径' @(':workspace', 'tmp') @((Join-Path $wsd 'tmp'))
T ':workspace use-virtual＝回退虚拟' @(':workspace', 'use-virtual') @('虚拟')
T ':workspace tmp＝虚拟工作区下 tmp 亦自动建' @(':workspace', 'tmp') @('tmp')
T ':workspace review＝tmp 待审清单（经引擎路由）' @(':workspace', 'review') @('待审')
T ':workspace release 缺参＝拒绝或预览不写盘' @(':workspace', 'release', 'no_such_file.xyz') @('拒绝')
$show = RunOne @(':config show')
if (($show.IndexOf('"***"', [System.StringComparison]::Ordinal) -ge 0) -and ($show -notmatch 'freellmapi-a923')) { $lines += 'PASS api_key 恒掩码（show 不出真实值）' } else { $fail++; $lines += 'FAIL api_key 掩码' }
T '未知元指令报错不崩' @(':nosuch') @('未知元指令')
T ':agents 治理原生' @(':agents') @('检出', 'gateway')
T ':sh list＝系统 shell 检出' @(':sh', 'list') @('可检出系统 shell')
T ':session current＝会话层' @(':session', 'current') @('sess-')
T ':debug off 治理' @(':debug', 'off') @('关')
T ':mode status 界面模式查询' @(':mode', 'status') @('模式')
if (-not $SkipEngine) { T '托管引擎透传 :cmds' @(':cmds') @('shell') }
if (-not $Offline) {
  $t2 = RunOne @('用中文只回复两个字：收到')
  $ok2 = ($t2.Trim().Length -ge 2) -and ($t2 -notmatch '网关错误|拒绝：|未检出 agent')
  if ($ok2) { $lines += ('PASS 活网关流式回复: ' + ($t2 -replace '\s+', ' ').Trim()) } else { $fail++; $t3 = ($t2 -replace '\s+', ' '); if ($t3.Length -gt 260) { $t3 = $t3.Substring(0, 260) }; $lines += ('FAIL 活网关: ' + $t3) }
  $t4 = RunOne @(':session', 'new', 'ps1冒烟')
  if ($t4 -match 'sess-') { $lines += 'PASS :session new 会话层单发' } else { $fail++; $lines += ('FAIL :session new: ' + ($t4 -replace '\s+', ' ').Trim()) }
  RunOne @(':session', 'use', ($t4 -replace '[^a-zA-Z0-9\-]', ' ' ).Trim().Split(' ')[-1]) | Out-Null
}
$lines += ('TOTAL fail=' + $fail)
[IO.File]::WriteAllLines($rep, [string[]]$lines, (New-Object Text.UTF8Encoding $true))
exit $fail
