#!/bin/bash
# MaranYSE — met à jour le contrôle parental dans la VM :
# reconstruit l'image du bureau, recrée le conteneur (avec NET_ADMIN pour le pare-feu par enfant)
# et remplace le tableau de bord.  Les sessions ouvertes sont fermées.
# Lancer depuis Git Bash :  bash F:/vm_enfants/vm/installer_controle.sh
set -e
VM=192.168.1.15
KEY=/f/vm_enfants/vm/build/cle_vm
ADM=$(cut -d: -f2 /f/vm_enfants/vm/build/compte_admin_vm.txt)
O="-F /dev/null -i $KEY -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR"

# Capacités de l'ordinateur hôte (page Puissance : le curseur est un pourcentage de cet ordinateur).
# Le plafond de la VM (Get-VM) demande les droits administrateur : sinon la valeur déjà connue est gardée.
powershell.exe -NoProfile -Command '$c=Get-CimInstance Win32_ComputerSystem; $p=(Get-CimInstance Win32_Processor | Select-Object -First 1).Name.Trim();
  $h=[ordered]@{cpu=$p; threads=[int]$c.NumberOfLogicalProcessors; ram_mo=[int]($c.TotalPhysicalMemory/1MB); disque_libre_go=[int]((Get-PSDrive F).Free/1GB)};
  try { $m=Get-VM bureau-enfants -ErrorAction Stop; $h.vm_ram_mo=[int]($(if($m.DynamicMemoryEnabled){$m.MemoryMaximum}else{$m.MemoryStartup})/1MB) } catch {}
  $h | ConvertTo-Json -Compress' | tr -d '
' > /tmp/maranyse_hote.json
scp $O /tmp/maranyse_hote.json parent@$VM:/tmp/hote_mesure.json
scp $O /f/vm_enfants/vm/tableau.py /f/vm_enfants/vm/logique.py /f/vm_enfants/vm/marque.py /f/vm_enfants/vm/logiciels.py /f/vm_enfants/vm/i18n.py /f/vm_enfants/vm/themes.py /f/vm_enfants/container/Dockerfile /f/vm_enfants/container/entrypoint.sh /f/vm_enfants/container/firefox-net.c /f/vm_enfants/container/sans-internet.c /f/vm_enfants/container/sans-internet-ff.c parent@$VM:/tmp/
ssh $O parent@$VM 'rm -rf /tmp/bureau /tmp/i18n'
scp $O -r /f/vm_enfants/vm/i18n parent@$VM:/tmp/
scp $O -r /f/vm_enfants/container/bureau parent@$VM:/tmp/
ssh $O parent@$VM "ADM='$ADM' bash -s" <<'REMOTE'
set -e
S() { echo "$ADM" | sudo -S -p '' "$@"; }
S install -m 644 /tmp/Dockerfile /tmp/entrypoint.sh /tmp/firefox-net.c /tmp/sans-internet.c /tmp/sans-internet-ff.c /srv/bureau/build/
# bureau « façon Windows » (thème, barre des tâches, menu Démarrer, fond d'écran)
S rm -rf /srv/bureau/build/bureau && S cp -r /tmp/bureau /srv/bureau/build/bureau
# logiciels installés depuis l'espace parents : intégrés à l'image (sinon réinstallés après coup)
(cd /tmp && python3 logiciels.py script) > /tmp/logiciels.sh
S install -m 644 /tmp/logiciels.sh /srv/bureau/build/
echo "1/3 Construction de l'image du bureau (quelques minutes)..."
docker build -q -t bureau-enfants:latest /srv/bureau/build >/dev/null
echo "2/3 Recreation du bureau..."
# Dossiers des enfants : aucun programme ne peut y être lancé (programmes téléchargés, copiés...)
if ! findmnt -no OPTIONS /srv/bureau/home 2>/dev/null | grep -q noexec; then
  grep -q '^/srv/bureau/home ' /etc/fstab || S sh -c "echo '/srv/bureau/home /srv/bureau/home none bind,nosuid,nodev,noexec 0 0' >> /etc/fstab"
  findmnt /srv/bureau/home >/dev/null 2>&1 || S mount --bind /srv/bureau/home /srv/bureau/home
  S mount -o remount,bind,nosuid,nodev,noexec /srv/bureau/home
