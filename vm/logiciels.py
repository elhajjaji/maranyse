#!/usr/bin/env python3
"""MaranYSE — logiciels installés pour tous les enfants (page « Logiciels » de l'espace parents).

- Un catalogue d'outils choisis (VS Code, Scratch, Inkscape, Stellarium...) + n'importe quel paquet Debian.
- L'installation se fait dans le bureau des enfants, en root, en arrière-plan (une à la fois).
- Chaque logiciel installé devient une application gérable comme les autres : bloquer / limiter par enfant
  (Règles), temps d'utilisation (Statistiques).
- La liste est gardée dans ~/logiciels.json : elle est intégrée à l'image du bureau lors d'une mise à jour
  (installer_controle.sh) et, si le bureau est recréé sans eux, ils sont réinstallés automatiquement.

Utilisé aussi en ligne de commande :  python3 logiciels.py script   (script d'installation pour le Dockerfile)
"""
import base64, json, os, re, shlex, subprocess, sys, threading, time
from datetime import datetime

C = "bureau-enfants"
FICHIER = os.path.join(os.path.expanduser("~"), "logiciels.json")
PAQUET_RE = r"[a-z0-9][a-z0-9+.-]{1,60}"
# Outils de contournement : refusés même si les parents les demandent (le réseau des enfants est contrôlé
# par le pare-feu, mais autant ne pas les proposer)
INTERDITS = re.compile(r"^(tor|torsocks|torbrowser-launcher|obfs4proxy|onionshare.*|nyx|"
                       r"openvpn|network-manager-.*|wireguard.*|openconnect|vpnc.*|strongswan.*|libreswan|ocserv|softether.*|"
                       r"tailscale|zerotier-one|nebula|tinc|vtun|n2n|iodine|ptunnel.*|udptunnel|httptunnel|corkscrew|stunnel4|autossh|"
                       r"shadowsocks.*|v2ray|xray|trojan|hysteria|redsocks|tun2socks|"
                       r"proxychains.*|tinyproxy|privoxy|squid.*|polipo|dante-.*|3proxy|microsocks|ziproxy|sshuttle|i2p.*|"
                       r"dnscrypt-proxy|dnsmasq.*|unbound|bind9|knot-resolver|pdns-recursor|stubby|cloudflared|"
                       r"openssh-server|dropbear.*|sudo|doas|polkitd|pkexec)$")

DEPOTS = {   # dépôts externes officiels (signés)
    "microsoft": ("wget -qO- https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > /usr/share/keyrings/microsoft.gpg; "
                  "echo 'deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft.gpg] https://packages.microsoft.com/repos/code stable main' "
                  "> /etc/apt/sources.list.d/vscode.list",
                  "/etc/apt/sources.list.d/vscode.list"),
}

