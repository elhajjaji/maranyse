#!/usr/bin/env python3
"""Scénario de test graphique du contrôle parental — comptes de test driss, paul, nadia.

Tourne dans la VM sous l'utilisateur parent :  python3 ~/tests/scenario.py
- Le conteneur « testeur » ouvre de vraies sessions Bureau à distance (xfreerdp) et prend les captures.
- Les actions passent par le tableau de bord (mêmes formulaires que les parents).
- Les comptes réels ne sont pas touchés : règles sauvegardées puis restaurées, tests globaux
  sautés si un vrai enfant a une session ouverte.
Résultat : ~/tests/out/rapport.html (+ resultats.json, captures).
"""
import base64, html, http.client, json, os, re, shlex, shutil, sqlite3, subprocess, sys, threading, time, traceback
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlencode, unquote

HOME = os.path.expanduser("~")
OUT = f"{HOME}/tests/out"
BUREAU, T = "bureau-enfants", "testeur"
LOGIN, PASSWORD = open(f"{HOME}/.tableau.conf").read().strip().split(":", 1)
AUTH = "Basic " + base64.b64encode(f"{LOGIN}:{PASSWORD}".encode()).decode()
REAL = []                                                # vrais comptes des enfants : lus au démarrage (setup)
KIDS = {"driss": "Driss", "paul": "Paul", "nadia": "Nadia"}
PW = {"driss": "Driss2026", "paul": "Paul2026"}          # nadia : mot de passe généré par le tableau
DISP = {"driss": 11, "paul": 12, "nadia": 13}            # écrans virtuels des clients ; 14 = tentatives refusées
DB = f"{HOME}/stats.db"
RULES = f"{HOME}/controle.json"
WD = datetime.now().weekday()

RESULTS, SHOTS = [], {}
T0 = time.time()


def log(*a):
    print(f"[{time.time() - T0:6.0f}s]", *a, flush=True)


# ======================================================================
# Outils
# ======================================================================
def run(args, inp=None, timeout=60):
    try:
        r = subprocess.run(args, capture_output=True, text=True, input=inp, timeout=timeout)
        return r.stdout + r.stderr
    except subprocess.TimeoutExpired:
        return "TIMEOUT"


def bx(cmd, user=None, env=None, detach=False, timeout=60):
    """Commande dans le bureau des enfants (cmd : texte shell ou liste)."""
    a = ["docker", "exec"] + (["-d"] if detach else []) + (["-u", user] if user else [])
    for k, v in (env or {}).items():
        a += ["-e", f"{k}={v}"]
    a.append(BUREAU)
    a += cmd if isinstance(cmd, list) else ["sh", "-c", cmd]
    return run(a, timeout=timeout)


def tx(cmd, detach=False, timeout=90):
    return run(["docker", "exec"] + (["-d"] if detach else []) + [T, "sh", "-c", cmd], timeout=timeout)


def displays():
    d = {}
    for l in bx("ps -eo user:32,args | grep '[X]org :'").splitlines():
        m = re.match(r"(\S+)\s+\S*Xorg (:\d+)", l)
        if m:
            d[m.group(1)] = m.group(2)
    return d


def xenv(u):
    """Programme lancé dans la session de l'enfant, dans la langue de sa session (comme depuis son menu)."""
    lg = bx(f"awk '$1==\"{u}\" {{print $2}}' /etc/maranyse/langues").strip() or "fr"
    loc = {"fr": "fr_FR", "en": "en_US", "es": "es_ES", "de": "de_DE", "pt": "pt_PT", "ru": "ru_RU", "ar": "ar_MA", "hi": "hi_IN",
           "zh": "zh_CN", "ja": "ja_JP"}.get(lg, "fr_FR")
    return {"DISPLAY": displays().get(u, ":0"), "XAUTHORITY": f"/home/{u}/.Xauthority", "LANG": f"{loc}.UTF-8", "LC_ALL": f"{loc}.UTF-8",
            "LANGUAGE": f"{loc}:{lg}"}


def kid(u, cmd, gui=False, detach=False, timeout=60):
    return bx(cmd, user=u, env=xenv(u) if gui else None, detach=detach, timeout=timeout)


def locked(u):
    f = bx(f"passwd -S {u}").split()
    return len(f) > 1 and f[1] == "L"


def wait(pred, timeout=100, step=3):
    end = time.time() + timeout
    while time.time() < end:
        try:
            if pred():
                return True
        except Exception:
            pass
        time.sleep(step)
    return False


def post(**form):
    c = http.client.HTTPConnection("127.0.0.1", 8080, timeout=120)
    c.request("POST", "/", urlencode(form), {"Authorization": AUTH, "Content-Type": "application/x-www-form-urlencoded"})
    r = c.getresponse()
    loc = r.getheader("Location", "")
    r.read()
    return unquote(loc.split("msg=")[-1]) if "msg=" in loc else f"HTTP {r.status}"


def get(path, auth=True, headers=None):
    c = http.client.HTTPConnection("127.0.0.1", 8080, timeout=60)
    h = {"Authorization": AUTH} if auth else {}
    c.request("GET", path, headers={**h, **(headers or {})})
    r = c.getresponse()
    return r.status, r.read().decode(errors="replace")


def planning(u, letter="V", quota=0):
    form = {"a": "planning", "u": u, "back": "/?p=planning"}
    for d in range(7):
        form[f"grille_{d}"] = letter * 48
        form[f"quota_{d}"] = quota if d == WD else 0
    return post(**form)


def rules():
    return json.load(open(RULES))


def inject_usage(u, sec, app="(injection test)"):
    c = sqlite3.connect(DB, timeout=20)
    c.execute("INSERT INTO usage(day,user,app,sec) VALUES(?,?,?,?) ON CONFLICT DO UPDATE SET sec=sec+excluded.sec",
              (datetime.now().date().isoformat(), u, app, sec))
    c.commit()
    c.close()


def used_today(u):
    c = sqlite3.connect(DB, timeout=20)
    v = c.execute("SELECT COALESCE(SUM(sec),0) FROM usage WHERE day=? AND user=?", (datetime.now().date().isoformat(), u)).fetchone()[0]
    c.close()
    return v


# --- réseau vu par un enfant (python3 dans le bureau, exécuté sous son identité)
PY_RESOLVE = "import socket,sys\ntry: print(socket.gethostbyname(sys.argv[1]))\nexcept Exception as e: print('ERR', type(e).__name__)"
PY_TCP = ("import socket,sys\ns=socket.socket();s.settimeout(5)\n"
          "try: s.connect((sys.argv[1],int(sys.argv[2])));print('OK')\nexcept Exception as e: print('ERR', type(e).__name__)")
PY_DNS = r"""import socket,struct,sys
name,server=sys.argv[1],sys.argv[2]
q=struct.pack(">HHHHHH",0x1234,0x0100,1,0,0,0)+b"".join(bytes([len(p)])+p.encode() for p in name.split("."))+b"\0"+struct.pack(">HH",1,1)
s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);s.settimeout(5)
try:
    s.sendto(q,(server,53));d,_=s.recvfrom(4096)
except Exception as e:
    print("ERR",type(e).__name__);sys.exit()
an=struct.unpack(">H",d[6:8])[0];i=len(q);ips=[]
for _ in range(an):
    if d[i]&0xc0==0xc0: i+=2
    else:
        while d[i]: i+=d[i]+1
        i+=1
    t,c,ttl,l=struct.unpack(">HHIH",d[i:i+10]);i+=10
    if t==1: ips.append(".".join(map(str,d[i:i+4])))
    i+=l
print(" ".join(ips) or "AUCUNE")"""
PY_DOH = ("import json,urllib.request,sys\n"
          "r=urllib.request.Request('https://'+sys.argv[2]+('/resolve' if sys.argv[2].startswith('8.') else '/dns-query')"
          "+'?name='+sys.argv[1]+'&type=A',headers={'accept':'application/dns-json'})\n"
          "try: print(' '.join(a['data'] for a in json.load(urllib.request.urlopen(r,timeout=8)).get('Answer',[]) if a['type']==1) or 'AUCUNE')\n"
          "except Exception as e: print('ERR', type(e).__name__)")


PY_DROP = ("import os,pwd\np=pwd.getpwnam(os.environ['KID'])\ng=int(os.environ.get('NETGID') or p.pw_gid)\n"
           "os.setgroups([]);os.setgid(g);os.setuid(p.pw_uid)\n")
NET_GID = 2000      # groupe « internet » du lanceur de Firefox


def probe(u, code, *args, net=True):
    """Sonde réseau : python lancé par root puis passé sous l'identité de l'enfant.
    net=True : comme Firefox (groupe « internet », filtrage des sites) ; net=False : comme un script de l'enfant."""
    return bx(["python3", "-c", PY_DROP + code, *map(str, args)], env={"KID": u, "NETGID": str(NET_GID) if net else ""}).strip()


def resolve(u, name, net=True):
    return probe(u, PY_RESOLVE, name, net=net)


def tcp(u, host, port, net=True):
    return probe(u, PY_TCP, host, port, net=net)


def secu(scope, k, v):
    return post(a="secu", s=scope, k=k, v=v, back="/?p=regles")


def blocked_dns(r):
    return r.startswith("0.0.0.0") or r.startswith("ERR") or r == "AUCUNE"      # AUCUNE : site inexistant (NXDOMAIN)


# ======================================================================
# Client Bureau à distance + captures
# ======================================================================
def connect(u, pw, n=None):
    n = n or DISP[u]
    disconnect(n)
    time.sleep(1)
    tx(f"DISPLAY=:{n} xfreerdp /t:ecran{n} /v:127.0.0.1:3389 /u:{u} '/p:{pw}' /cert:ignore /size:1280x800 /bpp:24 -wallpaper "
       f"/log-level:ERROR > /out/rdp_{u}_{n}.log 2>&1", detach=True)


def disconnect(n):
    tx(f"pkill -f 'xfreerdp /t:ecran{n} '; true")


def desktop_ready(u):
    return u in displays() and "xfce4-panel" in bx(f"pgrep -u {u} -a xfce4-panel")


def shot(n, name, caption):
    tx(f"import -display :{n} -window root /out/{name}.png")
    SHOTS[name] = caption
    return name


def web_shot(path, name, caption, h=1500):
    tx(f"rm -rf /tmp/chr; timeout 60 chromium --headless=new --no-sandbox --disable-gpu --hide-scrollbars --user-data-dir=/tmp/chr "
       f"--window-size=1360,{h} --screenshot=/out/{name}.png 'http://127.0.0.1:18080{path}' >/dev/null 2>&1", timeout=90)
    SHOTS[name] = caption
    return name


class Proxy(BaseHTTPRequestHandler):
    """Relais local qui ajoute l'identification parent (pour les captures du tableau par chromium)."""
    def do_GET(self):
        c = http.client.HTTPConnection("127.0.0.1", 8080, timeout=60)      # transmet aussi les images (logo)
        c.request("GET", self.path, headers={"Authorization": AUTH})
        r = c.getresponse()
        b, st, ctype = r.read(), r.status, r.getheader("Content-Type", "text/html; charset=utf-8")
        self.send_response(st)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def log_message(self, *a):
        pass


# ======================================================================
# Enregistrement des résultats
# ======================================================================
def check(tid, group, title, ok, detail="", shots=(), kind=None):
    st = kind or ("OK" if ok else "ÉCHEC")
    RESULTS.append(dict(id=tid, group=group, title=title, status=st, detail=str(detail)[:900], shots=list(shots)))
    log(f"{st:7} {tid} {title} — {str(detail)[:160]}")


def step(tid, group, title, fn):
    try:
        fn()
    except Exception as ex:
        check(tid, group, title, False, "Erreur du scénario : " + "".join(traceback.format_exception_only(type(ex), ex)).strip())
        traceback.print_exc()


# ======================================================================
# Scénario
# ======================================================================
def setup():
    REAL[:] = [u for u in bx("cut -d: -f1 /secrets/comptes.txt").split() if u not in KIDS]    # jamais touchés par les tests
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        os.remove(os.path.join(OUT, f))
    shutil.copy(RULES, f"{HOME}/tests/controle.json.avant_tests")
    threading.Thread(target=ThreadingHTTPServer(("127.0.0.1", 18080), Proxy).serve_forever, daemon=True).start()
    run(["docker", "rm", "-f", T])
    run(["docker", "run", "-d", "--name", T, "--network", "host", "--shm-size", "512m", "-v", f"{OUT}:/out", "testeur:latest"])
    for n in (11, 12, 13, 14):
        tx(f"Xvfb :{n} -screen 0 1280x800x24 -nolisten tcp >/dev/null 2>&1", detach=True)
    time.sleep(2)
    for u in KIDS:                                   # restes d'un essai précédent
        post(a="delkid", u=u, purge="1", back="/?p=comptes")
        bx(f"rm -rf /home/{u}")
    c = sqlite3.connect(DB, timeout=20)              # statistiques d'un compte de test supprimé sans purge
    for t in ("usage", "titles", "sites", "events", "segments", "ressources"):
        c.execute(f"DELETE FROM {t} WHERE user IN ('driss','paul','nadia')")
    c.commit()
    c.close()


GROUP = {"A": "Comptes", "B": "Connexion et sessions", "C": "Planning et temps d'écran", "D": "Filtrage internet et applications",
         "E": "Pause à distance", "F": "Messages", "G": "Statistiques et journal", "H": "Robustesse et sécurité",
         "L": "Logiciels pour tous (VS Code…)", "S": "Outils libres, contournements impossibles", "R": "Ressources par enfant",
         "P": "Puissance (part de l'ordinateur)", "I": "Langues (10 langues)",
         "K": "Famille : scénarios pour chacun des enfants"}


def A():
    g = GROUP["A"]
    m1 = post(a="addkid", nom="Driss", login="driss", pw=PW["driss"], copie="", back="/?p=comptes")
    m2 = post(a="addkid", nom="Paul", login="paul", pw=PW["paul"], copie="", back="/?p=comptes")
    m3 = post(a="addkid", nom="Nadia", login="nadia", pw="", copie="", back="/?p=comptes")
    m = re.search(r"mot de passe : (\S+)", m3)
    PW["nadia"] = m.group(1) if m else ""
    ok = all(bx(f"id -u {u}").strip().isdigit() for u in KIDS) and all("créé" in x for x in (m1, m2, m3))
    check("A1", g, "Création de 3 comptes depuis la page Comptes (mot de passe choisi ou généré)", ok and bool(PW["nadia"]),
          f"{m1} | {m2} | {m3}", [web_shot("/?p=comptes", "a1_comptes", "Page Comptes avec les 3 comptes de test")])
    r = [post(a="addkid", nom="X", login="driss", back="/?p=comptes"), post(a="addkid", nom="X", login="Driss!", back="/?p=comptes"),
         post(a="addkid", nom="X", login="root", back="/?p=comptes"), post(a="addkid", nom="", login="zoe", back="/?p=comptes")]
    check("A2", g, "Refus : identifiant déjà pris, invalide, réservé, prénom vide", all("créé" not in x for x in r) and not bx("id -u zoe").strip().isdigit(),
          " | ".join(r))
    m = post(a="rename", u="nadia", v="Nadia B.", back="/?p=comptes")
    page = get("/?p=comptes")[1]
    check("A3", g, "Renommer le prénom affiché", "Nadia B." in page, m)
    m = post(a="pw", u="paul", v="Paul2027", back="/?p=comptes")
    old = PW["paul"]
    PW["paul"] = "Paul2027"
    check("A4", g, "Changer le mot de passe", "changé" in m and "Paul2027" in bx("cat /secrets/mots_de_passe.txt"), m)
    PW["paul_ancien"] = old
    for u in KIDS:
        planning(u, "V")


