# sms_shell.ps1 — sms-shell 原生入口：完全在系统 shell 里运行（cmd→PowerShell），DOS 程序风格 TUI，壳本体零 python；仅 :托管引擎 命令把 python 脚本当外部程序调用
param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Rest)
$ErrorActionPreference = 'Continue'
foreach ($f in @('sms_state', 'sms_dos', 'sms_gw', 'sms_route')) { . (Join-Path $PSScriptRoot ($f + '.ps1')) }
$null = SMS_WTmp
$script:IMG = $null
$sink = { param($t) Write-Host -NoNewline $t }
Import-Module PSReadLine -ErrorAction SilentlyContinue
$HAS_PSL = [bool](Get-Module PSReadLine)
$script:RLERR = ''
function Read-Line {
  if ($HAS_PSL) { try { return [Microsoft.PowerShell.PSConsoleReadLine]::ReadLine('') } catch { $script:RLERR = 'PSReadLine: ' + $_.Exception.Message } }
  if ([Console]::IsInputRedirected) { return [Console]::ReadLine() }
  try { $l = (Read-Host ''); return $l } catch { $script:RLERR = 'Read-Host: ' + $_.Exception.Message; return $null }
}
$pos = @($Rest | Where-Object { $_ -and $_ -notlike '--*' })
$flags = @($Rest | Where-Object { $_ -and $_ -like '--*' })
if ($flags -contains '--gui' -or $flags -contains '--tui') { Run-Engine 'shell.py' $pos; ChainsGit; exit $LASTEXITCODE }
if ($pos.Count -gt 0) {
  if ($pos[0].ToLower() -eq 'api') { Run-Engine 'api.py' @($pos | Select-Object -Skip 1); exit $LASTEXITCODE }
  Handle-Line ($pos -join ' ') $sink | Out-Null; ChainsGit; exit 0
}
Init-Dos; Show-Banner
$nulls = 0
try {
  while ($true) {
    Write-Host -ForegroundColor White 'sms>' -NoNewline; Write-Host ' ' -NoNewline
    $line = Read-Line
    if ($null -eq $line) {
      if ($nulls -ge 1 -and -not [Console]::IsInputRedirected) { Write-Host ''; Write-Dim ('输入通道结束（' + $script:RLERR + '）·退出；可改用 Read-Host 模式或重开窗口'); break }
      $nulls++; if ([Console]::IsInputRedirected) { Write-Host ''; break } else { continue }
    }
    $nulls = 0
    if (-not $line.Trim()) { continue }
    if ((Handle-Line $line $sink) -eq 'exit') { break }
  }
} finally { ChainsGit; Exit-Dos; Write-Host 'SMS-SHELL 退出（对话链已收口·chains 已 git 提交）' -ForegroundColor DarkGray }