# clé -> nom, catégorie, description, paquets, taille indicative, badge (couleur, lettres), dépôt, préparation par enfant
CATALOGUE = {
    "vscode":     dict(nom="Visual Studio Code", cat="Programmer", desc="L'éditeur de code des pros : Python, web, etc. Dans la langue de l'enfant, avec l'extension Python déjà installée.",
                       paquets=["code"], taille="≈ 400 Mo", badge=("#0078d4", "VS"), depot="microsoft", prep="vscode",
                       # Chromium (moteur de VS Code) ne peut pas créer son bac à sable dans le conteneur : il plante
                       # avant de lire ~/.vscode/argv.json. Menu et commande « code » passent donc --no-sandbox.
                       post="sed -i 's#^Exec=/usr/share/code/code#Exec=/usr/share/code/code --no-sandbox#' /usr/share/applications/com.microsoft.VSCode*.desktop; "
                            "rm -f /usr/bin/code; printf '#!/bin/sh\nexec /usr/share/code/bin/code --no-sandbox \"$@\"\n' > /usr/bin/code; chmod 755 /usr/bin/code; "
                            "rm -f /usr/share/code/bin/code-tunnel"),
    "scratch":    dict(nom="Scratch", cat="Programmer", desc="Programmer avec des blocs à emboîter (version 1.4, hors ligne). Idéal pour commencer.",
                       paquets=["scratch"], taille="≈ 60 Mo", badge=("#f7a020", "S")),
    "kturtle":    dict(nom="KTurtle", cat="Programmer", desc="Apprendre à programmer en dessinant avec une tortue.",
                       paquets=["kturtle"], taille="≈ 150 Mo", badge=("#2e9e57", "Kt")),
    "geany":      dict(nom="Geany", cat="Programmer", desc="Éditeur de code léger et simple (Python, HTML, C...).",
                       paquets=["geany"], taille="≈ 10 Mo", badge=("#7a4fb3", "Ge")),
    "godot":      dict(nom="Godot 3", cat="Programmer", desc="Créer ses propres jeux vidéo en 2D et 3D.",
                       paquets=["godot3"], taille="≈ 80 Mo", badge=("#478cbf", "Go")),
    "inkscape":   dict(nom="Inkscape", cat="Créer", desc="Dessin vectoriel : logos, affiches, illustrations.",
                       paquets=["inkscape"], taille="≈ 250 Mo", badge=("#1f1f1f", "In")),
    "gimp":       dict(nom="GIMP", cat="Créer", desc="Retouche photo et dessin.",
                       paquets=["gimp"], taille="≈ 250 Mo", badge=("#5c5543", "Gi")),
    "krita":      dict(nom="Krita", cat="Créer", desc="Peinture numérique et bande dessinée.",
                       paquets=["krita"], taille="≈ 400 Mo", badge=("#3daee9", "Kr")),
    "blender":    dict(nom="Blender", cat="Créer", desc="Modélisation et animation 3D. Demande un ordinateur puissant.",
                       paquets=["blender"], taille="≈ 700 Mo", badge=("#e87d0d", "Bl")),
    "audacity":   dict(nom="Audacity", cat="Créer", desc="Enregistrer et monter du son.",
                       paquets=["audacity"], taille="≈ 60 Mo", badge=("#0000cc", "Au")),
    "musescore":  dict(nom="MuseScore", cat="Créer", desc="Écrire et écouter des partitions de musique.",
                       paquets=["musescore3"], taille="≈ 150 Mo", badge=("#1a70b8", "Mu")),
    "sweethome":  dict(nom="Sweet Home 3D", cat="Créer", desc="Dessiner des plans de maison et les visiter en 3D.",
                       paquets=["sweethome3d"], taille="≈ 250 Mo", badge=("#c0392b", "SH")),
    "stellarium": dict(nom="Stellarium", cat="Découvrir", desc="Planétarium : le ciel en temps réel, étoiles et planètes.",
                       paquets=["stellarium"], taille="≈ 300 Mo", badge=("#14213d", "St")),
    "kgeography": dict(nom="KGeography", cat="Découvrir", desc="Apprendre les pays, capitales et drapeaux.",
                       paquets=["kgeography"], taille="≈ 120 Mo", badge=("#16a085", "Kg")),
    "kalzium":    dict(nom="Kalzium", cat="Découvrir", desc="Le tableau périodique des éléments, en interactif.",
                       paquets=["kalzium"], taille="≈ 200 Mo", badge=("#8e44ad", "Ka")),
    "step":       dict(nom="Step", cat="Découvrir", desc="Simulateur de physique : forces, ressorts, gravité.",
                       paquets=["step"], taille="≈ 200 Mo", badge=("#d35400", "Sp")),
    "tuxmath":    dict(nom="Tux Math", cat="Apprendre", desc="Calcul mental en jouant.",
                       paquets=["tuxmath"], taille="≈ 40 Mo", badge=("#e67e22", "+")),
    "tuxtype":    dict(nom="Tux Typing", cat="Apprendre", desc="Apprendre à taper au clavier en jouant.",
                       paquets=["tuxtype"], taille="≈ 30 Mo", badge=("#27ae60", "Tt")),
    "klavaro":    dict(nom="Klavaro", cat="Apprendre", desc="Cours de dactylographie progressif.",
                       paquets=["klavaro"], taille="≈ 5 Mo", badge=("#2c3e50", "Kl")),
    "kbruch":     dict(nom="KBruch", cat="Apprendre", desc="Exercices sur les fractions.",
                       paquets=["kbruch"], taille="≈ 100 Mo", badge=("#2980b9", "½")),
    "minetest":   dict(nom="Minetest", cat="Jouer", desc="Jeu de construction en cubes (proche de Minecraft), en solo.",
                       paquets=["minetest"], taille="≈ 80 Mo", badge=("#5d8b2f", "Mt")),
    "supertuxkart": dict(nom="SuperTuxKart", cat="Jouer", desc="Course de karts.",
                       paquets=["supertuxkart"], taille="≈ 700 Mo", badge=("#f1c40f", "K")),
    "frozenbubble": dict(nom="Frozen Bubble", cat="Jouer", desc="Faire éclater des bulles de couleur.",
                       paquets=["frozen-bubble"], taille="≈ 60 Mo", badge=("#5dade2", "FB")),
    "echecs":     dict(nom="Échecs", cat="Jouer", desc="Jeu d'échecs contre l'ordinateur.",
                       paquets=["gnome-chess"], taille="≈ 20 Mo", badge=("#444444", "♞")),
    # --- Programmer (suite)
    "idle":       dict(nom="IDLE (Python)", cat="Programmer", desc="L'éditeur Python officiel : tout simple, pour écrire ses premiers programmes.",
                       paquets=["idle3"], taille="≈ 10 Mo", badge=("#3776ab", "Py")),
    "laby":       dict(nom="Laby", cat="Programmer", desc="Programmer une fourmi pour sortir d'un labyrinthe (Python, C, Java...). Parfait pour débuter.",
                       paquets=["laby"], taille="≈ 20 Mo", badge=("#c0392b", "La")),
    "codeblocks": dict(nom="Code::Blocks", cat="Programmer", desc="Environnement complet pour programmer en C et C++.",
                       paquets=["codeblocks", "g++"], taille="≈ 150 Mo", badge=("#2a7a3e", "CB")),
    "bluefish":   dict(nom="Bluefish", cat="Programmer", desc="Éditeur pour créer des pages web (HTML, CSS, JavaScript).",
                       paquets=["bluefish"], taille="≈ 15 Mo", badge=("#2b6cb0", "Bf")),
    "kate":       dict(nom="Kate", cat="Programmer", desc="Éditeur de code avancé : coloration, plusieurs fichiers, terminal intégré.",
                       paquets=["kate"], taille="≈ 120 Mo", badge=("#1d99f3", "Ka")),
    "sqlite":     dict(nom="DB Browser for SQLite", cat="Programmer", desc="Créer et explorer des bases de données, apprendre le SQL.",
                       paquets=["sqlitebrowser"], taille="≈ 30 Mo", badge=("#1f6feb", "DB")),
    "gitcola":    dict(nom="Git Cola", cat="Programmer", desc="Gérer les versions de ses projets avec Git, en mode graphique.",
                       paquets=["git-cola", "git"], taille="≈ 40 Mo", badge=("#f05133", "Gi")),
    # --- Bureautique
    "lomath":     dict(nom="LibreOffice Math", cat="Bureautique", desc="Écrire des formules de mathématiques, à insérer dans Writer.",
                       paquets=["libreoffice-math"], taille="≈ 5 Mo", badge=("#5c2d91", "∑")),
    "atril":      dict(nom="Atril", cat="Bureautique", desc="Lire les PDF et les livres numériques (manuels, fiches de l'école).",
                       paquets=["atril"], taille="≈ 10 Mo", badge=("#b7312c", "Pdf")),
    "xournalpp":  dict(nom="Xournal++", cat="Bureautique", desc="Prendre des notes à la main et annoter des PDF (fiches d'exercices).",
                       paquets=["xournalpp"], taille="≈ 25 Mo", badge=("#3b7dd8", "Xo")),
    "freeplane":  dict(nom="Freeplane", cat="Bureautique", desc="Cartes mentales pour organiser ses idées et réviser.",
                       paquets=["freeplane"], taille="≈ 150 Mo", badge=("#2f9e44", "Fp")),
    "zim":        dict(nom="Zim", cat="Bureautique", desc="Carnet de notes personnel organisé en pages, avec liens et images.",
                       paquets=["zim"], taille="≈ 15 Mo", badge=("#6b7280", "Zi")),
    "focuswriter": dict(nom="FocusWriter", cat="Bureautique", desc="Écrire des histoires et des rédactions sans distraction, en plein écran.",
                       paquets=["focuswriter"], taille="≈ 20 Mo", badge=("#445566", "Fw")),
    "dia":        dict(nom="Dia", cat="Bureautique", desc="Dessiner des schémas : organigrammes, diagrammes, circuits.",
                       paquets=["dia"], taille="≈ 20 Mo", badge=("#e67e22", "Di")),
    "scribus":    dict(nom="Scribus", cat="Bureautique", desc="Mise en page de journaux, magazines et affiches (comme un journal de classe).",
                       paquets=["scribus"], taille="≈ 120 Mo", badge=("#26a65b", "Sc")),
    "calibre":    dict(nom="Calibre", cat="Bureautique", desc="Bibliothèque de livres numériques : ranger, lire et convertir ses e-books.",
                       paquets=["calibre"], taille="≈ 350 Mo", badge=("#7a4b2a", "Ca")),
    # --- Créer (suite)
    "pencil2d":   dict(nom="Pencil2D", cat="Créer", desc="Dessin animé image par image, simple et amusant.",
                       paquets=["pencil2d"], taille="≈ 25 Mo", badge=("#2b8a9e", "P2")),
    "lmms":       dict(nom="LMMS", cat="Créer", desc="Composer de la musique électronique : boucles, instruments, effets.",
                       paquets=["lmms"], taille="≈ 120 Mo", badge=("#27ae60", "Lm")),
    "hydrogen":   dict(nom="Hydrogen", cat="Créer", desc="Boîte à rythmes : créer des rythmes de batterie.",
                       paquets=["hydrogen"], taille="≈ 60 Mo", badge=("#2c3e50", "Hy")),
    "tuxguitar":  dict(nom="TuxGuitar", cat="Créer", desc="Apprendre et écrire des morceaux de guitare (tablatures).",
                       paquets=["tuxguitar"], taille="≈ 80 Mo", badge=("#8e5a2b", "TG")),
    # --- Découvrir (suite)
    "marble":     dict(nom="Marble", cat="Découvrir", desc="Globe virtuel : explorer la Terre, la Lune et les cartes historiques.",
                       paquets=["marble"], taille="≈ 80 Mo", badge=("#2e86de", "Ma")),
    "geogebra":   dict(nom="GeoGebra", cat="Découvrir", desc="Géométrie et fonctions interactives, comme au collège.",
                       paquets=["geogebra"], taille="≈ 120 Mo", badge=("#6a5acd", "GG")),
    "avogadro":   dict(nom="Avogadro", cat="Découvrir", desc="Construire des molécules et les voir en 3D (chimie).",
                       paquets=["avogadro"], taille="≈ 60 Mo", badge=("#16a085", "Av")),
    "kig":        dict(nom="Kig", cat="Découvrir", desc="Géométrie interactive : constructions avec la règle et le compas.",
                       paquets=["kig"], taille="≈ 50 Mo", badge=("#2980b9", "Kg")),
    "kmplot":     dict(nom="KmPlot", cat="Découvrir", desc="Tracer des courbes de fonctions mathématiques.",
                       paquets=["kmplot"], taille="≈ 30 Mo", badge=("#8e44ad", "Kp")),
    # --- Apprendre (suite)
    "ktouch":     dict(nom="KTouch", cat="Apprendre", desc="Apprendre à taper vite au clavier, avec des leçons progressives.",
                       paquets=["ktouch"], taille="≈ 30 Mo", badge=("#1abc9c", "Kt")),
    "khangman":   dict(nom="KHangMan", cat="Apprendre", desc="Le jeu du pendu pour apprendre le vocabulaire.",
                       paquets=["khangman"], taille="≈ 40 Mo", badge=("#d35400", "Hm")),
    "kanagram":   dict(nom="Kanagram", cat="Apprendre", desc="Retrouver le mot caché dans les lettres mélangées.",
                       paquets=["kanagram"], taille="≈ 40 Mo", badge=("#c0392b", "An")),
    "klettres":   dict(nom="KLettres", cat="Apprendre", desc="Apprendre l'alphabet et les sons (petits).",
                       paquets=["klettres"], taille="≈ 10 Mo", badge=("#f1c40f", "Ab")),
    "kwordquiz":  dict(nom="KWordQuiz", cat="Apprendre", desc="Fiches de révision : vocabulaire, langues, définitions.",
                       paquets=["kwordquiz"], taille="≈ 30 Mo", badge=("#3498db", "Wq")),
    "parley":     dict(nom="Parley", cat="Apprendre", desc="Apprendre le vocabulaire d'une langue étrangère avec des fiches.",
                       paquets=["parley"], taille="≈ 20 Mo", badge=("#9b59b6", "Pa")),
    "solfege":    dict(nom="GNU Solfege", cat="Apprendre", desc="Entraîner son oreille musicale : notes, intervalles, rythmes.",
                       paquets=["solfege"], taille="≈ 30 Mo", badge=("#34495e", "♪")),
    "pysiogame":  dict(nom="Pysiogame", cat="Apprendre", desc="Plus de 100 petits jeux éducatifs : lecture, maths, logique (dès 3 ans).",
                       paquets=["pysiogame"], taille="≈ 40 Mo", badge=("#e84393", "Pg")),
    # --- Jouer (suite)
    "supertux":   dict(nom="SuperTux", cat="Jouer", desc="Jeu de plateforme avec Tux le pingouin.",
                       paquets=["supertux"], taille="≈ 150 Mo", badge=("#2980b9", "ST")),
    "tuxracer":   dict(nom="Extreme Tux Racer", cat="Jouer", desc="Descendre des pistes enneigées sur le ventre avec Tux.",
                       paquets=["extremetuxracer"], taille="≈ 60 Mo", badge=("#5dade2", "TR")),
    "pingus":     dict(nom="Pingus", cat="Jouer", desc="Guider les pingouins jusqu'à la sortie (réflexion).",
                       paquets=["pingus"], taille="≈ 40 Mo", badge=("#48c9b0", "Pi")),
    "neverball":  dict(nom="Neverball", cat="Jouer", desc="Faire rouler une bille en inclinant le plateau. Adresse et réflexion.",
                       paquets=["neverball"], taille="≈ 50 Mo", badge=("#f39c12", "Nb")),
    "kblocks":    dict(nom="KBlocks", cat="Jouer", desc="Empiler les blocs qui tombent (comme Tetris).",
                       paquets=["kblocks"], taille="≈ 20 Mo", badge=("#e74c3c", "Kb")),
    "ksudoku":    dict(nom="KSudoku", cat="Jouer", desc="Grilles de sudoku de tous niveaux.",
                       paquets=["ksudoku"], taille="≈ 20 Mo", badge=("#7f8c8d", "Su")),
    "mahjongg":   dict(nom="Mahjongg", cat="Jouer", desc="Retrouver les paires de tuiles (réflexion, calme).",
                       paquets=["gnome-mahjongg"], taille="≈ 10 Mo", badge=("#b03a2e", "Mj")),
    "aisleriot":  dict(nom="Solitaires", cat="Jouer", desc="Plus de 80 jeux de cartes en solitaire.",
                       paquets=["aisleriot"], taille="≈ 30 Mo", badge=("#1e8449", "♠")),
    "lbreakout":  dict(nom="LBreakout2", cat="Jouer", desc="Casser les briques avec la balle (casse-briques).",
                       paquets=["lbreakout2"], taille="≈ 10 Mo", badge=("#ca6f1e", "Lb")),
    "blobby":     dict(nom="Blobby Volley", cat="Jouer", desc="Volley-ball rigolo à deux sur le même clavier.",
                       paquets=["blobby"], taille="≈ 5 Mo", badge=("#2471a3", "Bv")),
    "kapman":     dict(nom="Kapman", cat="Jouer", desc="Manger les pastilles en évitant les fantômes.",
                       paquets=["kapman"], taille="≈ 20 Mo", badge=("#f4d03f", "Kp")),
    "openttd":    dict(nom="OpenTTD", cat="Jouer", desc="Construire et gérer un réseau de trains, bus et bateaux (stratégie, dès 10 ans).",
                       paquets=["openttd", "openttd-opengfx", "openttd-opensfx"], taille="≈ 60 Mo", badge=("#7d6608", "TT")),
    "wesnoth":    dict(nom="Bataille pour Wesnoth", cat="Jouer", desc="Stratégie au tour par tour dans un monde fantastique (combats, dès 10 ans).",
                       paquets=["wesnoth"], taille="≈ 500 Mo", badge=("#7b241c", "W")),
    "xmoto":      dict(nom="X-Moto", cat="Jouer", desc="Moto trial en 2D : garder l'équilibre sur des parcours fous.",
                       paquets=["xmoto"], taille="≈ 40 Mo", badge=("#922b21", "XM")),
    # --- encore plus de logiciels
    "spyder": dict(nom='Spyder', cat='Programmer', desc='Python scientifique : calculs, graphiques, explorateur de variables.',
                       paquets=['spyder'], taille='≈ 250 Mo', badge=('#c0392b', 'Sp')),
    "love": dict(nom='LÖVE', cat='Programmer', desc='Créer ses propres jeux 2D en Lua, un langage simple.',
                       paquets=['love'], taille='≈ 15 Mo', badge=('#e74a99', 'Lö')),
    "java": dict(nom='Java (JDK)', cat='Programmer', desc='Programmer en Java (le langage de Minecraft).',
                       paquets=['openjdk-17-jdk'], taille='≈ 250 Mo', badge=('#e76f00', 'Jv')),
    "nodejs": dict(nom='Node.js', cat='Programmer', desc="Exécuter des programmes JavaScript sur l'ordinateur.",
                       paquets=['nodejs'], taille='≈ 50 Mo', badge=('#3c873a', 'JS')),
    "golang": dict(nom='Go (Golang)', cat='Programmer', desc='Le langage Go de Google : simple et rapide.',
                       paquets=['golang'], taille='≈ 350 Mo', badge=('#00add8', 'Go')),
    "lazarus": dict(nom='Lazarus', cat='Programmer', desc='Créer des applications avec fenêtres et boutons en Pascal.',
                       paquets=['lazarus-ide', 'lazarus'], taille='≈ 600 Mo', badge=('#3b5998', 'Lz')),
    "octave": dict(nom='GNU Octave', cat='Programmer', desc='Calcul scientifique et mathématiques (proche de Matlab).',
                       paquets=['octave'], taille='≈ 300 Mo', badge=('#0790c0', 'Oc')),
    "meld": dict(nom='Meld', cat='Programmer', desc='Comparer deux fichiers ou dossiers et voir les différences.',
                       paquets=['meld'], taille='≈ 20 Mo', badge=('#7cb342', 'Me')),
    "gnumeric": dict(nom='Gnumeric', cat='Bureautique', desc='Tableur léger et rapide pour les calculs et les tableaux.',
                       paquets=['gnumeric'], taille='≈ 40 Mo', badge=('#2e7d32', 'Gn')),
    "abiword": dict(nom='AbiWord', cat='Bureautique', desc='Traitement de texte simple et léger.',
                       paquets=['abiword'], taille='≈ 30 Mo', badge=('#1565c0', 'Ab')),
    "okular": dict(nom='Okular', cat='Bureautique', desc='Lire et annoter des PDF, livres numériques et bandes dessinées.',
                       paquets=['okular'], taille='≈ 80 Mo', badge=('#2980b9', 'Ok')),
    "ghostwriter": dict(nom='ghostwriter', cat='Bureautique', desc='Écrire en Markdown avec aperçu en direct.',
                       paquets=['ghostwriter'], taille='≈ 20 Mo', badge=('#455a64', 'Gw')),
    "pdfarranger": dict(nom='PDF Arranger', cat='Bureautique', desc='Fusionner, découper, tourner et réorganiser les pages de PDF.',
                       paquets=['pdfarranger'], taille='≈ 10 Mo', badge=('#d84315', 'Pa')),
    "foliate": dict(nom='Foliate', cat='Bureautique', desc='Lecteur de livres numériques (EPUB) agréable.',
                       paquets=['foliate'], taille='≈ 20 Mo', badge=('#6d4c41', 'Fo')),
    "cherrytree": dict(nom='CherryTree', cat='Bureautique', desc='Prendre des notes organisées en arbre, avec images et tableaux.',
                       paquets=['cherrytree'], taille='≈ 20 Mo', badge=('#c62828', 'Ch')),
    "keepassxc": dict(nom='KeePassXC', cat='Bureautique', desc='Coffre-fort de mots de passe : apprendre les bonnes habitudes.',
                       paquets=['keepassxc'], taille='≈ 20 Mo', badge=('#43a047', 'Kp')),
    "homebank": dict(nom='HomeBank', cat='Bureautique', desc='Suivre son argent de poche et ses dépenses.',
                       paquets=['homebank'], taille='≈ 15 Mo', badge=('#00897b', 'Hb')),
    "speedcrunch": dict(nom='SpeedCrunch', cat='Bureautique', desc='Calculatrice rapide avec historique et fonctions.',
                       paquets=['speedcrunch'], taille='≈ 5 Mo', badge=('#5e35b1', 'Sc')),
    "qalculate": dict(nom='Qalculate!', cat='Bureautique', desc='Calculatrice puissante : unités, conversions, équations.',
                       paquets=['qalculate-gtk'], taille='≈ 20 Mo', badge=('#3949ab', 'Qa')),
    "kdenlive": dict(nom='Kdenlive', cat='Créer', desc='Montage vidéo : couper, assembler, ajouter titres et musique.',
                       paquets=['kdenlive'], taille='≈ 200 Mo', badge=('#5c6bc0', 'Kd')),
    "shotcut": dict(nom='Shotcut', cat='Créer', desc='Montage vidéo simple et efficace.',
                       paquets=['shotcut'], taille='≈ 150 Mo', badge=('#26a69a', 'Sh')),
    "openshot": dict(nom='OpenShot', cat='Créer', desc='Montage vidéo facile, idéal pour débuter.',
                       paquets=['openshot-qt'], taille='≈ 100 Mo', badge=('#e53935', 'Os')),
    "mypaint": dict(nom='MyPaint', cat='Créer', desc='Peinture numérique avec de beaux pinceaux, sur une toile infinie.',
                       paquets=['mypaint'], taille='≈ 30 Mo', badge=('#ef6c00', 'Mp')),
    "synfig": dict(nom='Synfig Studio', cat='Créer', desc='Créer des dessins animés en 2D.',
                       paquets=['synfigstudio'], taille='≈ 80 Mo', badge=('#283593', 'Sy')),
    "kolourpaint": dict(nom='KolourPaint', cat='Créer', desc='Dessin simple, comme Paint sous Windows.',
                       paquets=['kolourpaint'], taille='≈ 20 Mo', badge=('#f9a825', 'Kl')),
    "drawing": dict(nom='Drawing', cat='Créer', desc='Petit logiciel de dessin très simple pour les plus jeunes.',
                       paquets=['drawing'], taille='≈ 5 Mo', badge=('#ff7043', 'Dw')),
    "librecad": dict(nom='LibreCAD', cat='Créer', desc='Dessin technique en 2D (plans, pièces).',
                       paquets=['librecad'], taille='≈ 30 Mo', badge=('#546e7a', 'LC')),
    "openscad": dict(nom='OpenSCAD', cat='Créer', desc="Créer des objets 3D en écrivant du code (pour l'impression 3D).",
                       paquets=['openscad'], taille='≈ 40 Mo', badge=('#f4b400', '3D')),
    "freecad": dict(nom='FreeCAD', cat='Créer', desc="Conception 3D d'objets et de pièces (dès 12 ans).",
                       paquets=['freecad'], taille='≈ 500 Mo', badge=('#d32f2f', 'FC')),
    "fontforge": dict(nom='FontForge', cat='Créer', desc="Créer sa propre police d'écriture.",
                       paquets=['fontforge'], taille='≈ 30 Mo', badge=('#6a1b9a', 'Ff')),
    "darktable": dict(nom='darktable', cat='Créer', desc='Développer et retoucher ses photos comme un photographe.',
                       paquets=['darktable'], taille='≈ 100 Mo', badge=('#37474f', 'Dt')),
    "vokoscreen": dict(nom='vokoscreenNG', cat='Créer', desc='Enregistrer son écran en vidéo (tutoriels, exposés).',
                       paquets=['vokoscreen-ng'], taille='≈ 30 Mo', badge=('#00838f', 'Vk')),
    "rosegarden": dict(nom='Rosegarden', cat='Créer', desc='Composer de la musique avec partitions et instruments virtuels.',
                       paquets=['rosegarden'], taille='≈ 60 Mo', badge=('#ad1457', 'Rg')),
    "kstars": dict(nom='KStars', cat='Découvrir', desc='Atlas du ciel : étoiles, planètes, galaxies et éclipses.',
                       paquets=['kstars'], taille='≈ 150 Mo', badge=('#1a237e', 'Ks')),
    "xaos": dict(nom='XaoS', cat='Découvrir', desc="Zoomer à l'infini dans les fractales.",
                       paquets=['xaos'], taille='≈ 10 Mo', badge=('#8e24aa', 'Xa')),
    "kalgebra": dict(nom='KAlgebra', cat='Découvrir', desc='Calculatrice graphique : tracer des fonctions en 2D et 3D.',
                       paquets=['kalgebra'], taille='≈ 30 Mo', badge=('#0277bd', 'Ka')),
    "kiten": dict(nom='Kiten', cat='Apprendre', desc='Dictionnaire et apprentissage du japonais (kanjis).',
                       paquets=['kiten'], taille='≈ 30 Mo', badge=('#c62828', '日')),
    "minuet": dict(nom='Minuet', cat='Apprendre', desc='Apprendre la musique : notes, accords, gammes, rythmes.',
                       paquets=['minuet'], taille='≈ 30 Mo', badge=('#6d4c41', 'Mi')),
    "blinken": dict(nom='Blinken', cat='Apprendre', desc='Entraîner sa mémoire en répétant des suites de couleurs.',
                       paquets=['blinken'], taille='≈ 20 Mo', badge=('#fbc02d', 'Bl')),
    "gbrainy": dict(nom='gbrainy', cat='Apprendre', desc='Casse-têtes, calcul mental et jeux de mémoire.',
                       paquets=['gbrainy'], taille='≈ 20 Mo', badge=('#7cb342', 'Gb')),
    "gtans": dict(nom='Gtans', cat='Apprendre', desc='Le tangram : reconstituer des formes avec 7 pièces.',
                       paquets=['gtans'], taille='≈ 5 Mo', badge=('#e64a19', 'Tg')),
    "ktuberling": dict(nom='KTuberling', cat='Apprendre', desc='Habiller une pomme de terre et apprendre des mots (dès 3 ans).',
                       paquets=['ktuberling'], taille='≈ 40 Mo', badge=('#a1887f', 'Kt')),
    "palapeli": dict(nom='Palapeli', cat='Jouer', desc='Puzzles à reconstituer, avec ses propres photos.',
                       paquets=['palapeli'], taille='≈ 30 Mo', badge=('#8d6e63', 'Pz')),
    "freeciv": dict(nom='Freeciv', cat='Jouer', desc="Bâtir une civilisation de l'âge de pierre à l'espace (stratégie, dès 10 ans).",
                       paquets=['freeciv-client-gtk3', 'freeciv-server'], taille='≈ 80 Mo', badge=('#2e7d32', 'Fc')),
    "lincity": dict(nom='LinCity-NG', cat='Jouer', desc='Construire et gérer sa ville.',
                       paquets=['lincity-ng'], taille='≈ 50 Mo', badge=('#558b2f', 'Lc')),
    "simutrans": dict(nom='Simutrans', cat='Jouer', desc='Construire des réseaux de transport et faire grandir les villes.',
                       paquets=['simutrans', 'simutrans-pak64'], taille='≈ 50 Mo', badge=('#6d4c41', 'Sm')),
    "triggerrally": dict(nom='Trigger Rally', cat='Jouer', desc='Course de rallye en 3D.',
                       paquets=['trigger-rally'], taille='≈ 60 Mo', badge=('#ef6c00', 'TR')),
    "armagetron": dict(nom='Armagetron', cat='Jouer', desc='Course de motos de lumière (comme dans Tron).',
                       paquets=['armagetronad'], taille='≈ 20 Mo', badge=('#00bcd4', 'Ar')),
    "g2048": dict(nom='2048', cat='Jouer', desc='Additionner les tuiles pour atteindre 2048.',
                       paquets=['gnome-2048'], taille='≈ 5 Mo', badge=('#edc22e', '2k')),
    "mines": dict(nom='Démineur', cat='Jouer', desc='Le démineur classique.',
                       paquets=['gnome-mines'], taille='≈ 5 Mo', badge=('#607d8b', 'Dm')),
    "quadrapassel": dict(nom='Quadrapassel', cat='Jouer', desc='Faire des lignes avec les blocs qui tombent.',
                       paquets=['quadrapassel'], taille='≈ 5 Mo', badge=('#3f51b5', 'Qp')),
    "klotski": dict(nom='Klotski', cat='Jouer', desc='Faire glisser les blocs pour libérer le grand bloc.',
                       paquets=['gnome-klotski'], taille='≈ 5 Mo', badge=('#795548', 'Kk')),
    "iagno": dict(nom='Iagno (Othello)', cat='Jouer', desc="Le jeu de réversi / Othello contre l'ordinateur.",
                       paquets=['iagno'], taille='≈ 5 Mo', badge=('#212121', 'Ot')),
    "puissance4": dict(nom='Puissance 4', cat='Jouer', desc="Aligner 4 pions avant l'adversaire.",
                       paquets=['four-in-a-row'], taille='≈ 5 Mo', badge=('#d32f2f', 'P4')),
    "nibbles": dict(nom='Nibbles', cat='Jouer', desc='Le jeu du serpent qui grandit.',
                       paquets=['gnome-nibbles'], taille='≈ 5 Mo', badge=('#43a047', 'Sn')),
    "kbounce": dict(nom='KBounce', cat='Jouer', desc='Construire des murs pour enfermer les balles.',
                       paquets=['kbounce'], taille='≈ 10 Mo', badge=('#0288d1', 'Kb')),
    "kdiamond": dict(nom='KDiamond', cat='Jouer', desc='Aligner trois diamants identiques.',
                       paquets=['kdiamond'], taille='≈ 10 Mo', badge=('#7b1fa2', '◆')),
    "katomic": dict(nom='KAtomic', cat='Jouer', desc='Assembler des molécules en faisant glisser les atomes (réflexion).',
                       paquets=['katomic'], taille='≈ 10 Mo', badge=('#00796b', 'At')),
    "navale": dict(nom='Bataille navale', cat='Jouer', desc="La bataille navale contre l'ordinateur.",
                       paquets=['knavalbattle'], taille='≈ 10 Mo', badge=('#1565c0', 'Bn')),
    "bovo": dict(nom='Bovo', cat='Jouer', desc='Aligner 5 pions (morpion géant).',
                       paquets=['bovo'], taille='≈ 5 Mo', badge=('#9e9d24', 'X0')),
    "picmi": dict(nom='Picmi', cat='Jouer', desc='Nonogrammes : retrouver le dessin caché avec la logique.',
                       paquets=['picmi'], taille='≈ 5 Mo', badge=('#5d4037', 'Pm')),
    "flare": dict(nom='Flare', cat='Jouer', desc="Jeu d'aventure et de quêtes en solo (combats fantastiques, dès 10 ans).",
                       paquets=['flare-game'], taille='≈ 300 Mo', badge=('#bf360c', 'Fl')),
    "endlesssky": dict(nom='Endless Sky', cat='Jouer', desc="Explorer l'espace, commercer et piloter son vaisseau (dès 10 ans).",
                       paquets=['endless-sky'], taille='≈ 300 Mo', badge=('#263238', 'ES')),
    "atomix": dict(nom='Atomix', cat='Jouer', desc='Former des molécules en déplaçant les atomes.',
                       paquets=['atomix'], taille='≈ 5 Mo', badge=('#00897b', 'Ax')),
    "tuxpuck": dict(nom='TuxPuck', cat='Jouer', desc='Hockey sur table contre Tux et ses amis.',
                       paquets=['tuxpuck'], taille='≈ 5 Mo', badge=('#0d47a1', 'Hk')),
    "mirrormagic": dict(nom='Mirror Magic', cat='Jouer', desc='Diriger un rayon avec des miroirs (réflexion).',
                       paquets=['mirrormagic'], taille='≈ 10 Mo', badge=('#6a1b9a', 'Mm')),
    "pipewalker": dict(nom='PipeWalker', cat='Jouer', desc="Relier les tuyaux pour faire circuler l'eau (réflexion).",
                       paquets=['pipewalker'], taille='≈ 5 Mo', badge=('#039be5', 'Pw')),
}
CATEGORIES = ["Programmer", "Bureautique", "Créer", "Découvrir", "Apprendre", "Jouer"]