def B():
    g = GROUP["B"]
    for u in KIDS:
        connect(u, PW[u])
    ok = wait(lambda: all(desktop_ready(u) for u in KIDS), 120)
    time.sleep(12)
    shots = [shot(DISP[u], f"b1_{u}", f"Bureau de {KIDS[u]} ouvert par Bureau à distance") for u in KIDS]
    mem = run(["free", "-m"]).splitlines()[1].split()
    check("B1", g, "3 sessions simultanées (driss, paul, nadia)", ok, f"Sessions X : {displays()} · RAM VM utilisée {mem[2]} Mo / {mem[1]} Mo", shots)
    time.sleep(2)
    st, page = get("/?p=live")
    online = len(re.findall(r'class="dot on"', page))
    check("B1b", g, "L'accueil du tableau montre les enfants en ligne", online >= 3, f"{online} pastille(s) « en ligne »",
          [web_shot("/?p=live", "b1_accueil", "Accueil du tableau de bord pendant les 3 sessions", 2200)])
    connect("paul", PW["paul_ancien"], 14)
    time.sleep(12)
    s = shot(14, "b2_mauvais_mdp", "Connexion de paul avec l'ancien mot de passe")
    sess = bx("ps -eo user:32,args | grep -c '^paul .*[X]org'").strip()
    disconnect(14)
    check("B2", g, "Mauvais mot de passe (ancien) refusé", sess == "1", f"sessions X de paul : {sess} (attendu 1, la session existante)", [s])
    r = {
        "lire le dossier de paul": kid("driss", "ls /home/paul >/dev/null 2>&1 && echo POSSIBLE || echo refusé").strip(),
        "lire un fichier de paul": kid("driss", "cat /home/paul/.xsession >/dev/null 2>&1 && echo POSSIBLE || echo refusé").strip(),
        "écrire chez paul": kid("driss", "touch /home/paul/intrus 2>/dev/null && echo POSSIBLE || echo refusé").strip(),
    }
    check("B3", g, "Isolation : un enfant ne peut pas lire les fichiers d'un autre",
          all(v == "refusé" for v in r.values()), " ; ".join(f"{k} : {v}" for k, v in r.items()))
    r = {
        "sudo": kid("driss", "sudo -n true 2>/dev/null && echo POSSIBLE || echo refusé").strip(),
        "lire les mots de passe": kid("driss", "cat /secrets/mots_de_passe.txt >/dev/null 2>&1 && echo POSSIBLE || echo refusé").strip(),
        "modifier le pare-feu": kid("driss", "iptables -F 2>/dev/null && echo POSSIBLE || echo refusé").strip(),
        "changer l'heure": kid("driss", "date -s '2030-01-01' >/dev/null 2>&1 && echo POSSIBLE || echo refusé").strip(),
        "tuer les processus d'un autre": kid("driss", "pkill -u paul xfce4-panel 2>/dev/null && echo POSSIBLE || echo refusé").strip(),
    }
    check("B4", g, "Pas de droits administrateur pour les enfants", all(v == "refusé" for v in r.values()), " ; ".join(f"{k} : {v}" for k, v in r.items()))


def F():
    g = GROUP["F"]
    m = post(a="msg", u="nadia", v="Test : à table dans 5 minutes !", back="/?p=live")
    ok = wait(lambda: popup_text("nadia", "à table dans 5 minutes"), 15, 1)
    time.sleep(3)
    s = shot(DISP["nadia"], "f1_message", "Message des parents affiché chez Nadia")
    bx("pkill -u nadia zenity; true")
    check("F1", g, "Message des parents affiché sur l'écran de l'enfant", ok, m, [s])


def popup_text(u, words):
    """Vrai si une fenêtre de message de l'enfant contient ce texte (et pas seulement « une fenêtre »)."""
    return words.lower() in bx(f"pgrep -u {u} -a zenity").lower()


def mousepad_win(u):
    return kid(u, "xdotool search --onlyvisible --class mousepad 2>/dev/null | head -1", gui=True).strip()


def type_client(n, text="abc"):
    tx(f"DISPLAY=:{n} xdotool mousemove 640 420 sleep 0.3 type --delay 120 {text}")


def E():
    g = GROUP["E"]
    u, n = "driss", DISP["driss"]
    kid(u, "mousepad", gui=True, detach=True)
    wait(lambda: mousepad_win(u), 30, 1)
    w = mousepad_win(u)
    pid0 = bx(f"pgrep -u {u} -x mousepad").strip()
    time.sleep(4)
    for x, y in ((600, 400), (700, 500), (500, 300)):          # jusqu'à 3 essais (client de test parfois lent)
        tx(f"DISPLAY=:{n} xdotool mousemove {x} {y} sleep 0.3 mousemove {x + 40} {y + 20}")
        time.sleep(1.5)
        idle0 = int(kid(u, "xprintidle", gui=True).strip() or 0) // 1000
        if idle0 <= 2:
            break
    check("E0", g, "Contrôle : la souris du client de test arrive bien dans la session", idle0 <= 2,
          f"inactivité juste après un mouvement de souris : {idle0} s")
    m = post(a="pause15", u=u, back="/?p=live")
    ok_overlay = wait(lambda: "PAUSE-BUREAU-ENFANTS" in bx(f"pgrep -u {u} -a zenity"), 20, 1)
    time.sleep(4)
    s1 = shot(n, "e1_pause", "Écran de pause chez Driss (clavier et souris coupés)")
    kid(u, f"xdotool windowactivate {w}", gui=True)
    time.sleep(6)
    type_client(n, "abc")
    time.sleep(2)
    idle = int(kid(u, "xprintidle", gui=True).strip() or 0) // 1000
    title = kid(u, f"xdotool getwindowname {w}", gui=True).strip()
    check("E1", g, "Pause : écran bloqué tout de suite", ok_overlay, m, [s1])
    check("E2", g, "Pause : le clavier et la souris de l'enfant n'ont plus d'effet", idle >= 6 and not title.startswith("*"),
          f"inactivité vue par la session après frappe : {idle} s ; titre Mousepad : « {title} »")
    check("E3", g, "Pause : le compte est verrouillé (pas de nouvelle connexion)", locked(u), f"passwd -S : {bx(f'passwd -S {u}').strip()}")
    m = post(a="lever", u=u, back="/?p=live")
    ok_gone = wait(lambda: "PAUSE-BUREAU-ENFANTS" not in bx(f"pgrep -u {u} -a zenity"), 15, 1)
    time.sleep(2)
    kid(u, f"xdotool windowactivate {w}", gui=True)
    time.sleep(1)
    type_client(n, "abc")
    time.sleep(2)
    idle = int(kid(u, "xprintidle", gui=True).strip() or 0) // 1000
    title = kid(u, f"xdotool getwindowname {w}", gui=True).strip()
    pid1 = bx(f"pgrep -u {u} -x mousepad").strip()
    s2 = shot(n, "e4_reprise", "Après la reprise : Mousepad toujours ouvert, le texte tapé arrive")
    check("E4", g, "Reprise : écran débloqué, saisie de nouveau possible, compte déverrouillé",
          ok_gone and idle <= 3 and title.startswith("*") and not locked(u), f"{m} ; inactivité {idle} s ; titre « {title} »", [s2])
    check("E5", g, "Pause : les applications restent ouvertes", bool(pid0) and pid0 == pid1, f"pid Mousepad avant {pid0} / après {pid1}")


def firefox_shot(u, url, name, caption):
    bx(f"pkill -u {u} -x firefox-esr; true")       # pas de « pkill -f » : il tuerait sa propre commande
    time.sleep(1)
    kid(u, f"firefox-esr --new-instance '{url}' >/dev/null 2>&1", gui=True, detach=True)
    wait(lambda: "Firefox" in kid(u, "wmctrl -l", gui=True) or "Mozilla" in kid(u, "wmctrl -l", gui=True), 90, 3)
    time.sleep(10)
    s = shot(DISP[u], name, caption)
    bx(f"pkill -u {u} -x firefox-esr; true")
    return s


