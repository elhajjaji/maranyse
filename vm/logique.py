#!/usr/bin/env python3
"""MaranYSE — logique du contrôle parental (règles, statistiques, application), utilisée par tableau.py.

Tourne dans la VM sous l'utilisateur parent (groupe docker).
- Toutes les 30 s : relève l'application / le site au premier plan de chaque enfant (statistiques)
  et applique les règles.
- Planning par demi-heure : vert = aucune restriction, orange = règles de l'orange, rouge = pas de session.
- Règles de l'orange : communes à tous les enfants + individuelles (qui remplacent les communes).
- Fichiers : ~/.tableau.conf (identifiant:mot de passe), ~/controle.json (règles), ~/stats.db (statistiques).
"""
import base64, html, json, os, re, secrets, sqlite3, subprocess, threading, time
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse, quote

C = "bureau-enfants"
# Comptes enfants : liste lue dans /secrets/comptes.txt (lignes « identifiant:Nom affiché »).
# USERS et NAMES sont modifiés sur place, jamais réaffectés (tableau.py les importe).
DEFAULT_USERS = ["driss", "paul", "carole"]          # comptes d'exemple, seulement si aucune liste n'existe encore
USERS = []
NAMES = {}
ACCOUNTS = "/secrets/comptes.txt"
LOGIN_RE = r"[a-z][a-z0-9_]{1,30}"
RESERVED = {"root", "parent", "admin", "xrdp", "nobody", "messagebus", "daemon", "bin", "sys", "games", "man", "mail", "www-data"}
ALL = "_tous"                    # clé des règles communes
PORT = 8080
TICK = 30
HOME = os.path.expanduser("~")
CONF = f"{HOME}/.tableau.conf"
RULES = f"{HOME}/controle.json"
DB = f"{HOME}/stats.db"
LOGIN, PASSWORD = open(CONF).read().strip().split(":", 1)
# Filtre familial CleanBrowsing Family : contenu adulte, logiciels malveillants, mais aussi sites proxy, VPN et anonymiseurs
# (le contournement le plus courant par le navigateur) ; recherche sécurisée Google et YouTube en mode restreint imposés.
FAMILY_DNS = ["185.228.168.168", "185.228.169.168"]
PIP_PROXY_PORT = 8888                # relais vers PyPI seulement (tinyproxy, voir container/Dockerfile)
JOURS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
SLOTS = 48                       # cases d'une demi-heure par jour

# Applications gérables : clé -> (nom affiché, nom dans les statistiques, binaires)
APPS = {
    "firefox":   ("Firefox (internet)", "Firefox", ["/usr/lib/firefox-esr/firefox-esr", "/usr/lib/firefox-esr/firefox-bin"]),
    "office":    ("LibreOffice (texte, tableur, présentation)", "LibreOffice", ["/usr/lib/libreoffice/program/soffice.bin", "/usr/lib/libreoffice/program/oosplash"]),
    "gcompris":  ("GCompris", "GCompris", ["/usr/games/gcompris-qt"]),
    "tuxpaint":  ("Tux Paint", "Tux Paint", ["/usr/bin/tuxpaint"]),
    "mousepad":  ("Éditeur de texte", "Éditeur de texte", ["/usr/bin/mousepad"]),
    "ristretto": ("Visionneuse d'images", "Visionneuse d'images", ["/usr/bin/ristretto"]),
    "terminal":  ("Terminal", "Terminal", ["/usr/bin/xfce4-terminal"]),
    "thonny":    ("Thonny (programmation Python)", "Thonny", ["/usr/bin/thonny"]),
}
# Sites gérables : clé -> (nom, domaines bloqués (sous-domaines inclus), mots du titre d'onglet pour mesurer le temps)
SITES = {
    "youtube":   ("YouTube", ["youtube.com", "youtu.be", "googlevideo.com", "ytimg.com", "youtube-nocookie.com", "youtubei.googleapis.com", "youtubekids.com"], ["youtube"]),
    "tiktok":    ("TikTok", ["tiktok.com", "tiktokcdn.com", "tiktokv.com", "tiktokcdn-eu.com", "ttwstatic.com"], ["tiktok"]),
    "reseaux":   ("Réseaux sociaux", ["instagram.com", "cdninstagram.com", "facebook.com", "fbcdn.net", "snapchat.com", "x.com", "twitter.com",
                                      "twimg.com", "discord.com", "discord.gg", "discordapp.com"], ["instagram", "facebook", "snapchat", "/ x", "twitter", "discord"]),
    "twitch":    ("Twitch", ["twitch.tv", "ttvnw.net", "jtvnw.net"], ["twitch"]),
    "jeux":      ("Jeux en ligne (Roblox, Fortnite, Poki...)", ["roblox.com", "rbxcdn.com", "epicgames.com", "fortnite.com", "poki.com", "crazygames.com", "miniclip.com"],
                  ["roblox", "fortnite", "poki", "crazygames", "miniclip"]),
    "streaming": ("Netflix / Disney+", ["netflix.com", "nflxvideo.net", "nflximg.net", "disneyplus.com", "disney-plus.net", "bamgrid.com"], ["netflix", "disney+"]),
}
LABELS = {   # nom du processus -> nom affiché dans les statistiques
    "firefox-esr": "Firefox", "firefox-bin": "Firefox", "GeckoMain": "Firefox", "firefox": "Firefox",
    "soffice.bin": "LibreOffice", "gcompris-qt": "GCompris", "tuxpaint": "Tux Paint", "mousepad": "Éditeur de texte",
    "ristretto": "Visionneuse d'images", "xfce4-terminal": "Terminal", "thunar": "Fichiers", "Thunar": "Fichiers",
    "xfdesktop": "Bureau", "xfce4-panel": "Bureau", "xfce4-appfinder": "Bureau", "zenity": "Message des parents",
    "thonny": "Thonny", "python3": "Python", "python3.11": "Python",
}
# Logiciels ajoutés par les parents (page Logiciels) : applications gérables comme les autres
import logiciels                 # noqa: E402
import i18n                      # noqa: E402
logiciels.register(APPS, LABELS)
# Contournements : serveurs « DNS par HTTPS » (DoH) publics, bloqués quand l'internet d'un enfant est filtré
DOH_IPS = ["1.1.1.1", "1.0.0.1", "1.1.1.2", "1.0.0.2", "1.1.1.3", "1.0.0.3", "8.8.8.8", "8.8.4.4", "9.9.9.9", "149.112.112.112",
           "9.9.9.10", "149.112.112.10", "9.9.9.11", "149.112.112.11", "208.67.222.222", "208.67.220.220", "208.67.222.123",
           "208.67.220.123", "94.140.14.14", "94.140.15.15", "94.140.14.15", "94.140.15.16", "185.228.168.9", "185.228.169.9",
           "185.228.168.168", "185.228.169.168", "76.76.2.0/24", "76.76.10.0/24", "45.90.28.0/24", "45.90.30.0/24",
           "194.242.2.0/24", "77.88.8.8", "77.88.8.1", "86.54.11.0/24"]
DOH_NAMES = ["dns.google", "dns.google.com", "cloudflare-dns.com", "one.one.one.one", "family.cloudflare-dns.com",
             "security.cloudflare-dns.com", "dns.quad9.net", "doh.opendns.com", "dns.opendns.com", "dns.adguard-dns.com",
             "dns.adguard.com", "dns.nextdns.io", "doh.cleanbrowsing.org", "dns.mullvad.net", "doh.mullvad.net",
             "doh.dns.sb", "dns.controld.com", "freedns.controld.com", "doh.libredns.gr", "dns.dnswarden.com"]
# Anciens « outils interdits » (Python, Perl, OpenSSL) : les outils ne sont plus verrouillés. Les contournements
# sont empêchés par ce que seul root contrôle (pare-feu, filtre DNS, droits) : on retire juste d'anciens blocages.
OUTILS = ["/usr/bin/python3.11", "/usr/bin/perl", "/usr/bin/openssl"]
# Réglages « contournements » choisis par les parents : clé -> (titre, explication, réglable par enfant ?)
SECU = {
    "reseau": ("Internet pour les programmes autres que Firefox",
               "Interdit : seul Firefox (filtré) va sur internet. Un VPN, un proxy, un tunnel ou un script ne peut donc "
               "ni changer d'adresse IP ni sortir du filtrage. On peut toujours programmer (Python, VS Code, terminal).", True),
    "doh": ("DNS sécurisé (DoH) et serveurs DNS publics",
            "Permettent de contourner le filtrage des sites. Ne joue que quand l'internet de l'enfant est filtré ou a des sites bloqués.", True),
    "programmes": ("Programmes téléchargés ou copiés",
                   "Lancer un programme enregistré dans son dossier ou un dossier temporaire (VPN portable, autre navigateur, jeu téléchargé...).", False),
    "pip": ("Installer des bibliothèques Python (pip)",
            "Autorisé : pip install fonctionne, mais uniquement depuis PyPI (le dépôt officiel des bibliothèques Python), "
            "par un relais qui refuse tout autre site.", True),
}
SECU_VAL = {"interdit": "Interdit", "autorise": "Autorisé"}
EXEC_MOUNTS = ["/home", "/tmp", "/var/tmp", "/run/lock"]
INTERNET_GID = 2000                  # groupe « internet » du lanceur de Firefox (voir container/firefox-net.c)
SECU_DEFAUT = {"programmes": "interdit", "reseau": "interdit", "pip": "autorise", "doh": "interdit"}