# Préparation dans le dossier de chaque enfant (comptes existants et futurs)
# packs de langue : ceux des langues proposées aux enfants qui existent pour VS Code (pas d'arabe ni de hindi : anglais)
VSCODE_PACKS = ["fr", "de", "es", "pt-BR", "ru", "zh-hans", "ja"]
VSCODE_EXT = [f"MS-CEINTL.vscode-language-pack-{x}" for x in VSCODE_PACKS] + ["ms-python.python"]
VSCODE_REGLAGES = {
    "telemetry.telemetryLevel": "off", "update.mode": "none", "extensions.autoUpdate": False,
    "extensions.autoCheckUpdates": False, "security.workspace.trust.enabled": False,
    "chat.disableAIFeatures": True, "workbench.startupEditor": "none",
    "python.locator": "js",       # le détecteur natif de l'extension Python ne peut pas s'exécuter depuis le dossier perso (noexec)
    "python.defaultInterpreterPath": "/usr/bin/python3",
    "workbench.secondarySideBar.defaultVisibility": "hidden",
}
# ajoute les réglages manquants sans écraser ceux que l'enfant a changés
_FUSION = ("import json,sys\nf=sys.argv[1]\ntry: d=json.load(open(f))\nexcept Exception: d={}\n"
           "for k,v in json.loads(sys.argv[2]).items(): d.setdefault(k,v)\njson.dump(d,open(f,'w'),indent=1)")