def D():
    g = GROUP["D"]
    u = "paul"
    planning(u, "O")
    m = post(a="internet", s=u, v="bloque", back="/?p=regles")
    ok = wait(lambda: tcp(u, "1.1.1.1", 443).startswith("ERR"), 100)
    other = tcp("nadia", "1.1.1.1", 443)
    s = firefox_shot(u, "http://example.com", "d1_coupe", "Firefox chez Paul quand internet est coupé")
    check("D1", g, "Orange + internet coupé : plus aucun accès (les autres enfants ne sont pas touchés)", ok and other == "OK",
          f"{m} ; paul → 1.1.1.1:443 {tcp(u, '1.1.1.1', 443)} ; nadia (vert) → {other}", [s])
    m = post(a="internet", s=u, v="filtre", back="/?p=regles")
    ok = wait(lambda: blocked_dns(resolve(u, "pornhub.com")) and not blocked_dns(resolve(u, "example.com")), 100)
    normal = resolve(u, "example.com")
    check("D2", g, "Internet filtré : sites pour adultes bloqués (DNS familial), sites normaux accessibles",
          ok, f"{m} ; pornhub.com → {resolve(u, 'pornhub.com')} ; example.com → {normal}")
    m = post(a="addrule", s=u, cle="site:youtube", mode="bloquer", back="/?p=regles")
    ok = wait(lambda: blocked_dns(resolve(u, "www.youtube.com")) and blocked_dns(resolve(u, "m.youtube.com")), 100)
    nad = resolve("nadia", "www.youtube.com")
    s = firefox_shot(u, "https://www.youtube.com", "d3_youtube", "Firefox chez Paul : YouTube bloqué")
    check("D3", g, "Bloquer un site de la liste (YouTube, sous-domaines compris)", ok and not blocked_dns(nad),
          f"{m} ; www.youtube.com → {resolve(u, 'www.youtube.com')} ; chez nadia → {nad}", [s])
    m = post(a="addrule", s=u, cle="dom:", dom="https://www.wikipedia.org/wiki", mode="bloquer", back="/?p=regles")
    ok = wait(lambda: blocked_dns(resolve(u, "fr.wikipedia.org")), 100)
    check("D4", g, "Bloquer un site saisi à la main (adresse nettoyée, sous-domaines compris)", ok,
          f"{m} ; fr.wikipedia.org → {resolve(u, 'fr.wikipedia.org')}")
    m = post(a="addrule", s=u, cle="app:gcompris", mode="bloquer", back="/?p=regles")
    ok = wait(lambda: "refusé" in kid(u, "[ -x /usr/games/gcompris-qt ] && echo permis || echo refusé"), 100)
    out = kid(u, "/usr/games/gcompris-qt --version 2>&1; echo code=$?").strip().replace("\n", " ")
    nad = kid("nadia", "[ -x /usr/games/gcompris-qt ] && echo permis || echo refusé").strip()
    check("D5", g, "Bloquer une application (GCompris) pour cet enfant seulement", ok and nad == "permis",
          f"{m} ; lancement par paul : {out[-120:]} ; nadia : {nad}")
    kid(u, "tuxpaint --windowed >/dev/null 2>&1", gui=True, detach=True)
    wait(lambda: bx(f"pgrep -u {u} -x tuxpaint").strip(), 30, 1)
    time.sleep(6)
    m = post(a="addrule", s=u, cle="app:tuxpaint", mode="limiter", minutes="5", back="/?p=regles")
    time.sleep(35)
    running = bool(bx(f"pgrep -u {u} -x tuxpaint").strip())
    inject_usage(u, 301, "Tux Paint")
    ok = wait(lambda: not bx(f"pgrep -u {u} -x tuxpaint").strip(), 100)
    popup = wait(lambda: popup_text(u, "fini pour aujourd'hui : Tux Paint"), 30, 1)
    time.sleep(2)
    s = shot(DISP[u], "d6_limite", "Paul : limite de 5 min de Tux Paint atteinte")
    bx(f"pkill -u {u} zenity; true")
    check("D6", g, "Limite de temps par application : fermée et bloquée une fois la limite atteinte, avec message",
          running and ok and popup, f"{m} ; Tux Paint ouvert sous la limite : {running} ; fermé après dépassement : {ok} ; message : {popup}", [s])
    r = {
        "DNS chiffré (DoT, port 853)": tcp(u, "1.1.1.1", 853),
        "DNS direct vers 8.8.8.8 (redirigé)": probe(u, PY_DNS, "www.youtube.com", "8.8.8.8"),
    }
    check("D7", g, "Contournements DNS classiques neutralisés (DoT bloqué, DNS externe redirigé)",
          r["DNS chiffré (DoT, port 853)"].startswith("ERR") and blocked_dns(r["DNS direct vers 8.8.8.8 (redirigé)"]),
          " ; ".join(f"{k} → {v}" for k, v in r.items()))
    # --- réglage « DNS sécurisé (DoH) » sur Interdire (par défaut)
    doh_ok = lambda: (probe(u, PY_DOH, "www.youtube.com", "1.1.1.1").startswith("ERR")
                      and probe(u, PY_DOH, "www.youtube.com", "8.8.8.8").startswith("ERR"))
    wait(doh_ok, 60)
    doh, doh2 = probe(u, PY_DOH, "www.youtube.com", "1.1.1.1"), probe(u, PY_DOH, "www.youtube.com", "8.8.8.8")
    names = {n: resolve(u, n) for n in ("dns.google", "mozilla.cloudflare-dns.com", "dns.quad9.net")}
    canary = resolve(u, "use-application-dns.net")
    pol = bx("cat /usr/lib/firefox-esr/distribution/policies.json")
    try:
        pj = json.loads(pol)["policies"]
        pol_ok = (pj["DNSOverHTTPS"].get("Locked") and pj.get("BlockAboutConfig") and pj["Proxy"].get("Locked")
                  and pj["ExtensionSettings"]["*"]["installation_mode"] == "blocked")
    except (ValueError, KeyError, TypeError):
        pol_ok = False
    ok = doh.startswith("ERR") and doh2.startswith("ERR") and all(blocked_dns(v) for v in names.values()) and canary.startswith("ERR") and pol_ok
    check("D8", g, "DNS sécurisé (DoH) interdit : serveurs DoH injoignables, Firefox verrouillé", ok,
          f"DoH vers 1.1.1.1 → {doh} ; vers 8.8.8.8 → {doh2} ; " + ", ".join(f"{k} → {v}" for k, v in names.items())
          + f" ; use-application-dns.net → {canary} (doit être inexistant) ; Firefox (DoH, extensions, about:config, proxy verrouillés) : {pol_ok}")
    ip = resolve("nadia", "www.youtube.com")
    direct = tcp(u, ip, 443)
    check("D8b", g, "Accès direct à un site par son adresse IP (sans DNS)", direct.startswith("ERR"),
          f"connexion {ip}:443 → {direct}. Le filtrage passe par le DNS ; sans programme ni extension, seul Firefox "
          "pourrait viser une adresse IP, ce qui ne fonctionne pas pour les grands sites (YouTube…).",
          kind=None if direct.startswith("ERR") else "LIMITE")
    # --- programmes téléchargés ou copiés : interdits (par défaut)
    def executables():
        r = {}
        for where in ("~", "/tmp", "/var/tmp", "/dev/shm", "/run/lock"):
            r[f"programme copié dans {where}"] = kid(u, f"cp /bin/ls {where}/monprog 2>/dev/null && {where}/monprog / >/dev/null 2>&1 "
                                                        f"&& echo POSSIBLE || echo refusé; rm -f {where}/monprog").strip()
        r["astuce ld.so"] = kid(u, "cp /bin/ls ~/monprog; /lib64/ld-linux-x86-64.so.2 ~/monprog / >/dev/null 2>&1 "
                                   "&& echo POSSIBLE || echo refusé; rm -f ~/monprog").strip()
        return r
    r = executables()
    bad = [k for k, v in r.items() if v == "POSSIBLE"]
    check("D9", g, "Programmes téléchargés ou copiés : impossibles à lancer", not bad, " ; ".join(f"{k} : {v}" for k, v in r.items()))
    # --- programmer reste possible (outils autorisés par défaut)
    prog = kid(u, "printf 'import turtle, pygame\\nprint(sum(range(10)))\\n' > ~/essai.py && python3 ~/essai.py 2>&1 | tail -1; rm -f ~/essai.py").strip()
    perl = kid(u, "perl -e 'print 6*7' 2>&1").strip()
    kid(u, "thonny >/dev/null 2>&1", gui=True, detach=True)
    th = wait(lambda: "Thonny" in kid(u, "wmctrl -l", gui=True) and bx(f"pgrep -u {u} -f thonny").strip(), 60, 3)
    time.sleep(4)
    s_th = shot(DISP[u], "d9b_thonny", "Paul peut programmer en Python avec Thonny")
    bx(f"pkill -u {u} -f thonny; true")
    check("D9b", g, "Programmer reste possible : script Python (tortue, pygame), Perl, éditeur Thonny",
          prog == "45" and perl == "42" and th, f"script Python → {prog} ; perl → {perl} ; Thonny ouvert : {th}", [s_th])
    # --- internet réservé à Firefox : un script n'a aucun accès (donc aucun contournement possible)
    yt = resolve("nadia", "www.youtube.com")
    r = {
        "script → 1.1.1.1:443": tcp(u, "1.1.1.1", 443, net=False),
        "script → adresse IP de YouTube": tcp(u, yt, 443, net=False),
        "script → example.com": tcp(u, resolve(u, "example.com"), 80, net=False),
        "script → DoH (dns.google 8.8.8.8)": probe(u, PY_DOH, "www.youtube.com", "8.8.8.8", net=False),
        "script → DoH (1.1.1.1)": probe(u, PY_DOH, "www.youtube.com", "1.1.1.1", net=False),
        "script d'un enfant en vert (nadia)": tcp("nadia", "1.1.1.1", 443, net=False),
        "obtenir le groupe internet (sg)": kid(u, "sg internet -c true </dev/null >/dev/null 2>&1 && echo POSSIBLE || echo refusé").strip(),
        "injecter du code dans Firefox (LD_PRELOAD)": kid(u, "LD_PRELOAD=/tmp/x.so /usr/local/bin/firefox-net --version 2>&1 | grep -qi 'error.*x.so' && echo POSSIBLE || echo refusé").strip(),
    }
    ff = kid(u, f"rm -rf /tmp/ffp_{u}; mkdir -p /tmp/ffp_{u}; timeout 60 /usr/local/bin/firefox-net --headless --no-remote --profile /tmp/ffp_{u} "
                f"--screenshot /tmp/ffp_{u}/s.png http://example.com >/dev/null 2>&1; stat -c %s /tmp/ffp_{u}/s.png 2>/dev/null || echo 0", timeout=90).strip()
    ff_ok = ff.isdigit() and int(ff) > 3000
    bad = [k for k, v in r.items() if not (v.startswith("ERR") or v == "refusé")]
    check("D10", g, "Internet réservé à Firefox : aucun script ne sort sur internet (pas de DoH, proxy, VPN…), Firefox oui",
          not bad and ff_ok, " ; ".join(f"{k} : {v}" for k, v in r.items()) + f" ; Firefox charge une page : {ff_ok} ({ff} octets)")
    # --- pip install : PyPI seulement, par le relais local
    PY_VIA_RELAIS = ("import urllib.request,sys\nh=urllib.request.ProxyHandler({'https':'http://127.0.0.1:8888'})\n"
                     "try:\n urllib.request.build_opener(h).open(sys.argv[1],timeout=15);print('POSSIBLE')\n"
                     "except Exception as e: print('refusé', type(e).__name__)")
    pip_out = kid(u, "cd ~ && timeout 150 pip install --no-cache-dir cowsay >/tmp/pip_$USER.log 2>&1; tail -1 /tmp/pip_$USER.log; "
                     "python3 -c 'import cowsay; print(\"IMPORT-OK\")' 2>&1 | tail -1", timeout=180).strip().replace("\n", " ")
    via = {site: kid(u, ["python3", "-c", PY_VIA_RELAIS, site]).strip()
           for site in ("https://www.youtube.com", "https://example.com", "https://pypi.org/simple/")}
    m = secu("paul", "pip", "interdit")
    off = wait(lambda: tcp(u, "127.0.0.1", 8888, net=False).startswith("ERR"), 100)
    secu("paul", "pip", "herite")
    on = wait(lambda: tcp(u, "127.0.0.1", 8888, net=False) == "OK", 100)
    check("D13", g, "pip install depuis PyPI uniquement : la bibliothèque s'installe, le relais refuse tout autre site, réglage par enfant",
          "IMPORT-OK" in pip_out and via["https://pypi.org/simple/"] == "POSSIBLE" and via["https://www.youtube.com"].startswith("refusé")
          and via["https://example.com"].startswith("refusé") and off and on,
          f"pip install cowsay → {pip_out[-160:]} ; relais : " + " ; ".join(f"{k} → {v}" for k, v in via.items())
          + f" ; {m} → relais coupé : {off} ; remis : {on}")
    # --- proxys web, VPN, recherche sécurisée (filtre familial CleanBrowsing)
    px = {n: resolve(u, n) for n in ("proxysite.com", "hide.me", "www.croxyproxy.com", "nordvpn.com", "www.hidemyass.com")}
    gg, ex = resolve(u, "www.google.com"), resolve(u, "example.com")
    s14 = firefox_shot(u, "https://www.proxysite.com", "d14_proxy", "Firefox chez Paul : site proxy bloqué par le filtre familial")
    check("D14", g, "Sites proxy et VPN bloqués, recherche Google sécurisée imposée (internet filtré)",
          all(blocked_dns(v) for v in px.values()) and gg == "216.239.38.120" and not blocked_dns(ex),
          " ; ".join(f"{k} → {v}" for k, v in px.items()) + f" ; www.google.com → {gg} (forcesafesearch = 216.239.38.120) ; example.com → {ex}", [s14])
    # --- aucune fuite pendant que les règles sont réappliquées (changement de réglage)
    secu("paul", "pip", "interdit")
    leaks, n, end = [], 0, time.time() + 40
    while time.time() < end:
        r = resolve(u, "proxysite.com")
        n += 1
        if not blocked_dns(r):
            leaks.append(r)
    secu("paul", "pip", "herite")
    check("D15", g, "Aucune fuite du filtrage pendant la réapplication des règles (changement de réglage)",
          not leaks and n >= 10, f"{n} résolutions de proxysite.com pendant 40 s autour d'un changement de réglage ; non filtrées : {leaks[:3] or 'aucune'}")
    # --- le parent autorise, puis interdit de nouveau (réglages du tableau de bord)
    m = [secu("_tous", "programmes", "autorise"), secu("paul", "reseau", "autorise"), secu("paul", "doh", "autorise")]
    ok = wait(lambda: kid(u, "cp /bin/ls ~/monprog && ~/monprog / >/dev/null 2>&1 && echo POSSIBLE; rm -f ~/monprog").strip() == "POSSIBLE"
              and tcp(u, "1.1.1.1", 443, net=False) == "OK", 100)
    autre = tcp("nadia", "1.1.1.1", 443, net=False)
    s = web_shot("/?p=regles&s=paul", "d12_reglages", "Règles de Paul : réglages Contournements (exceptions)", 2400)
    m += [secu("_tous", "programmes", "interdit"), secu("paul", "reseau", "herite"), secu("paul", "doh", "herite")]
    back = wait(lambda: not [k for k, v in executables().items() if v == "POSSIBLE"] and doh_ok()
                and tcp(u, "1.1.1.1", 443, net=False).startswith("ERR") and kid(u, "python3 -c 'print(1)'").strip() == "1", 100)
    check("D12", g, "Le parent peut autoriser puis interdire chaque réglage (programmes, internet des scripts, DoH) ; Python reste utilisable",
          ok and autre.startswith("ERR") and back,
          " | ".join(m) + f" ; exceptions effectives pour paul : {ok} ; nadia garde la règle commune : {autre} ; de nouveau comme avant : {back}", [s])
    # règle commune + exception individuelle « autoriser » (domaine inoffensif example.org)
    if any(r in displays() for r in REAL):
        check("D11", g, "Règle commune + exception individuelle", True, "Sauté : un vrai enfant a une session ouverte.", kind="SAUTÉ")
        return
    planning("nadia", "O")
    m1 = post(a="addrule", s="_tous", cle="dom:", dom="example.org", mode="bloquer", back="/?p=regles")
    m2 = post(a="addrule", s="nadia", cle="dom:example.org", mode="autoriser", back="/?p=regles")
    ok = wait(lambda: blocked_dns(resolve(u, "example.org")), 100)
    nad = resolve("nadia", "example.org")
    post(a="delrule", s="_tous", cle="dom:example.org", back="/?p=regles")
    post(a="delrule", s="nadia", cle="dom:example.org", back="/?p=regles")
    planning("nadia", "V")
    check("D11", g, "Règle commune à tous + exception « autorisé » pour un enfant", ok and not blocked_dns(nad),
          f"{m1} | {m2} ; paul → {resolve(u, 'example.org')} (commune) ; nadia → {nad} (exception)",
          [web_shot("/?p=regles&s=paul", "d_regles_paul", "Règles de Paul (communes en pointillés + personnelles)", 1700)])


def C():
    g = GROUP["C"]
    u = "nadia"
    bx(f"pkill -u {u} zenity; true")
    planning(u, "V", quota=60)
    inject_usage(u, max(0, 57 * 60 - used_today(u)))
    ok = wait(lambda: popup_text(u, "il te reste environ"), 100, 2)
    time.sleep(2)
    s = shot(DISP[u], "c1_avertissement", "Nadia : avertissement 3 minutes avant la fin du temps d'écran")
    bx(f"pkill -u {u} zenity; true")
    check("C1", g, "Avertissement avant la fin du temps d'écran (≤ 5 min)", ok, f"temps d'écran du jour : {used_today(u) // 60} min / 60", [s])
    # fin d'accès : nadia par quota, paul par planning rouge (en parallèle)
    inject_usage(u, 6 * 60)
    planning("paul", "R")
    okn = wait(lambda: popup_text(u, "temps d'écran du jour épuisé"), 100, 2)
    okp = wait(lambda: popup_text("paul", "horaire interdit"), 60, 2)
    time.sleep(2)
    s1 = shot(DISP[u], "c2_quota", "Nadia : temps d'écran épuisé, la session va se fermer")
    s2 = shot(DISP["paul"], "c3_rouge", "Paul : horaire rouge, la session va se fermer")
    t = time.time()
    gone = wait(lambda: u not in displays() and "paul" not in displays(), 120, 3)
    # côté enfant : la fenêtre « Connexion Bureau à distance » doit se fermer (pas d'image figée qui reste affichée)
    time.sleep(8)
    # « [x]freerdp » : le motif ne se trouve pas lui-même dans la ligne de commande du shell qui lance pgrep
    client = {x: bool(tx(f"pgrep -f '[x]freerdp /t:ecran{DISP[x]} '").strip()) for x in (u, "paul")}
    s_cl = shot(DISP[u], "c2_client_apres", "Écran du PC de Nadia après la fermeture de sa session")
    check("C2b", g, "Après la fermeture, la fenêtre Bureau à distance de l'enfant se ferme aussi (pas d'écran figé)",
          not any(client.values()), f"client encore connecté : {client}", [s_cl])
    check("C2", g, "Temps d'écran quotidien épuisé : message puis session fermée après 1 minute",
          okn and gone and locked(u), f"message {okn} ; fermée {gone} (après {time.time() - t:.0f} s de plus) ; compte verrouillé {locked(u)}", [s1])
    check("C3", g, "Horaire rouge du planning : message puis session fermée", okp and gone and locked("paul"),
          f"message {okp} ; fermée {gone} ; compte verrouillé {locked('paul')}", [s2])
    connect("paul", PW["paul"], 14)
    time.sleep(14)
    s = shot(14, "c4_refus", "Paul essaie de se reconnecter pendant l'horaire rouge")
    disconnect(14)
    check("C4", g, "Reconnexion refusée pendant l'horaire rouge", "paul" not in displays(), "", [s])
    m = post(a="bonus", u=u, back="/?p=live")
    ok = wait(lambda: not locked(u), 100)
    connect(u, PW[u])
    ok2 = wait(lambda: desktop_ready(u), 90)
    time.sleep(8)
    s = shot(DISP[u], "c5_bonus", "Nadia reconnectée grâce aux 30 minutes bonus")
    check("C5", g, "Bonus de 30 minutes : l'enfant peut se reconnecter malgré le temps épuisé", ok and ok2, m, [s])
    planning(u, "V", quota=0)


