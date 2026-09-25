# sms_state.ps1 — 原生状态层（零 python）：SMS_HOME 解析 · 配置读写（api_key 恒掩码）· 壳状态文件（与 python 侧同格式）· 个性化指令查找 · 十一链碎片原生写入（chain_store 兼容 schema）＋git 管理 · 压缩记忆尾
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
function StatePut($n, $v) { [IO.File]::WriteAllText((StateFile $n), $v) }
function AliasFind($name) { $p = Join-Path (Join-Path $SMS 'commands') 'user_commands.json'; if (-not (Test-Path $p)) { return $null }
  @((Get-Content $p -Raw -Encoding UTF8 | ConvertFrom-Json).commands) | Where-Object { $_.name -eq $name } | Select-Object -First 1 }
function FragVec($t) {
  $s = $t.ToLower(); $toks = @([regex]::Matches($s, '[a-z0-9]+') | ForEach-Object { $_.Value })
  foreach ($run in [regex]::Matches($s, '[\u4e00-\u9fff][\u4e00-\u9fff]+') | ForEach-Object { $_.Value }) { for ($i = 0; $i -lt $run.Length - 1; $i++) { $toks += [string]$run[$i] + [string]$run[$i + 1] } }
  $v = New-Object 'double[]' 64; $md5 = [Security.Cryptography.MD5]::Create()
  foreach ($x in ($toks | Select-Object -Unique)) { $hx = [BitConverter]::ToString($md5.ComputeHash([Text.Encoding]::UTF8.GetBytes($x)), 0, 4) -replace '-'; $v[[int]([Convert]::ToUInt32($hx, 16) % 64)] += 1 }
  $sq = 0.0; foreach ($x in $v) { $sq += $x * $x }; $n = [Math]::Sqrt($sq); if ($n -gt 0) { $v = @($v | ForEach-Object { [Math]::Round($_ / $n, 4) }) }
  $v
}
function Record($chain, $text) {
  try {
    if ((CfgGet ('chains.' + $chain + '.enabled') $true) -eq $false) { return }
    $md5 = [Security.Cryptography.MD5]::Create()
    $id = ((-join ($md5.ComputeHash([Text.Encoding]::UTF8.GetBytes($chain + $text + (Get-Date -UFormat %s))) | ForEach-Object { $_.ToString('x2') }))).Substring(0, 10)
    $dir = Join-Path (Join-Path $SMS 'chains') $chain; New-Item -ItemType Directory -Force -Path $dir | Out-Null
    $frag = [ordered]@{ id = $id; chain = $chain; ts = (Get-Date -Format 'yyyy-MM-ddTHH:mm:ss'); text = $text.Trim(); vec = (FragVec $text); freq = 1; edges = @() }
    [IO.File]::WriteAllText((Join-Path $dir ($id + '.json')), ($frag | ConvertTo-Json -Depth 5), (New-Object Text.UTF8Encoding $false))
  } catch {}
}
function TailPush($role, $text) {
  $p = StateFile 'tail.log'; $lines = @(); if (Test-Path $p) { $lines = @(Get-Content $p -Encoding UTF8) }
  $x = ($text -replace '\s+', ' '); $lines = $lines + ($role + ': ' + $x.Substring(0, [Math]::Min(160, $x.Length)))
  if ($lines.Count -gt 30) { $lines = $lines[($lines.Count - 30)..($lines.Count - 1)] }
  [IO.File]::WriteAllLines($p, $lines, (New-Object Text.UTF8Encoding $false))
}
function TailText { $p = StateFile 'tail.log'; if (-not (Test-Path $p)) { return '' }; $t = (Get-Content $p -Raw -Encoding UTF8).Trim(); if ($t.Length -gt 1200) { $t.Substring($t.Length - 1200) } else { $t } }
function ChainsGit {
  $r = Join-Path $SMS 'chains'; if (-not (Test-Path (Join-Path $r '.git'))) { try { & git -C $r init --quiet 2>$null } catch { return } }
  try { & git -C $r add -A 2>&1 | Out-Null; & git -C $r -c user.name=sms -c user.email=sms@local commit -qm ('sms-shell ' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss')) 2>&1 | Out-Null } catch {}
}