fi
grep -q '^/srv/bureau/home ' /etc/fstab || S sh -c "echo '/srv/bureau/home /srv/bureau/home none bind,nosuid,nodev,noexec 0 0' >> /etc/fstab"
findmnt -no OPTIONS /srv/bureau/home | grep -q noexec || { echo "ERREUR : /srv/bureau/home n'est pas en noexec"; exit 1; }
# USERS = comptes de départ seulement ; ensuite la liste est dans /secrets/comptes.txt (page Comptes)
docker rm -f bureau-enfants >/dev/null 2>&1 || true
docker run -d --init --name bureau-enfants --hostname bureau-enfants --restart unless-stopped --shm-size 2g \
  --cap-add NET_ADMIN -p 3389:3389 -e USERS="driss paul carole" \
  --tmpfs /tmp:rw,nosuid,nodev,noexec,mode=1777 --tmpfs /var/tmp:rw,nosuid,nodev,noexec,mode=1777 \
  --tmpfs /run/lock:rw,nosuid,nodev,noexec,mode=1777 --tmpfs /run/xrdp/sockdir:rw,nosuid,nodev,noexec,mode=3777 \
  -v /srv/bureau/home:/home -v /srv/bureau/secrets:/secrets bureau-enfants:latest >/dev/null
echo "3/3 Mise a jour du tableau de bord..."
python3 - <<'PY'
import json, os
f = os.path.expanduser("~/hote.json")
try: h = json.load(open(f))
except (OSError, ValueError): h = {}
try: h.update(json.load(open("/tmp/hote_mesure.json")))
except (OSError, ValueError): pass
json.dump(h, open(f, "w"))
PY
# Quotas disque par enfant (page Puissance) : quotas Linux sur le disque de la VM, activés sans redémarrage
command -v setquota >/dev/null 2>&1 || [ -x /usr/sbin/setquota ] || S env DEBIAN_FRONTEND=noninteractive apt-get install -y -q quota >/dev/null
grep -qE '^\S+\s+/\s+ext4\s+\S*usrquota' /etc/fstab || S sed -i -E '/^\S+\s+\/\s+ext4\s/ s/(\S+\s+\/\s+ext4\s+)(\S+)/\1\2,usrquota/' /etc/fstab
findmnt -no OPTIONS / | grep -q usrquota || { S mount -o remount,usrquota / && S quotacheck -cum / && S quotaon -u /; }
# Mémoire ajoutée à chaud par Hyper-V (mémoire dynamique) : mise en service tout de suite, sinon la VM reste à sa taille de départ
S sh -c 'printf "%s
" "SUBSYSTEM==\"memory\", ACTION==\"add\", ATTR{state}==\"offline\", ATTR{state}=\"online\"" > /etc/udev/rules.d/40-maranyse-memoire.rules'
S sh -c 'for f in /sys/devices/system/memory/memory*/state; do grep -q offline $f && echo online > $f; done; true'
install -m 755 /tmp/tableau.py ~/tableau.py
install -m 644 /tmp/logique.py ~/logique.py
install -m 644 /tmp/marque.py ~/marque.py
install -m 644 /tmp/logiciels.py ~/logiciels.py
install -m 644 /tmp/themes.py ~/themes.py
install -m 644 /tmp/i18n.py ~/i18n.py
mkdir -p ~/i18n && install -m 644 /tmp/i18n/*.json ~/i18n/
S systemctl restart tableau-parent
sleep 3
echo "bureau : $(docker inspect -f '{{.State.Status}}' bureau-enfants) / tableau : $(systemctl is-active tableau-parent)"
REMOTE
echo "MaranYSE est a jour : http://$VM:8080"