IDLE = "(inactif)"
INTERNET = {"libre": "Libre", "filtre": "Filtré", "bloque": "Coupé"}
MODES = {"bloquer": "Bloqué", "limiter": "Limité", "autoriser": "Autorisé sans limite"}
NIVEAU = {"V": "Accès complet", "O": "Accès restreint", "R": "Pas d'accès", "P": "En pause"}
ETAT = {"V": "accès complet", "O": "accès restreint", "R": "pas d'accès", "P": "en pause"}

lock = threading.Lock()
acc_lock = threading.RLock()     # la liste des comptes ne change pas pendant un passage de la boucle


# ======================================================================
# Accès au conteneur
# ======================================================================
def dx(cmd, user=None, env=None, inp=None, detach=False):
    a = ["docker", "exec"] + (["-d"] if detach else []) + (["-i"] if inp else [])
    if user:
        a += ["-u", user]
    for k, v in (env or {}).items():
        a += ["-e", f"{k}={v}"]
    try:
        r = subprocess.run(a + [C, "sh", "-c", cmd], capture_output=True, text=True, input=inp, timeout=25)
        return r.stdout
    except subprocess.TimeoutExpired:
        return ""


def container_state():
    r = subprocess.run(["docker", "inspect", "-f", "{{.State.Status}}", C], capture_output=True, text=True)
    return r.stdout.strip() or "absent"


def active_connections():
    out = set()
    for line in dx("cat /proc/net/tcp6 /proc/net/tcp 2>/dev/null").splitlines():
        f = line.split()
        if len(f) < 4 or f[3] != "01" or ":" not in f[1]:
            continue
        if int(f[1].split(":")[1], 16) != 3389:
            continue
        h, p = f[2].split(":")
        out.add((".".join(str(x) for x in bytes.fromhex(h[-8:])[::-1]), int(p, 16)))
    return out


def last_sessions():
    names, last = {}, {}
    for l in dx("tail -n 3000 /var/log/xrdp.log 2>/dev/null").splitlines():
        m = re.match(r"\[(\d{8}-\d\d:\d\d:\d\d)\].*Connected client computer name: (.*)", l)
        if m:
            names[m.group(1)] = m.group(2).strip()
    for l in dx("tail -n 3000 /var/log/xrdp-sesman.log 2>/dev/null").splitlines():
        m = re.match(r"\[(\d{8}-\d\d:\d\d:\d\d)\].*created session.*username (\S+), ip (?:::ffff:)?([\d.]+):(\d+)", l)
        if m:
            ts, u, ip, port = m.groups()
            last[u] = dict(ts=ts, ip=ip, port=int(port), name=names.get(ts, ""))
    return last


def displays():
    d = {}
    for l in dx("ps -eo user:32,args | grep '[X]org :'").splitlines():
        m = re.match(r"(\S+)\s+\S*Xorg (:\d+)", l)
        if m:
            d[m.group(1)] = m.group(2)
    return d


def xenv(u, disp):
    """Affichage de l'enfant, dans sa langue (boutons des messages, écran de pause...)."""
    loc = i18n.LANGUES.get(STATE.get("langues", {}).get(u, i18n.DEFAUT), i18n.LANGUES[i18n.DEFAUT])[1]
    return {"DISPLAY": disp, "XAUTHORITY": f"/home/{u}/.Xauthority", "LANG": loc, "LC_ALL": loc, "LANGUAGE": loc.split(".")[0]}


def windows(u, disp):
    res = []
    for l in dx("wmctrl -lx 2>/dev/null", user=u, env=xenv(u, disp)).splitlines():
        f = l.split(None, 4)
        if len(f) >= 5 and f[1] != "-1":
            res.append((f[4], f[2].split(".")[-1]))
    return res


def foreground(u, disp):
    """(application, titre, inactivité en secondes) de la fenêtre au premier plan."""
    out = dx('w=$(xdotool getactivewindow 2>/dev/null); p=$(xdotool getwindowpid "$w" 2>/dev/null); '
             'echo "$(cat /proc/$p/comm 2>/dev/null)"; echo "$(xdotool getwindowname "$w" 2>/dev/null | head -1)"; '
             'xprintidle 2>/dev/null || echo 0', user=u, env=xenv(u, disp)).split("\n")
    comm = out[0].strip() if out else ""
    title = out[1].strip() if len(out) > 1 else ""
    try:
        idle = int(out[2].strip()) // 1000
    except (IndexError, ValueError):
        idle = 0
    app = LABELS.get(comm, comm or "Bureau")
    if app == "Bureau":
        title = ""
    return app, title[:200], idle


def passwords():
    p = {}
    for l in dx("cat /secrets/mots_de_passe.txt").splitlines():
        if ":" in l:
            k, v = l.split(":", 1)
            p[k] = v
    return p


def uids():
    out = dx("for u in " + " ".join(USERS) + "; do echo $u $(id -u $u 2>/dev/null); done")
    return {a: b for a, b in (l.split() for l in out.splitlines() if len(l.split()) == 2)}


# ======================================================================
# Comptes enfants
# ======================================================================
def nom(u):
    return NAMES.get(u) or u.replace("_", " ").title()


def save_accounts(acc):
    dx(f"cat > {ACCOUNTS} && chmod 600 {ACCOUNTS}", inp="".join(f"{u}:{n}\n" for u, n in acc))


def load_accounts():
    """Relit la liste des comptes. Renvoie False si le bureau ne répond pas (la liste reste inchangée)."""
    out = dx(f"cat {ACCOUNTS} 2>/dev/null || echo __ABSENT__")
    if not out.strip():                             # bureau occupé ou en train de redémarrer : on réessaie une fois
        time.sleep(2)
        out = dx(f"cat {ACCOUNTS} 2>/dev/null || echo __ABSENT__")
    if not out.strip():
        return False
    if out.strip() == "__ABSENT__":                 # première fois : reprend les comptes d'origine
        acc = [(u, "") for u in DEFAULT_USERS]
        save_accounts(acc)
    else:
        acc = []
        for l in out.splitlines():
            u, _, n = l.partition(":")
            if re.fullmatch(LOGIN_RE, u.strip()) and u.strip() not in [x for x, _ in acc]:
                acc.append((u.strip(), n.strip()))
    if not acc:
        return False
    with acc_lock:
        USERS[:] = [u for u, _ in acc]
        NAMES.clear()
        NAMES.update({u: n for u, n in acc if n})
    return True


def clean_name(n):
    return re.sub(r"[:\r\n\t]", " ", n).strip()[:40]


def new_password():
    return "".join(secrets.choice("abcdefghijkmnpqrstuvwxyz23456789") for _ in range(8))


def add_account(login, name, pw=""):
    """Crée un compte enfant. Renvoie (ok, message, mot de passe)."""
    login, name = login.strip().lower(), clean_name(name)
    if not re.fullmatch(LOGIN_RE, login):
        return False, "Identifiant invalide : lettres minuscules sans accent, chiffres ou « _ », 2 à 31 caractères, en commençant par une lettre.", ""
    if not name:
        return False, "Indiquez le prénom de l'enfant.", ""
    pw = pw.strip() or new_password()
    if not re.fullmatch(r"[^\s:]{4,64}", pw):
        return False, "Mot de passe refusé : 4 caractères minimum, sans espace ni « : ».", ""
    with acc_lock:
        if not load_accounts():
            return False, "Les sessions MaranYSE ne répondent pas : démarrez-les d'abord.", ""
        if login in USERS or login in RESERVED or dx(f"id -u {login} >/dev/null 2>&1 && echo pris").strip():
            return False, f"L'identifiant « {login} » est déjà utilisé.", ""
        # dossier personnel déjà présent (compte supprimé en gardant ses fichiers) : on le reprend
        out = dx(f"set -e; if [ -d /home/{login} ]; then useradd -u $(stat -c %u /home/{login}) -s /bin/bash {login}; "
                 f"else useradd -m -K UID_MIN=1001 -K GID_MIN=1001 -s /bin/bash {login}; fi; "
                 f"[ -f /home/{login}/.xsession ] || {{ echo 'exec /usr/local/bin/maranyse-session' > /home/{login}/.xsession; chown {login}: /home/{login}/.xsession; }}; "
                 f"chmod 700 /home/{login}; "
                 f"[ -f /home/{login}/.config/Thonny/configuration.ini ] || {{ mkdir -p /home/{login}/.config/Thonny; "
                 f"printf '[general]\nlanguage = fr_FR\n' > /home/{login}/.config/Thonny/configuration.ini; chown -R {login}: /home/{login}/.config; }}; "
                 f"sed -i '/^{login}:/d' /secrets/mots_de_passe.txt; tee -a /secrets/mots_de_passe.txt | chpasswd; echo cree",
                 inp=f"{login}:{pw}\n")
        if out.strip() != "cree":
            return False, "La création du compte a échoué dans le bureau.", ""
        save_accounts([(u, NAMES.get(u, "")) for u in USERS] + [(login, name)])
        load_accounts()
    threading.Thread(target=logiciels.preparer, args=([login],), daemon=True).start()   # VS Code en français, etc.
    return True, f"Compte de {name} créé.", pw


