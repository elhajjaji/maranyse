"""MaranYSE — page d'aide et documentation intégrée de l'espace parents."""
from style import e, ic

AIDE_SECTIONS = [("presentation", "Présentation"), ("fonctionnement", "Comment ça marche"), ("premiers-pas", "Premiers pas"),
                 ("pages", "Les pages"), ("regles", "Planning et règles"), ("contournements", "Contournements"),
                 ("programmer", "Programmer"), ("logiciels", "Logiciels"), ("deploiement", "Déploiement"), ("maintenance", "Maintenance"),
                 ("depannage", "Dépannage"), ("limites", "Limites connues"), ("a-propos", "À propos")]


AIDE_PRESENTATION = r"""<div class="help-goals">
<div><b>🖥️ Un bureau pour chacun</b><p>Plusieurs enfants en même temps, chacun dans sa session : fichiers privés, applications éducatives (GCompris, Tux Paint,
LibreOffice, Python…), Firefox.</p></div>
<div><b>⏰ Un temps d'écran maîtrisé</b><p>Planning par demi-heure, maximum par jour, avertissement 5 min avant la fin, pause à distance, bonus ponctuel.</p></div>
<div><b>🛡️ Un internet adapté</b><p>Filtrage des sites adultes et dangereux, blocage ou limite de YouTube, réseaux sociaux, jeux… et résistance aux contournements.</p></div>
<div><b>👀 Veiller sans surveiller</b><p>Statistiques claires (quelles applications, quand, combien de temps) pour en parler avec les enfants, pas pour les espionner.</p></div>
</div>"""

AIDE_FONCTIONNEMENT = r"""<div class="arch">
<div class="arch-users"><div class="arch-box kid">{IC_USERS}<b>Enfants</b><span>Connexion Bureau à distance<br>vers <code>{VM}</code></span></div>
<div class="arch-box parent">{IC_MONITOR}<b>Parents</b><span>Navigateur<br><code>https://{VM}:8080</code></span></div></div>
<div class="arch-arrow">▼</div>
<div class="arch-host"><div class="arch-title">PC Windows de la maison · Hyper-V</div>
<div class="arch-vm"><div class="arch-title">Machine virtuelle Debian « bureau-enfants » · adresse {VM} sur la box</div>
<div class="arch-row"><div class="arch-box ct"><b>Bureau des enfants</b><span>Conteneur Docker : XFCE + xrdp (port 3389)<br>une session par enfant, pare-feu et DNS par enfant</span></div>
<div class="arch-box svc"><b>Espace parents</b><span>Service <code>tableau-parent</code> (port 8080)<br>cette page + la boucle qui applique les règles toutes les 30 s</span></div></div>
</div></div></div>
<p>Toutes les <b>30 secondes</b>, MaranYSE relève ce que fait chaque enfant (application au premier plan, titre de la fenêtre) et applique les règles :
verrouillage du compte en rouge ou en pause, pare-feu et filtrage DNS par enfant, droits sur les applications, messages à l'écran.
Un changement fait ici est donc appliqué en moins de 30 secondes (la pause et les messages : immédiatement).</p>"""

AIDE_PREMIERS_PAS = r"""<ol class="help-steps">
<li><b>Ouvrir l'espace parents</b> : <code>https://{VM}:8080</code> (identifiant et mot de passe parent ; une redirection automatique depuis <code>http://</code> est active). Astuce : ajoutez-le à l'écran d'accueil du téléphone.</li>
<li><b>Créer les comptes</b> des enfants dans <a href="/?p=comptes">Comptes</a> (le mot de passe peut être créé automatiquement).</li>
<li><b>Régler le planning</b> de chacun dans <a href="/?p=planning">Planning</a> (modèle « École » pour commencer).</li>
<li><b>Choisir les règles</b> de l'orange dans <a href="/?p=regles">Règles</a> : d'abord « Tous les enfants », puis les exceptions.</li>
<li><b>Connecter un enfant</b> : sur un PC Windows, ouvrir <b>Connexion Bureau à distance</b> (<code>mstsc</code>), ordinateur <code>{VM}</code>,
puis son identifiant et son mot de passe. Sur Mac, tablette ou téléphone : l'application <b>Windows App</b> (ex-Microsoft Remote Desktop).</li>
</ol>"""