def G():
    g = GROUP["G"]
    time.sleep(35)
    c = sqlite3.connect(DB, timeout=20)
    apps = c.execute("SELECT app, SUM(sec) FROM usage WHERE day>=? AND user='driss' GROUP BY app ORDER BY 2 DESC",   # hier compris (passage de minuit)
                     ((datetime.now() - timedelta(days=1)).date().isoformat(),)).fetchall()
    evs = c.execute("SELECT user, kind FROM events WHERE user IN ('driss','paul','nadia')").fetchall()
    c.close()
    kinds = {k for _, k in evs}
    check("G1", g, "Temps passé par application enregistré", any(a == "Éditeur de texte" for a, _ in apps),
          "driss : " + ", ".join(f"{a} {s}s" for a, s in apps),
          [web_shot("/?p=stats&s=driss", "g1_stats", "Statistiques de Driss", 1900)])
    want = {"connexion", "déconnexion", "En pause", "session fermée"}
    check("G2", g, "Journal : connexions, pauses, fermetures de session", want <= kinds, "événements : " + ", ".join(sorted(kinds)))
    c = sqlite3.connect(DB, timeout=20)
    seg = c.execute("SELECT user, app, COUNT(*), MIN(start), MAX(end) FROM segments WHERE user IN ('driss','paul','nadia') "
                    "GROUP BY user, app ORDER BY user").fetchall()
    c.close()
    from urllib.parse import quote as q_
    check("G4", g, "Détail heure par heure : quelle application, quel enfant, de quelle heure à quelle heure",
          any(u == "driss" and a == "Éditeur de texte" for u, a, *_ in seg) and {u for u, *_ in seg} >= {"driss", "paul", "nadia"},
          " ; ".join(f"{u} · {a} : {n} période(s) {st[11:16]}–{en[11:16]}" for u, a, n, st, en in seg),
          [web_shot("/?p=stats&vue=ensemble&per=7", "g4_ensemble", "Vue « Ensemble » : temps par jour, heures d'utilisation, qui utilise quoi", 2400),
           web_shot("/?p=stats&vue=enfant&s=paul", "g4_chrono_paul", "Statistiques de Paul : chronologie de la journée et graphiques", 3600),
           web_shot("/?p=stats&vue=app&app=" + q_("Éditeur de texte"), "g4_par_app", "Vue « Par application » : qui a utilisé l'éditeur de texte et quand", 2400),
           web_shot("/?p=stats&vue=app&app=Firefox", "g4_firefox", "Vue « Par application » : Firefox", 2400)])
    m = post(a="logout", u="driss", back="/?p=live")
    ok = wait(lambda: "driss" not in displays(), 30, 2)
    check("G3", g, "Le parent ferme la session d'un enfant à distance", ok, m)


def H():
    g = GROUP["H"]
    st, _ = get("/?p=live", auth=False)
    c = http.client.HTTPConnection("127.0.0.1", 8080, timeout=30)
    c.request("POST", "/", "a=logout&u=nadia", {"Authorization": AUTH, "Origin": "http://site-pirate.example",
                                                 "Content-Type": "application/x-www-form-urlencoded"})
    st2 = c.getresponse().status
    check("H1", g, "Tableau protégé : mot de passe exigé, formulaires d'un autre site refusés", st == 401 and st2 == 403,
          f"sans mot de passe → {st} ; formulaire venant d'un autre site → {st2}")
    check("H2", g, "Tableau de bord chiffré (HTTPS)", False,
          "Le tableau est en HTTP simple : le mot de passe parent circule en clair sur le Wi-Fi local.", kind="LIMITE")
    if any(r in displays() for r in REAL):
        check("H3", g, "Verrouillages conservés après redémarrage du bureau", True, "Sauté : un vrai enfant a une session ouverte.", kind="SAUTÉ")
    else:
        post(a="pause1h", u="nadia", back="/?p=live")
        run(["docker", "restart", BUREAU], timeout=120)
        wait(lambda: "xrdp" in bx("pgrep -a xrdp"), 30, 1)
        lk = locked("nadia")
        check("H3", g, "Verrouillages (pause, rouge) conservés après redémarrage du bureau", lk and locked("paul"),
              f"juste après redémarrage : nadia (pause) verrouillée {lk}, paul (rouge) verrouillé {locked('paul')}")
        post(a="lever", u="nadia", back="/?p=live")
        # après un redémarrage du bureau, une nouvelle connexion doit afficher le bureau (et pas un écran noir)
        connect("driss", PW["driss"])
        ok = wait(lambda: desktop_ready("driss"), 90)
        time.sleep(10)
        perm = bx("stat -c %a /run/xrdp/sockdir").strip()
        sock = bx("ls /run/xrdp/sockdir | grep -c xrdp_display_").strip()
        s = shot(DISP["driss"], "h5_apres_redemarrage", "Nouvelle connexion de Driss juste après un redémarrage du bureau")
        check("H5", g, "Après un redémarrage du bureau, une nouvelle connexion affiche bien le bureau (pas d'écran noir)",
              ok and perm == "3777" and sock not in ("", "0"), f"bureau prêt : {ok} ; droits du dossier des prises : {perm} ; prises d'affichage : {sock}", [s])
        disconnect(DISP["driss"])
    mem = run(["free", "-m"]).splitlines()[1].split()
    check("H4", g, "Mémoire de la VM suffisante pour plusieurs enfants", int(mem[1]) >= 3500,
          f"RAM totale de la VM : {mem[1]} Mo. Pendant les tests (3 sessions + Firefox), voir B1. "
          "Recommandé : 4 Go pour 3 enfants avec Firefox.", kind=None if int(mem[1]) >= 3500 else "LIMITE")


def lg_job_done(timeout=900):
    """Attend la fin de la tâche d'installation lancée depuis la page Logiciels."""
    return wait(lambda: 'class="spin"' not in get("/?p=logiciels")[1], timeout, 5)


def vscode_win(u):
    return kid(u, "wmctrl -l 2>/dev/null | grep -i 'visual studio code' | head -1", gui=True).strip()


def L():
    g = GROUP["L"]
    u, n = "driss", DISP["driss"]
    inst = json.load(open(f"{HOME}/logiciels.json"))["installes"]
    if "vscode" not in inst:                                  # VS Code installé par les parents (sinon : l'installer)
        post(a="lginstall", cle="vscode", back="/?p=logiciels")
        lg_job_done()
        inst = json.load(open(f"{HOME}/logiciels.json"))["installes"]
    s = web_shot("/?p=logiciels", "l1_page", "Page Logiciels : VS Code installé pour tous, catalogue, autre paquet Debian", 2400)
    page = get("/?p=regles")[1]
    check("L1", g, "VS Code installé pour tous depuis la page Logiciels et gérable dans Règles → Applications",
          "vscode" in inst and bx("dpkg-query -W -f='${Status}' code").strip() == "install ok installed" and 'value="app:lg_vscode"' in page,
          f"logiciels.json : {list(inst)} ; paquet code : {bx(['dpkg-query', '-W', '-f=${Version}', 'code']).strip()} ; présent dans Règles : {'app:lg_vscode' in page}", [s])
    # nouveau compte (driss créé dans A) : préparé automatiquement (français, extension Python, sans bac à sable Chromium)
    ok = wait(lambda: "ms-python.python" in bx(f"ls /home/{u}/.vscode/extensions 2>/dev/null"), 240, 5)
    ext = bx(f"ls /home/{u}/.vscode/extensions").split()
    ok = ok and wait(lambda: "fr" in bx(f"cat /home/{u}/.config/Code/languagepacks.json 2>/dev/null"), 120, 5)
    argv = bx(f"cat /home/{u}/.vscode/argv.json")
    own = bx(f"stat -c %U /home/{u}/.vscode/extensions").strip()
    check("L2", g, "Nouveau compte : VS Code déjà préparé (français, extension Python), fichiers à l'enfant",
          ok and "locale" in argv and own == u, f"extensions : {' '.join(x for x in ext if x != 'extensions.json')} ; argv.json : {argv} ; propriétaire : {own}")
    # ouvrir VS Code dans la vraie session, lancer un programme Python (Ctrl+F5)
    kid(u, "mkdir -p ~/projet && printf 'open(\"/home/driss/projet/resultat.txt\",\"w\").write(\"BONJOUR \" + str(6*7))\\nprint(\"Bonjour depuis VS Code\")\\n' > ~/projet/bonjour.py")
    kid(u, "code ~/projet ~/projet/bonjour.py >/dev/null 2>&1", gui=True, detach=True)
    up = wait(lambda: vscode_win(u), 90, 2)
    time.sleep(20)                                             # extensions chargées
    w = vscode_win(u).split()[0] if up else ""
    ran = False
    geo = dict(re.findall(r"(\w+)=(\d+)", kid(u, f"xdotool getwindowgeometry --shell {w}", gui=True))) if w else {}
    bx_ = int(geo.get("X", 0)) + int(geo.get("WIDTH", 1280)) - 87     # position du bouton ▷ d'après la fenêtre
    by_ = int(geo.get("Y", 26)) + 52
    for i in range(4):                                         # l'extension Python peut mettre un moment à être prête
        if w:                                                  # vraie frappe / vrai clic, par le client Bureau à distance
            kid(u, f"xdotool windowactivate --sync {w}", gui=True)
            time.sleep(1)
            tx(f"DISPLAY=:{n} xdotool mousemove 700 300 click 1 sleep 0.5 key ctrl+F5" if i % 2 == 0 else
               f"DISPLAY=:{n} xdotool mousemove {bx_} {by_} click 1")  # bouton ▷ « Exécuter le fichier Python » (haut à droite)
        ran = wait(lambda: "BONJOUR 42" in bx(f"cat /home/{u}/projet/resultat.txt 2>/dev/null"), 25, 2)
        if ran:
            break
    time.sleep(4)
    s = shot(n, "l3_vscode", "Driss : VS Code en français, programme Python lancé avec Ctrl+F5")
    title = kid(u, f"xdotool getwindowname {w}", gui=True).strip() if w else ""
    check("L3", g, "VS Code s'ouvre dans la session de l'enfant et exécute un programme Python",
          up and ran, f"fenêtre : « {title} » ; résultat du programme : {bx(f'cat /home/{u}/projet/resultat.txt 2>/dev/null') or 'aucun'}", [s])
    # pas d'internet pour VS Code (boutique d'extensions), avec le réglage par défaut
    net = probe(u, "import urllib.request;urllib.request.urlopen('https://marketplace.visualstudio.com',timeout=8);print('POSSIBLE')", net=False)
    check("L4", g, "VS Code n'a pas internet (boutique d'extensions) tant que les programmes n'y ont pas droit",
          "POSSIBLE" not in net, f"marketplace.visualstudio.com depuis un programme de l'enfant → {net.strip()[-120:]}")
    # statistiques : temps passé dans VS Code
    ok = wait(lambda: sqlite3.connect(DB, timeout=20).execute(
        "SELECT COUNT(*) FROM usage WHERE user=? AND app='Visual Studio Code' AND day>=?",
        (u, (datetime.now() - timedelta(days=1)).date().isoformat())).fetchone()[0] > 0, 100, 5)
    check("L5", g, "Temps passé dans VS Code compté dans les statistiques", ok,
          str(sqlite3.connect(DB, timeout=20).execute("SELECT app,sec FROM usage WHERE user=? ORDER BY sec DESC LIMIT 4", (u,)).fetchall()))
    # bloquer VS Code pour driss (orange) : fermé et ne se relance plus ; les autres enfants gardent VS Code
    planning(u, "O")
    m = post(a="addrule", s=u, cle="app:lg_vscode", mode="bloquer", back="/?p=regles")
    closed = wait(lambda: not bx(f"pgrep -u {u} -x code").strip(), 100, 3)
    popup = wait(lambda: popup_text(u, "Visual Studio Code"), 30, 1)
    time.sleep(2)
    s = shot(n, "l6_bloque", "Driss : VS Code bloqué par les parents, fenêtre fermée")
    again = kid(u, "/usr/share/code/code --version 2>&1 | head -1; code --version 2>&1 | tail -1").strip().replace("\n", " ")
    other = kid("nadia", "[ -r /usr/share/code/code ] && [ -x /usr/share/code/code ] && echo permis || echo refusé").strip()
    check("L6", g, "Bloquer VS Code pour un enfant : fermé, relance impossible, les autres le gardent",
          closed and bool(re.search("denied|refus|permission|non accord", again, re.I)) and other == "permis",
          f"{m} ; fermé {closed} ; message {popup} ; relance : {again[-140:]} ; nadia : {other}", [s])
    bx(f"pkill -u {u} zenity; true")
    planning(u, "V")
    # autre paquet Debian : installer puis désinstaller ; outils de contournement refusés
    tor = post(a="lginstall", cle="_paquet", paquet="tor", back="/?p=logiciels")
    bad = post(a="lginstall", cle="_paquet", paquet="paquet-qui-n-existe-pas", back="/?p=logiciels")
    m1 = post(a="lginstall", cle="_paquet", paquet="tuxpuck", back="/?p=logiciels")
    lg_job_done()
    inst = json.load(open(f"{HOME}/logiciels.json"))["installes"]
    menu = bx("grep -l -i tuxpuck /usr/share/applications/*.desktop 2>/dev/null").strip()
    regles = 'value="app:lg_p_tuxpuck"' in get("/?p=regles")[1]
    s = web_shot("/?p=logiciels", "l7_paquet", "Page Logiciels après l'installation du paquet Debian « tuxpuck »", 1300)
    check("L7", g, "Installer un paquet Debian au choix (dans le menu, gérable) ; Tor et paquet inconnu refusés",
          "p_tuxpuck" in inst and bool(menu) and regles and "contourner" in tor and "existe pas" in bad,
          f"{m1} ; menu : {menu} ; dans Règles : {regles} ; programmes : {inst.get('p_tuxpuck', {}).get('bins')} ; tor → {tor} ; inconnu → {bad}", [s])
    m2 = post(a="lgremove", cle="p_tuxpuck", back="/?p=logiciels")
    lg_job_done()
    inst = json.load(open(f"{HOME}/logiciels.json"))["installes"]
    gone = not bx("command -v tuxpuck; ls /usr/games/tuxpuck 2>/dev/null").strip()
    check("L8", g, "Désinstaller : retiré pour tous, VS Code reste installé", "p_tuxpuck" not in inst and gone and "vscode" in inst,
          f"{m2} ; binaire supprimé : {gone} ; restants : {list(inst)}")


def cleanup():
    g = GROUP["A"]
    if "driss" not in bx("cut -d: -f1 /secrets/comptes.txt").split():
        return                                       # groupe A pas lancé : aucun compte de test à supprimer
    for n in (11, 12, 13, 14):
        disconnect(n)
    m = post(a="delkid", u="paul", back="/?p=comptes")
    ok = not bx("id -u paul").strip().isdigit() and bx("[ -d /home/paul ] && echo garde").strip() == "garde"
    check("A5", g, "Supprimer un compte en gardant ses fichiers", ok, m)
    msgs = [post(a="delkid", u=u, purge="1", back="/?p=comptes") for u in ("driss", "nadia")]
    bx("rm -rf /home/paul")
    left = [u for u in KIDS if bx(f"[ -e /home/{u} ] || id -u {u} >/dev/null 2>&1 && echo reste").strip()]
    acc = bx("cut -d: -f1 /secrets/comptes.txt").split()
    check("A6", g, "Supprimer définitivement (fichiers + statistiques) ; comptes réels intacts",
          not left and acc == REAL, " | ".join(msgs) + f" ; comptes restants : {acc}")
    shutil.copy(f"{HOME}/tests/controle.json.avant_tests", RULES)


