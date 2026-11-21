# MaranYSE - installe l'envoi de la charge de ce PC au tableau de bord (indicateur « PC » de l'en-tete).
# Tache planifiee de l'utilisateur courant, lancee a l'ouverture de session, sans fenetre. Pas besoin d'etre administrateur.
# Usage : powershell -ExecutionPolicy Bypass -File deploy\vm-windows\installer_charge_hote.ps1
# Desinstaller : Unregister-ScheduledTask -TaskName 'MaranYSE charge' -Confirm:$false
$script = Join-Path $PSScriptRoot 'charge_hote.ps1'
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$script`""
$declencheur = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$reglages = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName 'MaranYSE charge' -Action $action -Trigger $declencheur -Settings $reglages -Description 'MaranYSE : charge de ce PC pour le tableau de bord' -Force | Out-Null
Start-ScheduledTask -TaskName 'MaranYSE charge'
"Tache « MaranYSE charge » installee et demarree."