AIDE_REGLES = r"""<div class="help-legend">
<div style="background:var(--green-soft)"><i class="cV"></i><span><b>Vert</b> · accès complet, aucune restriction</span></div>
<div style="background:var(--orange-soft)"><i class="cO"></i><span><b>Orange</b> · accès avec les règles de la page Règles</span></div>
<div style="background:var(--red-soft)"><i class="cR"></i><span><b>Rouge</b> · pas d'accès : message, puis session fermée après 1 minute</span></div></div>
<ul class="help-list">
<li><b>Temps d'écran maximum</b> (Planning) : une fois atteint, l'enfant passe en rouge pour la journée. Avertissement 5 minutes avant.</li>
<li><b>Pause</b> (Accueil) : écran figé tout de suite, clavier et souris coupés, applications gardées ouvertes. « Reprendre » rend la main.</li>
<li><b>+30 min</b> : accès complet pendant 30 minutes, même en rouge ou après le maximum du jour.</li>
<li><b>Message</b> : s'affiche immédiatement sur l'écran de l'enfant.</li>
<li><b>Règles communes et exceptions</b> : une règle sur « Tous les enfants » s'applique à chacun ; une règle sur un enfant (même site ou application) la remplace,
y compris « Autoriser » pour lever un blocage commun.</li>
<li><b>Limites par application ou site</b> : comptées sur toute la journée ; quand la limite est atteinte, l'application ou l'onglet du site (vidéo incluse) est fermé et bloqué automatiquement jusqu'au lendemain.</li>
<li><b>Actions pour tous et repère visuel</b> : sur l'Accueil, <b>Pause tous</b> / <b>Message à tous</b> agissent sur toute la famille ; sur le Planning, <b>Appliquer à tous</b> copie la semaine sur tous les comptes. Lorsqu'un seul enfant est sélectionné, sa couleur (modifiable dans Comptes) s'affiche en bande à droite et sur les cartes pour éviter toute erreur.</li>
</ul>"""

AIDE_CONTOURNEMENTS = r"""<p>Dans <a href="/?p=regles&s=_tous">Règles</a>, carte « Contournements ».
Les <b>outils ne sont jamais bloqués</b> (Python, VS Code, terminal…) : un contournement, c'est changer d'adresse IP (VPN, proxy, tunnel)
ou sortir du filtrage des sites, et cela dépend de réglages que seul l'administrateur peut changer.
Chaque réglage s'autorise ou s'interdit pour tous, avec des exceptions par enfant. Il s'applique à toute heure.</p>
<div class="tw"><table class="t"><tr><th>Réglage</th><th>Si « Interdit »</th></tr>
<tr><td><b>Internet pour les programmes autres que Firefox</b></td><td>Seul Firefox (filtré) va sur internet. VPN, proxys, tunnels et scripts
n'ont aucun accès réseau : impossible de changer d'adresse IP ou d'échapper au filtrage.</td></tr>
<tr><td><b>DNS sécurisé (DoH)</b></td><td>Les serveurs DNS publics et « DNS sur HTTPS » sont injoignables : le filtrage ne peut pas être contourné par ce biais.</td></tr>
<tr><td><b>Programmes téléchargés ou copiés</b></td><td>Impossible de lancer un programme enregistré dans son dossier ou un dossier temporaire
(VPN portable, autre navigateur, jeu téléchargé…). Réglage commun à tous les enfants.</td></tr>
<tr><td><b>Installer des bibliothèques Python (pip)</b></td><td>pip install refusé. Si « Autorisé » : seulement depuis PyPI, le dépôt officiel,
par un relais qui refuse tout autre site.</td></tr>
</table></div>
<p class="muted small">Toujours actifs : VPN, Tor, proxys et tunnels refusés à l'installation de logiciels ; un programme ouvert depuis Firefox
(« Ouvrir avec… ») n'a pas l'accès internet de Firefox ; pas de droits administrateur, pas d'accès aux fichiers des autres enfants ;
Firefox verrouillé (pas d'extensions, de proxy, de navigation privée ni d'about:config) ; DNS chiffré (port 853) bloqué, DNS extérieurs redirigés vers le filtre.
Quand l'internet est « Filtré », les <b>sites proxy et VPN</b> sont bloqués et la recherche Google et YouTube (mode restreint) sont imposés.</p>"""

