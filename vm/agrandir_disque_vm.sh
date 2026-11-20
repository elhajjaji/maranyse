#!/bin/bash
# MaranYSE — agrandit le disque de la VM sans l'arrêter (les sessions des enfants continuent).
# Usage depuis Git Bash :  bash F:/vm_enfants/vm/agrandir_disque_vm.sh 250      (taille voulue en Go)
# Windows demande l'autorisation administrateur (Hyper-V). Un disque ne peut pas être réduit ensuite.
set -e
GO=${1:?Taille voulue en Go, par exemple : bash agrandir_disque_vm.sh 250}
VM=192.168.1.15
KEY=/f/vm_enfants/vm/build/cle_vm
ADM=$(cut -d: -f2 /f/vm_enfants/vm/build/compte_admin_vm.txt)
O="-F /dev/null -i $KEY -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR"
TMP=$(cygpath -w "${TMPDIR:-/tmp}")
PS1="$TMP\\maranyse_disque.ps1"; OUT="$TMP\\maranyse_disque.txt"

# 1. Hyper-V : agrandit le fichier .vhdx (possible VM allumée : disque SCSI d'une VM de génération 2)
cat > "$(cygpath -u "$PS1")" <<EOF
\$r = try {
  \$d = Get-VMHardDiskDrive -VMName bureau-enfants | Select-Object -First 1
  \$v = Get-VHD -Path \$d.Path
  if (\$v.Size -lt ${GO}GB) { Resize-VHD -Path \$d.Path -SizeBytes ${GO}GB -ErrorAction Stop }
  'OK ' + [math]::Round((Get-VHD -Path \$d.Path).Size/1GB) + ' Go : ' + \$d.Path
} catch { 'ERREUR ' + \$_ }
\$r | Out-File -Encoding utf8 '$OUT'
EOF
rm -f "$(cygpath -u "$OUT")"
powershell.exe -NoProfile -Command "Start-Process powershell -Verb RunAs -Wait -WindowStyle Hidden -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File','$PS1'"
R=$(tr -d '\r\357\273\277' < "$(cygpath -u "$OUT")")
echo "Hyper-V : $R"
case "$R" in OK*) ;; *) exit 1 ;; esac

# 2. Dans la VM : la partition et le système de fichiers prennent la nouvelle place (à chaud)
ssh $O parent@$VM "ADM='$ADM' bash -s" <<'REMOTE'
set -e
S() { echo "$ADM" | sudo -S -p '' "$@"; }
S sh -c 'echo 1 > /sys/class/block/sda/device/rescan'
command -v growpart >/dev/null || [ -x /usr/bin/growpart ] || S env DEBIAN_FRONTEND=noninteractive apt-get install -y -q cloud-guest-utils >/dev/null
S growpart /dev/sda 1 || true          # « NOCHANGE » si déjà à la bonne taille
S resize2fs /dev/sda1 >/dev/null 2>&1
df -h / | tail -1 | awk '{print "Disque de la VM : " $2 ", libre : " $4}'
REMOTE
echo "Le curseur « Espace disque par enfant » (page Puissance) peut maintenant aller plus haut."