# ----------------------------------------------------------------------
# S : les outils restent libres, mais rien ne permet de contourner
# ----------------------------------------------------------------------
# Processus « comme Firefox » (enfant + groupe internet) qui lance des programmes de toutes les façons possibles
FF_TEST = r"""
import os, socket, subprocess, sys, shlex
def net():
    try:
        socket.create_connection(("CIBLE", 80), timeout=5); return "INTERNET"
    except Exception: return "sans internet"
P = "import os,socket\ntry:\n socket.create_connection(('CIBLE',80),timeout=5);r='INTERNET'\nexcept Exception: r='sans internet'\nprint(os.getgid(),r)"
print("Firefox:", os.getgid(), net(), flush=True)
print("subprocess:", subprocess.run([sys.executable, "-c", P], capture_output=True, text=True).stdout.strip(), flush=True)
print("system:", end=" ", flush=True); os.system("python3 -c " + shlex.quote(P)); sys.stdout.flush()
print("posix_spawn:", end=" ", flush=True); os.waitpid(os.posix_spawn("/usr/bin/python3", ["python3", "-c", P], os.environ), 0)
print("posix_spawnp:", end=" ", flush=True); os.waitpid(os.posix_spawnp("python3", ["python3", "-c", P], os.environ), 0)
print("popen:", os.popen("python3 -c " + shlex.quote(P)).read().strip(), flush=True)
print("execvp:", end=" ", flush=True)
if os.fork() == 0: os.execvp("python3", ["python3", "-c", P])
os.wait()
"""
FF_DROP = r"""
import os, pwd, sys, base64
p = pwd.getpwnam(sys.argv[1])
os.setgroups([p.pw_gid]); os.setresgid(2000, 2000, 2000); os.setresuid(p.pw_uid, p.pw_uid, p.pw_uid)
env = {"PATH": "/usr/bin:/bin", "HOME": p.pw_dir}
if sys.argv[2] == "1": env["LD_PRELOAD"] = "/usr/local/lib/maranyse/sans-internet-ff.so"
os.chdir(p.pw_dir)
os.execve("/usr/bin/python3", ["python3", "-c", base64.b64decode(sys.argv[3]).decode()], env)
"""
DIAG = ("#!/bin/sh\n{ echo \"lancé : gid=$(id -g) groupes=$(id -G) args=$*\"; python3 -c \"import socket\ntry: "
        "socket.create_connection(('CIBLE',80),timeout=5);print('INTERNET OUI')\nexcept Exception as e: print('internet non',e)\"; } "
        ">> /tmp/diag-ff.log 2>&1\n")


def ff_profile(u):
    if not kid(u, "ls -d ~/.config/mozilla/firefox/*.default-esr 2>/dev/null").strip():
        kid(u, "cd ~; firefox-esr about:blank >/dev/null 2>&1", gui=True, detach=True)
        wait(lambda: kid(u, "ls ~/.config/mozilla/firefox/*.default-esr/prefs.js 2>/dev/null").strip(), 60, 2)
        time.sleep(5)
    bx(f"pkill -KILL -u {u} firefox-esr; true")
    time.sleep(3)
    return kid(u, "ls -d ~/.config/mozilla/firefox/*.default-esr | head -1").strip()


def prep_vscode_test(u):
    return run(["python3", "-c", f"import sys; sys.path.insert(0, {HOME!r}); import logiciels; logiciels.preparer([{u!r}], ['vscode'])"], timeout=900)


def S_():
    g = GROUP["S"]
    u, n = "driss", DISP["driss"]
    kgid = bx(f"id -g {u}").strip()
    cible = resolve(u, "example.com")              # site ordinaire (1.1.1.1 est un serveur DoH, bloqué même pour Firefox)
    # S1 : mécanisme, toutes les façons de lancer un programme depuis Firefox
    b = base64.b64encode(FF_TEST.replace("CIBLE", cible).encode()).decode()
    sans = bx(["python3", "-c", FF_DROP, u, "0", b], timeout=90)
    avec = bx(["python3", "-c", FF_DROP, u, "1", b], timeout=90)
    check("S1", g, "Un programme lancé par Firefox n'hérite pas de son accès internet (6 façons de lancer : subprocess, system, posix_spawn…)",
          sans.count("INTERNET") == 7 and "Firefox: 2000 INTERNET" in avec and avec.count(f"{kgid} sans internet") == 6,
          f"cible : example.com ({cible}) ; SANS le correctif : " + " | ".join(sans.splitlines()) + " ### AVEC : " + " | ".join(avec.splitlines()))
    # S2 : la vraie attaque dans Firefox (lien vers une application choisie par l'enfant)
    prof = ff_profile(u)
    bx(f"echo {base64.b64encode(DIAG.replace('CIBLE', cible).encode()).decode()} | base64 -d > /usr/local/bin/maranyse-diag; chmod 755 /usr/local/bin/maranyse-diag; rm -f /tmp/diag-ff.log")
    h = {"defaultHandlersVersion": {}, "mimeTypes": {}, "isDownloadsImprovementsAlreadyMigrated": True,
         "schemes": {"maranyse": {"action": 2, "ask": False, "handlers": [{"name": "app", "path": "/usr/local/bin/maranyse-diag"}]}}}
    kid(u, f"echo {shlex.quote(json.dumps(h))} > {prof}/handlers.json; rm -rf {prof}/sessionstore.jsonlz4 {prof}/sessionstore-backups")
    kid(u, "cd ~; firefox-esr maranyse:essai >/dev/null 2>&1", gui=True, detach=True)
    time.sleep(15)
    s1 = shot(n, "s2_dialogue", "Driss : Firefox propose d'ouvrir le lien avec une application")
    for _ in range(4):
        if bx("cat /tmp/diag-ff.log 2>/dev/null").strip():
            break
        # bouton « Ouvrir le lien » : raccourci clavier, sinon clic (sa place dépend de la barre des tâches)
        tx([f"DISPLAY=:{n} xdotool key alt+o", f"DISPLAY=:{n} xdotool mousemove 803 426 click 1",
            f"DISPLAY=:{n} xdotool key Return", f"DISPLAY=:{n} xdotool mousemove 799 443 click 1"][_])
        time.sleep(8)
    diag = bx("cat /tmp/diag-ff.log 2>/dev/null").strip()
    check("S2", g, "Vraie attaque dans Firefox : l'application ouverte par un lien n'a pas internet",
          f"gid={kgid}" in diag and "internet non" in diag and "INTERNET OUI" not in diag,
          f"application lancée par Firefox : {diag or 'non lancée'}", [s1])
    bx(f"pkill -KILL -u {u} firefox-esr; rm -f /usr/local/bin/maranyse-diag /tmp/diag-ff.log; true")
    kid(u, f"rm -f {prof}/handlers.json")
    # S3 : options de pilotage à distance refusées ; Firefox va toujours sur internet
    time.sleep(3)
    kid(u, "cd ~; firefox-esr --marionette --remote-debugging-port 9222 --start-debugger-server 6000 https://example.org >/dev/null 2>&1",
        gui=True, detach=True)
    site = wait(lambda: "Example Domain" in kid(u, "xdotool search --class firefox getwindowname %@ 2>/dev/null", gui=True), 60, 3)
    ports = bx("python3 -c \"import socket\nfor p in (2828,9222,6000):\n s=socket.socket()\n s.settimeout(2)\n print(p, 'OUVERT' if s.connect_ex(('127.0.0.1',p))==0 else 'fermé')\"")
    s2 = shot(n, "s3_firefox", "Driss : Firefox lancé avec des options de pilotage : elles sont ignorées, le site s'ouvre")
    lock = bx("cat /usr/lib/firefox-esr/defaults/pref/maranyse.js")
    check("S3", g, "Firefox ne peut pas être piloté par un script (Marionette, débogage à distance) ; il navigue normalement",
          site and "OUVERT" not in ports and 'devtools.chrome.enabled", false, locked' in lock,
          f"site ouvert : {site} ; ports de pilotage : {' '.join(ports.split())} ; réglages verrouillés : {'oui' if 'locked' in lock else 'non'}", [s2])
    bx(f"pkill -KILL -u {u} firefox-esr; true")
    # S4 : préparation de VS Code avec les droits de l'enfant : un programme ou un lien déposé par l'enfant ne gagne rien
    kid(u, "mkdir -p ~/.vscode/extensions/piege-1.0/bin && cp /usr/bin/id ~/.vscode/extensions/piege-1.0/bin/outil && chmod +x ~/.vscode/extensions/piege-1.0/bin/outil")
    bx("echo temoin > /etc/maranyse-temoin; chmod 644 /etc/maranyse-temoin")
    kid(u, "mkdir -p ~/.config/Code/User && mv -f ~/.config/Code/User/settings.json ~/.config/Code/User/settings.json.bak 2>/dev/null; "
           "ln -sf /etc/maranyse-temoin ~/.config/Code/User/settings.json")
    prep_vscode_test(u)
    piege = bx(f"[ -L /home/{u}/.vscode/extensions/piege-1.0/bin/outil ] && echo lien || echo fichier").strip()
    lance = kid(u, "~/.vscode/extensions/piege-1.0/bin/outil 2>&1 | head -1; true").strip()
    temoin = bx("cat /etc/maranyse-temoin").strip()
    kid(u, "rm -rf ~/.vscode/extensions/piege-1.0; rm -f ~/.config/Code/User/settings.json; "
           "mv -f ~/.config/Code/User/settings.json.bak ~/.config/Code/User/settings.json 2>/dev/null; true")
    bx("rm -f /etc/maranyse-temoin")
    prep_vscode_test(u)
    pet = bx(f"find /home/{u}/.vscode/extensions -name pet -path '*python*' | head -1 | xargs -r readlink").strip()
    detect = kid(u, "p=$(find ~/.vscode/extensions -name pet -path '*python*' | head -1); $p --version 2>&1 | head -1").strip()
    fr = "fr" in bx(f"cat /home/{u}/.config/Code/languagepacks.json 2>/dev/null")
    own = bx(f"find /home/{u}/.vscode /home/{u}/.config/Code ! -user {u} | head -3").strip()
    refuse = "denied" in lance.lower() or "refus" in lance.lower()
    check("S4", g, "Préparation de VS Code avec les droits de l'enfant : son programme déposé reste interdit, un lien piégé ne fait rien écrire à root",
          piege == "fichier" and refuse and temoin == "temoin" and pet.startswith("/usr/local/lib/maranyse/bin/") and fr and not own,
          f"programme déposé : {piege}, lancement → {lance[-70:]} ; fichier système visé par le lien : « {temoin} » (inchangé = « temoin ») ; "
          f"programme de l'extension Python : lien vers {pet or '?'} ({detect[:40]}) ; français : {fr} ; fichiers pas à l'enfant : {own or 'aucun'}")
    # S5 : paquets de contournement refusés, même en dépendance ; droits spéciaux retirés après installation
    m1 = post(a="lginstall", cle="_paquet", paquet="openvpn-systemd-resolved", back="/?p=logiciels")
    m2 = post(a="lginstall", cle="_paquet", paquet="torsocks", back="/?p=logiciels")
    m3 = post(a="lginstall", cle="_paquet", paquet="dnsmasq", back="/?p=logiciels")
    m4 = post(a="lginstall", cle="_paquet", paquet="fping", back="/?p=logiciels")
    lg_job_done()
    caps = bx("python3 -c \"import os\ntry: print('capacités', os.getxattr('/usr/bin/fping','security.capability'))\nexcept OSError: print('aucune')\"").strip()
    mode = bx("stat -c '%A' /usr/bin/fping").strip()
    rc = bx("cat /usr/sbin/policy-rc.d 2>/dev/null").strip()
    ok_inst = "p_fping" in json.load(open(f"{HOME}/logiciels.json"))["installes"]
    check("S5", g, "VPN, tunnels, relais DNS refusés (même comme dépendance) ; un logiciel installé perd ses droits spéciaux ; aucun service démarré",
          "openvpn" in m1 and "contourner" in m1 and "contourner" in m2 and "contourner" in m3 and ok_inst and caps == "aucune"
          and "s" not in mode and "exit 101" in rc,
          f"openvpn-systemd-resolved → {m1} | torsocks → {m2} | dnsmasq → {m3} | fping : {m4} → installé {ok_inst}, capacités : {caps}, droits {mode} ; "
          f"policy-rc.d : {rc.splitlines()[-1] if rc else 'absent'}")
    if ok_inst:
        post(a="lgremove", cle="p_fping", back="/?p=logiciels")
        lg_job_done()
    # S6 : les outils ne sont pas verrouillés ; la carte Contournements le dit
    py = kid(u, "python3 -c 'print(6*7)'").strip()
    pl = kid(u, "perl -e 'print 6*7'").strip()
    page = get("/?p=regles")[1]
    s3 = web_shot("/?p=regles", "s6_contournements", "Règles → Contournements : réglages et protections toujours actives", 2600)
    check("S6", g, "Outils jamais bloqués (Python, Perl) ; carte Contournements sans réglage « outils », avec les protections permanentes",
          py == "42" and pl == "42" and "Outils de programmation" not in page and "Toujours actif" in page and "Programmes ouverts depuis Firefox" in page,
          f"python3 → {py} ; perl → {pl} ; réglage « outils » affiché : {'Outils de programmation' in page} ; protections permanentes affichées : {'Toujours actif' in page}", [s3])


# ----------------------------------------------------------------------
# R : ressources utilisées par chaque enfant (Statistiques, 30 jours)
# ----------------------------------------------------------------------
PY_DL = ("import urllib.request,sys\nr=urllib.request.urlopen(sys.argv[1],timeout=30)\nn=0\n"
         "while n<int(sys.argv[2]):\n b=r.read(65536)\n if not b: break\n n+=len(b)\nprint(n)")
GROS_FICHIER = "https://deb.debian.org/debian/dists/bookworm/main/Contents-all.gz"


def res_today(u):
    """(processeur s, pic mémoire Mo, reçu octets, envoyé octets, dossier Mo) mesurés aujourd'hui pour u."""
    c = sqlite3.connect(DB, timeout=20)
    r = c.execute("SELECT COALESCE(SUM(cpu),0), COALESCE(MAX(mem_max),0), COALESCE(SUM(net_in),0), COALESCE(SUM(net_out),0), "
                  "(SELECT disk FROM ressources WHERE user=? AND disk IS NOT NULL ORDER BY hour DESC LIMIT 1) "
                  "FROM ressources WHERE user=? AND hour>=?", (u, u, datetime.now().date().isoformat() + "T00")).fetchone()
    c.close()
    return r


