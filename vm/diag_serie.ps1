# Redémarre la VM en capturant sa console série pendant 4 minutes
$log = 'F:\vm_enfants\vm\build\serie.log'
Stop-VM bureau-enfants -TurnOff -Force
Set-VMComPort -VMName bureau-enfants -Number 1 -Path '\\.\pipe\bureau-com1'
Start-VM bureau-enfants
$pipe = New-Object IO.Pipes.NamedPipeClientStream('.', 'bureau-com1', [IO.Pipes.PipeDirection]::In)
$pipe.Connect(10000)
$fs = [IO.File]::Open($log, 'Create', 'Write', 'Read')
$buf = New-Object byte[] 4096
$end = (Get-Date).AddMinutes(4)
while ((Get-Date) -lt $end) {
    $t = $pipe.ReadAsync($buf, 0, $buf.Length)
    if ($t.Wait(5000)) { if ($t.Result -le 0) { break }; $fs.Write($buf, 0, $t.Result); $fs.Flush() }
}
$fs.Close(); $pipe.Close()
(Get-VMNetworkAdapter -VMName bureau-enfants).IPAddresses | Out-File 'F:\vm_enfants\vm\build\ip_apres.txt'
