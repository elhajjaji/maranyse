# Crée la VM Hyper-V "bureau-enfants" avec sa propre IP sur la Livebox.
# A lancer dans un PowerShell ouvert en tant qu'administrateur :
#   powershell -ExecutionPolicy Bypass -File F:\vm_enfants\vm\creer_vm.ps1
$ErrorActionPreference = 'Stop'
$Dir     = $PSScriptRoot
$VmName  = 'bureau-enfants'
$Switch  = 'Externe-WiFi'
$Adapter = 'Wi-Fi'
$Vhd     = Join-Path $Dir 'bureau-enfants.vhdx'
$Iso     = Join-Path $Dir 'seed.iso'

if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Ce script doit etre lance en tant qu'administrateur."
}

if (-not (Get-Command New-VM -ErrorAction SilentlyContinue)) {
    Write-Host "Activation des outils Hyper-V (un redemarrage sera demande)..." -ForegroundColor Yellow
    Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V-All -All
    Write-Host "Redemarrez le PC puis relancez ce script." -ForegroundColor Yellow
    return
}

if (Get-VM -Name $VmName -ErrorAction SilentlyContinue) { throw "La VM $VmName existe deja." }

# 1. Commutateur externe sur le Wi-Fi (coupure reseau de quelques secondes)
if (-not (Get-VMSwitch -Name $Switch -ErrorAction SilentlyContinue)) {
    Write-Host "Creation du commutateur externe '$Switch' sur '$Adapter' (le Wi-Fi va se couper ~10 s)..."
    New-VMSwitch -Name $Switch -NetAdapterName $Adapter -AllowManagementOS $true | Out-Null
    Start-Sleep 15
}

# 2. VM
Write-Host "Creation de la VM..."
Resize-VHD -Path $Vhd -SizeBytes 80GB
New-VM -Name $VmName -Generation 2 -MemoryStartupBytes 8GB -VHDPath $Vhd -SwitchName $Switch -Path (Join-Path $Dir 'hyperv') | Out-Null
Set-VMProcessor -VMName $VmName -Count 8
Set-VMMemory   -VMName $VmName -DynamicMemoryEnabled $true -MinimumBytes 2GB -StartupBytes 8GB -MaximumBytes 16GB
Set-VMFirmware -VMName $VmName -SecureBootTemplate MicrosoftUEFICertificateAuthority
Add-VMDvdDrive -VMName $VmName -Path $Iso
Set-VMFirmware -VMName $VmName -FirstBootDevice (Get-VMHardDiskDrive -VMName $VmName)
Set-VM -Name $VmName -AutomaticStartAction Start -AutomaticStartDelay 30 -AutomaticStopAction ShutDown -CheckpointType Disabled
Start-VM -Name $VmName

# 3. Attente de l'adresse IP (premier demarrage : installation de Docker)
Write-Host "Premier demarrage en cours, attente de l'adresse IP (jusqu'a 10 min)..."
$ip = $null
for ($i = 0; $i -lt 120 -and -not $ip; $i++) {
    Start-Sleep 5
    $ip = (Get-VMNetworkAdapter -VMName $VmName).IPAddresses | Where-Object { $_ -match '^\d+\.\d+\.\d+\.\d+$' -and $_ -notlike '169.254*' } | Select-Object -First 1
}
if (-not $ip) { throw "Pas d'IP obtenue. Ouvrez la console de la VM dans le Gestionnaire Hyper-V pour voir ce qui se passe." }
$mac = ((Get-VMNetworkAdapter -VMName $VmName).MacAddress -replace '(..)(?!$)', '$1:')
Write-Host "IP de la VM : $ip   (MAC $mac)" -ForegroundColor Green

# 4. Attente du bureau (construction du conteneur, ~5-10 min)
Write-Host "Construction du bureau des enfants, attente du port 3389 (jusqu'a 20 min)..."
$ok = $false
for ($i = 0; $i -lt 240 -and -not $ok; $i++) {
    Start-Sleep 5
    $c = New-Object Net.Sockets.TcpClient
    try { $c.Connect($ip, 3389); $ok = $true } catch {} finally { $c.Close() }
}
Set-VMDvdDrive -VMName $VmName -Path $null

if ($ok) {
    Write-Host ""
    Write-Host "PRET ! Connexion Bureau a distance : $ip" -ForegroundColor Green
    Write-Host "Conseil : dans la Livebox, reservez l'IP $ip pour l'adresse MAC $mac."
} else {
    Write-Host "La VM a l'IP $ip mais le bureau n'est pas encore pret. Reessayez dans quelques minutes." -ForegroundColor Yellow
}
"$ip $mac" | Set-Content -Encoding ascii (Join-Path $Dir 'build\ip_vm.txt')
