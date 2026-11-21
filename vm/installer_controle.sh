#!/bin/bash
# MaranYSE — met à jour le contrôle parental dans la VM :
# reconstruit l'image du bureau, recrée le conteneur (avec NET_ADMIN pour le pare-feu par enfant)
# et remplace le tableau de bord. Les sessions ouvertes sont fermées.
# Lancer depuis Git Bash :  bash vm/installer_controle.sh
set -e
ICI=$(cd "$(dirname "$0")" && pwd)
RACINE=$(cd "$ICI/.." && pwd)
[ -f "$ICI/config.env" ] && . "$ICI/config.env"
VM=${MARANYSE_VM_IP:-192.168.1.15}
USERS_INIT=${MARANYSE_USERS:-driss paul carole}
KEY="$ICI/build/cle_vm"
KNOWN="$ICI/build/known_hosts"
ADM=$(cut -d: -f2 "$ICI/build/compte_admin_vm.txt")
O="-F /dev/null -i $KEY -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=$KNOWN -o LogLevel=ERROR"

# Capacités de l'ordinateur hôte (page Puissance : le curseur est un pourcentage de cet ordinateur).
# Fonctionne sous Windows (Git Bash / PowerShell) et sous Linux hôte.
if command -v powershell.exe >/dev/null 2>&1; then
  powershell.exe -NoProfile -Command '$c=Get-CimInstance Win32_ComputerSystem; $p=(Get-CimInstance Win32_Processor | Select-Object -First 1).Name.Trim();
    $h=[ordered]@{cpu=$p; threads=[int]$c.NumberOfLogicalProcessors; ram_mo=[int]($c.TotalPhysicalMemory/1MB); disque_libre_go=[int]((Get-PSDrive F).Free/1GB)};
    try { $m=Get-VM bureau-enfants -ErrorAction Stop; $h.vm_ram_mo=[int]($(if($m.DynamicMemoryEnabled){$m.MemoryMaximum}else{$m.MemoryStartup})/1MB) } catch {}
    $h | ConvertTo-Json -Compress' | tr -d '\r\n' > /tmp/maranyse_hote.json
else
  python3 - <<'PY' > /tmp/maranyse_hote.json
import json, os, shutil
cpu = next((l.split(":", 1)[1].strip() for l in open("/proc/cpuinfo") if l.startswith("model name")), "")
mem_kb = next((int(l.split()[1]) for l in open("/proc/meminfo") if l.startswith("MemTotal:")), 4096 * 1024)
disk_go = shutil.disk_usage("/").free // (1024 ** 3)
print(json.dumps({"cpu": cpu, "threads": os.cpu_count() or 1, "ram_mo": mem_kb // 1024, "disque_libre_go": disk_go}))
PY
fi
scp $O /tmp/maranyse_hote.json parent@$VM:/tmp/hote_mesure.json
scp $O "$ICI/config.env" "$ICI/tableau.py" "$ICI/style.py" "$ICI/stats.py" "$ICI/aide.py" "$ICI/logique.py" "$ICI/marque.py" "$ICI/logiciels.py" "$ICI/i18n.py" "$ICI/themes.py" \
  "$RACINE/container/Dockerfile" "$RACINE/container/entrypoint.sh" "$RACINE/container/firefox-net.c" "$RACINE/container/sans-internet.c" "$RACINE/container/sans-internet-ff.c" parent@$VM:/tmp/
ssh $O parent@$VM 'rm -rf /tmp/bureau /tmp/i18n /tmp/logo_web && mkdir -p /tmp/logo_web/web'
scp $O -r "$ICI/i18n" parent@$VM:/tmp/
scp $O -r "$RACINE/container/bureau" parent@$VM:/tmp/
scp $O "$RACINE/container/logo_web/logo4_440.png" parent@$VM:/tmp/logo_web/
scp $O "$RACINE/container/logo_web/web/e320.png" "$RACINE/container/logo_web/web/e128.png" "$RACINE/container/logo_web/web/logo420.jpg" \
  "$RACINE/container/logo_web/web/logo200.jpg" "$RACINE/container/logo_web/web/ban440.jpg" "$RACINE/container/logo_web/web/slogan760.jpg" \
  "$RACINE/container/logo_web/web/ban1200.jpg" "$RACINE/container/logo_web/web/favjpeg.png" parent@$VM:/tmp/logo_web/web/

# Le mot de passe sudo est transmis via un fichier 0600 éphémère sur stdin (jamais exposé dans ps aux)
printf '%s\n' "$ADM" | ssh $O parent@$VM 'umask 077 && cat > /tmp/.maranyse_adm'
ssh $O parent@$VM "USERS_INIT='$USERS_INIT' bash -s" <<'REMOTE'
set -e
ADM=$(cat /tmp/.maranyse_adm); rm -f /tmp/.maranyse_adm
S() { printf '%s\n' "$ADM" | sudo -S -p '' "$@"; }
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
  --cap-add NET_ADMIN --sysctl net.ipv6.conf.all.disable_ipv6=1 --sysctl net.ipv6.conf.default.disable_ipv6=1 \
  -p 3389:3389 -e USERS="$USERS_INIT" \
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
# Règle sudoers ciblée (évite de lancer un conteneur privilégié toutes les 5 min pour les quotas et montages noexec)
S sh -c 'printf "%s\n" "parent ALL=(root) NOPASSWD: /usr/sbin/setquota, /usr/sbin/repquota, /usr/bin/nsenter" > /etc/sudoers.d/maranyse && chmod 440 /etc/sudoers.d/maranyse'
# Mémoire ajoutée à chaud par Hyper-V (mémoire dynamique) : mise en service tout de suite, sinon la VM reste à sa taille de départ
S sh -c 'printf "%s\n" "SUBSYSTEM==\"memory\", ACTION==\"add\", ATTR{state}==\"offline\", ATTR{state}=\"online\"" > /etc/udev/rules.d/40-maranyse-memoire.rules'
S sh -c 'for f in /sys/devices/system/memory/memory*/state; do grep -q offline $f && echo online > $f; done; true'
install -m 600 /tmp/config.env ~/config.env
install -m 755 /tmp/tableau.py ~/tableau.py
for m in style.py stats.py aide.py logique.py marque.py logiciels.py themes.py i18n.py; do
  install -m 644 "/tmp/$m" ~/"$m"
done
mkdir -p ~/i18n && install -m 644 /tmp/i18n/*.json ~/i18n/
rm -rf ~/logo_web && cp -r /tmp/logo_web ~/logo_web
S systemctl restart tableau-parent
sleep 3
echo "bureau : $(docker inspect -f '{{.State.Status}}' bureau-enfants) / tableau : $(systemctl is-active tableau-parent)"
REMOTE
echo "MaranYSE est a jour : https://$VM:8080"
