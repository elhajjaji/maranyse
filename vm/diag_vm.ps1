# Diagnostic : état de la VM + capture d'écran de sa console
$out = Join-Path $PSScriptRoot 'build'
$vm = Get-VM bureau-enfants
$vm | Format-List Name,State,Uptime,Heartbeat,Status,MemoryAssigned | Out-File "$out\diag.txt" -Encoding utf8
Get-VMNetworkAdapter -VMName bureau-enfants | Format-List MacAddress,IPAddresses,Status,SwitchName | Out-File "$out\diag.txt" -Append -Encoding utf8
Get-VMFirmware bureau-enfants | Format-List SecureBoot,SecureBootTemplate,BootOrder | Out-File "$out\diag.txt" -Append -Encoding utf8
Get-VMSwitch | Format-List Name,SwitchType,NetAdapterInterfaceDescription | Out-File "$out\diag.txt" -Append -Encoding utf8

# Capture de la console (API WMI Hyper-V)
Add-Type -AssemblyName System.Drawing
$ms  = Get-CimInstance -Namespace root\virtualization\v2 -ClassName Msvm_VirtualSystemManagementService
$sys = Get-CimInstance -Namespace root\virtualization\v2 -ClassName Msvm_ComputerSystem -Filter "ElementName='bureau-enfants'"
$set = Get-CimAssociatedInstance -InputObject $sys -ResultClassName Msvm_VirtualSystemSettingData | Where-Object VirtualSystemType -eq 'Microsoft:Hyper-V:System:Realized'
$w = 1024; $h = 768
$r = Invoke-CimMethod -InputObject $ms -MethodName GetVirtualSystemThumbnailImage -Arguments @{ TargetSystem = $set; WidthPixels = [uint16]$w; HeightPixels = [uint16]$h }
$bytes = $r.ImageData
$bmp = New-Object Drawing.Bitmap $w, $h, ([Drawing.Imaging.PixelFormat]::Format16bppRgb565)
$data = $bmp.LockBits((New-Object Drawing.Rectangle 0,0,$w,$h), 'WriteOnly', $bmp.PixelFormat)
[Runtime.InteropServices.Marshal]::Copy([byte[]]$bytes, 0, $data.Scan0, $bytes.Length)
$bmp.UnlockBits($data)
$bmp.Save("$out\console.png", [Drawing.Imaging.ImageFormat]::Png)
