$ErrorActionPreference='SilentlyContinue'
Add-Type -AssemblyName System.Speech
$s=New-Object System.Speech.Synthesis.SpeechSynthesizer
$cv='?'
while($null -ne ($l=[Console]::ReadLine())){
 $j=$null; try{$j=$l|ConvertFrom-Json}catch{}
 if(-not $j){continue}
 if($j.op -eq 'q'){break}
 if($j.op -eq 'c'){[void]$s.SpeakAsyncCancelAll();continue}
 if($j.op -ne 's'){continue}
 if($j.v -ne $cv){$cv=$j.v;$n=@(($s.GetInstalledVoices()|Where-Object{$_.Enabled}).VoiceInfo.Name)
  $w=@($n|Where-Object{$_ -eq $cv -or $_ -like ($cv+'*')}|Select-Object -First 1);if(-not $w[0]){$w=@($n|Where-Object{$_ -match 'Huihui|Xiaoxiao|Kangkang|Yaoyao|Chinese'}|Select-Object -First 1)};if($w[0]){$s.SelectVoice($w[0])}}
 $x='<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="zh-CN"><prosody rate="'+$j.r+'%" pitch="'+$j.p+'" volume="'+$j.o+'%">'+$j.t+'</prosody></speak>'
 $e=$s.SpeakSsmlAsync($x);for($k=0;$k -lt 900 -and -not $e.IsCompleted;$k++){Start-Sleep -m 100}
 if($e -and -not $e.IsCompleted){[void]$s.SpeakAsyncCancelAll()}
 if($j.a){[Console]::Out.WriteLine('OK')}
 [Console]::Out.Flush()
}
