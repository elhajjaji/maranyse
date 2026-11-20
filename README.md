# MaranYSE — One VM, Many Accounts

![MaranYSE](container/logo_web/banniere.jpeg)

Un ordinateur pour toute la famille, sous l'œil bienveillant des parents.
MaranYSE est un **bureau Linux multi-sessions pour les enfants**, avec un **espace parents** web pour régler, suivre et protéger.

- **Une VM Hyper-V** (Debian 12) qui fait tourner un conteneur Docker **XFCE + xrdp** : chaque enfant se connecte avec le
  Bureau à distance, sur son propre compte, en même temps que les autres.
- **Espace parents** (`http://<ip-de-la-vm>:8080`) : planning (vert / orange / rouge), temps d'écran, règles par site et
  par application, pause à distance, messages, statistiques, logiciels à installer, puissance (processeur, mémoire, disque),
  comptes, 10 langues et plusieurs thèmes.

## Fonctions

| | |
|---|---|
| Planning | Grille par demi-heure : vert (accès complet), orange (règles), rouge (pas d'accès), temps d'écran maximum par jour |
| Règles | Internet libre / filtré (DNS familial) / coupé ; sites et applications bloqués ou limités ; règles communes + exceptions |
| Contournements | Internet réservé à Firefox, pas de VPN, proxy, DoH ni programme téléchargé ; outils (Python, VS Code) jamais bloqués |
| Pause et messages | Écran figé à distance (applications gardées), messages affichés chez l'enfant, fin de session propre |
| Statistiques | Temps par enfant, par application, par site, heure par heure ; ressources (processeur, mémoire, internet, disque) |
| Logiciels | Catalogue de ~140 logiciels éducatifs, bureautiques, de création, de programmation et de jeux, installés d'un clic |
| Puissance | Part de l'ordinateur hôte laissée aux enfants (curseur), quota disque par enfant, charge de la VM et du PC |
| Langues | Espace parents et bureau des enfants en français, anglais, espagnol, allemand, portugais, russe, arabe, hindi, chinois, japonais |

## Organisation du dépôt

| Dossier | Contenu |
|---|---|
| `container/` | Image Docker du bureau des enfants (`Dockerfile`, `entrypoint.sh`, lanceurs C qui réservent internet à Firefox, bureau « façon Windows » dans `bureau/`, logos dans `logo_web/`) |
| `vm/` | Espace parents : `tableau.py` (pages web), `logique.py` (règles appliquées toutes les 30 s, statistiques), `logiciels.py`, `i18n.py` + `i18n/` (traductions), `themes.py`, scripts d'installation et de maintenance |
| `tests/` | `scenario.py` : scénarios graphiques de bout en bout (vraies sessions Bureau à distance, captures, rapport HTML) |

## Installation (résumé)

1. Créer la VM : `vm/creer_vm.ps1` (PowerShell administrateur, Hyper-V).
2. Déployer le bureau des enfants et l'espace parents : `bash vm/installer_controle.sh` (Git Bash).
3. Ouvrir `http://<ip-de-la-vm>:8080`, créer les comptes des enfants dans **Comptes**.
4. Les enfants se connectent avec **Connexion Bureau à distance** sur `<ip-de-la-vm>`.

Les secrets (clé SSH, mots de passe, jetons) restent dans `vm/build/`, qui n'est jamais publié.

## Tests

Dans la VM : `cd ~/tests && python3 scenario.py` (tous les groupes) ou `python3 scenario.py A B C` (quelques groupes).
Les comptes de test sont temporaires et supprimés à la fin ; les vrais comptes ne sont jamais touchés.