# index des packs de langue : VS Code ne l'écrit qu'à son premier démarrage (qui serait donc en anglais)
_LANGUE = """import glob,hashlib,json,os,sys
H=sys.argv[1]; out={}
for d in sorted(glob.glob(H+'/.vscode/extensions/ms-ceintl.vscode-language-pack-*')):
  p=json.load(open(d+'/package.json'))
  l=p['contributes']['localizations'][0]
  tr={t['id']:os.path.normpath(os.path.join(d,t['path'])) for t in l['translations']}
  h=hashlib.md5((p['publisher']+'.'+p['name']+'@'+p['version']).encode()).hexdigest()
  out[l['languageId']]={'hash':h,'extensions':[{'extensionIdentifier':{'id':p['publisher'].lower()+'.'+p['name']},'version':p['version']}],
   'translations':tr,'label':l.get('localizedLanguageName',l['languageId'])}
json.dump(out,open(H+'/.config/Code/languagepacks.json','w'))"""


# Programmes livrés par les extensions (ex. « pet » de l'extension Python) : le dossier perso est en noexec.
# Les extensions sont téléchargées par root dans un dossier de RÉFÉRENCE (système, lecture seule pour les enfants).
# Seuls les programmes de ce dossier sont copiés dans BIN (exécutable) ; dans le dossier de l'enfant, ils sont
# remplacés par un lien vers BIN. Tout ce qui touche au dossier de l'enfant se fait AVEC SES DROITS (runuser) :
# un fichier ou un lien déposé par l'enfant ne peut ni faire autoriser son propre programme, ni faire écrire root ailleurs.
BIN = "/usr/local/lib/maranyse/bin"
REF = "/usr/local/share/maranyse/vscode-ext"
STOCK = os.path.join(os.path.expanduser("~"), "maranyse-bin")     # copie dans la VM (le bureau peut être recréé)
_BINREF = """import hashlib,os,shutil,sys
R,B=sys.argv[1],sys.argv[2]; os.makedirs(B,exist_ok=True); garde=set()
for r,ds,fs in os.walk(R):
  for n in fs:
    f=os.path.join(r,n)
    if os.path.islink(f) or not os.stat(f).st_mode&0o111: continue
    with open(f,'rb') as x:
      if x.read(4)!=b'\x7fELF': continue
    h=hashlib.sha256(open(f,'rb').read()).hexdigest()[:20]; d=os.path.join(B,h); garde.add(h)
    if not os.path.exists(d): shutil.copyfile(f,d); os.chmod(d,0o755)
if any(n.startswith('ms-python.python-') for n in os.listdir(R)):
  for h in os.listdir(B):
    if h not in garde: os.remove(os.path.join(B,h))"""