AIDE_PROGRAMMER = r"""<p>Réglage recommandé : <b>Internet pour les autres programmes : Interdire</b>.
Les enfants peuvent alors apprendre à programmer (Python, VS Code, terminal) sans pouvoir contourner le filtrage.</p>
<ul class="help-list">
<li><b>Thonny</b> (menu Applications → Développement) : éditeur Python pour débuter, dans la langue de l'enfant. Bouton ▶ pour exécuter.</li>
<li>Bibliothèques incluses : <code>turtle</code> (dessin), <code>pygame</code> (jeux), <code>tkinter</code> (fenêtres).</li>
<li>Un script se lance avec <code>python3 mon_script.py</code> ou ▶ dans Thonny (pas <code>./mon_script.py</code>, bloqué par l'interdiction des programmes téléchargés).</li>
<li><code>pip install nom</code> fonctionne (réglage « pip » autorisé) : uniquement depuis PyPI, installé dans le dossier de l'enfant.
Même installée, une bibliothèque ne peut se connecter à rien d'autre.</li>
<li>Les bibliothèques qui contiennent du code compilé (numpy, par exemple) ne se chargent pas tant que « Programmes téléchargés » est interdit.</li>
</ul>"""

AIDE_LOGICIELS = r"""<p>Page <a href="/?p=logiciels">Logiciels</a> : un clic installe un outil <b>pour tous les enfants</b>, dans leur menu Applications.
L'installation se fait en arrière-plan (quelques minutes), les enfants peuvent continuer à travailler.</p>
<ul class="help-list">
<li><b>Catalogue</b> : VS Code, Scratch, KTurtle, Geany, Godot (programmer) ; Inkscape, GIMP, Krita, Blender, Audacity, MuseScore (créer) ;
Stellarium, KGeography, Kalzium, Step (découvrir) ; Tux Math, Tux Typing, Klavaro, KBruch (apprendre) ; quelques jeux.</li>
<li><b>Autre logiciel</b> : n'importe quel paquet de Debian 12, par son nom. Les outils de contournement (VPN, Tor, proxys, sudo) sont refusés.</li>
<li>Un logiciel installé est <b>autorisé pour tous</b> ; il devient une application comme les autres dans Règles (bloquer, limiter, pour tous
ou pour un enfant) et dans les Statistiques.</li>
<li>Il n'a <b>pas internet</b> tant que « Internet pour les programmes autres que Firefox » est interdit : pas de jeu en ligne,
pas de boutique d'extensions dans VS Code.</li>
<li><b>VS Code</b> est préparé pour chaque enfant, y compris les comptes créés plus tard : dans la langue de l'enfant, extension Python installée,
mises à jour et assistant IA désactivés. <b>Ctrl+F5</b> exécute le programme Python ouvert. Son terminal intégré est une ligne de commande :
bloquer « Terminal » ne le bloque pas.</li>
<li>Les logiciels font partie de l'image du bureau : ils restent après une mise à jour de MaranYSE. S'il en manque
(bureau recréé à la main), ils sont réinstallés automatiquement dans les 10 minutes.</li>
</ul>"""

