# MaranYSE — One VM, Many Accounts

![MaranYSE](container/logo_web/banniere.jpeg)

Un ordinateur pour toute la famille, sous l'œil bienveillant des parents.
MaranYSE est un **bureau Linux multi-sessions pour les enfants**, avec un **espace parents** web (HTTPS) pour régler, suivre et protéger.

Chaque mode ci-dessous attribue au bureau des enfants sa **propre adresse IP sur le réseau local** (distincte de la machine hôte), permettant aux enfants de se connecter avec le **Bureau à distance** standard (`:3389`) et aux parents d'ouvrir l'espace parents (`https://<ip-dediee>:8080`).

## Fonctions

| | |
|---|---|
| Planning | Grille 15 min ou réglage **à la minute (`HH:MM`)** : vert (accès complet), orange (règles), rouge (pas d'accès), temps d'écran max/jour, modèle Tout rouge, « Appliquer à tous » |
| Règles | Internet libre / filtré (DNS familial) / coupé ; sites et applications bloqués ou limités (dès 1 min/jour) ; arrêt automatique des apps et onglets/vidéos épuisés ; règles communes + exceptions |
| Contournements | Internet réservé à Firefox, pas de VPN, proxy, DoH, IPv6 ni programme téléchargé ; accès au LAN et à `:8080` bloqué pour les enfants ; outils (Python, VS Code) jamais bloqués |
| Pause et messages | Écran figé à distance (individuel ou **Pause tous** / **Message à tous**), fin de session propre |
| Statistiques | Temps par enfant, par application, **navigation web Firefox par site** (Simple / Plus de détail), heure par heure ; ressources (processeur, mémoire, internet, disque) |
| Logiciels | Catalogue de ~140 logiciels éducatifs, bureautiques, de création, de programmation et de jeux, installés d'un clic |
| Puissance | Part de l'ordinateur hôte laissée aux enfants (curseur), quota disque par enfant, charge de la VM et du PC |
| Ergonomie & Langues | Couleur personnalisable par enfant (bande à droite + relief), sélection persistante entre menus, alerte si non enregistré, HTTPS intégré, 10 langues et plusieurs thèmes |

## 3 modes de déploiement

### Mode 1 — VM Windows (Hyper-V)
1. Copier `vm/config.env.example` vers `vm/config.env` et adapter si besoin.
2. Créer la VM (PowerShell administrateur) : `powershell -ExecutionPolicy Bypass -File vm\creer_vm.ps1`
3. Déployer MaranYSE (Git Bash) : `bash vm/installer_controle.sh`

### Mode 2 — Docker (hôte Linux, IP LAN dédiée via `macvlan` / `ipvlan`)
1. Copier `.env.example` vers `.env` et renseigner `MARANYSE_LAN_IP` (ex. `192.168.1.50`), `MARANYSE_LAN_IFACE` (`eth0` en `macvlan`, ou `wlan0` avec `MARANYSE_NET_DRIVER=ipvlan`), `MARANYSE_LOGIN` et `MARANYSE_PASSWORD`.
2. Lancer les deux conteneurs (`bureau-enfants` + `maranyse-parents`) :
   ```bash
   docker compose up -d --build
   ```
3. Ouvrir `https://<MARANYSE_LAN_IP>:8080` (parents) et `<MARANYSE_LAN_IP>` en Bureau à distance (enfants).

### Mode 3 — VM Linux (KVM / libvirt, IP LAN dédiée via pont réseau)
1. Copier `vm/config.env.example` vers `vm/config.env` (et définir `MARANYSE_BRIDGE=br0` si votre pont a un autre nom).
2. Créer la VM Debian 12 : `bash vm/creer_vm_linux.sh`
3. Renseigner `MARANYSE_VM_IP` dans `vm/config.env` puis déployer : `bash vm/installer_controle.sh`

## Organisation du dépôt

| Dossier | Contenu |
|---|---|
| `container/` | Image Docker du bureau des enfants (`Dockerfile`, `entrypoint.sh`, lanceurs C qui réservent internet à Firefox, `bureau/`, `logo_web/`) et `Dockerfile.parents` (mode Docker) |
| `vm/` | Espace parents (`tableau.py`, `style.py`, `stats.py`, `aide.py`, `logique.py`, `logiciels.py`, `i18n.py`, `themes.py`) et scripts VM Windows / VM Linux |
| `docker-compose.yml` | Orchestration du Mode 2 (100 % Docker avec IP LAN dédiée) |
| `tests/` | `scenario.py` : scénarios graphiques de bout en bout (vraies sessions Bureau à distance, captures, rapport HTML) |

Les secrets (`vm/build/`, `vm/seed/`, `vm/config.env`, `.env`) ne sont jamais publiés.

## Tests

Dans la VM : `cd ~/tests && python3 scenario.py` (tous les groupes) ou `python3 scenario.py A B C` (quelques groupes).
Les comptes de test sont temporaires et supprimés à la fin ; les vrais comptes ne sont jamais touchés.