def rename_account(u, name):
    name = clean_name(name)
    if not name:
        return "Le prénom ne peut pas être vide."
    with acc_lock:
        if not load_accounts() or u not in USERS:
            return "Enfant inconnu."
        NAMES[u] = name
        save_accounts([(x, NAMES.get(x, "")) for x in USERS])
    return f"Nom affiché changé : {name}."


def remove_account(u, purge=False):
    """Supprime un compte enfant. purge=True efface aussi ses fichiers et ses statistiques."""
    with acc_lock:
        if not load_accounts() or u not in USERS:
            return "Enfant inconnu."
        if len(USERS) == 1:
            return "Impossible de supprimer le dernier compte."
        n = nom(u)
        logout(u)
        pid = f"/run/kids-dns-{u}.pid"
        dx(f"[ -e {pid} ] && kill $(cat {pid}) 2>/dev/null; rm -f {pid} /etc/kids-dns/{u}.conf /run/kids-pause-{u}; "
           f"userdel -f {'-r ' if purge else ''}{u} 2>/dev/null; "
           f"sed -i '/^{u}:/d' /secrets/mots_de_passe.txt; sed -i '/^{u}$/d' /secrets/verrouilles.txt 2>/dev/null; true")
        save_accounts([(x, NAMES.get(x, "")) for x in USERS if x != u])
        load_accounts()
        with lock:
            save_rules(load_rules())                 # retire ses règles et son planning
        if purge:
            c = db()
            for t in ("usage", "titles", "sites", "events", "segments", "ressources"):
                c.execute(f"DELETE FROM {t} WHERE user=?", (u,))
            c.commit()
            c.close()
        for k in ("prev_conn", "warned", "grace", "lvl", "blk"):
            STATE[k].pop(u, None)
        STATE["net_sig"] = STATE["app_sig"] = None   # pare-feu et applications réappliqués au prochain passage
    return f"Compte de {n} supprimé." + ("" if purge else " Ses fichiers sont conservés : en recréant un compte avec le même identifiant, il les retrouvera.")


# ======================================================================
# Règles
# ======================================================================
def clean_domain(d):
    d = re.sub(r"^(https?://)?(www\.)?", "", d.strip().lower()).split("/")[0]
    return d if re.fullmatch(r"[a-z0-9-]+(\.[a-z0-9-]+)*\.[a-z]{2,}", d) else ""


def target(cle):
    """Décrit l'objet d'une règle : (type, nom, domaines, mots du titre, nom dans les stats ou None)."""
    if cle.startswith("app:") and cle[4:] in APPS:
        n, lab, _ = APPS[cle[4:]]
        return "app", n, [], [], lab
    if cle.startswith("site:") and cle[5:] in SITES:
        n, doms, kws = SITES[cle[5:]]
        return "site", n, doms, kws, None
    if cle.startswith("dom:") and clean_domain(cle[4:]):
        d = cle[4:]
        return "site", d, [d], [d.split(".")[-2] if d.count(".") >= 1 else d], None
    return None


def default_child():
    return {"grille": {str(i): "V" * SLOTS for i in range(7)}, "quota": {str(i): 0 for i in range(7)},
            "internet": "herite", "regles": [], "bonus_jusqu": None, "pause_jusqu": None, "langue": i18n.DEFAUT}


def load_rules():
    try:
        data = json.load(open(RULES))
    except (OSError, ValueError):
        data = {}
    g = data.get(ALL) or {"internet": "filtre", "regles": [{"cle": "site:youtube", "mode": "bloquer", "minutes": 0}]}
    gs = g.get("securite") or {}
    out = {ALL: {"internet": g.get("internet", "filtre"), "regles": [r for r in g.get("regles", []) if target(r.get("cle", ""))],
                 "securite": {k: gs.get(k) if gs.get(k) in SECU_VAL else SECU_DEFAUT[k] for k in SECU}}}
    for u in USERS:
        old = data.get(u, {})
        r = default_child()
        for k in ("grille", "quota", "bonus_jusqu", "pause_jusqu", "internet", "regles", "langue"):
            if k in old:
                r[k] = old[k]
        if r["langue"] not in i18n.LANGUES:
            r["langue"] = i18n.DEFAUT
        us = old.get("securite") or {}
        r["securite"] = {k: us.get(k) if us.get(k) in SECU_VAL else "herite" for k, v in SECU.items() if v[2]}
        if "orange" in old and "regles" not in old:           # ancien format (version précédente)
            o = old["orange"]
            r["internet"] = o.get("internet", "herite") if o.get("internet") != "filtre" else "herite"
            r["regles"] = ([{"cle": f"site:{s}", "mode": "bloquer", "minutes": 0} for s in o.get("sites", []) if s != "youtube"] +
                           [{"cle": f"app:{a}", "mode": "bloquer", "minutes": 0} for a in o.get("apps_bloquees", [])] +
                           [{"cle": f"dom:{d}", "mode": "bloquer", "minutes": 0}
                            for d in filter(None, map(clean_domain, re.split(r"[\s,;]+", o.get("sites_perso", ""))))])
        r["regles"] = [x for x in r["regles"] if target(x.get("cle", ""))]
        for i in range(7):
            gg = r["grille"].get(str(i), "")
            r["grille"][str(i)] = gg if re.fullmatch(f"[VOR]{{{SLOTS}}}", gg) else "V" * SLOTS
        out[u] = r
    return out


def rules_stamp():
    try:
        return os.stat(RULES).st_mtime_ns
    except OSError:
        return None


def save_rules(data):
    tmp = RULES + ".tmp"
    json.dump(data, open(tmp, "w"), indent=2, ensure_ascii=False)
    os.replace(tmp, RULES)


def merged_rules(data, u):
    """Règles de l'orange pour un enfant : communes, remplacées par les individuelles sur le même objet."""
    m = {x["cle"]: dict(x, source="commune") for x in data[ALL]["regles"]}
    m.update({x["cle"]: dict(x, source="individuelle") for x in data[u]["regles"]})
    return list(m.values())


def secu(data, u, k):
    """Réglage effectif d'un enfant : son exception, sinon la règle commune."""
    v = data[u].get("securite", {}).get(k, "herite") if SECU[k][2] else "herite"
    return data[ALL]["securite"][k] if v == "herite" else v


def internet_mode(data, u):
    m = data[u].get("internet", "herite")
    return data[ALL]["internet"] if m == "herite" else m


def dt(s):
    return datetime.fromisoformat(s) if s else None