def R():
    g = GROUP["R"]
    u, autre = "driss", "paul"
    for x in (u, autre):
        planning(x, "V")
    cible = resolve(u, "example.com")
    wait(lambda: tcp(u, cible, 80) == "OK", 100)
    # R1 + R2 : un programme de Driss calcule pendant 90 s en occupant 300 Mo
    wait(lambda: res_today(u)[4] is not None, 70)            # premier relevé du nouveau compte
    a0, p0 = res_today(u), res_today(autre)
    kid(u, "timeout 90 python3 -c \"x=bytearray(300<<20)\nx[::4096]=b'1'*(len(x)//4096)\nwhile 1: pass\"", detach=True)
    time.sleep(90 + 2 * 30 + 5)                              # fin du programme + 2 relevés
    a1, p1 = res_today(u), res_today(autre)
    dcpu, dautre = a1[0] - a0[0], p1[0] - p0[0]
    check("R1", g, "Processeur : le calcul d'un enfant (1 cœur pendant 90 s) lui est compté, pas à un autre",
          60 <= dcpu <= 110 and dautre < 15,
          f"Driss : +{dcpu:.0f} s de calcul (attendu ≈ 90) ; Paul pendant ce temps : +{dautre:.1f} s")
    check("R2", g, "Mémoire : les 300 Mo occupés par le programme apparaissent dans le pic de l'enfant",
          a1[1] >= 290, f"pic de mémoire de Driss aujourd'hui : {a1[1]:.0f} Mo (avant le test : {a0[1]:.0f} Mo)")
    # R3 : volume internet (Firefox), sans changer le filtrage des autres programmes
    a0, p0 = res_today(u), res_today(autre)
    n = probe(u, PY_DL, GROS_FICHIER, 4 * 1048576)
    time.sleep(2 * 30 + 5)
    a1, p1 = res_today(u), res_today(autre)
    rx, prx = (a1[2] - a0[2]) / 1048576, (p1[2] - p0[2]) / 1048576
    script = tcp(u, cible, 80, net=False)
    check("R3", g, "Internet : 4 Mo téléchargés par Firefox sont comptés à l'enfant ; un script reste sans internet",
          n.isdigit() and int(n) >= 4 * 1048576 and 3.8 <= rx <= 8 and prx < 0.5 and script != "OK",
          f"téléchargé : {n} octets ; compté à Driss : {rx:.2f} Mo reçus, {(a1[3] - a0[3]) / 1024:.0f} Ko envoyés ; "
          f"Paul : {prx:.2f} Mo ; script de Driss vers example.com : {script}")
    # R4 : taille du dossier personnel (relevée dès la création du compte, puis toutes les heures)
    du, mes = [], None
    def proche():                                            # relevé toutes les 10 min : on attend le suivant au besoin
        nonlocal du, mes
        du, mes = bx(f"du -sxm /home/{u}").split(), res_today(u)[4]
        return mes is not None and du and abs(mes - int(du[0])) <= 5
    wait(proche, 660, 20)
    check("R4", g, "Disque : la taille du dossier de l'enfant est relevée dès la création du compte, puis toutes les 10 minutes",
          mes is not None and du and abs(mes - int(du[0])) <= 5,
          f"relevé du tableau : {mes} Mo ; mesure directe : {du[0] if du else '?'} Mo")
    # R5 : page Statistiques, les 4 onglets, vue d'ensemble et vue par enfant
    vus = {}
    for k, lab in (("cpu", "processeur"), ("mem", "mémoire"), ("net", "internet"), ("disk", "disque")):
        st, page = get(f"/?p=stats&vue=ensemble&per=7&res={k}")
        vus[k] = st == 200 and f"Ressources utilisées : {lab}" in page and "Driss : " in page
    st, pe = get(f"/?p=stats&vue=enfant&s={u}&per=7&res=mem")
    enfant = st == 200 and "Ressources utilisées : mémoire" in pe and "Pic de mémoire" in pe
    s1 = web_shot("/?p=stats&vue=ensemble&per=7&res=cpu", "r5_ressources", "Statistiques → Ressources utilisées (processeur), une courbe par enfant", 2600)
    s2 = web_shot(f"/?p=stats&vue=enfant&s={u}&per=7&res=net", "r5_ressources_driss", "Vue Par enfant (Driss) : volume internet", 2600)
    check("R5", g, "Page Statistiques : courbe des ressources par enfant (processeur, mémoire, internet, disque) sur 30 jours",
          all(vus.values()) and enfant, f"onglets avec la courbe de Driss : {vus} ; vue Par enfant : {enfant}", [s1, s2])
    # R6 : compteurs effacés (bureau redémarré) : recréés seuls, filtrage intact
    avant = bx("iptables -S KIDS")
    bx("iptables -t mangle -D OUTPUT -j MNET_OUT; iptables -t mangle -D INPUT -j MNET_IN; "
       "iptables -t mangle -F MNET_OUT; iptables -t mangle -F MNET_IN; iptables -t mangle -X MNET_OUT; iptables -t mangle -X MNET_IN; true")
    ok = wait(lambda: "-A OUTPUT -j MNET_OUT" in bx("iptables -t mangle -S") and f"u{bx(f'id -u {u}').strip()}" in bx("iptables -t mangle -S MNET_IN"), 100)
    apres = bx("iptables -S KIDS")
    check("R6", g, "Compteurs internet effacés (bureau redémarré) : recréés automatiquement, filtrage des enfants inchangé",
          ok and avant == apres and "REJECT" in apres,
          f"compteurs recréés : {ok} ; règles de filtrage identiques : {avant == apres}")


# ----------------------------------------------------------------------
# P : curseur « part de l'ordinateur pour les enfants » (page Puissance)
# ----------------------------------------------------------------------
PUISS = f"{HOME}/puissance.json"


def conteneur():
    """(id, processeurs accordés, mémoire accordée en Mo, heure de démarrage) du bureau des enfants."""
    f = run(["docker", "inspect", "-f", "{{.Id}} {{.HostConfig.NanoCpus}} {{.HostConfig.Memory}} {{.State.StartedAt}}", BUREAU]).split()
    return f[0], int(f[1]) / 1e9, int(f[2]) // 1048576, f[3]


def cgroup(cid, name):
    return dict(l.split() for l in open(f"/sys/fs/cgroup/system.slice/docker-{cid}.scope/{name}").read().splitlines())


def attendu(pct):
    """Limites calculées comme le tableau : pct % de l'ordinateur hôte, sans dépasser la VM."""
    h = json.load(open(f"{HOME}/hote.json"))
    vm_cpu = os.cpu_count()
    vm_ram = h.get("vm_ram_mo", 0)
    pmax = max(5, min(60, int(100 * min(vm_cpu / h["threads"], vm_ram / h["ram_mo"]) + 0.5)))
    p = max(5, min(pmax, pct))
    return p, round(min(vm_cpu, h["threads"] * p / 100), 2), int(min(vm_ram - 1024, h["ram_mo"] * p / 100)), h


def P():
    g = GROUP["P"]
    u, autre = "driss", "paul"
    avant = open(PUISS).read() if os.path.exists(PUISS) else None
    try:
        for x in (u, autre):
            planning(x, "V")
        # P1 : curseur à 10 %, appliqué tout de suite, sessions et programmes gardés
        st, page = get("/?p=puissance")
        cid, c0, m0, d0 = conteneur()
        kid(autre, "sleep 900", detach=True)                # programme témoin d'un autre enfant
        time.sleep(1)
        p, ec, em, h = attendu(10)
        msg = post(a="puissance", pct="10", back="/?p=puissance")
        cid, c1, m1, d1 = conteneur()
        temoin = bx(f"pgrep -u {autre} -x sleep").strip()
        shot = web_shot("/?p=puissance", "p1_puissance", "Page Puissance : curseur réglé sur 10 %", 1300)
        check("P1", g, f"Curseur à 10 % : le bureau reçoit 10 % de l'ordinateur ({h['threads']} processeurs, {h['ram_mo'] // 1024} Go), "
                       "appliqué tout de suite sans fermer les sessions",
              st == 200 and 'type="range"' in page and abs(c1 - ec) < 0.01 and m1 == em and d1 == d0 and bool(temoin),
              f"{msg} ; avant : {c0:g} processeurs / {m0} Mo ; après : {c1:g} processeurs / {m1} Mo (attendu {ec:g} / {em}) ; "
              f"bureau redémarré : {d1 != d0} ; programme de Paul toujours ouvert : {bool(temoin)}", [shot])
        # P2 : 8 calculs en parallèle ne dépassent pas la limite de processeur
        kid(u, "for i in 1 2 3 4 5 6 7 8; do timeout 45 sh -c 'while :; do :; done' & done; wait", detach=True)
        time.sleep(8)
        a, t0 = int(cgroup(cid, "cpu.stat")["usage_usec"]), time.time()
        time.sleep(30)
        b, t1 = int(cgroup(cid, "cpu.stat")["usage_usec"]), time.time()
        occ = (b - a) / 1e6 / (t1 - t0)
        alerte = wait(lambda: "Limite de processeur atteinte" in get("/?p=puissance")[1], 70)
        check("P2", g, f"Processeur : 8 calculs lancés par un enfant n'occupent pas plus que la limite ({ec:g} processeurs)",
              ec * 0.85 <= occ <= ec * 1.05 and alerte,
              f"processeurs occupés pendant 30 s : {occ:.2f} (limite {ec:g}, la VM en a {os.cpu_count()}) ; "
              f"alerte « limite atteinte » sur la page : {alerte}")
        time.sleep(10)
        # P3 : mémoire pleine : seul le programme trop gourmand est fermé
        p5, _, em5, _ = attendu(5)
        post(a="puissance", pct="5", back="/?p=puissance")
        oom0 = int(cgroup(cid, "memory.events").get("oom_kill", 0))
        trop = em5 + 1024
        # remplissage progressif (par 256 Mo) : la limite du bureau ferme le programme, sans refus d'allocation immédiat
        r = kid(u, f"python3 -c \"b=[]\nfor i in range({trop}//256):\n x=bytearray(256<<20); x[::4096]=b'1'*(len(x)//4096); b.append(x)\nprint('fini')\"; echo code=$?", timeout=240)
        oom1 = int(cgroup(cid, "memory.events").get("oom_kill", 0))
        vivant = bool(bx(f"pgrep -u {autre} -x sleep").strip()) and run(["docker", "inspect", "-f", "{{.State.Status}}", BUREAU]).strip() == "running"
        xrdp = bool(bx("pgrep -x xrdp").strip())
        alerte = wait(lambda: "Mémoire pleine" in get("/?p=puissance")[1], 70)
        shot = web_shot("/?p=puissance", "p3_puissance", "Après le test mémoire : l'alerte « Mémoire pleine » est affichée", 1300)
        check("P3", g, f"Mémoire : un programme qui veut {trop // 1024} Go alors que la limite est {em5 / 1024:.1f} Go est fermé ; "
                       "le reste du bureau continue",
              "fini" not in r and "code=137" in r and oom1 > oom0 and vivant and xrdp and alerte,
              f"programme : {r.strip().splitlines()[-1] if r.strip() else '?'} ; fermetures faute de mémoire : {oom0} → {oom1} ; "
              f"autre enfant et bureau intacts : {vivant} ; xrdp actif : {xrdp} ; alerte sur la page : {alerte}", [shot])
        # P4 : bornes du curseur et limites remises si on les modifie (ex. bureau recréé)
        pm, cm, mm, _ = attendu(99)
        post(a="puissance", pct="99", back="/?p=puissance")
        haut = conteneur()[1:3]
        post(a="puissance", pct="1", back="/?p=puissance")
        bas = conteneur()[1:3]
        run(["docker", "update", "--cpus", "7", "--memory", "12g", "--memory-swap", "13g", BUREAU])
        remis = wait(lambda: conteneur()[1:3] == bas, 75)
        check("P4", g, f"Curseur borné ({p5} % à {pm} %, plafond : Windows garde au moins 40 %) ; limites modifiées à la main : remises seules",
              haut == (cm, mm) and bas == (attendu(1)[1], em5) and remis,
              f"99 % → {haut[0]:g} processeurs / {haut[1]} Mo ; 1 % → {bas[0]:g} / {bas[1]} Mo ; "
              f"remises après modification : {remis}")
        # P5 : quota disque : un enfant ne dépasse pas son quota, les autres ne sont pas gênés
        ids = {x: bx(f"id -u {x}").strip() for x in KIDS}
        msg = post(a="quota", disque_go="1", back="/?p=puissance")
        r1 = kid(u, "dd if=/dev/zero of=$HOME/gros bs=1M count=1500 2>&1; stat -c %s $HOME/gros", timeout=120)
        r2 = kid(autre, "dd if=/dev/zero of=$HOME/petit bs=1M count=100 2>&1 | tail -1; stat -c %s $HOME/petit", timeout=120)
        taille = int(r1.split()[-1]) if r1.split() and r1.split()[-1].isdigit() else -1
        post(a="quota", disque_go="1", back="/?p=puissance")       # relit la place occupée
        page = get("/?p=puissance")[1]
        shot = web_shot("/?p=puissance", "p5_quota", "Quota de 1 Go : Driss a rempli le sien, l'alerte est affichée", 1600)
        kid(u, "rm -f $HOME/gros")
        kid(autre, "rm -f $HOME/petit")
        check("P5", g, "Espace disque : quota de 1 Go par enfant ; au-delà l'enregistrement échoue, les autres enfants ne sont pas gênés ; "
                       "les comptes enfants n'ont jamais le numéro du compte « parent » de la VM (1000)",
              "quota" in r1.lower() and 0 < taille <= 1 << 30 and "104857600" in r2 and "Presque plein pour Driss" in page
              and all(v.isdigit() and int(v) >= 1001 for v in ids.values()),
              f"{msg} ; Driss écrit 1,5 Go : « {r1.splitlines()[0] if r1 else '?'} », fichier de {taille / 2**20:.0f} Mo ; "
              f"Paul écrit 100 Mo : {'OK' if '104857600' in r2 else r2.strip()} ; alerte sur la page : {'Presque plein pour Driss' in page} ; "
              f"numéros des comptes : {ids}", [shot])
    finally:
        kid(u, "rm -f $HOME/gros; pkill -u driss -x sh; true")
        kid(autre, "rm -f $HOME/petit")
        bx(f"pkill -u {autre} -x sleep; true")
        if avant is None:
            if os.path.exists(PUISS):
                os.remove(PUISS)
        else:
            open(PUISS, "w").write(avant)
        try:
            post(a="puissance", pct=str(json.loads(avant)["pct"] if avant else 100), back="/?p=puissance")
        except ValueError:
            pass
        if avant is None and os.path.exists(PUISS):
            os.remove(PUISS)
        elif avant and "disque_go" in avant:
            post(a="quota", disque_go=str(json.loads(avant)["disque_go"]), back="/?p=puissance")
            open(PUISS, "w").write(avant)


# ----------------------------------------------------------------------
# I : langues (espace parents, bureau et messages des enfants)
# ----------------------------------------------------------------------
LANGS = ["fr", "en", "es", "de", "pt", "ru", "ar", "hi", "zh", "ja"]


def env_de(u, prog):
    return kid(u, f"p=$(pgrep -u {u} -x {prog} | head -1); [ -n \"$p\" ] && tr '\\0' '\\n' < /proc/$p/environ | grep -E '^(LANG|GTK_IM_MODULE)='")


