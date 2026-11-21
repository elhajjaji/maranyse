# MaranYSE — contrôle parental et bureau multi-sessions pour les enfants

![MaranYSE](app/assets/banniere.jpeg)

MaranYSE fournit un bureau Linux complet (XFCE, Firefox, LibreOffice, GCompris, Tux Paint, Thonny) accessible en Bureau à distance (RDP), piloté par un tableau de bord web HTTPS réservé aux parents (plages horaires, filtrage web/logiciels, quotas, suivi d'activité, gestion des comptes).

---

## 3 modes de déploiement

### Mode 1 — VM Windows (Hyper-V)
1. Copier `deploy/vm-common/config.env.example` vers `deploy/vm-common/config.env` et adapter si besoin.
2. Créer la VM Hyper-V (PowerShell administrateur) : `deploy/vm-windows/creer_vm.ps1`.
3. Déployer MaranYSE (Git Bash) : `bash deploy/vm-common/installer_controle.sh`.
- Accès parents : `https://<IP_VM>:8080`
- Accès enfants (RDP) : `<IP_VM>:3389`

### Mode 2 — 100 % Docker
#### Sous hôte Linux (IP LAN dédiée via `ipvlan` L2)
```bash
cd deploy/docker
cp .env.example .env   # renseigner MARANYSE_LAN_IP (ex. 192.168.1.50), MARANYSE_LAN_IFACE, MARANYSE_LOGIN, MARANYSE_PASSWORD
docker compose up -d --build
```
- Accès parents : `https://<MARANYSE_LAN_IP>:8080`
- Accès enfants (RDP) : `<MARANYSE_LAN_IP>:3389`

#### Sous Docker Desktop Windows / macOS (`bridge` + redirection de ports)
```powershell
cd deploy/docker
copy .env.example .env
docker compose -f docker-compose.windows.yml up -d --build
```
- Accès parents : `https://localhost:8080`
- Accès enfants (RDP) : `127.0.0.1:3390` (port `3390` par défaut pour éviter le conflit avec le service RDP de Windows sur `3389`)

### Mode 3 — VM Linux (KVM / libvirt)
1. Copier `deploy/vm-common/config.env.example` vers `deploy/vm-common/config.env` (et définir `MARANYSE_BRIDGE=br0`).
2. Créer la VM Debian 12 en bridge sur votre réseau local : `bash deploy/vm-linux/creer_vm_linux.sh`.
3. Renseigner `MARANYSE_VM_IP` dans `deploy/vm-common/config.env` puis déployer : `bash deploy/vm-common/installer_controle.sh`.
- Accès parents : `https://<IP_VM>:8080`
- Accès enfants (RDP) : `<IP_VM>:3389`

---

## Organisation du projet

| Dossier | Rôle |
|---|---|
| `app/` | Code applicatif Espace Parents (`tableau.py`, `logique.py`, `style.py`, `i18n/`, `assets/`, `Dockerfile`) |
| `bureau/` | OS de base du bureau enfants (`Dockerfile`, `entrypoint.sh`, `logiciels.sh`, `firefox-net.c`, `sans-internet*.c`, `xfce/`) |
| `deploy/docker/` | Déploiement 100 % Docker (`docker-compose.yml`, `docker-compose.windows.yml`, `.env.example`) |
| `deploy/vm-windows/` | Scripts Hyper-V pour hôte Windows (`creer_vm.ps1`, `charge_hote.ps1`, diagnostics) |
| `deploy/vm-linux/` | Script KVM/libvirt pour hôte Linux (`creer_vm_linux.sh`) |
| `deploy/vm-common/` | Scripts de provisionnement partagés entre VM Windows et VM Linux (`installer_controle.sh`, `installer_tableau.sh`, `config.env.example`) |
| `tests/` | Scénarios et vérifications automatisés |

## Accès aux interfaces

- **Espace parents (HTTPS)** : `https://<IP_OU_LOCALHOST>:8080` (accepter le certificat auto-signé au premier accès, ou télécharger le certificat depuis la page **Aide**).
- **Bureau enfants (RDP / Windows App)** : utiliser l'adresse et le port affichés dans l'infobulle **RDP** de chaque enfant (sur la page **Accueil** ou **Comptes**), avec son identifiant et son mot de passe.

## Sécurité et fichiers locaux

Les secrets (`deploy/vm-common/build/`, `deploy/vm-common/seed/`, `deploy/vm-common/config.env`, `.env`, `deploy/docker/.env`) ne sont jamais suivis par Git.
Sur Docker, les identifiants de l'espace parents proviennent de `deploy/docker/.env` (`MARANYSE_LOGIN` / `MARANYSE_PASSWORD`).