# côté enfant (ses droits) : copie de la référence, chemins corrigés, programmes autorisés remplacés par un lien
_LIENS = """import hashlib,os,sys
H,R,B=sys.argv[1],sys.argv[2],sys.argv[3]; E=H+'/.vscode/extensions'
j=E+'/extensions.json'
if os.path.isfile(j) and not os.path.islink(j):
  t=open(j).read().replace(R,E); open(j,'w').write(t)
for r,ds,fs in os.walk(E):
  for n in fs:
    f=os.path.join(r,n)
    if os.path.islink(f) or not os.path.isfile(f): continue
    with open(f,'rb') as x:
      if x.read(4)!=b'\x7fELF': continue
    h=hashlib.sha256(open(f,'rb').read()).hexdigest()[:20]; d=os.path.join(B,h)
    if os.path.isfile(d): os.remove(f); os.symlink(d,f)"""


def _py(code, *args):
    return f"python3 -c \"$(echo {base64.b64encode(code.encode()).decode()} | base64 -d)\" " + " ".join(args)


def ref_vscode():
    """Root, une fois : extensions dans le dossier de référence, programmes autorisés dans BIN."""
    ext = " ".join(f"--install-extension {x}" for x in VSCODE_EXT)
    return (f"mkdir -p {REF} /root/.maranyse-vscode; "
            f"{{ ls {REF} | grep -qi '^ms-python.python-' && ls {REF} | grep -qi '^ms-ceintl.vscode-language-pack-zh-hans-'; }} || "
            f"code --no-sandbox --user-data-dir /root/.maranyse-vscode --extensions-dir {REF} {ext} --force >/dev/null 2>&1; "
            f"chmod -R a+rX {REF}; " + _py(_BINREF, REF, BIN))