def I():
    g = GROUP["I"]
    sys.path.insert(0, HOME)
    import i18n
    import tableau
    # I1 : espace parents dans les 10 langues ; part des phrases traduites sur les pages principales
    pages = ["/?p=live", "/?p=planning", "/?p=regles&s=_tous", "/?p=stats", "/?p=logiciels", "/?p=puissance", "/?p=comptes", "/?p=aide"]
    tableau.load_accounts()                          # prénoms et identifiants des enfants : gardés tels quels
    noms = tableau.noms_page()
    cles = []
    for pg in pages:
        cles += i18n.cles(get(pg)[1], noms)
    cles = list(dict.fromkeys(cles))
    res = {}
    for lg in LANGS:
        st, page = get(f"/?p=live&lang={lg}")
        cat = i18n.catalogue(lg)
        part = 100.0 if lg == "fr" else 100 * sum(k in cat for k in cles) / max(1, len(cles))
        mot = cat.get("Accueil", "Accueil")
        res[lg] = (st == 200 and f'lang="{lg}"' in page and mot in page and (lg != "ar" or 'dir="rtl"' in page), part)
    shots = [web_shot("/?p=live&lang=ja", "i1_accueil_ja", "Espace parents en japonais", 1500),
             web_shot("/?p=live&lang=ar", "i1_accueil_ar", "Espace parents en arabe (de droite à gauche)", 1500),
             web_shot("/?p=puissance&lang=de", "i1_puissance_de", "Page Puissance en allemand", 1500)]
    check("I1", g, "Espace parents en 10 langues (sélecteur, arabe de droite à gauche) : phrases traduites sur les pages principales",
          all(ok and part >= 97 for ok, part in res.values()),
          " ; ".join(f"{lg} {'OK' if ok else 'PROBLÈME'} {part:.0f} %" for lg, (ok, part) in res.items()) + f" ({len(cles)} phrases)", shots)
    # I2 : bureau de l'enfant dans sa langue (japonais pour Driss, arabe pour Paul) à sa prochaine connexion
    choix = {"driss": "ja", "paul": "ar"}
    msgs = [post(a="langue", u=u, v=lg, back="/?p=comptes") for u, lg in choix.items()]
    wait(lambda: all(f"{u} {lg}" in bx("cat /etc/maranyse/langues") for u, lg in choix.items()), 70)
    for u in choix:
        post(a="logout", u=u, back="/?p=live")
    wait(lambda: not any(u in displays() for u in choix), 60)
    for u in choix:
        connect(u, PW[u])
    ok = wait(lambda: all(desktop_ready(u) for u in choix), 150)
    time.sleep(15)
    kid("driss", "firefox-esr about:blank >/dev/null 2>&1", gui=True, detach=True)
    time.sleep(20)
    env = {u: env_de(u, "xfce4-panel") for u in choix}
    fc = {u: bool(bx(f"pgrep -u {u} -x fcitx5").strip()) for u in choix}
    shots = [shot(DISP["driss"], "i2_bureau_ja", "Bureau de Driss en japonais (Firefox ouvert ; Ctrl+Espace : saisie japonaise)"),
             shot(DISP["paul"], "i2_bureau_ar", "Bureau de Paul en arabe")]
    check("I2", g, "Bureau de l'enfant dans sa langue à sa prochaine connexion (japonais, arabe) avec la saisie de cette écriture",
          ok and "LANG=ja_JP.UTF-8" in env["driss"] and "LANG=ar_MA.UTF-8" in env["paul"] and all(fc.values()),
          f"{' | '.join(msgs)} ; environnement : {env} ; saisie fcitx5 active : {fc}", shots)
    # I3 : message automatique dans la langue de l'enfant (Paul en arabe : passage en mode restreint)
    planning("paul", "O")
    # les messages automatiques se remplacent : passage en mode restreint ou limite atteinte, pourvu qu'il soit en arabe
    cat = i18n.catalogue("ar")
    mots = [cat.get(k, "?") for k in ("Mode restreint", "C'est fini pour aujourd'hui", "Bloqué par tes parents")]
    attendu = " / ".join(mots)

    def lu():
        txt = bx("for p in $(pgrep -u paul -x zenity); do tr '\\0' ' ' < /proc/$p/cmdline; done")
        return any(m in txt for m in mots) and "Mode restreint" not in txt and "C'est fini" not in txt
    vu = wait(lu, 75)
    s3 = shot(DISP["paul"], "i3_message_ar", "Message automatique reçu par Paul, en arabe")
    planning("paul", "V")
    kid("driss", "pkill -x firefox-esr; true")
    for u in choix:
        post(a="langue", u=u, v="fr", back="/?p=comptes")
    check("I3", g, "Message automatique (passage en mode restreint) écrit dans la langue de l'enfant", vu,
          f"texte attendu « {attendu} » dans la fenêtre de message de Paul : {vu}", [s3])


# ----------------------------------------------------------------------
# K : la famille — copies des 3 vrais enfants (mêmes réglages), scénarios de la vie courante.
# Les vrais comptes, leurs fichiers et leurs statistiques ne sont jamais touchés.
# ----------------------------------------------------------------------
FAMILLE = {}                  # vrai compte -> (copie d'essai, prénom affiché de la copie, écran) : rempli au début du groupe K


def famille():
    """Les 3 premiers vrais comptes et leurs prénoms affichés (comptes.txt)."""
    FAMILLE.clear()
    noms = []
    for i, l in enumerate(bx("cat /secrets/comptes.txt").splitlines()):
        u, _, n = l.partition(":")
        if u and u not in KIDS and len(FAMILLE) < 3:
            n = n.strip() or u.replace("_", " ").title()
            FAMILLE[u] = (f"essai_{len(FAMILLE) + 1}", f"{n} (essai)", 21 + len(FAMILLE))
            noms.append(n)
    return noms
PW_ESSAI = "Essai2026"


def inject_site(u, cle, sec):
    c = sqlite3.connect(DB, timeout=20)
    c.execute("INSERT INTO sites(day,user,cle,sec) VALUES(?,?,?,?) ON CONFLICT DO UPDATE SET sec=sec+excluded.sec",
              (datetime.now().date().isoformat(), u, cle, sec))
    c.commit()
    c.close()


def creneau(u, lettre, quota=0):
    """Planning de la copie : la case de maintenant (et toute la semaine) dans cette couleur — « on est à cette heure-là »."""
    return planning(u, lettre, quota)


def semaine(r):
    """Résumé de la semaine d'un enfant selon son planning réel : heures vert / orange / rouge, temps d'écran maximum."""
    out = []
    for d in range(7):
        gr = r["grille"][str(d)]
        v, o, rr = (gr.count(x) / 2 for x in "VOR")
        q = int(r["quota"].get(str(d)) or 0)
        out.append(f"{['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'][d]} : vert {v:g} h, orange {o:g} h, rouge {rr:g} h, "
                   + (f"maximum {q // 60} h {q % 60:02d}" if q else "sans maximum"))
    return out


def K():
    g = GROUP["K"]
    N1, N2, N3 = (famille() + ["enfant 1", "enfant 2", "enfant 3"])[:3]
    A1, A2, A3 = list(FAMILLE)[:3]
    for n in (21, 22, 23):
        tx(f"Xvfb :{n} -screen 0 1280x800x24 -nolisten tcp >/dev/null 2>&1", detach=True)
    vrai = rules()
    copies = {}
    try:
        # --- préparation : une copie de chaque enfant, avec ses réglages actuels (planning, règles, internet, langue)
        for src, (login, nom_, n) in FAMILLE.items():
            post(a="delkid", u=login, purge="1", back="/?p=comptes")
            bx(f"rm -rf /home/{login}")
            m = post(a="addkid", nom=nom_, login=login, pw=PW_ESSAI, copie=src, langue=vrai.get(src, {}).get("langue", "fr"),
                     back="/?p=comptes")
            copies[src] = login
            DISP[login] = n
            PW[login] = PW_ESSAI
        wait(lambda: all(bx(f"id -u {x}").strip().isdigit() for x in copies.values()), 60)
        time.sleep(35)                                     # règles appliquées aux nouveaux comptes
        for x in copies.values():
            connect(x, PW_ESSAI)
        ok_co = wait(lambda: all(desktop_ready(x) for x in copies.values()), 150)
        time.sleep(10)
        mo, ra, an = copies[A1], copies[A2], copies[A3]
        shots = [shot(DISP[x], f"k1_{x}", f"{FAMILLE[s][1]} : bureau ouvert avec les réglages actuels de {s}") for s, x in copies.items()]
        check("K1", g, f"Les 3 copies (mêmes réglages que {N1}, {N2} et {N3}) se connectent en même temps", ok_co,
              f"comptes d'essai : {', '.join(copies.values())} ; sessions : {displays()}", shots)

        # ================= PARTIE 1 : les réglages ACTUELS, tels quels =================
        # Le planning actuel est tout vert : en vert, l'enfant a l'accès complet (les règles ne s'appliquent qu'en orange).
        adulte = {x: resolve(x, "pornhub.com") for x in copies.values()}
        check("K2", g, "Réglages actuels : internet filtré pour tous… mais le planning est tout vert, donc le filtre n'agit jamais",
              True, "pornhub.com vu par chaque copie : " + " ; ".join(f"{x} → {r}" for x, r in adulte.items())
              + ". En vert, internet n'est pas filtré : pour que le filtre familial agisse, mettre des cases orange dans le Planning.",
              kind="OK" if all(blocked_dns(r) for r in adulte.values()) else "LIMITE")
        inject_site(an, "site:youtube", 40 * 60)           # 3e enfant : limite YouTube 15 min… dépassée
        time.sleep(35)
        yt = resolve(an, "www.youtube.com")
        lo = kid(an, "[ -x /usr/lib/libreoffice/program/soffice.bin ] && echo autorisé || echo bloqué").strip()
        check("K3", g, f"Réglages actuels de {N3} (LibreOffice bloqué, YouTube 15 min) : sans effet tant que son planning est vert",
              True, f"après 40 min de YouTube aujourd'hui : www.youtube.com → {yt} ({'bloqué' if blocked_dns(yt) else 'accessible'}) ; "
                    f"LibreOffice : {lo}. Ces règles ne s'appliquent qu'en orange.",
              kind="OK" if blocked_dns(yt) and lo == "bloqué" else "LIMITE")
        protections = {x: tcp(x, "1.1.1.1", 443, net=False) for x in copies.values()}
        check("K4", g, "Toujours actif, même en vert : un programme ou un script de l'enfant n'a pas internet (seul Firefox l'a)",
              all(v != "OK" for v in protections.values()), " ; ".join(f"script de {x} → {v}" for x, v in protections.items()))

        # ================= PARTIE 2 : journées types =================
        # 2e enfant, 8 h 15 : c'est l'heure de l'école (rouge). Elle essaie quand même de se connecter.
        creneau(ra, "R")
        msg_r = wait(lambda: popup_text(ra, "horaire interdit"), 90, 2)
        time.sleep(2)
        s1 = shot(DISP[ra], "k5_ecole", f"{N2} (essai) pendant l'heure d'école : message, la session va se fermer")
        ferme = wait(lambda: ra not in displays(), 120, 3)
        tx("Xvfb :24 -screen 0 1280x800x24 -nolisten tcp >/dev/null 2>&1", detach=True)
        connect(ra, PW_ESSAI, 24)
        time.sleep(15)
        s2 = shot(24, "k5_ecole_refus", f"{N2} (essai) réessaie pendant l'école : connexion refusée")
        disconnect(24)
        check("K5", g, f"{N2}, heure d'école (rouge) : message, session fermée après 1 minute, reconnexion refusée",
              msg_r and ferme and ra not in displays() and locked(ra), f"message {msg_r} ; session fermée {ferme} ; compte verrouillé {locked(ra)}", [s1, s2])
        # 16 h 30 : retour de l'école, temps libre (vert)
        creneau(ra, "V")
        wait(lambda: not locked(ra), 90)
        connect(ra, PW_ESSAI)
        ok = wait(lambda: desktop_ready(ra), 120)
        time.sleep(8)
        s = shot(DISP[ra], "k6_retour", f"{N2} (essai) de retour de l'école : temps libre, bureau ouvert")
        check("K6", g, f"{N2}, 16 h 30 (vert) : elle peut se reconnecter", ok, "", [s])
        # 19 h : à table ! Message puis pause pendant le repas, ses applications restent ouvertes
        m = post(a="msg", u=ra, v="À table dans 5 minutes, enregistre ce que tu fais !", back="/?p=live")
        okm = wait(lambda: popup_text(ra, "à table dans 5 minutes"), 20, 1)
        time.sleep(2)
        s1 = shot(DISP[ra], "k7_message", f"{N2} (essai) reçoit le message des parents")
        bx(f"pkill -u {ra} zenity; true")
        kid(ra, "mousepad", gui=True, detach=True)
        wait(lambda: bx(f"pgrep -u {ra} -x mousepad").strip(), 30, 1)
        pid0 = bx(f"pgrep -u {ra} -x mousepad").strip()
        post(a="pause15", u=ra, back="/?p=live")
        okp = wait(lambda: "PAUSE-BUREAU-ENFANTS" in bx(f"pgrep -u {ra} -a zenity"), 30, 1)
        time.sleep(4)
        s2 = shot(DISP[ra], "k7_pause", f"{N2} (essai) pendant le repas : écran en pause")
        post(a="lever", u=ra, back="/?p=live")
        okl = wait(lambda: "PAUSE-BUREAU-ENFANTS" not in bx(f"pgrep -u {ra} -a zenity"), 30, 1)
        pid1 = bx(f"pgrep -u {ra} -x mousepad").strip()
        check("K7", g, f"{N2}, 19 h : message « à table », pause pendant le repas, puis reprise avec ses applications intactes",
              okm and okp and okl and pid0 and pid0 == pid1, f"{m} ; pause {okp} ; reprise {okl} ; Mousepad gardé {pid0 == pid1}", [s1, s2])

        # 1er enfant : devoirs (orange). Internet filtré, YouTube bloqué pendant les devoirs, le reste est permis.
        post(a="addrule", s=mo, cle="site:youtube", mode="bloquer", back="/?p=regles")
        creneau(mo, "O")
        ok = wait(lambda: blocked_dns(resolve(mo, "www.youtube.com")) and blocked_dns(resolve(mo, "pornhub.com")), 100)
        wiki = resolve(mo, "fr.wikipedia.org")
        thonny = kid(mo, "[ -x /usr/bin/thonny ] && echo autorisé || echo bloqué").strip()
        s = firefox_shot(mo, "https://www.youtube.com", "k8_devoirs", f"{N1} (essai) pendant les devoirs : YouTube bloqué")
        check("K8", g, f"{N1}, devoirs (orange) : YouTube et sites adultes bloqués, Wikipédia et Thonny permis",
              ok and not blocked_dns(wiki) and thonny == "autorisé",
              f"youtube → {resolve(mo, 'www.youtube.com')} ; pornhub → {resolve(mo, 'pornhub.com')} ; wikipedia → {wiki} ; Thonny : {thonny}", [s])
        # Soirée : 2 h d'écran par jour au maximum. Avertissement, fin, puis 30 minutes de bonus accordées.
        creneau(mo, "V", quota=120)
        inject_usage(mo, max(0, 117 * 60 - used_today(mo)))
        okw = wait(lambda: popup_text(mo, "il te reste environ"), 100, 2)
        time.sleep(2)
        s1 = shot(DISP[mo], "k9_avertissement", f"{N1} (essai) : il reste 3 minutes sur ses 2 heures")
        inject_usage(mo, 5 * 60)
        okf = wait(lambda: popup_text(mo, "épuisé"), 100, 2)
        time.sleep(2)
        s2 = shot(DISP[mo], "k9_fin", f"{N1} (essai) : 2 heures atteintes, la session va se fermer")
        ferme = wait(lambda: mo not in displays(), 120, 3)
        post(a="bonus", u=mo, back="/?p=live")
        okb = wait(lambda: not locked(mo), 100)
        connect(mo, PW_ESSAI)
        okr = wait(lambda: desktop_ready(mo), 120)
        check("K9", g, f"{N1}, soirée (2 h par jour) : avertissement, fermeture à 2 h, bonus de 30 min pour finir un travail",
              okw and okf and ferme and okb and okr, f"avertissement {okw} ; fin {okf} ; session fermée {ferme} ; bonus {okb} ; reconnecté {okr}", [s1, s2])

        # 3e enfant : ses vraies règles appliquées pendant les devoirs (orange) : LibreOffice bloqué, YouTube 15 min déjà dépassées
        creneau(an, "O")
        ok = wait(lambda: "bloqué" in kid(an, "[ -x /usr/lib/libreoffice/program/soffice.bin ] && echo autorisé || echo bloqué")
                  and blocked_dns(resolve(an, "www.youtube.com")), 100)
        msg_a = wait(lambda: popup_text(an, "youtube") or popup_text(an, "libreoffice"), 60, 2)
        time.sleep(2)
        s = shot(DISP[an], "k10_enfant3", f"{N3} (essai) en orange : ses règles s'appliquent (message reçu)")
        bx(f"pkill -u {an} zenity; true")
        check("K10", g, f"{N3} en orange : ses règles s'appliquent (LibreOffice bloqué, YouTube fini après 15 min) avec un message",
              ok and msg_a, f"LibreOffice : {kid(an, '[ -x /usr/lib/libreoffice/program/soffice.bin ] && echo autorisé || echo bloqué').strip()} ; "
                            f"youtube → {resolve(an, 'www.youtube.com')} ; message {msg_a}", [s])
        # 3e enfant a « internet libre » : il essaie de contourner (VPN, proxy, DNS sécurisé, script)
        tent = {"script vers example.com": tcp(an, resolve(an, "example.com"), 80, net=False),
                "DNS sécurisé 1.1.1.1:443": tcp(an, "1.1.1.1", 443),
                "dns.google": resolve(an, "dns.google"),
                "site proxy proxysite.com": resolve(an, "proxysite.com")}
        bloque = {k: (v != "OK" if k.startswith(("script", "DNS")) else blocked_dns(v)) for k, v in tent.items()}
        check("K11", g, f"{N3} (internet libre) tente de contourner : script, DNS sécurisé et DoH bloqués ; un site proxy reste joignable en « libre »",
              bloque["script vers example.com"] and bloque["DNS sécurisé 1.1.1.1:443"] and bloque["dns.google"],
              " ; ".join(f"{k} → {v} ({'bloqué' if bloque[k] else 'accessible'})" for k, v in tent.items())
              + (". En « libre », les sites proxy ne sont pas bloqués : préférez « filtré » si besoin." if not bloque["site proxy proxysite.com"] else ""))

        # ================= PARTIE 3 : la semaine de chaque enfant avec son planning actuel =================
        lignes = []
        for src in FAMILLE:
            r = vrai.get(src)
            if r:
                tout_vert = all(r["grille"][str(d)] == "V" * 48 for d in range(7))
                lignes.append(f"{FAMILLE[src][1].replace(' (essai)', '')} : " + ("TOUT VERT 24 h/24, 7 j/7, sans maximum — aucune règle ni filtre ne s'applique"
                              if tout_vert and not any(int(v or 0) for v in r["quota"].values()) else " | ".join(semaine(r))))
        check("K12", g, "Semaine simulée avec les plannings actuels", True, " ;; ".join(lignes),
              [web_shot(f"/?p=planning&s={A1}", "k12_planning", f"Planning actuel de {N1}", 1700)],
              kind="LIMITE" if any("TOUT VERT" in x for x in lignes) else "OK")
    finally:
        for n in (21, 22, 23, 24):
            disconnect(n)
        for login in copies.values():
            post(a="delkid", u=login, purge="1", back="/?p=comptes")
            bx(f"rm -rf /home/{login}")


