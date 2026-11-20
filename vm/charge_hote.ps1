# MaranYSE - envoie la charge de ce PC (processeur, memoire) au tableau de bord, toutes les 5 secondes.
# Lance a l'ouverture de session Windows par la tache « MaranYSE charge » (voir installer_charge_hote.ps1).
# Le jeton (build\jeton_charge.txt) est le meme que ~/.jeton_charge dans la VM : sans lui, le tableau refuse les chiffres.
$ErrorActionPreference = 'SilentlyContinue'
$jeton = (Get-Content -Raw "$PSScriptRoot\build\jeton_charge.txt").Trim()
$url = 'http://192.168.1.15:8080/api/charge-hote'
while ($true) {
    try {
        $p = (Get-CimInstance Win32_PerfFormattedData_PerfOS_Processor -Filter "Name='_Total'").PercentProcessorTime
        $os = Get-CimInstance Win32_OperatingSystem
        $corps = @{ cpu = [int]$p; ram_mo = [int]($os.TotalVisibleMemorySize / 1024); libre_mo = [int]($os.FreePhysicalMemory / 1024) } | ConvertTo-Json -Compress
        Invoke-RestMethod -Uri $url -Method Post -Body $corps -ContentType 'application/json' -Headers @{ 'X-Jeton' = $jeton } -TimeoutSec 4 | Out-Null
    } catch {}
    Start-Sleep -Seconds 5
}
