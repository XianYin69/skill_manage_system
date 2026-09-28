$ErrorActionPreference='SilentlyContinue'
Add-Type -AssemblyName System.Speech
$s=New-Object System.Speech.Synthesis.SpeechSynthesizer
$rd=New-Object IO.StreamReader([Console]::OpenStandardInput())
$t=$rd.ReadLineAsync()
$cv='?';$turn=0;$pend=[System.Collections.Queue]::new()
while($true){
 if($pend.Count -gt 0){$l=$pend.Dequeue()}else{$l=$t.Result;$t=$rd.ReadLineAsync()}
 if($null -eq $l){break}
 $j=$null;try{$j=$l|ConvertFrom-Json}catch{}
 if(-not $j){continue}
 if($j.op -eq 'q'){break}
 if($j.op -eq 'c'){[void]$s.SpeakAsyncCancelAll();if($null -ne $j.n){$turn=[int]$j.n};continue}
 if($j.op -ne 's'){continue}
 $jn=if($null -eq $j.n){$turn}else{[int]$j.n}
 if($jn -lt $turn){continue}
 if($jn -gt $turn){[void]$s.SpeakAsyncCancelAll();$turn=$jn}
 if($j.v -ne $cv){$cv=$j.v;$n=@(($s.GetInstalledVoices()|Where-Object{$_.Enabled}).VoiceInfo.Name)
  $w=@($n|Where-Object{$_ -eq $cv -or $_ -like ($cv+'*')}|Select-Object -First 1);if(-not $w[0]){$w=@($n|Where-Object{$_ -match 'Huihui|Xiaoxiao|Kangkang|Yaoyao|Chinese'}|Select-Object -First 1)};if($w[0]){$s.SelectVoice($w[0])}}
 $x='<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="zh-CN"><prosody rate="'+$j.r+'%" pitch="'+$j.p+'" volume="'+$j.o+'%">'+$j.t+'</prosody></speak>'
 $e=$s.SpeakSsmlAsync($x)
 for($k=0;$k -lt 900 -and -not $e.IsCompleted;$k++){
  if($t.IsCompleted){
   $nl=$t.Result;$t=$rd.ReadLineAsync();$pj=$null;try{$pj=$nl|ConvertFrom-Json}catch{}
   $pn=if($null -eq $pj -or $null -eq $pj.n){$turn}else{[int]$pj.n}
   if($pj -and $pj.op -eq 'q'){[void]$s.SpeakAsyncCancelAll();break}
   if($pj -and $pj.op -eq 'c'){[void]$s.SpeakAsyncCancelAll();if($pn -gt $turn){$turn=$pn};$pend.Clear();continue}
   if($pj -and $pj.op -eq 's'){if($pn -gt $turn){[void]$s.SpeakAsyncCancelAll();$turn=$pn;$pend.Clear()};if($pn -ge $turn){$pend.Enqueue($nl)}}
  }
  Start-Sleep -m 100
 }
 if($e -and -not $e.IsCompleted){[void]$s.SpeakAsyncCancelAll()}
 if($j.a){[Console]::Out.WriteLine('OK')}
 [Console]::Out.Flush()
}