# ======================================================================
# Rapport
# ======================================================================
COVERAGE = [
    ("Comptes enfants : créer, renommer, mot de passe, supprimer", ["A1", "A2", "A3", "A4", "A5", "A6"]),
    ("Connexion multi-sessions simultanées", ["B1", "B1b", "B2"]),
    ("Isolation entre enfants / pas de droits admin", ["B3", "B4"]),
    ("Planning horaire (vert / orange / rouge)", ["C3", "C4", "D1"]),
    ("Temps d'écran quotidien + avertissement + bonus", ["C1", "C2", "C5"]),
    ("Filtrage internet (coupé, filtré, sites, domaines libres)", ["D1", "D2", "D3", "D4"]),
    ("Règles communes + exceptions par enfant", ["D11"]),
    ("Blocage et limite de temps par application", ["D5", "D6", "D9"]),
    ("Programmer (Python, Thonny, pip…) sans pouvoir contourner : internet réservé à Firefox", ["D9b", "D10", "D13"]),
    ("Sites proxy / VPN bloqués, recherche sécurisée imposée, sans fuite pendant les changements", ["D14", "D15"]),
    ("Résistance aux contournements (réglable : autoriser / interdire)", ["D7", "D8", "D8b", "D9", "D10", "D12", "B4"]),
    ("Pause à distance (écran figé, applis gardées)", ["E0", "E1", "E2", "E3", "E4", "E5"]),
    ("Messages aux enfants", ["F1"]),
    ("Statistiques, journal, fermeture à distance", ["G1", "G2", "G3", "G4"]),
    ("Sécurité du tableau / persistance / capacité", ["H1", "H2", "H3", "H4", "H5"]),
    ("Logiciels installés pour tous (VS Code, paquets Debian) : préparés, gérables, comptés, sans internet", ["L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8"]),
    ("Outils jamais bloqués, mais aucun contournement : programmes lancés par Firefox, pilotage de Firefox, préparation de VS Code, paquets VPN/tunnels, droits spéciaux",
     ["S1", "S2", "S3", "S4", "S5", "S6"]),
    ("Ressources utilisées par chaque enfant (processeur, mémoire, internet, disque), courbe sur 30 jours", ["R1", "R2", "R3", "R4", "R5", "R6"]),
    ("Famille : réglages actuels des 3 enfants vérifiés en vrai, journées types (école, devoirs, temps libre), semaine simulée",
     ["K1", "K2", "K3", "K4", "K5", "K6", "K7", "K8", "K9", "K10", "K11", "K12"]),
    ("Langues : espace parents en 10 langues (arabe de droite à gauche), bureau et messages de chaque enfant dans sa langue", ["I1", "I2", "I3"]),
    ("Puissance : curseurs qui limitent la part de l'ordinateur (processeur, mémoire) et l'espace disque de chaque enfant", ["P1", "P2", "P3", "P4", "P5"]),
]
NOT_IMPLEMENTED = [
    ("Recherche sécurisée forcée sur Bing", "Partiel : Google et YouTube (mode restreint) sont imposés par le filtre familial, pas Bing."),
    ("Liste blanche stricte (seulement les sites autorisés)", "Absent : seul le blocage par liste noire existe."),
    ("Alertes envoyées au parent (téléphone, e-mail)", "Absent : il faut ouvrir le tableau de bord."),
    ("Historique complet des sites visités", "Partiel : titres d'onglets au premier plan, heure par heure (G4) ; pas l'historique Firefox lui-même."),
    ("Filtrage des sites par adresse IP", "Absent : le filtrage passe par le DNS ; les contournements connus sont bloqués (D8, D8b, D9)."),
]


def esc(s):
    return html.escape(str(s))


def report():
    for name in SHOTS:
        tx(f"[ -f /out/{name}.png ] && convert /out/{name}.png -resize '1280x>' -quality 72 /out/{name}.jpg")
    img = {}
    for name in SHOTS:
        p = f"{OUT}/{name}.jpg"
        if os.path.exists(p):
            img[name] = base64.b64encode(open(p, "rb").read()).decode()
    by = {r["id"]: r for r in RESULTS}
    n = {k: sum(1 for r in RESULTS if r["status"] == k) for k in ("OK", "ÉCHEC", "LIMITE", "SAUTÉ")}
    cls = {"OK": "ok", "ÉCHEC": "ko", "LIMITE": "lim", "SAUTÉ": "skip"}
    cov = ""
    for feat, ids in COVERAGE:
        sts = [by[i]["status"] for i in ids if i in by]
        worst = "ÉCHEC" if "ÉCHEC" in sts else "LIMITE" if "LIMITE" in sts else "OK" if sts and all(s in ("OK", "SAUTÉ") for s in sts) else "SAUTÉ"
        cov += (f'<tr><td>{esc(feat)}</td><td>{" ".join(f"<a href=#{i} class=tag>{i}</a>" for i in ids)}</td>'
                f'<td><span class="st {cls[worst]}">{worst}</span></td></tr>')
    for feat, why in NOT_IMPLEMENTED:
        cov += f'<tr><td>{esc(feat)}</td><td class="mut">{esc(why)}</td><td><span class="st na">NON PRÉVU</span></td></tr>'
    body, cur = "", None
    for r in RESULTS:
        if r["group"] != cur:
            cur = r["group"]
            body += f"<h2>{esc(cur)}</h2>"
        figs = "".join(f'<figure><img loading="lazy" src="data:image/jpeg;base64,{img[s]}" alt="{esc(SHOTS[s])}"><figcaption>{esc(SHOTS[s])}</figcaption></figure>'
                       for s in r["shots"] if s in img)
        body += (f'<article id="{r["id"]}" class="t"><header><span class="st {cls[r["status"]]}">{r["status"]}</span>'
                 f'<b>{r["id"]}</b><span>{esc(r["title"])}</span></header><p>{esc(r["detail"])}</p>'
                 f'{f"<div class=figs>{figs}</div>" if figs else ""}</article>')
    dur = f"{(time.time() - T0) / 60:.0f} min"
    page = f"""<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Tests contrôle parental</title><style>
:root{{--bg:#f6f7fb;--card:#fff;--text:#161b29;--mut:#6b7385;--line:#e3e6ee;--ok:#1d8a4e;--okb:#e1f4e9;--ko:#c93a3f;--kob:#fde7e7;
--lim:#b8650a;--limb:#fff1dc;--skip:#5b6274;--skipb:#eceef3;--na:#5856d6;--nab:#ecebff}}
@media (prefers-color-scheme:dark){{:root:not([data-theme=light]){{--bg:#0f1116;--card:#181b22;--text:#eceef4;--mut:#959db0;--line:#2a2f3a;
--ok:#4cc77f;--okb:#15301f;--ko:#f26b6f;--kob:#3a1b1d;--lim:#f6a548;--limb:#38280f;--skip:#aab1c2;--skipb:#242833;--na:#9d9cf8;--nab:#25264a}}}}
:root[data-theme=dark]{{--bg:#0f1116;--card:#181b22;--text:#eceef4;--mut:#959db0;--line:#2a2f3a;--ok:#4cc77f;--okb:#15301f;--ko:#f26b6f;--kob:#3a1b1d;
--lim:#f6a548;--limb:#38280f;--skip:#aab1c2;--skipb:#242833;--na:#9d9cf8;--nab:#25264a}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--text);font:15px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}}
main{{max-width:1100px;margin:0 auto;padding:28px 16px 60px}}h1{{font-size:26px;margin:0 0 4px}}h2{{font-size:19px;margin:34px 0 12px}}
.mut{{color:var(--mut)}}.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin:20px 0}}
.kpi{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 16px}}.kpi b{{font-size:28px;display:block}}
table{{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);border-radius:14px;overflow:hidden}}
td,th{{padding:10px 12px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}}th{{font-size:13px;color:var(--mut)}}
.tw{{overflow-x:auto}}.tag{{display:inline-block;font-size:12px;padding:1px 7px;border-radius:7px;background:var(--skipb);color:var(--text);text-decoration:none;margin:1px}}
.st{{display:inline-block;font-size:12px;font-weight:700;padding:2px 9px;border-radius:99px;white-space:nowrap}}
.ok{{background:var(--okb);color:var(--ok)}}.ko{{background:var(--kob);color:var(--ko)}}.lim{{background:var(--limb);color:var(--lim)}}
.skip{{background:var(--skipb);color:var(--skip)}}.na{{background:var(--nab);color:var(--na)}}
.t{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 16px;margin:10px 0}}
.t header{{display:flex;gap:10px;align-items:baseline;flex-wrap:wrap}}.t p{{margin:6px 0 0;color:var(--mut);font-size:14px;overflow-wrap:anywhere}}
.figs{{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px;margin-top:12px}}
figure{{margin:0}}img{{width:100%;border-radius:10px;border:1px solid var(--line);display:block;cursor:zoom-in}}
figcaption{{font-size:12.5px;color:var(--mut);margin-top:4px}}img.big{{position:fixed;inset:0;margin:auto;width:auto;max-width:96vw;max-height:94vh;z-index:9;cursor:zoom-out;box-shadow:0 0 0 100vmax rgba(0,0,0,.7)}}
</style></head><body><main>
<h1>Tests du contrôle parental</h1>
<p class="mut">Scénario graphique avec les comptes de test driss, paul et nadia : vraies sessions Bureau à distance, actions par le tableau de bord.
{datetime.now():%d.%m.%Y %H:%M} · durée {dur} · {len(RESULTS)} vérifications.</p>
<div class="kpis"><div class="kpi"><b style="color:var(--ok)">{n["OK"]}</b>réussis</div><div class="kpi"><b style="color:var(--ko)">{n["ÉCHEC"]}</b>échecs</div>
<div class="kpi"><b style="color:var(--lim)">{n["LIMITE"]}</b>limites connues</div><div class="kpi"><b>{n["SAUTÉ"]}</b>sautés</div></div>
<h2>Couverture d'un contrôle parental complet</h2><div class="tw"><table><tr><th>Fonction</th><th>Tests</th><th>État</th></tr>{cov}</table></div>
{body}</main><script>document.querySelectorAll('img').forEach(i=>i.onclick=()=>i.classList.toggle('big'))</script></body></html>"""
    open(f"{OUT}/rapport.html", "w").write(page)
    json.dump(RESULTS, open(f"{OUT}/resultats.json", "w"), ensure_ascii=False, indent=1)
    log(f"Rapport : {OUT}/rapport.html — {n}")


if __name__ == "__main__":
    try:
        log("Préparation")
        setup()
        choix = set(sys.argv[1:])                    # ex. « python3 scenario.py A B L » : seulement ces groupes
        for name, fn in (("A", A), ("B", B), ("F", F), ("E", E), ("D", D), ("L", L), ("S", S_), ("R", R), ("P", P), ("I", I), ("K", K), ("C", C), ("G", G), ("H", H)):
            if choix and name not in choix:
                continue
            log(f"=== {GROUP[name]}")
            step(name, GROUP[name], "Groupe " + GROUP[name], fn)
    finally:
        log("Nettoyage")
        step("A5", GROUP["A"], "Nettoyage", cleanup)
        report()
        run(["docker", "rm", "-f", T])