AIDE_DEPLOIEMENT = r"""<p>L'adresse de la VM ou du conteneur (<code>{VM}</code> actuellement) et les comptes initiaux se configurent dans <code>deploy/vm-common/config.env</code> (mode VM) ou <code>deploy/docker/.env</code> (mode Docker).</p>
<div class="tw"><table class="t"><tr><th>Mode / Étape</th><th>Comment</th></tr>
<tr><td><b>1. VM Windows (Hyper-V)</b></td><td>PowerShell <b>en administrateur</b> :<br><code>powershell -ExecutionPolicy Bypass -File deploy\vm-windows\creer_vm.ps1</code><br>
Active Hyper-V si besoin, crée la VM Debian sur le réseau local, démarrage automatique avec Windows.</td></tr>
<tr><td><b>2. VM Linux (KVM)</b></td><td>Terminal Linux :<br><code>bash deploy/vm-linux/creer_vm_linux.sh</code><br>
Crée la VM Debian 12 en bridge sur votre réseau local (<code>MARANYSE_BRIDGE=br0</code>).</td></tr>
<tr><td><b>3. Installer ou mettre à jour (VM)</b></td><td>Git Bash / Terminal :<br><code>bash deploy/vm-common/installer_controle.sh</code><br>
Reconstruit le bureau des enfants (<code>bureau/</code>), met à jour l'espace parents (<code>app/</code>).
<b>Ferme les sessions ouvertes</b> : prévenez les enfants (bouton Message) avant.</td></tr>
<tr><td><b>4. Mode 100 % Docker</b></td><td>Linux (IP LAN dédiée <code>ipvlan</code>) : <code>cd deploy/docker && docker compose up -d --build</code><br>
Docker Desktop Windows : <code>cd deploy/docker && docker compose -f docker-compose.windows.yml up -d --build</code></td></tr>
<tr><td><b>5. Vérifier</b></td><td>Scénario de test graphique (vraies sessions, captures) : <code>tests/scenario.py</code>.
Comptes de test temporaires, rapport HTML avec captures ; vos réglages sont restaurés à la fin.</td></tr>
</table></div>
<p class="muted small">Sur chaque carte enfant (Accueil et Comptes), l'infobulle <b>RDP</b> indique l'adresse et le port exacts pour la Connexion Bureau à distance.</p>"""

AIDE_MAINTENANCE = r"""<ul class="help-list">
<li><b>Redémarrer le bureau</b> (bas du menu) : ferme toutes les sessions et redémarre le bureau des enfants. Utile si quelque chose semble bloqué.</li>
<li><b>Sauvegarde</b> : copier <code>/srv/bureau/home</code> (fichiers des enfants), <code>/srv/bureau/secrets</code> (comptes), <code>~/controle.json</code> (règles)
et <code>~/stats.db</code> (statistiques). Le disque virtuel de la VM est <code>vm\bureau-enfants.vhdx</code>.</li>
<li><b>Mémoire</b> : la VM utilise la mémoire dynamique de Hyper-V ; compter environ 1,5 Go par enfant connecté avec Firefox.</li>
<li><b>Mises à jour de sécurité</b> : reconstruire le bureau de temps en temps (étape 2 ci-dessus) récupère les dernières versions de Debian et Firefox.</li>
</ul>"""