def prep_vscode(u):
    """Dans le dossier de l'enfant, avec SES droits."""
    argv = json.dumps({"disable-chromium-sandbox": True, "locale": "fr"})
    reg = json.dumps(VSCODE_REGLAGES)
    corps = (f"H=/home/{u}; mkdir -p $H/.vscode/extensions $H/.config/Code/User && "
             f"printf '%s' '{argv}' > $H/.vscode/argv.json; "
             + _py(_FUSION, "$H/.config/Code/User/settings.json", shlex.quote(reg)) + "; "
             f"cp -R --no-preserve=mode,ownership {REF}/. $H/.vscode/extensions/ && "
             + _py(_LIENS, "$H", REF, BIN) + "; " + _py(_LANGUE, "$H"))
    return f"[ -d /home/{u} ] && runuser -u {u} -- env HOME=/home/{u} sh -c {shlex.quote(corps)}"


PREPS = {"vscode": (ref_vscode, prep_vscode)}   # (root, une fois ; dans le dossier de chaque enfant)

JOB = {"en_cours": None, "dernier": None}      # tâche d'installation : {cle, nom, action, debut, log, ok}
_job_lock = threading.Lock()
_on_change = []                                  # appelé après chaque changement (logique : réappliquer les blocages)
_users = lambda: []


