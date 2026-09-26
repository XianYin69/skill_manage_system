# sms_state.ps1 — 原生状态层（零 python）：SMS_HOME 解析 · 配置读写（api_key 恒掩码）· 壳状态文件（与 python 侧同格式）· 工作区/临时目录解析 · 个性化指令查找；链碎片与压缩记忆尾见 sms_chain.ps1
function SMS_HOME {
  if ($env:SMS_HOME) { return $env:SMS_HOME }
  $h = if ($env:HOME) { $env:HOME } else { $env:USERPROFILE }
  $c = if ($env:OS -eq 'Windows_NT') { $env:LOCALAPPDATA } elseif (Test-Path "$h/Library/Caches") { "$h/Library/Caches" } else { "$h/.cache" }
  foreach ($p in @("$c\SMS", "$h\SMS")) { if (Test-Path (Join-Path (Join-Path $p 'config') 'config.json')) { return $p } }
  Join-Path $c 'SMS'
}
$SMS = SMS_HOME
function Read-CfgDoc { $p = Join-Path (Join-Path $SMS 'config') 'config.json'; if (Test-Path $p) { (Get-Content $p -Raw -Encoding UTF8) | ConvertFrom-Json } else { $null } }
function Cfg($sec) { $d = Read-CfgDoc; if ($d -and $d.$sec) { return $d.$sec }
  if ($sec -eq 'llm_gateway') { return [pscustomobject]@{ enabled = $false; base_url = ''; model = 'auto'; max_tokens = 1024; timeout = 120 } }
  if ($sec -eq 'agent_cli') { return [pscustomobject]@{} }
  $null }
function CfgGet($path, $default) { if ($path -isnot [string]) { $path = [string]$path }; if (-not $path) { return $default }; $o = Read-CfgDoc; foreach ($k in $path.Split('.')) { if ($null -eq $o) { return $default }; $o = $o.$k }; if ($null -eq $o) { $default } else { $o } }
function ParseVal($s) { if ($s -match '^(true|false|null)$') { if ($s -eq 'true') { return $true } elseif ($s -eq 'false') { return $false } else { return $null } }
  $v = $null; try { $v = $s | ConvertFrom-Json } catch { $v = ($s -replace '^["\x27]|["\x27]$', '') }; $v }
function CfgSet($path, $json) {
  $p = Join-Path (Join-Path $SMS 'config') 'config.json'; New-Item -ItemType Directory -Force -Path (Split-Path $p) | Out-Null
  $doc = if (Test-Path $p) { (Get-Content $p -Raw -Encoding UTF8) | ConvertFrom-Json } else { [pscustomobject]@{} }
  $o = $doc; $ks = $path.Split('.'); foreach ($k in $ks[0..($ks.Length - 2)]) { if (-not $o.PSObject.Properties[$k]) { $o | Add-Member NoteProperty $k ([pscustomobject]@{}) -Force }; $o = $o.$k }
  $o | Add-Member NoteProperty $ks[-1] (ParseVal $json) -Force
  [IO.File]::WriteAllText($p, ($doc | ConvertTo-Json -Depth 20), (New-Object Text.UTF8Encoding $false))
  Record 'event' ('config set ' + $path + ' (sms-shell native)')
}
function MaskJson($o) { ($o | ConvertTo-Json -Depth 20) -replace '("api_key"\s*:\s*)"[^"]*"', '$1"***"' }
function StateFile($n) { $d = Join-Path $SMS 'shell'; New-Item -ItemType Directory -Force -Path $d | Out-Null; Join-Path $d $n }
function StateGet($n, $d) { $p = StateFile $n; if (Test-Path $p) { (Get-Content $p -Raw -Encoding UTF8).Trim() } else { $d } }
function SMS_WS { $w = if ($env:SMS_WORKSPACE) { $env:SMS_WORKSPACE } else { [string](CfgGet 'sms_workspace' '') }; if ($w -and (Test-Path $w)) { return [string](Resolve-Path $w) }; Join-Path (Join-Path $SMS 'workspaces') '_virtual' }
function SMS_WTmp { $d = Join-Path (SMS_WS) 'tmp'; New-Item -ItemType Directory -Force -Path $d | Out-Null; $env:SMS_TMP = $d; $d }
function StatePut($n, $v) { [IO.File]::WriteAllText((StateFile $n), $v) }
function AliasFind($name) { $p = Join-Path (Join-Path $SMS 'commands') 'user_commands.json'; if (-not (Test-Path $p)) { return $null }
  @((Get-Content $p -Raw -Encoding UTF8 | ConvertFrom-Json).commands) | Where-Object { $_.name -eq $name } | Select-Object -First 1 }
