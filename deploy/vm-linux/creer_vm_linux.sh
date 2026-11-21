#!/bin/bash
# MaranYSE — Mode 3 : Crée une VM Debian 12 sous Linux (KVM / libvirt) avec sa propre IP sur la box.
# Prérequis sur l'hôte Linux : qemu-kvm, libvirt-daemon-system, virtinst, cloud-image-utils (ou xorriso), wget, openssh-client.
# Usage : bash deploy/vm-linux/creer_vm_linux.sh
set -euo pipefail

ICI=$(cd "$(dirname "$0")" && pwd)
RACINE=$(cd "$ICI/../.." && pwd)
VM_COMMON="$RACINE/deploy/vm-common"
CONF="$VM_COMMON/config.env"; [ -f "$CONF" ] || CONF="$RACINE/vm/config.env"
[ -f "$CONF" ] && . "$CONF"

VM_NAME=${MARANYSE_VM_NAME:-bureau-enfants}
BRIDGE=${MARANYSE_BRIDGE:-br0}
RAM_MB=${MARANYSE_VM_RAM_MB:-8192}
CPUS=${MARANYSE_VM_CPUS:-4}
DISK_GB=${MARANYSE_VM_DISK_GB:-80}

BUILD="$VM_COMMON/build"
SEED="$VM_COMMON/seed"
mkdir -p "$BUILD" "$SEED"

for cmd in virt-install virsh qemu-img wget ssh-keygen; do
  command -v "$cmd" >/dev/null || { echo "Outil manquant : $cmd (installez qemu-kvm libvirt-daemon-system virtinst cloud-image-utils)"; exit 1; }
done

if virsh dominfo "$VM_NAME" >/dev/null 2>&1; then
  echo "La VM $VM_NAME existe déjà."
  exit 1
fi

# 1. Clé SSH et identifiant admin
if [ ! -f "$BUILD/cle_vm" ]; then
  ssh-keygen -t ed25519 -N "" -f "$BUILD/cle_vm" -q
fi
PUB=$(cat "$BUILD/cle_vm.pub")
if [ ! -f "$BUILD/compte_admin_vm.txt" ]; then
  ADM=${MARANYSE_PASSWORD:-$(tr -dc 'a-km-np-zA-KM-NP-Z2-9' </dev/urandom | head -c 12)}
  echo "parent:$ADM" > "$BUILD/compte_admin_vm.txt"
  chmod 600 "$BUILD/compte_admin_vm.txt"
else
  ADM=$(cut -d: -f2 "$BUILD/compte_admin_vm.txt")
fi

# 2. Image officielle Debian 12 Cloud
IMG="$BUILD/debian-12-genericcloud-amd64.qcow2"
if [ ! -f "$IMG" ]; then
  echo "Téléchargement de l'image Debian 12 Cloud..."
  wget -q --show-progress -O "$IMG" "https://cloud.debian.org/images/cloud/bookworm/latest/debian-12-genericcloud-amd64.qcow2"
fi
DISK="$BUILD/${VM_NAME}.qcow2"
cp "$IMG" "$DISK"
qemu-img resize "$DISK" "${DISK_GB}G" >/dev/null

# 3. Configuration cloud-init (utilisateur parent + Docker + ssh)
cat > "$SEED/meta-data" <<EOF
instance-id: ${VM_NAME}
local-hostname: ${VM_NAME}
EOF

cat > "$SEED/user-data" <<EOF
#cloud-config
users:
  - name: parent
    sudo: ALL=(ALL) NOPASSWD:ALL
    groups: sudo,docker
    shell: /bin/bash
    lock_passwd: false
    ssh_authorized_keys:
      - ${PUB}
chpasswd:
  list: |
    parent:${ADM}
  expire: false
package_update: true
packages:
  - docker.io
  - docker-compose-v2
  - quota
  - cloud-guest-utils
  - openssl
runcmd:
  - systemctl enable --now docker
  - mkdir -p /srv/bureau/build /srv/bureau/home /srv/bureau/secrets
  - chown -R parent:parent /srv/bureau
EOF

ISO="$BUILD/seed-linux.iso"
if command -v cloud-localds >/dev/null 2>&1; then
  cloud-localds "$ISO" "$SEED/user-data" "$SEED/meta-data"
elif command -v genisoimage >/dev/null 2>&1; then
  genisoimage -output "$ISO" -volid cidata -joliet -rock "$SEED/user-data" "$SEED/meta-data" >/dev/null 2>&1
else
  xorriso -as mkisofs -o "$ISO" -V cidata -J -R "$SEED/user-data" "$SEED/meta-data" >/dev/null 2>&1
fi

# 4. Création de la VM KVM avec interface pontée sur le LAN
echo "Création de la VM $VM_NAME sur le pont réseau $BRIDGE..."
virt-install \
  --name "$VM_NAME" \
  --memory "$RAM_MB" \
  --vcpus "$CPUS" \
  --disk path="$DISK",format=qcow2,bus=virtio \
  --disk path="$ISO",device=cdrom \
  --os-variant debian12 \
  --network bridge="$BRIDGE",model=virtio \
  --graphics none \
  --noautoconsole \
  --import

echo "Attente de l'adresse IP sur $BRIDGE..."
IP=""
for _ in $(seq 1 60); do
  IP=$(virsh domifaddr "$VM_NAME" --source arp 2>/dev/null | awk '/ipv4/ {split($4,a,"/"); print a[1]; exit}')
  [ -n "$IP" ] && break
  sleep 5
done

if [ -n "$IP" ]; then
  echo "$IP" > "$BUILD/ip_vm.txt"
  echo "VM prête sur $IP !"
  echo "Mettez MARANYSE_VM_IP=$IP dans deploy/vm-common/config.env puis lancez : bash deploy/vm-common/installer_controle.sh"
else
  echo "VM démarrée. Vérifiez son IP avec : virsh domifaddr $VM_NAME --source arp"
fi