# ----------------------------------------------------------------------
def charger():
    try:
        d = json.load(open(FICHIER))
        return d if isinstance(d.get("installes"), dict) else {"installes": {}}
    except (OSError, ValueError):
        return {"installes": {}}


def sauver(d):
    tmp = FICHIER + ".tmp"
    json.dump(d, open(tmp, "w"), ensure_ascii=False, indent=1)
    os.replace(tmp, FICHIER)


def cle_app(cle):
    return "lg_" + re.sub(r"[^a-z0-9]", "_", cle)


def run(cmd, timeout=1800):
    """Commande root dans le bureau, longue durée. Renvoie (code, sortie)."""
    try:
        r = subprocess.run(["docker", "exec", "-e", "DEBIAN_FRONTEND=noninteractive", C, "sh", "-c", cmd],
                           capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout + r.stderr)
    except subprocess.TimeoutExpired:
        return 124, "délai dépassé"


# Après une installation : les fichiers nouveaux perdent setuid/setgid et les « capacités » (un programme installé
# ne doit jamais donner plus de droits que le compte de l'enfant).
_DURCIR = """import os,stat,sys
t=os.stat(sys.argv[1]).st_mtime
for top in ('/usr','/opt','/etc'):
  for r,ds,fs in os.walk(top):
    for n in fs:
      f=os.path.join(r,n)
      try: st=os.lstat(f)
      except OSError: continue
      if not stat.S_ISREG(st.st_mode) or st.st_ctime<t: continue
      if st.st_mode&0o6000: os.chmod(f,st.st_mode&0o1777); print('setuid retiré :',f)
      try: os.removexattr(f,'security.capability'); print('capacités retirées :',f)
      except OSError: pass"""


def script_install(paquets, depot=None, post=None):
    # policy-rc.d : l'installation ne démarre aucun service (serveur, relais...)
    s = ("set -e; printf '#!/bin/sh\\nexit 101\\n' > /usr/sbin/policy-rc.d; chmod 755 /usr/sbin/policy-rc.d; "
         "touch /tmp/.lg-debut; sleep 1; ")
    if depot:
        s += ("command -v gpg >/dev/null && command -v wget >/dev/null || { apt-get update -qq; "
              "apt-get install -y -qq --no-install-recommends wget gpg ca-certificates; }; ")
        s += f"[ -e {DEPOTS[depot][1]} ] || {{ {DEPOTS[depot][0]}; }}; "
    s += ("apt-get update -qq; apt-get install -y -qq --no-install-recommends " + " ".join(paquets) +
          "; apt-get clean; rm -rf /var/lib/apt/lists/*")
    s += f"; {post}" if post else ""
    return s + "; python3 -c \"$(echo " + base64.b64encode(_DURCIR.encode()).decode() + " | base64 -d)\" /tmp/.lg-debut; rm -f /tmp/.lg-debut"


def detecter(paquets):
    """Programmes d'un paquet : cibles des lanceurs du menu (.desktop) + /usr/bin, /usr/games.
    Renvoie (binaires réels à bloquer, noms de processus, nom affiché lu dans le menu)."""
    sh = ("for p in " + " ".join(paquets) + "; do dpkg -L $p 2>/dev/null; done | sort -u > /tmp/.lg; "
          "for d in $(grep -E '^/usr/share/applications/.*\\.desktop$' /tmp/.lg); do "
          "grep -q '^NoDisplay=true' $d && continue; "
          "echo N$(sed -n 's/^Name\\[fr\\]=//p;' $d | head -1)'|'$(sed -n 's/^Name=//p' $d | head -1); "
          "x=$(sed -n 's/^Exec=//p' $d | head -1 | awk '{print $1}'); "
          "[ \"$x\" = env ] && x=$(sed -n 's/^Exec=//p' $d | head -1 | awk '{for(i=2;i<=NF;i++) if($i !~ /=/){print $i; exit}}'); "
          "x=$(command -v \"$x\" 2>/dev/null || echo \"$x\"); [ -e \"$x\" ] && echo B$(readlink -f \"$x\"); done; "
          "grep -E '^/usr/(s?bin|games)/[^/]+$' /tmp/.lg | while read f; do [ -f \"$f\" ] && [ -x \"$f\" ] && echo B$(readlink -f \"$f\"); done; rm -f /tmp/.lg")
    _, out = run(sh, 60)
    bins, noms = [], []
    for line in out.splitlines():
        if line.startswith("B") and line[1:] not in bins:
            bins.append(line[1:])
        elif line.startswith("N"):
            fr, _, en = line[1:].partition("|")
            if fr or en:
                noms.append(fr or en)
    # script (python, shell...) : le nom du processus est celui du script ; binaire ELF : son nom
    comms = sorted({os.path.basename(b)[:15] for b in bins})
    return bins, comms, (noms[0] if noms else "")


# ----------------------------------------------------------------------
def register(apps, labels):
    """Ajoute les logiciels installés aux applications gérables (règles, blocage, statistiques)."""
    for k in [k for k in apps if k.startswith("lg_")]:
        del apps[k]
    for cle, info in charger()["installes"].items():
        if not info.get("bins"):
            continue
        apps[cle_app(cle)] = (info["nom"], info["nom"], info["bins"])
        for c in info.get("comms", []):
            labels.setdefault(c, info["nom"])


def badge(cle_app_):
    for cle, info in charger()["installes"].items():
        if cle_app(cle) == cle_app_:
            return tuple(info.get("badge") or ("#64748b", info["nom"][:2]))
    return None


def wm_item(low):
    """Fenêtre au premier plan (classe X) -> clé d'application, pour l'accueil."""
    for cle, info in charger()["installes"].items():
        if any(c.lower() in low for c in info.get("comms", []) + [cle]):
            return f"app:{cle_app(cle)}"
    return None


def preparer(users, cles=None):
    """Réglages dans le dossier de chaque enfant (VS Code : français, extensions, sans bac à sable Chromium)."""
    for cle in (cles or list(charger()["installes"])):
        if cle in PREPS:
            ref, perso = PREPS[cle]
            run(ref(), 900)
            for u in users:
                run(perso(u), 600)
    sauver_binaires()