AIDE_DEPANNAGE = r"""<details class="more faq"><summary>Écran noir à la connexion</summary><p>Attendez 30 secondes puis reconnectez-vous :
MaranYSE répare automatiquement les droits du dossier de connexion. Si ça persiste : « Redémarrer le bureau ».</p></details>
<details class="more faq"><summary>Un enfant n'arrive pas à se connecter</summary><p>Vérifiez sur l'Accueil : <b>rouge</b> (horaire ou temps du jour épuisé)
ou <b>pause</b> → le compte est verrouillé, c'est normal (« +30 min » ou « Reprendre » pour débloquer). Sinon, vérifiez son mot de passe dans Comptes.</p></details>
<details class="more faq"><summary>Un site devrait être bloqué mais s'ouvre encore</summary><p>Le blocage s'applique en moins de 30 s : MaranYSE coupe les connexions ouvertes et ferme l'onglet ou Firefox si le site vient d'être bloqué. Vérifiez surtout que l'enfant est bien en <b>orange</b> dans le Planning (en vert, rien n'est bloqué).</p></details>
<details class="more faq"><summary>Une application ne s'ouvre pas</summary><p>Elle est peut-être bloquée ou sa limite du jour est atteinte (page Règles de l'enfant).</p></details>
<details class="more faq"><summary>L'espace parents ne répond plus</summary><p>Vérifiez que la VM tourne (Gestionnaire Hyper-V) et que le PC Windows est allumé.
Elle redémarre toute seule avec Windows.</p></details>"""

AIDE_LIMITES = r"""<ul class="help-list">
<li>Le filtrage des sites passe par le DNS : visiter un site <b>par son adresse IP</b> reste possible dans Firefox (sans intérêt pour les grands sites).</li>
<li>L'espace parents est chiffré en <b>HTTPS</b> avec un certificat local généré automatiquement. Au premier accès, acceptez l'avertissement du navigateur (ou installez <a href="/maranyse.crt">le certificat MaranYSE</a> dans vos certificats de confiance).</li>
<li>Recherche sécurisée imposée sur Google et YouTube, pas sur Bing. Pas d'alertes envoyées au téléphone.</li>
<li>En <b>vert</b>, l'internet n'est pas filtré : les sites proxy y sont accessibles (c'est le principe de l'accès complet).</li>
<li>Avec « Programmes téléchargés : Interdit », Netflix et Disney+ peuvent ne pas fonctionner dans Firefox (module de lecture protégé).</li>
</ul>"""

APROPOS = r"""<p><b>MaranYSE</b> · un ordinateur partagé, des comptes pour chaque enfant, sous le contrôle des parents.</p>
<p class="muted small">Logiciels libres utilisés : Debian, XFCE, xrdp, Firefox ESR, Docker, dnsmasq, iptables, Thonny, GCompris, Tux Paint, LibreOffice.
Filtrage familial par CleanBrowsing Family. Relais pip : tinyproxy.</p>"""


