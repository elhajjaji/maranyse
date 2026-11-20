#!/bin/bash
# Installe le tableau de bord parent dans la VM (http://<IP>:8080)
# + clé SSH du PC Windows + outils wmctrl/zenity dans le bureau des enfants.
# Lancer depuis Git Bash :  bash vm/installer_tableau.sh
set -e
export MSYS_NO_PATHCONV=1
ICI=$(cd "$(dirname "$0")" && pwd)
RACINE=$(cd "$ICI/.." && pwd)
[ -f "$ICI/config.env" ] && . "$ICI/config.env"
VM=${MARANYSE_VM_IP:-192.168.1.15}
ADM=$(cut -d: -f2 "$ICI/build/compte_admin_vm.txt")

docker run --rm -i -e ADM="$ADM" -e VM="$VM" -v "$RACINE":/w debian:bookworm-slim bash <<'EOF'
set -e
apt-get update -qq >/dev/null && apt-get install -y -qq sshpass openssh-client >/dev/null 2>&1
export SSHPASS="$ADM"
O="-o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=/w/vm/build/known_hosts -o LogLevel=ERROR"
sshpass -e scp $O /w/vm/config.env /w/vm/tableau.py /w/vm/style.py /w/vm/stats.py /w/vm/aide.py /w/vm/logique.py /w/vm/marque.py /w/vm/logiciels.py /w/vm/i18n.py /w/vm/themes.py /w/container/Dockerfile /w/vm/build/cle_vm.pub parent@$VM:/tmp/
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