def access(u, r, now, used_s):
    """(niveau V/O/R, raison, minutes avant le rouge ou None). used_s = temps d'écran du jour."""
    p, b = dt(r.get("pause_jusqu")), dt(r.get("bonus_jusqu"))
    if p and p > now:
        return "P", f"pause jusqu'à {p:%H:%M}" + ("" if p.date() == now.date() else f" le {p:%d.%m}"), None
    if b and b > now:
        return "V", f"bonus accordé jusqu'à {b:%H:%M}", (b - now).total_seconds() / 60
    wd, mins = now.weekday(), now.hour * 60 + now.minute
    k = mins // 30
    g = r["grille"][str(wd)]
    q = int(r["quota"].get(str(wd)) or 0)
    if q and used_s >= q * 60:
        return "R", f"temps d'écran du jour épuisé ({q} min)", None
    if g[k] == "R":
        nxt = next((j for j in range(k + 1, SLOTS) if g[j] != "R"), None)
        return "R", "horaire interdit" + (f", réouverture à {nxt // 2}h{30 * (nxt % 2):02d}" if nxt is not None else ""), None
    left = None                 # minutes jusqu'à la prochaine case rouge (sur 24 h glissantes)
    for j in range(1, SLOTS + 1):
        d, kk = (wd + (k + j) // SLOTS) % 7, (k + j) % SLOTS
        if r["grille"][str(d)][kk] == "R":
            left = (k + j) * 30 - mins
            break
    if q:
        ql = q - used_s / 60
        left = ql if left is None else min(left, ql)
    why = "selon le planning" + (f" · écran {dur(used_s)} / {q} min" if q else "")
    return g[k], why, left


def orange_status(data, u, c):
    """Pour chaque règle de l'orange : (règle, utilisé aujourd'hui en s, bloqué maintenant ?)."""
    res = []
    for x in merged_rules(data, u):
        used = usage_of(c, u, x["cle"])
        blocked = x["mode"] == "bloquer" or (x["mode"] == "limiter" and used >= int(x.get("minutes") or 0) * 60)
        res.append((x, used, blocked))
    return res


def profile(data, u, lvl, c):
    """Restrictions effectives : {internet, apps (clés), domaines}."""
    if lvl == "V":
        return {"internet": "libre", "apps": [], "domains": [], "blocked": []}
    apps, doms, names = [], [], []
    for x, _, blocked in orange_status(data, u, c):
        if blocked:
            t = target(x["cle"])
            names.append(t[1].split(" (")[0])
            if t[0] == "app":
                apps.append(x["cle"][4:])
            else:
                doms += t[2]
    return {"internet": internet_mode(data, u), "apps": sorted(apps), "domains": sorted(set(doms)), "blocked": names}


def describe(prof):
    parts = ["internet " + INTERNET[prof["internet"]].lower()]
    if prof["blocked"]:
        parts.append("bloqué : " + ", ".join(prof["blocked"]))
    return " ; ".join(parts)


# ======================================================================
# Statistiques
# ======================================================================
def db():
    c = sqlite3.connect(DB, timeout=10)
    c.executescript("""
    CREATE TABLE IF NOT EXISTS usage(day TEXT, user TEXT, app TEXT, sec INTEGER, PRIMARY KEY(day,user,app));
    CREATE TABLE IF NOT EXISTS titles(day TEXT, user TEXT, app TEXT, title TEXT, sec INTEGER, PRIMARY KEY(day,user,app,title));
    CREATE TABLE IF NOT EXISTS sites(day TEXT, user TEXT, cle TEXT, sec INTEGER, PRIMARY KEY(day,user,cle));
    CREATE TABLE IF NOT EXISTS events(ts TEXT, user TEXT, kind TEXT, detail TEXT);
    CREATE TABLE IF NOT EXISTS segments(user TEXT, app TEXT, title TEXT, site TEXT, start TEXT, end TEXT);
    CREATE INDEX IF NOT EXISTS segments_user ON segments(user, start);
    CREATE INDEX IF NOT EXISTS segments_app ON segments(app, start);
    CREATE TABLE IF NOT EXISTS ressources(hour TEXT, user TEXT, cpu REAL, mem_sum REAL, mem_max REAL, n INTEGER,
                                          net_in INTEGER, net_out INTEGER, disk REAL, PRIMARY KEY(hour, user));
    """)
    return c


def add(c, table, keys, sec):
    cols = list(keys)
    c.execute(f"INSERT INTO {table}({','.join(cols)},sec) VALUES({','.join('?'*len(cols))},?) "
              f"ON CONFLICT DO UPDATE SET sec=sec+excluded.sec", [*keys.values(), sec])


def event(c, u, kind, detail=""):
    c.execute("INSERT INTO events VALUES(?,?,?,?)", (datetime.now().isoformat(timespec="seconds"), u, kind, detail))


def today():
    return datetime.now().date().isoformat()


def used_today(c, u):
    return c.execute("SELECT COALESCE(SUM(sec),0) FROM usage WHERE day=? AND user=?", (today(), u)).fetchone()[0]


def usage_of(c, u, cle):
    t = target(cle)
    if not t:
        return 0
    if t[0] == "app":
        q = ("SELECT COALESCE(SUM(sec),0) FROM usage WHERE day=? AND user=? AND app=?", (today(), u, t[4]))
    else:
        q = ("SELECT COALESCE(SUM(sec),0) FROM sites WHERE day=? AND user=? AND cle=?", (today(), u, cle))
    return c.execute(*q).fetchone()[0]


def tracked_sites(data):
    keys = {f"site:{k}" for k in SITES}
    for scope in data.values():
        keys |= {x["cle"] for x in scope.get("regles", []) if x["cle"].startswith("dom:")}
    return keys


# ======================================================================
# Boucle : collecte + application des règles
# ======================================================================
STATE = {"prev_conn": {}, "warned": {}, "grace": {}, "net_sig": None, "app_sig": None, "lvl": {}, "blk": {}, "seg": {}}


def _logiciels_changes():
    with acc_lock:                               # la boucle ne parcourt pas APPS pendant la mise à jour
        logiciels.register(APPS, LABELS)
        STATE["app_sig"] = None                  # blocages réappliqués au prochain passage (nouveaux programmes)


logiciels._on_change.append(_logiciels_changes)
logiciels._users = lambda: list(USERS)


def segment(c, u, app, title, site, now):
    """Journal détaillé : périodes continues « tel enfant, telle application (et fenêtre), de telle heure à telle heure ».
    Chaque relevé (toutes les 30 s) prolonge la période en cours ou en ouvre une nouvelle."""
    ts = now.isoformat(timespec="seconds")
    last = STATE["seg"].get(u)                      # (rowid, app, titre, fin)
    suite = last and (now - last[3]).total_seconds() <= TICK * 2.5
    if suite and last[1] == app and last[2] == title:
        c.execute("UPDATE segments SET end=? WHERE rowid=?", (ts, last[0]))
        STATE["seg"][u] = (last[0], app, title, now)
        return
    start = last[3].isoformat(timespec="seconds") if suite else (now - timedelta(seconds=TICK)).isoformat(timespec="seconds")
    cur = c.execute("INSERT INTO segments(user, app, title, site, start, end) VALUES(?,?,?,?,?,?)", (u, app, title, site, start, ts))
    STATE["seg"][u] = (cur.lastrowid, app, title, now)


# --- Ressources utilisées par chaque enfant (processeur, mémoire, internet, disque), cumulées par heure.
# Relevé dans le conteneur : /proc pour le processeur et la mémoire de tous les programmes de l'enfant ;
# compteurs du pare-feu (table mangle, chaînes MNET_*, sans effet sur le filtrage) pour le volume internet ;
# taille du dossier personnel toutes les 10 minutes.
RES_PROBE = r'''
import os, re, sys, json, subprocess
hz, pg = os.sysconf("SC_CLK_TCK"), os.sysconf("SC_PAGE_SIZE")
pr = []
for p in os.listdir("/proc"):
    if p.isdigit():
        try:
            uid = os.stat("/proc/" + p).st_uid
            if 1000 <= uid < 60000:
                s = open("/proc/%s/stat" % p).read()
                f = s[s.rindex(")") + 2:].split()
                pr.append([uid, int(p), int(f[19]), (int(f[11]) + int(f[12])) / hz, int(f[21]) * pg])
        except Exception:
            pass
net = {}
for ch, k in (("MNET_IN", 0), ("MNET_OUT", 1)):
    r = subprocess.run(["iptables", "-w", "-t", "mangle", "-nvxL", ch], capture_output=True, text=True)
    if r.returncode:
        net = None
        break
    for l in r.stdout.splitlines()[2:]:
        m = re.search(r"/\* u(\d+) \*/", l)
        if m:
            net.setdefault(m.group(1), [0, 0])[k] += int(l.split()[1])
disk = {}
for u in sys.argv[1:]:
    r = subprocess.run(["du", "-sxm", "/home/" + u], capture_output=True, text=True)
    if r.stdout.split():
        disk[u] = int(r.stdout.split()[0])
print(json.dumps({"pr": pr, "net": net, "disk": disk}))
'''


def apply_netcount(ids):
    """Compteurs internet par enfant : chaque connexion ouverte par un programme de l'enfant est marquée à son
    numéro ; on compte les octets envoyés (MNET_OUT) et reçus (MNET_IN). Rien n'est bloqué ici."""
    rules = "*mangle\n:MNET_OUT - [0:0]\n:MNET_IN - [0:0]\n"
    for u, uid in sorted(ids.items()):
        rules += (f"-A MNET_OUT ! -o lo -m owner --uid-owner {uid} -m comment --comment u{uid} -j CONNMARK --set-mark {uid}\n"
                  f"-A MNET_IN ! -i lo -m connmark --mark {uid} -m comment --comment u{uid} -j RETURN\n")
    rules += "COMMIT\n"
    dx("iptables-restore -w --noflush && "
       "{ iptables -w -t mangle -C OUTPUT -j MNET_OUT 2>/dev/null || iptables -w -t mangle -A OUTPUT -j MNET_OUT; } && "
       "{ iptables -w -t mangle -C INPUT -j MNET_IN 2>/dev/null || iptables -w -t mangle -A INPUT -j MNET_IN; }", inp=rules)


def ressources(c, ids, now):
    """Un relevé (toutes les 30 s) : ajoute à l'heure en cours le temps processeur consommé depuis le relevé
    précédent, la mémoire occupée, les octets internet échangés et (toutes les 10 minutes) la taille du dossier."""
    st = STATE.setdefault("res", {"cpu": None, "net": {}, "netsig": None, "disk": {}})
    sig = json.dumps(ids, sort_keys=True)
    if st["netsig"] != sig:
        apply_netcount(ids)
        st["netsig"], st["net"] = sig, {}
    hour = now.strftime("%Y-%m-%dT%H")
    tranche = now.strftime("%Y-%m-%dT%H:") + str(now.minute // 10)        # toutes les 10 minutes (et dès la création du compte)
    du = [u for u in USERS if u in ids and st["disk"].get(u) != tranche]
    try:
        r = json.loads(dx("python3 - " + " ".join(du), inp=RES_PROBE) or "null")
    except ValueError:
        r = None
    if not r:
        return
    for u in du:
        st["disk"][u] = tranche
    by_uid = {v: k for k, v in ids.items()}
    row = {u: [0.0, 0, 0, 0, 0, None] for u in USERS}         # cpu (s), mémoire (octets), programmes, reçu, envoyé, disque (Mo)
    cpu = {}
    for uid, pid, start, t, rss in r["pr"]:
        u = by_uid.get(str(uid))
        if u not in row:
            continue
        cpu[(pid, start)] = t
        if st["cpu"] is not None:                            # premier relevé : seulement la référence
            row[u][0] += max(0.0, t - st["cpu"].get((pid, start), 0.0))
        row[u][1] += rss
        row[u][2] += 1
    st["cpu"] = cpu
    if r["net"] is None:                                     # compteurs absents (bureau redémarré) : on les recrée
        st["netsig"] = None
    else:
        for uid, (rx, tx) in r["net"].items():
            u = by_uid.get(uid)
            p = st["net"].get(uid)
            st["net"][uid] = (rx, tx)
            if u in row and p:
                row[u][3] = rx - p[0] if rx >= p[0] else rx    # compteurs remis à zéro : on repart de là
                row[u][4] = tx - p[1] if tx >= p[1] else tx
    for u, mb in r["disk"].items():
        if u in row:
            row[u][5] = mb
    for u, (t, rss, n, rx, tx, mb) in row.items():
        if n or rx or tx or mb is not None:
            mo = rss / 1048576
            c.execute("INSERT INTO ressources(hour, user, cpu, mem_sum, mem_max, n, net_in, net_out, disk) VALUES(?,?,?,?,?,?,?,?,?) "
                      "ON CONFLICT(hour, user) DO UPDATE SET cpu=cpu+excluded.cpu, mem_sum=mem_sum+excluded.mem_sum, "
                      "mem_max=MAX(mem_max, excluded.mem_max), n=n+excluded.n, net_in=net_in+excluded.net_in, "
                      "net_out=net_out+excluded.net_out, disk=COALESCE(excluded.disk, disk)",
                      (hour, u, t, mo if n else 0, mo if n else 0, 1 if n else 0, rx, tx, mb))


# ======================================================================
# Puissance : part de l'ordinateur hôte (Windows) laissée au bureau des enfants
# ======================================================================
PUISSANCE = f"{HOME}/puissance.json"     # position du curseur (page Puissance)
HOTE = f"{HOME}/hote.json"               # capacités de l'ordinateur hôte, mesurées par installer_controle.sh
RESERVE_VM_MO = 1024                     # mémoire gardée pour la VM elle-même (tableau de bord, Docker)
PCT_MIN = 5
PCT_PLAFOND = 60                         # Windows garde toujours au moins 40 % de l'ordinateur


def hote():
    """Processeurs et mémoire de l'ordinateur hôte et plafond de la VM (réglages Hyper-V)."""
    try:
        h = json.load(open(HOTE))
    except (OSError, ValueError):
        h = {}
    vm_cpu = os.cpu_count() or 1
    try:
        mem = int(open("/proc/meminfo").read().split()[1]) // 1024
    except (OSError, ValueError, IndexError):
        mem = 2048
    threads = max(vm_cpu, int(h.get("threads") or vm_cpu))
    return {"nom": re.sub(r"\s*\((R|TM)\)", "", h.get("cpu", "")), "threads": threads, "ram_mo": max(mem, int(h.get("ram_mo") or mem)),
            "vm_cpu": vm_cpu, "vm_ram_mo": max(mem, int(h.get("vm_ram_mo") or mem)), "disque_libre_go": h.get("disque_libre_go")}


def pct_max(h):
    """Plus grande part possible : la VM ne peut pas dépasser ce qu'Hyper-V lui donne."""
    return max(PCT_MIN, min(PCT_PLAFOND, int(100 * min(h["vm_cpu"] / h["threads"], h["vm_ram_mo"] / h["ram_mo"]) + 0.5)))


def limites(pct, h):
    """(processeurs, mémoire en Mo) accordés au bureau des enfants pour une part de l'ordinateur en %."""
    cpus = round(min(h["vm_cpu"], h["threads"] * pct / 100), 2)
    mem = int(min(h["vm_ram_mo"] - RESERVE_VM_MO, h["ram_mo"] * pct / 100))
    return cpus, max(1024, mem)


def puissance_pct(h=None):
    h = h or hote()
    try:
        p = int(json.load(open(PUISSANCE))["pct"])
    except (OSError, ValueError, KeyError, TypeError):
        p = pct_max(h)                       # pas encore réglé : tout ce que la VM permet
    return max(PCT_MIN, min(pct_max(h), p))


def save_puissance(**kw):
    """Enregistre pct (part de l'ordinateur) et/ou disque_go (quota par enfant) sans perdre l'autre réglage."""
    try:
        d = json.load(open(PUISSANCE))
    except (OSError, ValueError):
        d = {}
    d.update({k: int(v) for k, v in kw.items()})
    tmp = PUISSANCE + ".tmp"
    json.dump(d, open(tmp, "w"))
    os.replace(tmp, PUISSANCE)


# --- Espace disque : quota par enfant (quotas Linux du disque de la VM, activés par installer_controle.sh)
QUOTA_RESERVE_GO = 10                    # place gardée libre pour la VM et le bureau (mises à jour, logiciels)
QUOTA_MIN_GO = 1


def disque_vm():
    """(taille du disque de la VM, place libre) en Go."""
    st = os.statvfs("/")
    return st.f_blocks * st.f_frsize / 2**30, st.f_bavail * st.f_frsize / 2**30


def quota_max_go(n=None):
    """Quota maximum par enfant : la place libre (plus ce que les enfants occupent déjà) partagée entre eux,
    pour que tous puissent remplir leur quota sans remplir le disque."""
    n = max(1, n or len(USERS))
    _, libre = disque_vm()
    occupe = sum(v for v in STATE.get("quota_use", {}).values()) / 2**20     # Ko -> Go
    return max(QUOTA_MIN_GO, int((libre + occupe - QUOTA_RESERVE_GO) / n))


def quota_go():
    try:
        q = int(json.load(open(PUISSANCE))["disque_go"])
    except (OSError, ValueError, KeyError, TypeError):
        q = quota_max_go()                   # pas encore réglé : la part équitable de la place libre
    return max(QUOTA_MIN_GO, q)


# --- Charge en direct (en-tête du tableau) : la VM elle-même et l'ordinateur hôte (envoyée par vm/charge_hote.ps1)
JETON_HOTE = f"{HOME}/.jeton_charge"
_CHARGE = {"vm_prec": None, "vm": None, "hote": None}
_charge_lock = threading.Lock()


def charge_vm():
    """Processeur (%, depuis l'appel précédent, au moins 1 s) et mémoire (%) de la VM."""
    with _charge_lock:
        now = time.time()
        if _CHARGE["vm"] and now - _CHARGE["vm"]["t"] < 2:
            return _CHARGE["vm"]
        f = [int(x) for x in open("/proc/stat").readline().split()[1:]]
        idle, total = f[3] + f[4], sum(f[:8])
        p = _CHARGE["vm_prec"]
        if not p or now - p[2] > 30:                     # pas de mesure récente : 1 s d'échantillon
            time.sleep(1)
            f2 = [int(x) for x in open("/proc/stat").readline().split()[1:]]
            p, (idle, total) = (idle, total, now), (f2[3] + f2[4], sum(f2[:8]))
            now = time.time()
        cpu = 100 * (1 - (idle - p[0]) / max(1, total - p[1]))
        mi = {l.split(":")[0]: int(l.split()[1]) for l in open("/proc/meminfo") if l.split()[0][:-1] in ("MemTotal", "MemAvailable")}
        mem = 100 * (1 - mi["MemAvailable"] / mi["MemTotal"])
        _CHARGE["vm_prec"] = (idle, total, now)
        _CHARGE["vm"] = {"cpu": round(max(0, min(100, cpu))), "mem": round(mem), "t": now,
                         "mem_go": round(mi["MemTotal"] / 2**20, 1)}
        return _CHARGE["vm"]


def jeton_hote():
    """Secret partagé avec le script de l'ordinateur hôte (créé au premier besoin)."""
    try:
        return open(JETON_HOTE).read().strip()
    except OSError:
        j = secrets.token_hex(16)
        fd = os.open(JETON_HOTE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        os.write(fd, j.encode())
        os.close(fd)
        return j


def recevoir_charge_hote(d):
    _CHARGE["hote"] = {"cpu": max(0, min(100, int(d["cpu"]))), "mem": round(100 * (1 - int(d["libre_mo"]) / max(1, int(d["ram_mo"])))),
                       "t": time.time()}


def charge_hote():
    h = _CHARGE["hote"]
    return h if h and time.time() - h["t"] < 30 else None     # plus de nouvelles depuis 30 s : PC hôte inconnu


def apply_quota(ids, force=False):
    """Fixe le quota de chaque enfant (si changé, nouveau compte, ou toutes les heures) et relève ce qu'ils
    occupent (toutes les 5 min). setquota/repquota de la VM via un petit conteneur privilégié (nsenter)."""
    go = quota_go()
    sig = json.dumps([go, sorted(ids.items())])
    now = time.time()
    regle = force or STATE.get("quota_sig") != sig or now - STATE.get("quota_t", 0) > 3600
    if not regle and now - STATE.get("quota_lu", 0) < 300:
        return
    kb = go * 1024 * 1024
    cmd = ("; ".join(f"setquota -u {uid} {kb} {kb} 0 0 /" for uid in ids.values()) + "; " if regle else "") + "repquota -un /"
    try:
        r = subprocess.run(["docker", "run", "--rm", "--privileged", "--pid=host", "debian:bookworm-slim",
                            "nsenter", "-t", "1", "-m", "--", "sh", "-c", cmd], capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        return
    by_uid = {v: k for k, v in ids.items()}
    use = {}
    for l in r.stdout.splitlines():
        f = l.split()
        if len(f) >= 5 and f[0].lstrip("#") in by_uid and f[2].isdigit():
            use[by_uid[f[0].lstrip("#")]] = int(f[2])                          # Ko occupés
    if "Report for user quotas" not in r.stdout:
        print("erreur quotas:", (r.stderr or r.stdout).strip()[:300], flush=True)
        return
    STATE["quota_use"] = {u: use.get(u, 0) for u in ids}
    STATE["quota_lu"] = now
    if regle:
        STATE["quota_sig"], STATE["quota_t"] = sig, now


def apply_puissance():
    """Applique les limites au conteneur (docker update, sans redémarrage ni fermeture de session) si elles ont
    changé ou si le bureau a été recréé, puis relève ce qu'il consomme (groupe de contrôle du conteneur)."""
    h = hote()
    cpus, mem = limites(puissance_pct(h), h)
    r = subprocess.run(["docker", "inspect", "-f", "{{.Id}} {{.HostConfig.NanoCpus}} {{.HostConfig.Memory}}", C],
                       capture_output=True, text=True)
    f = r.stdout.split()
    if len(f) != 3:
        return
    if f[1:] != [str(int(cpus * 1e9)), str(mem * 1048576)]:
        u = subprocess.run(["docker", "update", "--cpus", str(cpus), "--memory", f"{mem}m", "--memory-swap", f"{mem + 512}m", C],
                           capture_output=True, text=True)
        if u.returncode:
            print("erreur limites:", u.stderr.strip(), flush=True)
    st = STATE.setdefault("puiss", {})
    base = f"/sys/fs/cgroup/system.slice/docker-{f[0]}.scope/"
    try:
        cs = dict(l.split() for l in open(base + "cpu.stat"))
        ev = dict(l.split() for l in open(base + "memory.events"))
        cur = int(open(base + "memory.current").read())
    except (OSError, ValueError):
        return
    now = time.time()
    use, thr, oom = int(cs["usage_usec"]), int(cs.get("nr_throttled", 0)), int(ev.get("oom_kill", 0))
    p = st.get("brut")
    if p and p[0] == f[0] and now > p[1]:
        st["cpu"] = max(0.0, (use - p[2]) / 1e6 / (now - p[1]))     # processeurs occupés en moyenne depuis le relevé précédent
        if thr > p[3]:
            st["frein"] = now                                       # programmes ralentis par la limite
        if oom > p[4]:
            st["oom"] = now                                         # un programme fermé faute de mémoire
    st["brut"] = (f[0], now, use, thr, oom)
    st["mem"] = cur


def upstream_dns():
    for l in dx("cat /etc/resolv.conf").splitlines():
        m = re.match(r"\s*nameserver\s+(\d+\.\d+\.\d+\.\d+)", l)
        if m and not m.group(1).startswith("127."):
            return m.group(1)
    return "1.1.1.1"


def apply_internet(eff, ids, sec):
    """Pare-feu par enfant + un petit serveur DNS par enfant pour bloquer des sites.

    Les règles sont remplacées D'UN SEUL COUP (iptables-restore, atomique) : il n'existe jamais d'instant où la
    redirection vers le DNS filtré a disparu (sinon une requête pourrait partir vers le DNS normal, non filtré).
    Pendant le redémarrage des petits serveurs DNS, les requêtes échouent : en cas de doute, c'est fermé."""
    up = upstream_dns()
    filt, nat, dns = [], [], ["mkdir -p /etc/kids-dns"]
    for i, u in enumerate(USERS):
        uid, prof = ids.get(u), eff[u]
        mode, doms = prof["internet"], prof["domains"]
        pid = f"/run/kids-dns-{u}.pid"
        dns.append(f"[ -e {pid} ] && kill $(cat {pid}) 2>/dev/null && sleep 0.3; rm -f {pid}")
        if not uid:
            continue
        o = f"-m owner --uid-owner {uid}"
        if sec[u]["reseau"] == "interdit":
            # internet réservé à Firefox (groupe « internet ») ; le reste de la machine (lo) reste accessible
            filt.append(f"! -o lo {o} ! --gid-owner {INTERNET_GID} -j REJECT")
        if sec[u]["pip"] == "interdit":
            filt.append(f"-o lo -p tcp --dport {PIP_PROXY_PORT} {o} -j REJECT")
        if mode == "bloque":
            filt += [f"-o lo {o} -j RETURN", f"{o} -j REJECT"]
            continue
        if mode == "filtre" or doms:
            ip = f"127.0.1.{i + 1}"
            conf = [f"listen-address={ip}", "bind-interfaces", "port=53", "no-resolv", "no-hosts", "cache-size=1000",
                    *[f"server={x}" for x in (FAMILY_DNS if mode == 'filtre' else [up])], f"pid-file={pid}", "user=nobody", "group=nogroup"]
            doh = sec[u]["doh"] == "interdit"
            for d in doms + (DOH_NAMES if doh else []):
                conf += [f"address=/{d}/0.0.0.0", f"address=/{d}/::"]
            if doh:
                conf.append("address=/use-application-dns.net/")  # signal standard : « DoH désactivé ici » (Firefox)
            dns.append("printf '%s\\n' " + " ".join(f"'{x}'" for x in conf) + f" > /etc/kids-dns/{u}.conf")
            dns.append(f"dnsmasq --conf-file=/etc/kids-dns/{u}.conf")
            for proto in ("udp", "tcp"):
                nat.append(f"-p {proto} --dport 53 {o} -j DNAT --to-destination {ip}:53")
            filt.append(f"-p tcp --dport 853 {o} -j REJECT")      # DNS chiffré : interdit
            # DNS par HTTPS (DoH) : serveurs connus injoignables (le DNS normal, déjà redirigé plus haut, n'est pas touché)
            if doh:
                filt.append(f"-d {','.join(DOH_IPS)} {o} -j REJECT")
    rules = ("*filter\n:KIDS - [0:0]\n" + "".join(f"-A KIDS {r}\n" for r in filt) + "COMMIT\n"
             "*nat\n:KIDS - [0:0]\n" + "".join(f"-A KIDS {r}\n" for r in nat) + "COMMIT\n")
    # 1) chaînes et renvois présents ; 2) nouvelles règles, remplacées d'un bloc ; 3) serveurs DNS des enfants
    dx("iptables -N KIDS 2>/dev/null; iptables -C OUTPUT -j KIDS 2>/dev/null || iptables -I OUTPUT -j KIDS; "
       "iptables -t nat -N KIDS 2>/dev/null; iptables -t nat -C OUTPUT -j KIDS 2>/dev/null || iptables -t nat -I OUTPUT -j KIDS; true")
    dx("cat > /run/kids-rules && iptables-restore --noflush < /run/kids-rules && echo ok", inp=rules)
    dx("; ".join(dns) + "; touch /run/kids-net")


def apply_exec(allowed):
    """Programmes téléchargés : dossiers des enfants et dossiers temporaires montés avec ou sans « noexec ».
    Le bureau n'a pas le droit de changer ses montages (profil AppArmor) : un petit conteneur privilégié entre
    dans son espace de montage (nsenter) le temps de la commande. Le montage de la VM n'est pas modifié."""
    want = "exec" if allowed else "noexec"
    cur = {m: ("noexec" if "noexec" in o.split(",") else "exec")
           for _, m, _, o, *_ in (l.split() for l in dx("cat /proc/mounts").splitlines() if len(l.split()) >= 4) if m in EXEC_MOUNTS}
    todo = [m for m in EXEC_MOUNTS if m in cur and cur[m] != want]
    if not todo:
        return
    cmd = "; ".join(f"mount -o remount{',bind' if m == '/home' else ''},nosuid,nodev,{want} {m}" for m in todo)
    try:
        pid = subprocess.run(["docker", "inspect", "-f", "{{.State.Pid}}", C], capture_output=True, text=True, timeout=10).stdout.strip()
        if pid.isdigit() and pid != "0":
            subprocess.run(["docker", "run", "--rm", "--privileged", "--pid=host", "debian:bookworm-slim",
                            "nsenter", "-t", pid, "-m", "sh", "-c", cmd], capture_output=True, timeout=40)
    except subprocess.TimeoutExpired:
        pass


def net_ok():
    return dx("[ -e /run/kids-net ] && iptables -S KIDS >/dev/null 2>&1 || exit 1; "
              "for p in /run/kids-dns-*.pid; do [ -e \"$p\" ] || continue; kill -0 $(cat \"$p\") 2>/dev/null || exit 1; done; echo ok").strip() == "ok"


def apply_apps(eff, sec):
    lines = []
    for key, (_, _, bins) in APPS.items():
        for b in bins:
            lines.append(f"[ -e {b} ] && setfacl -b {b}")
            for u in USERS:
                if key in eff[u]["apps"]:
                    lines.append(f"[ -e {b} ] && setfacl -m u:{u}:--- {b}")
    for b in OUTILS:                                   # anciens blocages des outils de programmation : retirés
        lines.append(f"[ -e {b} ] && setfacl -b {b}")
    lines.append("echo ok > /etc/kids-apps")
    dx("; ".join(lines))


def kill_blocked_apps(eff):
    """Ferme les applications bloquées encore ouvertes, d'après le nom du processus (/proc/PID/comm) :
    lancée depuis le menu, une appli s'appelle « tuxpaint », pas « /usr/bin/tuxpaint », et le conteneur
    n'a pas le droit de lire /proc/PID/exe des autres utilisateurs."""
    cmds = []
    for u in USERS:
        names = {os.path.basename(b)[:15] for key in eff[u]["apps"] for b in APPS[key][2]}
        if "firefox-esr" in names:
            names.add("GeckoMain")
        for n in sorted(names):
            # fermeture normale, puis forcée si l'appli ignore la demande (Tux Paint le fait)
            cmds.append(f"if pkill -u {u} -x {n}; then sleep 2; pkill -KILL -u {u} -x {n}; fi")
    if cmds:
        dx("; ".join(cmds) + "; true")


AUTO_TITLE = "MaranYSE"


def popup(u, disp, text, kind="info", auto=True):
    """Fenêtre de message chez l'enfant. Les messages automatiques remplacent le précédent
    (sinon ils s'empilent) ; les messages écrits par les parents restent tous affichés."""
    lang = STATE.get("langues", {}).get(u, i18n.DEFAUT)
    title = AUTO_TITLE if auto else i18n.traduire_texte("Message des parents", lang)
    if auto:                                     # messages automatiques : dans la langue de l'enfant
        text = i18n.traduire_lignes(text, lang, noms_traduction())
    if auto:
        dx(f"for p in $(pgrep -u {u} -x zenity); do tr '\\0' ' ' < /proc/$p/cmdline | grep -q -- '--title={AUTO_TITLE}' && kill $p; done; true")
    dx(f'zenity --{kind} "--title={title}" --width=420 --text="$MSG"', user=u,
       env={**xenv(u, disp), "MSG": text}, detach=True)


def noms_traduction():
    """Noms propres gardés tels quels dans les messages traduits (sites, applications)."""
    return sorted({v[0] for v in APPS.values()} | {v[0] for v in SITES.values()} | set(LABELS.values()))


LANGUES_FICHIER = "/etc/maranyse/langues"     # dans le bureau : « login code » (lu par maranyse-session)


def sync_langues(data):
    """Langue de chaque enfant : messages automatiques + bureau (appliquée à sa prochaine connexion)."""
    lg = {u: data[u].get("langue", i18n.DEFAUT) for u in USERS}
    STATE["langues"] = lg
    txt = "".join(f"{u} {lg[u]}\n" for u in sorted(lg))
    if STATE.get("langues_txt") == txt and dx(f"cat {LANGUES_FICHIER} 2>/dev/null") == txt:
        return
    dx(f"mkdir -p /etc/maranyse && cat > {LANGUES_FICHIER}.tmp && chmod 644 {LANGUES_FICHIER}.tmp && mv {LANGUES_FICHIER}.tmp {LANGUES_FICHIER} "
       f"&& cp {LANGUES_FICHIER} /secrets/langues.txt", inp=txt)
    STATE["langues_txt"] = txt


def logout(u):
    """Ferme la session de l'enfant ET coupe sa connexion Bureau à distance : sans cela, xrdp garde la connexion
    ouverte et la fenêtre de l'enfant reste affichée (écran noir ou figé) alors que la session est terminée."""
    xorg = dx(f"pgrep -u {u} -x Xorg").split()
    front = set()
    if xorg:
        log = dx("tail -n 400 /var/log/xrdp.log")
        for x in xorg:
            front |= set(re.findall(rf"xrdp_pid=(\d+) connected to X11rdp_pid={x} ", log))
    dx(f"pkill -TERM -u {u}; sleep 2; pkill -KILL -u {u}; rm -f /run/kids-pause-{u}; true")
    for p in front:              # processus xrdp (root) qui sert la connexion de cet enfant : vérifié avant de l'arrêter
        dx(f"[ \"$(ps -o comm= -p {p})\" = xrdp ] && [ \"$(ps -o ppid= -p {p} | tr -d ' ')\" != 1 ] && kill {p}; true")


PAUSE_TITLE = "PAUSE-BUREAU-ENFANTS"


def is_paused(r, now):
    p = dt(r.get("pause_jusqu"))
    return bool(p and p > now)


def frozen(u):
    return dx(f"[ -e /run/kids-pause-{u} ] && echo oui").strip() == "oui"


def freeze(u, disp, until_txt):
    """Pause : clavier et souris de la session désactivés + écran « Pause » par-dessus. Les applications restent ouvertes."""
    lang = STATE.get("langues", {}).get(u, i18n.DEFAUT)
    t = lambda x: html.escape(i18n.traduire_texte(x, lang, (), "message enfant"), quote=False)   # texte Pango
    env = {**xenv(u, disp), "MSG": f"<span size='60000'>⏸</span>\n\n<span size='28000' weight='bold'>{t('Pause')}</span>\n\n"
                                     f"<span size='14000'>{t(f'Tes parents ont mis ton ordinateur en pause jusqu’à {until_txt}.')}\n"
                                     f"{t('Tes applications restent ouvertes : tu retrouveras tout à la reprise.')}</span>\n\n"
                                     "<span size='11000' foreground='#8a8f9c'>MaranYSE</span>"}
    dx("xinput disable xrdpKeyboard; xinput disable xrdpMouse", user=u, env=env)
    # Vérifié depuis root : un « pgrep -f TITRE » lancé dans le shell de l'enfant se trouverait lui-même.
    if not overlay_up(u):
        dx(f"zenity --info --no-wrap --title={PAUSE_TITLE} --text=\"$MSG\" --ok-label=' ' & sleep 1.5; "
           f"wmctrl -r {PAUSE_TITLE} -b add,fullscreen,above", user=u, env=env, detach=True)
    dx(f"touch /run/kids-pause-{u}")


def overlay_up(u):
    return PAUSE_TITLE in dx(f"pgrep -u {u} -a zenity")


def unfreeze(u, disp):
    # Ferme seulement la fenêtre de pause (pas un « pkill -f TITRE », qui tuerait aussi la commande elle-même).
    dx(f"for p in $(pgrep -u {u} -x zenity); do grep -q {PAUSE_TITLE} /proc/$p/cmdline && kill $p; done; true")
    if disp:
        dx("xinput enable xrdpKeyboard; xinput enable xrdpMouse; true", user=u, env=xenv(u, disp))
    dx(f"rm -f /run/kids-pause-{u}")


def write_locked(locked):
    """Liste des comptes verrouillés, relue par le bureau à son démarrage (sinon un redémarrage les rouvrirait)."""
    txt = "".join(f"{u}\n" for u in sorted(locked)) or "\n"
    if STATE.get("locked_file") != txt:
        dx("cat > /secrets/verrouilles.txt", inp=txt)
        STATE["locked_file"] = txt


def tick():
    if container_state() != "running":
        return
    # écran noir à la connexion si les sessions ne peuvent pas créer leur prise dans ce dossier (voir entrypoint.sh)
    dx("[ \"$(stat -c %a /run/xrdp/sockdir 2>/dev/null)\" = 3777 ] || { mkdir -p /run/xrdp/sockdir; chmod 3777 /run/xrdp/sockdir; }")
    with acc_lock:
        if load_accounts():
            _tick()


def _tick():
    now = datetime.now()
    day = now.date().isoformat()
    with lock:
        data = load_rules()
        stamp = rules_stamp()
    ids = uids()
    try:
        sync_langues(data)
    except Exception as ex:
        print("erreur langues:", repr(ex), flush=True)
    act, last, disp = active_connections(), last_sessions(), displays()
    sites = tracked_sites(data)
    c = db()
    try:
        conn, fg = {}, {}
        for u in USERS:
            s = last.get(u)
            connected = bool(s and (s["ip"], s["port"]) in act and u in disp)
            prev = STATE["prev_conn"].get(u)
            if prev is not None and prev != connected:
                event(c, u, "connexion" if connected else "déconnexion",
                      f"{s['ip']} {s['name']}".strip() if (connected and s) else "")
            STATE["prev_conn"][u] = conn[u] = connected
            # --- statistiques : application et site au premier plan (rien n'est compté pendant une pause)
            if connected and not is_paused(data[u], now):
                app, title, idle = foreground(u, disp[u])
                if idle >= 120:
                    add(c, "usage", {"day": day, "user": u, "app": IDLE}, TICK)
                    segment(c, u, IDLE, "", None, now)
                else:
                    add(c, "usage", {"day": day, "user": u, "app": app}, TICK)
                    if title:
                        add(c, "titles", {"day": day, "user": u, "app": app, "title": title}, TICK)
                    if app == "Firefox":
                        low = title.lower()
                        hit = [k for k in sites if k.startswith("site:") and any(w in low for w in target(k)[3])]
                        hit = hit or [k for k in sites if k.startswith("dom:") and any(w in low for w in target(k)[3])]
                        for cle in hit:
                            add(c, "sites", {"day": day, "user": u, "cle": cle}, TICK)
                            fg[u] = cle
                    else:
                        fg[u] = next((f"app:{k}" for k, v in APPS.items() if v[1] == app), None)
                    segment(c, u, app, title, fg.get(u) if app == "Firefox" else None, now)
            else:
                STATE["seg"].pop(u, None)          # déconnecté ou en pause : la période en cours se termine
        try:
            ressources(c, ids, now)
        except Exception as ex:                    # une mesure ratée ne doit pas empêcher d'appliquer les règles
            print("erreur ressources:", repr(ex), flush=True)
        try:
            apply_puissance()
            apply_quota(ids)
        except Exception as ex:
            print("erreur puissance:", repr(ex), flush=True)

        # --- niveau de chaque enfant et restrictions effectives
        lv = {u: access(u, data[u], now, used_today(c, u)) for u in USERS}
        eff = {u: profile(data, u, lv[u][0], c) for u in USERS}
        sec = {u: {k: secu(data, u, k) for k in SECU} for u in USERS}
        net_sig = json.dumps({u: [eff[u]["internet"], eff[u]["domains"], sec[u]["doh"], sec[u]["reseau"], sec[u]["pip"]] for u in USERS}) + json.dumps(ids)
        if net_sig != STATE["net_sig"] or not net_ok():
            apply_internet(eff, ids, sec)
            STATE["net_sig"] = net_sig
        app_sig = json.dumps({u: eff[u]["apps"] for u in USERS})
        if app_sig != STATE["app_sig"] or dx("cat /etc/kids-apps 2>/dev/null").strip() != "ok":
            apply_apps(eff, sec)
            STATE["app_sig"] = app_sig
        kill_blocked_apps(eff)
        apply_exec(data[ALL]["securite"]["programmes"] == "autorise")

        if rules_stamp() != stamp:
            # un parent a changé quelque chose pendant ce passage (pause, bonus...) : ne rien appliquer avec
            # des règles périmées (sinon une pause toute fraîche serait levée), le prochain passage s'en charge
            c.commit()
            return
        write_locked({u for u in USERS if lv[u][0] in ("R", "P")})
        for u in USERS:
            connected = conn[u]
            lvl, why, left = lv[u]
            ok = lvl not in ("R", "P")
            prev = STATE["lvl"].get(u)
            if not ok or prev is None or (prev in ("R", "P")) != (not ok):   # re-verrouille aussi après un redémarrage du bureau
                dx(f"usermod -{'U' if ok else 'L'} {u}")
            # --- pause : écran bloqué, applications gardées
            if lvl == "P":
                STATE["grace"].pop(u, None)
                if u in disp and (not frozen(u) or not overlay_up(u)):
                    freeze(u, disp[u], why.replace("pause jusqu'à ", ""))
            elif frozen(u):
                unfreeze(u, disp.get(u))
            if prev != lvl:
                if prev is not None:
                    event(c, u, NIVEAU[lvl], why)
                    if connected and ok:
                        popup(u, disp[u], "Accès complet : amuse-toi bien !" if lvl == "V"
                              else "Mode restreint : " + describe(eff[u]) + ".")
                STATE["lvl"][u] = lvl
            # --- limites de temps par site / application (orange)
            blk = set(eff[u]["blocked"])
            newly = blk - STATE["blk"].get(u, set())
            if lvl == "O" and connected and u in STATE["blk"] and newly:
                # limite de temps atteinte ≠ objet bloqué par les parents : messages différents
                lim = {target(x["cle"])[1].split(" (")[0] for x, _, b in orange_status(data, u, c) if b and x["mode"] == "limiter"}
                fini, bloque = sorted(newly & lim), sorted(newly - lim)
                txt = ([f"C'est fini pour aujourd'hui : {', '.join(fini)}."] if fini else []) + \
                      ([f"Bloqué par tes parents : {', '.join(bloque)}."] if bloque else [])
                popup(u, disp[u], "\n".join(txt), "warning")
                if fini:
                    event(c, u, "limite atteinte", ", ".join(fini))
                if bloque:
                    event(c, u, "bloqué", ", ".join(bloque))
            STATE["blk"][u] = blk
            if lvl == "O" and connected and fg.get(u):
                for x, used, blocked in orange_status(data, u, c):
                    if x["cle"] == fg[u] and x["mode"] == "limiter" and not blocked:
                        rest = int(x["minutes"]) - used / 60
                        wk = f"{day}-lim-{x['cle']}"
                        if rest <= 5 and STATE["warned"].get(u + wk) is None:
                            popup(u, disp[u], f"Il te reste environ {max(1, round(rest))} min de {target(x['cle'])[1]} aujourd'hui.", "warning")
                            STATE["warned"][u + wk] = True
            # --- fin d'accès (rouge)
            if ok:
                STATE["grace"].pop(u, None)
                key = f"{now + timedelta(minutes=left or 0):%Y%m%d%H%M}"[:-1]   # une fois par fin (tranche de 10 min)
                if left is not None and left <= 5 and connected and STATE["warned"].get(u) != key:
                    popup(u, disp[u], f"Attention : il te reste environ {max(1, round(left))} minute(s).\n"
                                      "Pense à enregistrer ton travail.", "warning")
                    STATE["warned"][u] = key
            elif lvl == "R" and u in disp:
                g = STATE["grace"].get(u)
                if g is None:
                    STATE["grace"][u] = now
                    if connected:
                        popup(u, disp[u], f"C'est terminé pour le moment ({why}).\n"
                                          "La session va se fermer dans 1 minute : enregistre ton travail !", "warning")
                elif (now - g).total_seconds() >= 60:
                    logout(u)
                    event(c, u, "session fermée", why)
                    STATE["grace"].pop(u, None)
        c.commit()
    finally:
        c.close()


def boucle():
    while True:
        t0 = time.time()
        try:
            tick()
            logiciels.verifier()         # bureau recréé : logiciels des parents réinstallés (toutes les 10 min au plus)
        except Exception as ex:  # ne jamais arrêter la boucle
            print("erreur boucle:", repr(ex), flush=True)
        time.sleep(max(1, TICK - (time.time() - t0)))



# ======================================================================
# Petits utilitaires d'affichage (partagés avec tableau.py)
# ======================================================================
def dur(sec):
    m = int(sec) // 60
    return f"{m // 60} h {m % 60:02d}" if m >= 60 else f"{m} min"


def hhmm(k):
    return f"{k // 2:02d}:{30 * (k % 2):02d}"