def render_aide(host, v_img, shell_fn):
    vm = (host or "").split(":")[0] or "<ip-de-la-vm>"
    toc = "".join(f'<a href="#{k}">{e(v)}</a>' for k, v in AIDE_SECTIONS)
    sec = lambda k, title, body, icon: (f'<section class="card stack help-sec" id="{k}"><div class="chead"><span class="cico">{ic(icon, 18)}</span>'
                                       f'<h2>{title}</h2></div>{body}</section>')
    pages = [("home", "Accueil", "Chaque enfant d'un coup d'œil : en ligne ou non, ce qui est ouvert, son niveau d'accès et le temps du jour. "
              "Boutons rapides : <b>Pause</b>, <b>Message</b>, <b>+30 min</b>, <b>Déconnecter</b>, « … » pour son mot de passe, ainsi que <b>Pause tous</b> et <b>Message à tous</b>."),
             ("calendar", "Planning", "Deux vues au choix : <b>Grille 15 min</b> (peinture rapide) ou <b>À la minute</b> (plages exactes <code>HH:MM</code>). Modèles École / Vacances / Tout vert / Tout orange / <b>Tout rouge</b>, "
              "copie d'un jour sur la semaine, bouton <b>Appliquer à tous</b>, <b>temps d'écran maximum par jour</b> à la minute, et alerte avant de perdre des modifications non enregistrées."),
             ("shield", "Règles", "Ce qui s'applique en orange : internet libre, filtré ou coupé ; sites et applications <b>bloqués</b>, <b>limités</b> "
              "(à la minute près, dès 1 min/jour) ou <b>autorisés</b>. Règles communes + exceptions par enfant. En bas : les <b>contournements</b>."),
             ("chart", "Statistiques", "Vues <b>Ensemble</b>, <b>Par enfant</b>, <b>Par application</b> : courbes d'évolution, temps par jour, heures d'utilisation, "
              "<b>Navigation web (Firefox)</b> avec temps par site et bascule <b>Simple / Plus de détail</b> (courbes, matrice Sites × Enfants, pages consultées), chronologie heure par heure, historique."),
             ("box", "Logiciels", "Installer un outil pour tous les enfants d'un clic (VS Code, Scratch, Stellarium…) ou n'importe quel "
              "paquet Debian ; le désinstaller."),
             ("cpu", "Puissance", "Un <b>curseur</b> règle la part de l'ordinateur (processeur et mémoire) que les enfants peuvent utiliser, "
              "en pourcentage de ce que l'ordinateur possède ; un second fixe l'<b>espace disque</b> de chaque enfant. "
              "Appliqué tout de suite, sans fermer les sessions."),
             ("users", "Comptes", "Ajouter un enfant (avec copie des réglages d'un autre), renommer, changer un mot de passe, choisir sa <b>couleur</b> "
              "(bande à droite, cartes, graphiques), supprimer (en gardant ou non ses fichiers et statistiques). La sélection d'un enfant reste active entre les menus.")]
    pages_html = "".join(f'<div class="help-page"><span class="cico">{ic(i, 18)}</span><div><b>{t}</b><p>{d}</p></div></div>' for i, t, d in pages)
    body = f"""<div class="help-layout"><nav class="toc card">{toc}</nav><div class="stack">

<section class="card help-hero"><img src="/logo-hd.jpg?v={v_img}" alt="MaranYSE"><div>
<h2><span class="wm-a">Maran</span><span class="wm-b">YSE</span> : un ordinateur pour toute la famille, sous l'œil bienveillant des parents</h2>
<p>MaranYSE transforme <b>une seule machine</b> en plusieurs ordinateurs personnels pour les enfants : chacun a son compte, son bureau, ses fichiers,
et s'y connecte depuis n'importe quel PC de la maison. Les parents fixent les horaires, filtrent internet, mettent en pause ou envoient un message,
et suivent l'utilisation — depuis cette page, sur ordinateur ou téléphone.</p>
<p class="muted small">« One VM · Many Accounts » : une machine virtuelle, autant de comptes que d'enfants.</p></div></section>

{sec("presentation", "Présentation et objectifs", AIDE_PRESENTATION, "sparkle")}

{sec("fonctionnement", "Comment ça marche", AIDE_FONCTIONNEMENT, "app")}

{sec("premiers-pas", "Premiers pas", AIDE_PREMIERS_PAS, "check")}

{sec("pages", "Les pages de l'espace parents", '<div class="help-pages">{PAGES}</div>', "home")}

{sec("regles", "Planning, règles et actions", AIDE_REGLES, "calendar")}

{sec("contournements", "Contournements : ce que les enfants ne peuvent pas faire", AIDE_CONTOURNEMENTS, "shield")}

{sec("programmer", "Programmer en toute sécurité", AIDE_PROGRAMMER, "edit")}

{sec("logiciels", "Ajouter des logiciels pour tous", AIDE_LOGICIELS, "box")}

{sec("deploiement", "Déploiement", AIDE_DEPLOIEMENT, "power")}

{sec("maintenance", "Maintenance", AIDE_MAINTENANCE, "clock")}

{sec("depannage", "Dépannage", AIDE_DEPANNAGE, "msg")}

{sec("limites", "Limites connues", AIDE_LIMITES, "ban")}

{sec("a-propos", "À propos", APROPOS, "eye")}
</div></div>"""
    body = (body.replace("{VM}", e(vm)).replace("{IC_USERS}", ic("users", 18)).replace("{IC_MONITOR}", ic("monitor", 18))
            .replace("{PAGES}", pages_html))
    return shell_fn("aide", "Aide", "Comprendre et utiliser MaranYSE", body)
