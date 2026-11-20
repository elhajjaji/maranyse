# MaranYSE - envoie la charge de ce PC (processeur, memoire) au tableau de bord, toutes les 5 secondes.
# Lance a l'ouverture de session Windows par la tache « MaranYSE charge » (voir installer_charge_hote.ps1).
# Le jeton (build\jeton_charge.txt) est le meme que ~/.jeton_charge dans la VM : sans lui, le tableau refuse les chiffres.
$ErrorActionPreference = 'SilentlyContinue'
$jeton = (Get-Content -Raw "$PSScriptRoot\build\jeton_charge.txt").Trim()
$ip = '192.168.1.15'; $port = '8080'
if (Test-Path "$PSScriptRoot\config.env") {
    Get-Content "$PSScriptRoot\config.env" | ForEach-Object {
        if ($_ -match '^\s*MARANYSE_VM_IP\s*=\s*["'']?([^"''\s]+)') { $ip = $Matches[1] }
        if ($_ -match '^\s*MARANYSE_PORT\s*=\s*["'']?(\d+)') { $port = $Matches[1] }
    }
} elseif (Test-Path "$PSScriptRoot\build\ip_vm.txt") {
    $ip = ((Get-Content -Raw "$PSScriptRoot\build\ip_vm.txt").Trim() -split '\s+')[0]
}
$url = "http://${ip}:${port}/api/charge-hote"
while ($true) {
    try {
        $p = (Get-CimInstance Win32_PerfFormattedData_PerfOS_Processor -Filter "Name='_Total'").PercentProcessorTime
        $os = Get-CimInstance Win32_OperatingSystem
        $corps = @{ cpu = [int]$p; ram_mo = [int]($os.TotalVisibleMemorySize / 1024); libre_mo = [int]($os.FreePhysicalMemory / 1024) } | ConvertTo-Json -Compress
        Invoke-RestMethod -Uri $url -Method Post -Body $corps -ContentType 'application/json' -Headers @{ 'X-Jeton' = $jeton } -TimeoutSec 4 | Out-Null
    } catch {}
    Start-Sleep -Seconds 5
}
