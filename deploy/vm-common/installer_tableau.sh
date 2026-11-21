#!/bin/bash
# Installe le tableau de bord parent dans la VM (http://<IP>:8080)
# + clé SSH du PC Windows + outils wmctrl/zenity dans le bureau des enfants.
# Lancer depuis Git Bash :  bash deploy/vm-common/installer_tableau.sh
set -e
export MSYS_NO_PATHCONV=1
ICI=$(cd "$(dirname "$0")" && pwd)
RACINE=$(cd "$ICI/../.." && pwd)
CONF="$ICI/config.env"; [ -f "$CONF" ] || CONF="$RACINE/vm/config.env"
[ -f "$CONF" ] && . "$CONF"
VM=${MARANYSE_VM_IP:-192.168.1.15}
BUILD="$ICI/build"; [ -d "$BUILD" ] || BUILD="$RACINE/vm/build"
ADM=$(cut -d: -f2 "$BUILD/compte_admin_vm.txt")

docker run --rm -i -e ADM="$ADM" -e VM="$VM" -v "$RACINE":/w debian:bookworm-slim bash <<'EOF'
set -e
apt-get update -qq >/dev/null && apt-get install -y -qq sshpass openssh-client >/dev/null 2>&1
export SSHPASS="$ADM"
BUILD_W=/w/deploy/vm-common/build; [ -d "$BUILD_W" ] || BUILD_W=/w/vm/build
CONF_W=/w/deploy/vm-common/config.env; [ -f "$CONF_W" ] || CONF_W=/w/vm/config.env
O="-o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=$BUILD_W/known_hosts -o LogLevel=ERROR"
sshpass -e scp $O "$CONF_W" /w/app/tableau.py /w/app/style.py /w/app/stats.py /w/app/aide.py /w/app/logique.py /w/app/marque.py /w/app/logiciels.py /w/app/i18n.py /w/app/themes.py /w/bureau/Dockerfile "$BUILD_W/cle_vm.pub" parent@$VM:/tmp/
printf '%s\n' "$ADM" | sshpass -e ssh $O parent@$VM 'umask 077 && cat > /tmp/.maranyse_adm'
sshpass -e ssh $O parent@$VM "bash -s" <<'REMOTE'
set -e
ADM=$(cat /tmp/.maranyse_adm); rm -f /tmp/.maranyse_adm
S() { printf '%s\n' "$ADM" | sudo -S -p '' "$@"; }
mkdir -p ~/.ssh && chmod 700 ~/.ssh
grep -qf /tmp/cle_vm.pub ~/.ssh/authorized_keys 2>/dev/null || cat /tmp/cle_vm.pub >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
install -m 600 /tmp/config.env ~/config.env
install -m 755 /tmp/tableau.py ~/tableau.py
for m in style.py stats.py aide.py logique.py marque.py logiciels.py themes.py i18n.py; do
  [ -f "/tmp/$m" ] && install -m 644 "/tmp/$m" ~/"$m"
done
printf 'parent:%s\n' "$ADM" > ~/.tableau.conf && chmod 600 ~/.tableau.conf
S install -m 644 /tmp/Dockerfile /srv/bureau/build/Dockerfile
docker exec bureau-enfants sh -c 'apt-get update -qq >/dev/null && apt-get install -y -qq --no-install-recommends wmctrl zenity >/dev/null 2>&1' && echo "outils wmctrl/zenity : OK"
printf '%s\n' '[Unit]' 'Description=Tableau de bord parent' 'After=docker.service network-online.target' 'Wants=network-online.target' \
  '[Service]' 'User=parent' 'ExecStart=/usr/bin/python3 /home/parent/tableau.py' 'Restart=always' 'RestartSec=5' \
  '[Install]' 'WantedBy=multi-user.target' > /tmp/tableau-parent.service
S install -m 644 /tmp/tableau-parent.service /etc/systemd/system/tableau-parent.service
S systemctl daemon-reload
S systemctl enable --now tableau-parent >/dev/null 2>&1
sleep 2
echo "service tableau-parent : $(systemctl is-active tableau-parent)"
nohup docker build -q -t bureau-enfants:latest /srv/bureau/build >/tmp/build.log 2>&1 &
REMOTE
EOF
echo "Termine. Ouvrez http://$VM:8080 (identifiant parent)."