def sauver_binaires():
    """Copie dans la VM les programmes autorisés de BIN (pour les remettre si le bureau est recréé) ; même contenu que BIN."""
    os.makedirs(STOCK, exist_ok=True)
    code, out = run(f"ls {BIN} 2>/dev/null", 30)
    dans_bin = {h for h in out.split() if re.fullmatch(r"[0-9a-f]{20}", h)}
    for h in dans_bin:
        if not os.path.exists(os.path.join(STOCK, h)):
            subprocess.run(["docker", "cp", f"{C}:{BIN}/{h}", os.path.join(STOCK, h)], capture_output=True, timeout=120)
    if code == 0 and dans_bin:
        for h in os.listdir(STOCK):
            if h not in dans_bin:
                os.remove(os.path.join(STOCK, h))


def remettre_binaires():
    try:
        stock = [h for h in os.listdir(STOCK) if re.fullmatch(r"[0-9a-f]{20}", h)]
    except OSError:
        return
    if not stock:
        return
    _, out = run(f"mkdir -p {BIN}; ls {BIN}", 30)
    for h in set(stock) - set(out.split()):
        subprocess.run(["docker", "cp", os.path.join(STOCK, h), f"{C}:{BIN}/{h}"], capture_output=True, timeout=120)
        run(f"chown root:root {BIN}/{h}; chmod 755 {BIN}/{h}", 30)


def _fini():
    for f in _on_change:
        try:
            f()
        except Exception as ex:
            print("logiciels: rappel :", repr(ex), flush=True)


def _tache(cle, nom, action, fn):
    def corps():
        log = ""
        try:
            ok, log = fn()
        except Exception as ex:
            ok, log = False, repr(ex)
        JOB["dernier"] = dict(JOB["en_cours"], fin=time.time(), ok=ok, log=log[-1500:])
        JOB["en_cours"] = None
        _fini()
    with _job_lock:
        if JOB["en_cours"]:
            return False
        JOB["en_cours"] = dict(cle=cle, nom=nom, action=action, debut=time.time())
    threading.Thread(target=corps, daemon=True).start()
    return True


def installer(cle, paquet=None):
    """Lance l'installation pour tous les enfants. Renvoie un message pour l'espace parents."""
    if cle == "_paquet":
        paquet = (paquet or "").strip().lower()
        if not re.fullmatch(PAQUET_RE, paquet):
            return "Nom de paquet invalide (ex. « tuxpuck », en minuscules)."
        if INTERDITS.match(paquet):
            return f"« {paquet} » sert à contourner le contrôle parental : il n'est pas installable ici."
        code, out = run(f"apt-cache show {paquet} >/dev/null 2>&1 || {{ apt-get update -qq >/dev/null 2>&1; apt-cache show {paquet} >/dev/null 2>&1; }} && echo ok", 180)
        if "ok" not in out:
            return f"Le paquet « {paquet} » n'existe pas dans Debian 12."
        _, sim = run(f"apt-get install -s --no-install-recommends {paquet} 2>/dev/null | awk '/^Inst /{{print $2}}'", 180)
        mauvais = [x for x in sim.split() if INTERDITS.match(x)]
        if mauvais:
            return f"« {paquet} » installerait aussi {', '.join(mauvais[:3])}, qui sert à contourner le contrôle parental : refusé."
        cle, info = "p_" + paquet, dict(nom=paquet, paquets=[paquet], badge=("#64748b", paquet[:2].capitalize()), perso=True)
    elif cle in CATALOGUE:
        info = dict(CATALOGUE[cle])
    else:
        return "Logiciel inconnu."
    if cle in charger()["installes"]:
        return f"{info['nom']} est déjà installé."

    def fn():
        code, out = run(script_install(info["paquets"], info.get("depot"), info.get("post")))
        if code:
            return False, out
        bins, comms, nom_menu = detecter(info["paquets"])
        if not bins:
            return False, out + "\nAucun programme trouvé dans ce paquet (ce n'est peut-être pas une application)."
        d = charger()
        d["installes"][cle] = dict(nom=nom_menu if info.get("perso") and nom_menu else info["nom"], paquets=info["paquets"],
                                   depot=info.get("depot"), post=info.get("post"), bins=bins, comms=comms, badge=list(info.get("badge") or ()),
                                   perso=bool(info.get("perso")), date=datetime.now().strftime("%Y-%m-%d %H:%M"))
        sauver(d)
        preparer(_users(), [cle])
        return True, out
    if not _tache(cle, info["nom"], "installer", fn):
        return "Une installation est déjà en cours : attendez qu'elle se termine."
    return f"Installation de {info['nom']} lancée pour tous les enfants. Cela peut prendre quelques minutes."


def desinstaller(cle):
    d = charger()
    info = d["installes"].get(cle)
    if not info:
        return "Ce logiciel n'est pas installé."

    def fn():
        autres = [i for k, i in d["installes"].items() if k != cle]
        gardes = {p for i in autres for p in i["paquets"]}
        paq = [p for p in info["paquets"] if p not in gardes]
        s = "set -e; " + (f"apt-get purge -y -qq {' '.join(paq)}; apt-get autoremove -y -qq --purge; " if paq else "")
        dep = info.get("depot")
        if dep and not any(i.get("depot") == dep for i in autres):
            s += f"rm -f {DEPOTS[dep][1]}; "
        code, out = run(s + "true")
        if code:
            return False, out
        d2 = charger()
        d2["installes"].pop(cle, None)
        sauver(d2)
        return True, out
    if not _tache(cle, info["nom"], "désinstaller", fn):
        return "Une installation est déjà en cours : attendez qu'elle se termine."
    return f"Désinstallation de {info['nom']} lancée. Les fichiers des enfants sont conservés."


_dernier_controle = [0]


def verifier(force=False):
    """Bureau recréé sans les logiciels (mise à jour, réparation) : on les réinstalle, en arrière-plan."""
    if JOB["en_cours"] or (not force and time.time() - _dernier_controle[0] < 600):
        return
    _dernier_controle[0] = time.time()
    remettre_binaires()
    inst = charger()["installes"]
    if not inst:
        return
    paq = sorted({p for i in inst.values() for p in i["paquets"]})
    code, out = run("for p in " + " ".join(paq) + "; do dpkg-query -W -f='${Status}\\n' $p 2>/dev/null | grep -q 'ok installed' || echo $p; done", 60)
    if code or not out.strip():
        return
    manquants = set(out.split())

    def fn():
        logs, ok = "", True
        for cle, info in inst.items():
            if manquants & set(info["paquets"]):
                c, o = run(script_install(info["paquets"], info.get("depot"), _post(cle, info)))
                logs += o
                ok = ok and not c
        return ok, logs
    _tache("_tous", "logiciels manquants", "réinstaller", fn)


def _post(cle, info):
    """Étape après installation : celle du catalogue actuel (corrections incluses), sinon celle enregistrée."""
    return CATALOGUE[cle].get("post") if cle in CATALOGUE else info.get("post")


def script():
    """Script d'installation de tous les logiciels, intégré à l'image du bureau (Dockerfile)."""
    lignes = ["#!/bin/sh", "# MaranYSE : logiciels installés depuis l'espace parents (généré)", "export DEBIAN_FRONTEND=noninteractive"]
    for cle, info in charger()["installes"].items():
        lignes.append(f"( {script_install(info['paquets'], info.get('depot'), _post(cle, info))} ) || echo 'ÉCHEC {cle}'")
    lignes.append("true")
    return "\n".join(lignes) + "\n"


if __name__ == "__main__" and sys.argv[1:] == ["script"]:
    sys.stdout.write(script())
