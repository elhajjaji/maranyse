#!/usr/bin/env python3
"""MaranYSE — espace parents : interface web (http://IP:8080) qui pilote les sessions des enfants servies par la VM.
- La logique (règles, statistiques, application toutes les 30 s) est dans logique.py.
- Les styles, icônes SVG et scripts JS sont dans style.py.
- Les calculs statistiques et graphiques SVG sont dans stats.py.
- La page d'aide intégrée est dans aide.py.
"""
import base64, hashlib, html, json, math, os, re, secrets, socket, ssl, subprocess, threading, time
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse, quote

from logique import *            # noqa: F401,F403
from logique import STATE, USERS, NAMES, lock, nom  # explicite
from marque import LOGO_PNG, FAVICON_PNG, EMBLEME_PNG, EMBLEME_PETIT_PNG, LOGO_HD_JPG, LOGO_PETIT_JPG, TITRE_JPG, SLOGAN_JPG, BANNIERE_JPG
from style import *              # noqa: F401,F403
from style import MOIS, IC, CSS, JS, LG_JS, e, ic, avatar, item_badge, wm_item, card, more
from stats import *              # noqa: F401,F403
from aide import *               # noqa: F401,F403
from aide import render_aide
import logiciels
import i18n
import themes

REQ = threading.local()
V_IMG = hashlib.md5(LOGO_HD_JPG + LOGO_PETIT_JPG + TITRE_JPG + BANNIERE_JPG + FAVICON_PNG).hexdigest()[:8]   # version des images


def fmt_ts(ts):
    d = datetime.strptime(ts, "%Y%m%d-%H:%M:%S")
    return f"{d:%H:%M}" if d.date() == datetime.now().date() else f"le {d.day} {MOIS[d.month - 1]} à {d:%H:%M}"


# ======================================================================
# Squelette de page
# ======================================================================
PAGES = [("live", "Accueil", "home"), ("planning", "Planning", "calendar"), ("regles", "Règles", "shield"), ("stats", "Statistiques", "chart"),
         ("logiciels", "Logiciels", "box"), ("puissance", "Puissance", "cpu"), ("comptes", "Comptes", "users"), ("aide", "Aide", "help")]


def jauge(cle, nom_, titre, d):
    """Indicateur de charge : processeur (chiffre + barre) et mémoire (barre fine)."""
    cpu, mem = (d["cpu"], d["mem"]) if d else (None, None)
    niv = lambda v: "" if v is None else "r" if v >= 85 else "o" if v >= 60 else "g"
    tip = f"Processeur {cpu} % · Mémoire {mem} %" if d else "Pas de nouvelles du PC hôte (script charge_hote.ps1 arrêté ?)"
    return (f'<div class="charge {"" if d else "off"}" id="ch-{cle}" aria-label="{e(titre)}" data-tip="{e(tip)}">'
            f'<b translate="no">{nom_}</b><span class="ch-b"><i class="{niv(cpu)}" style="width:{cpu or 0}%"></i>'
            f'<i class="m {niv(mem)}" style="width:{mem or 0}%"></i></span><span class="ch-v" translate="no">{"—" if cpu is None else f"{cpu} %"}</span></div>')


def charge_html():
    try:
        vm = charge_vm()
    except (OSError, ValueError, KeyError):
        vm = None
    return (jauge("vm", "VM", "Charge de la VM (processeur, mémoire)", vm)
            + jauge("hote", "PC", "Charge de l'ordinateur hôte (processeur, mémoire)", charge_hote()))


LANG_OPTIONS = "".join(f'<option value="{k}">{v[0]}</option>' for k, v in i18n.LANGUES.items())


def shell(active, title, sub, body, flash="", refresh=False, kid=None):
    now = datetime.now()
    theme = getattr(REQ, "theme", themes.DEFAUT)
    police = (f'<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link rel="stylesheet" href="{themes.POLICES[theme]}">'
              if theme in themes.POLICES else "")
    links = "".join(f'<a href="/?p={k}" class="{"on" if k == active else ""}" title="{lab}">{ic(i)}<span>{lab}</span></a>' for k, lab, i in PAGES)
    kid_ok = kid if (kid and kid in USERS) else None
    b_attr = f' class="kid-focus" style="--kid-c:{kid_hex(kid_ok)}"' if kid_ok else ""
    kid_band = '<div class="kid-band" aria-hidden="true"></div>' if kid_ok else ""
    kid_badge = f'<span class="kid-pill">{avatar(kid_ok, "sm")}<span>{e(nom(kid_ok))}</span></span>' if kid_ok else ""
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#1b5c63"><title>MaranYSE · Parents</title><link rel="icon" type="image/png" href="/favicon.png?v={V_IMG}">{police}<style>{CSS}{themes.CSS.get(theme, "")}</style></head>
<body{b_attr}{' data-refresh="1"' if refresh else ''}>{kid_band}<script>try{{if(localStorage.getItem('maranyse-menu')==='replie')document.body.classList.add('menu-replie')}}catch(e){{}}</script><div class="app">
<aside class="side"><button type="button" class="side-tog" id="side-tog" title="Réduire ou agrandir le menu" aria-label="Réduire ou agrandir le menu">{ic("replier", 16)}</button><div class="brand"><a class="brand-l" translate="no" href="/?p=live" title="MaranYSE"><img class="emb" src="/logo-hd.jpg?v={V_IMG}" alt="MaranYSE"></a><small class="brand-sub">Espace parents</small></div>
<nav class="menu">{links}</nav>
<div class="side-foot"><form method="post" data-confirm="Redémarrer le bureau ? Toutes les sessions ouvertes seront fermées." data-yes="Redémarrer">
{hidden(a="restart", back=f"/?p={active}")}<button class="btn ghost block" style="justify-content:flex-start;color:var(--muted)" title="Redémarrer le bureau">{ic("power", 18)}<span>Redémarrer le bureau</span></button></form></div></aside>
<main class="main"><a class="brand-l m-brand" translate="no" href="/?p=live" title="MaranYSE"><img class="emb" src="/logo-petit.jpg?v={V_IMG}" alt=""><img class="wm-img" src="/titre.jpg?v={V_IMG}" alt="MaranYSE"></a><div class="head"><div><div class="row" style="gap:10px"><h1>{title}</h1>{kid_badge}</div><p>{sub}</p></div>
<div class="head-r">{charge_html()}<div class="clock">{ic("clock", 16)} {JOURS[now.weekday()]} {now.day} {MOIS[now.month - 1]} · {now:%H:%M}</div>
<label class="lang" title="Apparence de l'espace parents">{ic("palette", 16)}<select id="theme-sel" aria-label="Apparence">{themes.options(theme)}</select></label>
<label class="lang" title="Langue de l'espace parents">{ic("globe", 16)}<select id="lang-sel" translate="no" aria-label="Langue">{LANG_OPTIONS}</select></label></div></div>{body}</main></div>
<nav class="tabbar">{links}</nav>
<div id="toast" role="status">{ic("check", 18) + e(flash) if flash else ""}</div>
<dialog id="dlg-confirm"><div class="dlg"><h3>Confirmation</h3><p id="cf-text" style="margin:0"></p>
<div class="dlg-foot"><button class="btn" data-close>Annuler</button><button class="btn primary" id="cf-yes">Confirmer</button></div></div></dialog>
<dialog id="dlg-dirty"><div class="dlg"><h3>Modifications non enregistrées</h3><p style="margin:0">Vous avez modifié ce planning sans l'enregistrer. Que voulez-vous faire avant de quitter ?</p>
<div class="dlg-foot" style="flex-wrap:wrap"><button type="button" class="btn" data-close>Annuler</button><button type="button" class="btn danger" id="df-leave">Quitter sans enregistrer</button><button type="button" class="btn primary" id="df-save">{ic("check", 18)} Enregistrer et continuer</button></div></div></dialog>
<script>{JS}</script></body></html>"""


def hidden(**kw):
    return "".join(f'<input type="hidden" name="{k}" value="{e(v)}">' for k, v in kw.items())


def people_tabs(page, cur, extra="", allow_all=False):
    out = ""
    if allow_all:
        out += f'<a href="/?p={page}&s={ALL}{extra}" class="{"on" if cur == ALL else ""}"><span class="av avall av-sm">{ic("users", 15)}</span>Tous les enfants</a>'
    for u in USERS:
        c_ = kid_hex(u)
        st = f' style="border-color:{c_};background:color-mix(in srgb,{c_} 14%,var(--surface));color:var(--text)"' if u == cur else ""
        out += f'<a href="/?p={page}&s={quote(u)}{extra}" class="{"on" if u == cur else ""}"{st}>{avatar(u, "sm")}{e(nom(u))}</a>'
    return f'<div class="people">{out}</div>'


# ======================================================================
# Accueil
# ======================================================================
MODE_IC = {"V": "check", "O": "shield", "R": "ban", "P": "pause"}


def mode_block(u, data, prof, lvl, why, left, c):
    fin = f" · se termine dans {dur(left * 60)}" if left is not None and lvl != "R" else ""
    chips = ""
    if lvl == "O":
        net = prof["internet"]
        chips += f'<span class="chip">{ic("wifioff" if net == "bloque" else "wifi", 14)} Internet {e(INTERNET[net].lower())}</span>'
        for x, used, blocked in orange_status(data, u, c):
            if x["mode"] == "autoriser":
                continue
            n = target(x["cle"])[1].split(" (")[0]
            txt = (f"{n} · {dur(used)}/{x['minutes']} min" if x["mode"] == "limiter" and not blocked else f"{n} bloqué")
            chips += f'<span class="chip">{item_badge(x["cle"], 20)}{e(txt)}</span>'
        chips = f'<div class="chips">{chips}</div>'
    return (f'<div class="mode mode-{lvl}"><span class="mi">{ic(MODE_IC[lvl], 19)}</span><div style="min-width:0">'
            f'<b>{NIVEAU[lvl]}</b><span>{e(why + fin)}</span>{chips}</div></div>')


def day_strip(r):
    now = datetime.now()
    g = normalize_grille_day(r["grille"][str(now.weekday())])
    cur = now.hour * 60 + now.minute
    segs, st, c0 = [], 0, g[0]
    for i in range(1, 1440):
        if g[i] != c0:
            segs.append((st, i, c0))
            st, c0 = i, g[i]
    segs.append((st, 1440, c0))
    fmt = lambda m: f"{m // 60:02d}:{m % 60:02d}"
    cells = "".join(f'<i class="c{m}" style="width:{(b - a) / 14.4:.3f}%" title="{fmt(a)}–{fmt(b)} : {ETAT[m]}"></i>' for a, b, m in segs)
    nowm = f'<span class="now-m" style="left:{cur / 14.4:.3f}%" title="Maintenant ({fmt(cur)})"></span>'
    return (f'<div><div class="label">Planning du jour</div><div class="strip">{cells}{nowm}</div>'
            '<div class="strip-l"><span>0h</span><span>6h</span><span>12h</span><span>18h</span><span>24h</span></div></div>')


QUICK_MSG = ["À table ! 🍽️", "Dans 10 minutes, on arrête.", "Range ta chambre, s'il te plaît.", "Viens me voir, s'il te plaît.", "Bravo, continue comme ça !"]


def kid_dialogs(u, has_session, pw):
    back = "/?p=live"
    msg = ""
    if has_session:
        quick = "".join(f'<button type="button" class="btn sm" data-fill-text="{e(m)}">{e(m)}</button>' for m in QUICK_MSG)
        msg = f"""<dialog id="msg-{u}"><form method="post" class="dlg">{hidden(a="msg", u=u, back=back)}
<h3>{avatar(u, "sm")} Message pour {e(nom(u))}</h3><div class="quick">{quick}</div>
<textarea name="v" placeholder="Votre message, il s'affichera sur son écran" required maxlength="500"></textarea>
<div class="dlg-foot"><button type="button" class="btn" data-close>Annuler</button><button class="btn primary">{ic("msg", 18)} Envoyer</button></div></form></dialog>"""
    close = ""
    if has_session:
        close = f"""<div class="sep"></div>
<div><div class="label">Ou fermer complètement la session</div>
<p class="muted small" style="margin:0 0 8px">Toutes ses applications sont fermées : le travail non enregistré est perdu.</p>
<form method="post" data-confirm="Fermer la session de {e(nom(u))} ? Le travail non enregistré sera perdu." data-yes="Fermer la session">
{hidden(a="logout", u=u, back=back)}<button class="btn block danger">{ic("logout")} Fermer la session maintenant</button></form></div>"""
    pause = f"""<dialog id="pause-{u}"><div class="dlg"><h3>{avatar(u, "sm")} Pause pour {e(nom(u))}</h3>
<div><div class="label">Mettre en pause</div>
<p class="muted small" style="margin:0 0 8px">L'écran est bloqué tout de suite (clavier et souris désactivés). Ses applications restent ouvertes :
il retrouvera tout à la reprise. Le temps de pause n'est pas compté.</p>
<div class="choice">
<form method="post">{hidden(a="pause15", u=u, back=back)}<button class="btn block">{ic("pause")} 15 minutes</button></form>
<form method="post">{hidden(a="pause1h", u=u, back=back)}<button class="btn block">{ic("timer")} 1 heure</button></form>
<form method="post">{hidden(a="pausejour", u=u, back=back)}<button class="btn block">{ic("ban")} Jusqu'à demain 7h</button></form>
</div></div>{close}
<div class="dlg-foot"><button class="btn" data-close>Annuler</button></div></div></dialog>"""
    more_dlg = f"""<dialog id="more-{u}"><div class="dlg"><h3>{avatar(u, "sm")} Compte de {e(nom(u))}</h3>
<div><div class="label">Identifiant</div><code translate="no">{e(u)}</code></div>
<div><div class="label">Mot de passe actuel</div><code style="font-size:16px" translate="no">{e(pw)}</code></div>
<form method="post" class="stack">{hidden(a="pw", u=u, back=back)}<div class="label" style="margin:0">Nouveau mot de passe</div>
<input type="text" name="v" placeholder="4 caractères minimum" required minlength="4">
<div class="dlg-foot"><button type="button" class="btn" data-close>Fermer</button><button class="btn primary">{ic("key", 18)} Changer</button></div></form>
<a href="/?p=comptes" class="small">{ic("users", 15)} Ajouter, renommer ou supprimer des comptes</a></div></dialog>"""
    return msg + pause + more_dlg


def c2_total():
    """Temps d'écran de toute la famille aujourd'hui (secondes)."""
    c = db()
    try:
        return sum(used_today(c, u) for u in USERS)
    finally:
        c.close()


def banniere(total, online, paused_any=False):
    """Bannière d'accueil : emblème MaranYSE, salutation, résumé du jour, enfants en ligne et actions familiales."""
    disp = displays()
    kids = "".join(f'<a class="hero-kid" href="/?p=stats&vue=enfant&s={quote(u)}">{avatar(u, "sm")}<span>{e(nom(u))}</span>'
                   f'<i class="dot{" on" if u in disp else ""}"></i></a>' for u in USERS)
    etat = f"{online} enfant{'s' if online > 1 else ''} en ligne" if online else "Aucun enfant connecté pour le moment"
    fam_btns = ""
    if USERS:
        fam_btns = f'<button type="button" class="btn sm" data-open="pause-_tous">{ic("pause", 15)} Pause tous</button>'
        if paused_any:
            fam_btns += f'<form method="post">{hidden(a="levertous", back="/?p=live")}<button class="btn sm primary">{ic("check", 15)} Reprendre tous</button></form>'
        if disp:
            fam_btns += f'<button type="button" class="btn sm" data-open="msg-_tous">{ic("msg", 15)} Message à tous</button>'
    quick = "".join(f'<button type="button" class="btn sm" data-fill-text="{e(m)}">{e(m)}</button>' for m in QUICK_MSG)
    dlgs = f"""<dialog id="pause-_tous"><div class="dlg"><h3>{ic("users", 20)} Pause pour tous les enfants</h3>
<p class="muted small" style="margin:0">L'écran de tous les enfants est bloqué tout de suite (clavier et souris désactivés). Leurs applications restent ouvertes.</p>
<div class="choice">
<form method="post">{hidden(a="pause15tous", back="/?p=live")}<button class="btn block">{ic("pause")} 15 minutes</button></form>
<form method="post">{hidden(a="pause1htous", back="/?p=live")}<button class="btn block">{ic("timer")} 1 heure</button></form>
<form method="post">{hidden(a="pausejourtous", back="/?p=live")}<button class="btn block">{ic("ban")} Jusqu'à demain 7h</button></form>
</div><div class="dlg-foot"><button class="btn" data-close>Annuler</button></div></div></dialog>
<dialog id="msg-_tous"><form method="post" class="dlg">{hidden(a="msgtous", back="/?p=live")}
<h3>{ic("msg", 20)} Message à tous les enfants connectés</h3><div class="quick">{quick}</div>
<textarea name="v" placeholder="Votre message, il s'affichera sur l'écran de chaque enfant en ligne" required maxlength="500"></textarea>
<div class="dlg-foot"><button type="button" class="btn" data-close>Annuler</button><button class="btn primary">{ic("msg", 18)} Envoyer à tous</button></div></form></dialog>"""
    return (f'<section class="card hero"><div class="hero-t"><p class="hero-st">{etat}</p>'
            f'<p class="hero-tm"><b>{dur(total)}</b> d\'écran aujourd\'hui pour toute la famille</p>'
            f'<div class="hero-kids">{kids}</div>'
            f'{f"<div class=row style=margin-top:12px>{fam_btns}</div>" if fam_btns else ""}</div>'
            f'<img class="hero-ban" src="/banniere.jpg?v={V_IMG}" alt="MaranYSE — One VM, Many Accounts" translate="no"></section>{dlgs}')


def page_live(q, flash=""):
    state = container_state()
    if state != "running":
        body = (f'<div class="card stack"><h2>Les sessions MaranYSE sont arrêtées</h2><p class="muted">État : {e(state)}</p>'
                f'<form method="post">{hidden(a="restart", back="/?p=live")}<button class="btn primary">{ic("power")} Démarrer</button></form></div>')
        return shell("live", "Accueil", "Vue d'ensemble", body, flash)
    act, last, disp, pws = active_connections(), last_sessions(), displays(), passwords()
    with lock:
        data = load_rules()
    c = db()
    cards, online, paused_any = [], 0, False
    for u in USERS:
        s, used = last.get(u), used_today(c, u)
        connected = bool(s and (s["ip"], s["port"]) in act and u in disp)
        online += connected
        lvl, why, left = access(u, data[u], datetime.now(), used)
        if lvl == "P":
            paused_any = True
        prof = profile(data, u, lvl, c)
        if connected:
            pres = f'<span class="dot on"></span>En ligne depuis {fmt_ts(s["ts"])} · {e(s["name"] or s["ip"])}'
        elif u in disp:
            pres = '<span class="dot idle"></span>Session ouverte, déconnecté'
        else:
            pres = '<span class="dot"></span>Hors ligne' + (f' · vu {fmt_ts(s["ts"])}' if s else "")
        now_list = ""
        if u in disp:
            ws = windows(u, disp[u])[:4]
            items = "".join(f'<div class="now-item">{item_badge(wm_item(cl), 26)}'
                            f'<span class="t">{e(t)}</span></div>' for t, cl in ws) or '<div class="muted small">Aucune fenêtre ouverte</div>'
            now_list = f'<div><div class="label">En ce moment</div><div class="now-list">{items}</div></div>'
        top = c.execute("SELECT app, SUM(sec) s FROM usage WHERE day=? AND user=? AND app!=? GROUP BY app ORDER BY s DESC LIMIT 1",
                        (today(), u, IDLE)).fetchone()
        kpis = (f'<div class="kpis"><div class="kpi"><b>{dur(used)}</b><span>d\'écran aujourd\'hui</span></div>'
                + (f'<div class="kpi"><b>{e(top[0])}</b><span>le plus utilisé ({dur(top[1])})</span></div>' if top else "") + "</div>")
        sess_btns = (f'<button class="btn sm" data-open="msg-{u}">{ic("msg", 16)} Message</button>' if u in disp else "")
        logout_btn = (f'<form method="post" data-confirm="Fermer la session de {e(nom(u))} ? Le travail non enregistré sera perdu." data-yes="Fermer la session">'
                      f'{hidden(a="logout", u=u, back="/?p=live")}<button class="btn sm danger">{ic("logout", 16)} Déconnecter</button></form>' if u in disp else "")
        if lvl == "P":
            pause_btn = (f'<form method="post">{hidden(a="lever", u=u, back="/?p=live")}'
                         f'<button class="btn sm primary">{ic("check", 16)} Reprendre maintenant</button></form>')
        else:
            pause_btn = f'<button class="btn sm" data-open="pause-{u}">{ic("pause", 16)} Pause</button>'
        bonus_btn = ("" if lvl == "P" else
                     f'<form method="post">{hidden(a="bonus", u=u, back="/?p=live")}<button class="btn sm" title="30 minutes d\'accès complet">{ic("plus", 16)} 30 min</button></form>')
        actions = (f'<div class="kid-actions">{pause_btn}{sess_btns}{bonus_btn}{logout_btn}'
                   f'<button class="btn sm ghost icon" data-open="more-{u}" title="Compte et mot de passe" style="margin-left:auto">{ic("more", 18)}</button></div>')
        cards.append(f'<section class="card kid"><div class="kid-head">{avatar(u, "lg")}<div><h2>{e(nom(u))}</h2>'
                     f'<div class="presence">{pres}</div></div></div>{mode_block(u, data, prof, lvl, why, left, c)}{kpis}'
                     f'{now_list}{day_strip(data[u])}{actions}{kid_dialogs(u, u in disp, pws.get(u, ""))}</section>')
    c.close()
    sub = f"{online} enfant{'s' if online > 1 else ''} en ligne" if online else "Aucun enfant connecté pour le moment"
    return shell("live", "Accueil", sub, banniere(c2_total(), online, paused_any) + f'<div class="grid">{"".join(cards)}</div>', flash, refresh=True)


# ======================================================================
# Planning
# ======================================================================
TEMPLATES = {
    "ecole": ("École", "Lun–ven : 7h–8h vert, 16h–18h orange, 18h–19h30 vert, 19h30–20h30 orange. Week-end plus large.",
              ["R" * 14 + "V" * 2 + "R" * 16 + "O" * 4 + "V" * 3 + "O" * 2 + "R" * 7] * 5 +
              ["R" * 16 + "O" * 8 + "V" * 4 + "O" * 10 + "V" * 3 + "R" * 7] * 2),
    "vacances": ("Vacances", "Tous les jours : 8h30–12h orange, 12h–13h30 vert, 13h30–18h orange, 18h–21h vert.",
                 ["R" * 17 + "O" * 7 + "V" * 3 + "O" * 9 + "V" * 6 + "R" * 6] * 7),
    "vert": ("Tout vert", "Aucune restriction, à toute heure.", ["V" * 48] * 7),
    "orange": ("Tout orange", "Toujours avec les règles de l'orange.", ["O" * 48] * 7),
    "rouge": ("Tout rouge", "Aucun accès, à toute heure.", ["R" * 48] * 7),
}


def planning_grid(r):
    now = datetime.now()
    cur_q = (now.weekday(), (now.hour * 60 + now.minute) // 15)
    head = "<thead><tr><th></th>" + "".join(f'<th class="{"today" if d == now.weekday() else ""}">{j[:3]}</th>' for d, j in enumerate(JOURS)) + "</tr></thead>"
    grilles = {d: normalize_grille_day(r["grille"][str(d)]) for d in range(7)}
    rows = []
    for q in range(96):
        m0 = q * 15
        cells = "".join(
            f'<td class="c{grilles[d][m0]}{" now" if (d, q) == cur_q else ""}" data-d="{d}" data-q="{q}"></td>' for d in range(7))
        lbl = f"{m0 // 60:02d}:00" if q % 4 == 0 else ""
        rows.append(f"<tr{' class=h' if q % 4 == 0 else ''}><th>{lbl}</th>{cells}</tr>")
    quota = ('<tr class="q"><th>Écran<br>max/jour<br>(min)</th>' +
             "".join(f'<td><input type="number" min="0" max="1440" step="1" name="quota_{d}" value="{int(r["quota"].get(str(d)) or 0)}" '
                     f'title="Temps d\'écran maximum le {JOURS[d]} (0 = pas de limite)"></td>' for d in range(7)) + "</tr>")
    hid = "".join(f'<input type="hidden" name="grille_{d}" value="{grilles[d]}">' for d in range(7))
    tpl = json.dumps({k: [normalize_grille_day(x) for x in v[2]] for k, v in TEMPLATES.items()})
    tpl_btns = "".join(f'<button type="button" class="btn sm" data-tpl="{k}" title="{e(v[1])}">{ic("sparkle", 15)} {e(v[0])}</button>' for k, v in TEMPLATES.items())
    day_pills = "".join(f'<a href="#" class="{"on" if d == now.weekday() else ""}" data-mday="{d}">{JOURS[d][:3]}</a>' for d in range(7))
    return f"""
<div class="between" style="gap:10px">
 <div class="seg" id="pg-pas" title="Pas d'affichage du planning">
  <a href="#" class="on" data-pas="15">Pas : 15 min</a>
  <a href="#" data-pas="1">Pas : À la minute</a>
 </div>
 <div class="row"><span class="muted small">Modèles :</span>{tpl_btns}</div>
</div>
<div class="brushes" id="pg-brushes">
 <button type="button" class="brush on" data-b="V"><i class="cV"></i><div><b>Vert</b><small>Accès complet</small></div></button>
 <button type="button" class="brush" data-b="O"><i class="cO"></i><div><b>Orange</b><small>Accès avec les règles</small></div></button>
 <button type="button" class="brush" data-b="R"><i class="cR"></i><div><b>Rouge</b><small>Pas d'accès</small></div></button>
</div>
<div class="between"><span class="muted small" id="pg-hint">Choisissez une couleur, puis cliquez ou glissez sur les cases (1 case = 15 min).</span>
<div class="row"><button type="button" class="btn sm" data-copy="0:0-4">Copier lundi → lun–ven</button>
<button type="button" class="btn sm" data-copy="5:6">Copier samedi → dimanche</button></div></div>
<div id="pg-view-15"><div class="pgw"><table class="pg" id="pg">{head}<tbody>{''.join(rows)}{quota}</tbody></table></div></div>
<div id="pg-view-1" class="stack" style="display:none">
 <div class="between"><div class="chips2" id="pg-mdays">{day_pills}</div>
  <div class="row small"><span class="muted">Écran max ce jour</span><input type="number" id="pg-mquota" min="0" max="1440" step="1" style="width:78px;text-align:center"><span class="muted">min</span></div></div>
 <div><div class="strip" id="pg-mstrip" style="height:18px;border-radius:7px"></div>
  <div class="strip-l"><span>0h</span><span>6h</span><span>12h</span><span>18h</span><span>24h</span></div></div>
 <div class="stack" id="pg-msegs" style="gap:8px"></div>
 <div class="pg-seg-add">
  <label>De<input type="time" id="pg-mfrom" value="18:00"></label>
  <label>À<input type="time" id="pg-mto" value="18:30"></label>
  <label>Accès<select id="pg-mmode"><option value="V">Vert (accès complet)</option><option value="O">Orange (règles)</option><option value="R">Rouge (pas d'accès)</option></select></label>
  <button type="button" class="btn sm primary" id="pg-madd">{ic("plus", 15)} Insérer cette plage</button>
 </div>
</div>
{hid}
<script>(()=>{{const t=document.getElementById('pg');let b='V',down=false,pas='15',mday={now.weekday()};const T={tpl};
const DAYS={json.dumps(JOURS)},COL={{V:'var(--g)',O:'var(--o)',R:'var(--r)'}},LAB={{V:'accès complet',O:'accès restreint',R:'pas d\\x27accès'}};
const dirty=()=>{{const bar=document.querySelector('.savebar');if(bar)bar.classList.add('is-dirty')}};
const inp=d=>document.querySelector('input[name=grille_'+d+']');
const qinp=d=>document.querySelector('input[name=quota_'+d+']');
const get=d=>inp(d).value;
const set=(d,s)=>{{inp(d).value=s}};
const toHHMM=m=>String(Math.floor(m/60)).padStart(2,'0')+':'+String(m%60).padStart(2,'0');
const fromHHMM=s=>{{const p=s.split(':');return (+p[0]||0)*60+(+p[1]||0)}};
const fill=(d,a,z,c)=>{{let s=get(d).split('');for(let i=Math.max(0,a);i<Math.min(1440,z);i++)s[i]=c;set(d,s.join(''))}};
const segsOf=d=>{{const s=get(d),out=[];let st=0,c=s[0];for(let i=1;i<1440;i++)if(s[i]!==c){{out.push({{a:st,b:i,c}});st=i;c=s[i]}}out.push({{a:st,b:1440,c}});return out}};
const renderGrid=()=>{{for(let d=0;d<7;d++){{const s=get(d);t.querySelectorAll('td[data-d="'+d+'"]').forEach(td=>{{
 const q=+td.dataset.q,m0=q*15,sub=s.slice(m0,m0+15),c0=sub[0];let same=true;for(let i=1;i<15;i++)if(sub[i]!==c0){{same=false;break}}
 td.className=td.className.replace(/c[VOR]/,'c'+c0);
 if(same){{td.style.background='';td.title=DAYS[d]+' '+toHHMM(m0)+'–'+toHHMM(m0+15)+' : '+LAB[c0]}}
 else{{let p=1;while(p<15&&sub[p]===c0)p++;const pct=Math.round(p/15*100);
  td.style.background='linear-gradient(135deg,'+COL[c0]+' '+pct+'%,'+COL[sub[14]]+' '+pct+'%)';
  td.title=DAYS[d]+' '+toHHMM(m0)+'–'+toHHMM(m0+15)+' : affiné à la minute'}}}})}}}};
const renderMin=()=>{{
 document.querySelectorAll('#pg-mdays a').forEach(a=>a.classList.toggle('on',+a.dataset.mday===mday));
 const mq=document.getElementById('pg-mquota');mq.value=qinp(mday).value;
 mq.oninput=()=>{{qinp(mday).value=Math.max(0,Math.min(1440,+mq.value||0));dirty()}};
 const segs=segsOf(mday);
 document.getElementById('pg-mstrip').innerHTML=segs.map(s=>'<i class="c'+s.c+'" style="width:'+((s.b-s.a)/14.4).toFixed(3)+'%" title="'+toHHMM(s.a)+'–'+toHHMM(s.b)+' : '+LAB[s.c]+'"></i>').join('');
 const box=document.getElementById('pg-msegs');
 box.innerHTML=segs.map((s,i)=>'<div class="pg-seg"><div class="row"><i class="c'+s.c+'" style="width:14px;height:14px;border-radius:4px;display:inline-block"></i>'
  +'<b>'+toHHMM(s.a)+' → '+(s.b===1440?'24:00':toHHMM(s.b))+'</b><span class="muted small">('+(s.b-s.a)+' min)</span></div>'
  +'<div class="row"><select data-sm="'+i+'"><option value="V"'+(s.c==='V'?' selected':'')+'>Vert</option><option value="O"'+(s.c==='O'?' selected':'')+'>Orange</option><option value="R"'+(s.c==='R'?' selected':'')+'>Rouge</option></select>'
  +(s.b<1440?'<button type="button" class="btn sm" data-sn="'+i+':-1">−1m</button><input type="time" data-se="'+i+'" value="'+toHHMM(s.b)+'"><button type="button" class="btn sm" data-sn="'+i+':1">+1m</button>':'<span class="muted small">fin</span>')
  +'</div></div>').join('');
 box.querySelectorAll('[data-sm]').forEach(el=>el.onchange=()=>{{const s=segs[+el.dataset.sm];fill(mday,s.a,s.b,el.value);dirty();renderAll()}});
 box.querySelectorAll('[data-sn]').forEach(el=>el.onclick=()=>{{const[i,d]=el.dataset.sn.split(':').map(Number),s=segs[i],nx=segs[i+1];
  const nb=Math.max(s.a+1,Math.min((nx?nx.b:1440)-1,s.b+d));
  if(nb>s.b)fill(mday,s.b,nb,s.c);else if(nb<s.b&&nx)fill(mday,nb,s.b,nx.c);dirty();renderAll()}});
 box.querySelectorAll('[data-se]').forEach(el=>el.onchange=()=>{{const i=+el.dataset.se,s=segs[i],nx=segs[i+1];
  const nb=Math.max(s.a+1,Math.min((nx?nx.b:1440)-1,fromHHMM(el.value)));
  if(nb>s.b)fill(mday,s.b,nb,s.c);else if(nb<s.b&&nx)fill(mday,nb,s.b,nx.c);dirty();renderAll()}})}};
const renderAll=()=>{{renderGrid();if(pas==='1')renderMin()}};
document.querySelectorAll('.brush').forEach(x=>x.onclick=()=>{{b=x.dataset.b;document.querySelectorAll('.brush').forEach(y=>y.classList.toggle('on',y===x))}});
const paint=td=>{{if(td&&td.dataset.d!==undefined){{const d=+td.dataset.d,q=+td.dataset.q;fill(d,q*15,(q+1)*15,b);dirty();renderGrid()}}}};
t.addEventListener('pointerdown',ev=>{{const td=ev.target.closest('td[data-d]');if(!td)return;down=true;ev.preventDefault();paint(td)}});
t.addEventListener('pointermove',ev=>{{if(down){{const el=document.elementFromPoint(ev.clientX,ev.clientY);paint(el&&el.closest('td[data-d]'))}}}});
addEventListener('pointerup',()=>down=false);addEventListener('pointercancel',()=>down=false);
t.addEventListener('input',dirty);
document.querySelectorAll('#pg-mdays a').forEach(a=>a.onclick=ev=>{{ev.preventDefault();mday=+a.dataset.mday;renderMin()}});
document.getElementById('pg-madd').onclick=()=>{{const a=fromHHMM(document.getElementById('pg-mfrom').value),z=fromHHMM(document.getElementById('pg-mto').value),m=document.getElementById('pg-mmode').value;
 if(z>a){{fill(mday,a,z,m);dirty();renderAll()}}}};
const setPas=p=>{{pas=p;document.querySelectorAll('#pg-pas a').forEach(a=>a.classList.toggle('on',a.dataset.pas===p));
 document.getElementById('pg-view-15').style.display=p==='15'?'':'none';document.getElementById('pg-view-1').style.display=p==='1'?'':'none';
 document.getElementById('pg-brushes').style.display=p==='15'?'':'none';
 document.getElementById('pg-hint').textContent=p==='15'?'Choisissez une couleur, puis cliquez ou glissez sur les cases (1 case = 15 min).':'Affinez les plages horaires de chaque jour à la minute près (HH:MM).';
 try{{localStorage.setItem('maranyse-plan-pas',p)}}catch(e){{}}renderAll()}};
document.querySelectorAll('#pg-pas a').forEach(a=>a.onclick=ev=>{{ev.preventDefault();setPas(a.dataset.pas)}});
document.querySelectorAll('[data-copy]').forEach(x=>x.onclick=()=>{{const[src,dst]=x.dataset.copy.split(':');const[a,z]=dst.split('-');
 const s=get(src),q=qinp(src).value;for(let d=+a;d<=+(z??a);d++){{set(d,s);qinp(d).value=q}}dirty();renderAll()}});
document.querySelectorAll('[data-tpl]').forEach(x=>x.onclick=()=>{{T[x.dataset.tpl].forEach((s,d)=>set(d,s));dirty();renderAll()}});
try{{const saved=localStorage.getItem('maranyse-plan-pas');if(saved==='1'||saved==='15')setPas(saved);else renderAll()}}catch(e){{renderAll()}}
}})()</script>"""


def page_planning(q, flash=""):
    u = q.get("s", q.get("u", [getattr(REQ, "kid", None) or USERS[0]]))[0]
    u = u if u in USERS else USERS[0]
    with lock:
        data = load_rules()
    c = db()
    lvl, why, left = access(u, data[u], datetime.now(), used_today(c, u))
    prof = profile(data, u, lvl, c)
    status = mode_block(u, data, prof, lvl, why, left, c)
    c.close()
    body = f"""{people_tabs("planning", u)}
<div class="legend card" style="padding:10px;margin-bottom:16px">
<div style="background:var(--green-soft)"><i class="cV"></i><span><b>Vert</b> · accès complet, aucune restriction</span></div>
<div style="background:var(--orange-soft)"><i class="cO"></i><span><b>Orange</b> · accès avec les <a href="/?p=regles&s={quote(u)}">règles</a></span></div>
<div style="background:var(--red-soft)"><i class="cR"></i><span><b>Rouge</b> · pas d'accès à la session</span></div></div>
<form method="post">{hidden(a="planning", u=u)}
<section class="card stack kid-card"><div class="between"><div class="row">{avatar(u)}<div><h2>Semaine de {e(nom(u))}</h2>
<span class="muted small">La case encadrée correspond à maintenant</span></div></div><div style="max-width:420px;flex:1">{status}</div></div>
{planning_grid(data[u])}
<p class="muted small" style="margin:0">La dernière ligne limite le temps d'écran total de la journée (0 = pas de limite). Un avertissement s'affiche 5 minutes avant chaque fin d'accès.</p></section>
<div class="savebar"><span><span class="dirty">● Modifications non enregistrées</span></span>
<div class="row"><a class="btn" href="/?p=planning&s={quote(u)}">Annuler</a>
<button type="submit" name="tous" value="1" class="btn" onclick="return confirm('Appliquer ce planning et ces limites à tous les enfants ?')">{ic("users", 18)} Appliquer à tous</button>
<button class="btn primary">{ic("check", 18)} Enregistrer</button></div></div></form>"""
    return shell("planning", "Planning", "Quand chaque enfant peut utiliser son bureau", body, flash, kid=u)


# ======================================================================
# Règles de l'orange
# ======================================================================
def rule_dialog(scope):
    sites = "".join(f'<label class="tile"><input type="radio" name="cle" value="site:{k}" {"checked" if i == 0 else ""}><span>{item_badge("site:" + k, 28)}{e(v[0])}</span></label>'
                    for i, (k, v) in enumerate(SITES.items()))
    sites += f'<label class="tile"><input type="radio" name="cle" value="dom:"><span>{item_badge("dom:x", 28)}Autre site…</span></label>'
    apps = "".join(f'<label class="tile"><input type="radio" name="cle" value="app:{k}"><span>{item_badge("app:" + k, 28)}{e(v[0].split(" (")[0])}</span></label>'
                   for k, v in APPS.items())
    who = "tous les enfants" if scope == ALL else nom(scope)
    allow = ('' if scope == ALL else f'<label><input type="radio" name="mode" value="autoriser"><span>{ic("check", 16)} Autoriser</span></label>')
    return f"""<dialog id="add-{scope}" class="rule-dlg"><form method="post" class="dlg">{hidden(a="addrule", s=scope)}
<h3>{ic("shield", 22)} Règle pour {e(who)}</h3>
<div><div class="label">1 · Quoi ?</div><div class="tiles">{sites}</div>
<div class="dom" style="margin-top:8px"><input type="text" name="dom" placeholder="Adresse du site, ex. minecraft.net"></div>
<div class="label" style="margin-top:12px">Applications</div><div class="tiles">{apps}</div></div>
<div><div class="label">2 · Quelle règle en orange ?</div><div class="seg">
<label><input type="radio" name="mode" value="bloquer" checked><span>{ic("ban", 16)} Bloquer</span></label>
<label><input type="radio" name="mode" value="limiter"><span>{ic("timer", 16)} Limiter</span></label>{allow}</div>
{'<div class="muted small" style="margin-top:6px">« Autoriser » fait une exception à une règle commune.</div>' if scope != ALL else ''}</div>
<div class="mins"><div class="label">3 · Combien de temps par jour ?</div>
<div class="range"><input type="range" min="1" max="240" step="1" value="60" aria-label="Durée par jour">
<button type="button" class="btn sm min-step" data-d="-1" title="1 minute en moins">−</button>
<input type="number" class="min-num" name="minutes" min="1" max="1440" step="1" value="60" aria-label="Minutes par jour">
<button type="button" class="btn sm min-step" data-d="1" title="1 minute en plus">+</button>
<output>1 h</output></div>
<div class="quick" style="margin-top:8px">
<button type="button" class="btn sm min-quick" data-v="5">5 min</button>
<button type="button" class="btn sm min-quick" data-v="15">15 min</button>
<button type="button" class="btn sm min-quick" data-v="30">30 min</button>
<button type="button" class="btn sm min-quick" data-v="60">1 h</button>
<button type="button" class="btn sm min-quick" data-v="120">2 h</button></div></div>
<div class="dlg-foot"><button type="button" class="btn" data-close>Annuler</button><button class="btn primary">{ic("check", 18)} Enregistrer la règle</button></div>
</form></dialog>"""


def rule_card(scope, x, used=None, inherited=False, overrides=False):
    t = target(x["cle"])
    kind = "Application" if t[0] == "app" else "Site web"
    src = ""
    if scope != ALL:
        src = " · <span class='pill' style='padding:1px 8px'>règle commune</span>" if inherited else (" · remplace la règle commune" if overrides else "")
    if x["mode"] == "limiter":
        lim = int(x["minutes"])
        st = f'<span class="pill o">{ic("timer", 14)} {dur(lim * 60)} / jour</span>'
        if used is not None:
            pct = min(100, 100 * used / 60 / lim)
            st += f'<div style="width:120px"><div class="meter"><i class="{"full" if pct >= 100 else ""}" style="width:{pct:.0f}%"></i></div></div><span class="muted small">{dur(used)} aujourd\'hui</span>'
    elif x["mode"] == "bloquer":
        st = f'<span class="pill r">{ic("ban", 14)} Bloqué</span>'
    else:
        st = f'<span class="pill g">{ic("check", 14)} Autorisé</span>'
    pre = e(json.dumps({"cle": x["cle"], "mode": x["mode"], "minutes": x.get("minutes") or 60}))
    if inherited:
        acts = f'<button class="btn sm" data-open="add-{scope}" data-preset="{pre}" title="Créer une règle différente pour {e(nom(scope))}">{ic("edit", 15)} Personnaliser</button>'
    else:
        acts = (f'<button class="btn sm ghost icon" data-open="add-{scope}" data-preset="{pre}" title="Modifier">{ic("edit", 17)}</button>'
                f'<form method="post" data-confirm="Supprimer la règle « {e(t[1])} » ?" data-yes="Supprimer">{hidden(a="delrule", s=scope, cle=x["cle"])}'
                f'<button class="btn sm ghost icon danger" title="Supprimer">{ic("trash", 17)}</button></form>')
    return (f'<div class="rule{" inh" if inherited else ""}">{item_badge(x["cle"], 40)}<div class="nm"><b>{e(t[1])}</b><small>{kind}{src}</small></div>'
            f'<div class="st">{st}</div><div class="row" style="flex-wrap:nowrap">{acts}</div></div>')


NET_OPTS = [("libre", "wifi", "Libre", "Internet normal, sauf les sites bloqués"),
            ("filtre", "shield", "Filtré", "Sites adultes et dangereux bloqués"),
            ("bloque", "wifioff", "Coupé", "Aucun accès à internet")]


def secu_card(scope, data):
    """Réglages des contournements : Autoriser / Interdire (+ « Comme tous » pour un enfant)."""
    g = data[ALL]["securite"]
    rows = ""
    for k, (titre, expl, par_enfant) in SECU.items():
        if scope != ALL and not par_enfant:
            etat = SECU_VAL[g[k]]
            rows += (f'<div class="rule inh"><span class="item" style="--c:#64748b;width:40px;height:40px">{ic("app", 22)}</span>'
                     f'<div class="nm"><b>{e(titre)}</b><small>{e(expl)} Réglé pour tous les enfants : '
                     f'<a href="/?p=regles&s={ALL}">{e(etat.lower())}</a>.</small></div></div>')
            continue
        cur = g[k] if scope == ALL else data[scope]["securite"].get(k, "herite")
        choix = ([("herite", "users", f"Comme tous ({SECU_VAL[g[k]].lower()})")] if scope != ALL else []) + [("interdit", "ban", "Interdire"), ("autorise", "check", "Autoriser")]
        radios = "".join(f'<label><input type="radio" name="v" value="{v}" {"checked" if v == cur else ""}><span>{ic(i, 15)} {e(lab)}</span></label>'
                         for v, i, lab in choix)
        rows += (f'<div class="rule"><span class="item" style="--c:{"#e0464b" if secu(data, scope, k) == "interdit" else "#1f9d55"};width:40px;height:40px">'
                 f'{ic("ban" if secu(data, scope, k) == "interdit" else "check", 22)}</span>'
                 f'<div class="nm"><b>{e(titre)}</b><small>{e(expl)}</small></div>'
                 f'<form method="post" data-auto>{hidden(a="secu", s=scope, k=k)}<div class="seg">{radios}</div></form></div>')
    who = "tous les enfants" if scope == ALL else nom(scope)
    garanti = "".join(f'<li>{ic("check", 14)} <span><b>{e(t)}</b> {e(x)}</span></li>' for t, x in GARANTIS)
    return (f'<section class="card stack"><div><h2>{ic("shield", 20)} Contournements</h2>'
            f'<span class="muted small">Pour {e(who)} · s’applique à toute heure (vert et orange). Changement pris en compte en moins de 30 secondes. '
            f'Les outils (Python, VS Code, terminal…) ne sont jamais bloqués : ce qui empêche de contourner est réglé ici et par l’administrateur.</span></div>'
            f'<div class="rules">{rows}</div>'
            f'<div class="garanti"><b>{ic("lock", 15)} Toujours actif, impossible à changer par un enfant</b><ul>{garanti}</ul></div></section>')


# Protections permanentes (rien à régler) : affichées sous les réglages de contournement
GARANTIS = [
    ("VPN, Tor, proxys, tunnels :", "refusés à l’installation de logiciels, et sans internet de toute façon tant que « Internet pour les autres programmes » est interdit."),
    ("Programmes ouverts depuis Firefox :", "ils n’ont pas l’accès internet de Firefox (« Ouvrir avec… », liens vers une application)."),
    ("Firefox verrouillé :", "pas d’extensions, de proxy, de navigation privée, d’about:config ni de DNS sécurisé ; DNS extérieurs redirigés vers le filtre."),
    ("Terminal, VS Code, Python :", "ils ne donnent aucun droit de plus que le compte de l’enfant : pas d’administrateur, pas d’accès aux fichiers des autres, applications bloquées toujours bloquées."),
]


def page_regles(q, flash=""):
    scope = q.get("s", [getattr(REQ, "kid", None) or ALL])[0]
    scope = scope if scope in USERS or scope == ALL else ALL
    with lock:
        data = load_rules()
    c = db()
    g = data[ALL]
    opts = ([("herite", "users", "Comme tous", f"Suit la règle commune ({INTERNET[g['internet']].lower()})")] if scope != ALL else []) + NET_OPTS
    cur = data[scope]["internet"] if scope != ALL else g["internet"]
    net = "".join(f'<label class="opt"><input type="radio" name="v" value="{k}" {"checked" if k == cur else ""}>'
                  f'<span><b>{ic(i, 18)} {e(lab)}</b><small>{e(hint)}</small></span></label>' for k, i, lab, hint in opts)
    if scope == ALL:
        cards = "".join(rule_card(ALL, x) for x in g["regles"])
        title, who = "Règles communes", "tous les enfants"
        intro = "Ces règles s'appliquent à chaque enfant pendant ses heures orange. Une règle individuelle sur le même site ou la même application les remplace."
    else:
        st = {x["cle"]: used for x, used, _ in orange_status(data, scope, c)}
        own = {x["cle"] for x in data[scope]["regles"]}
        gk = {x["cle"] for x in g["regles"]}
        cards = "".join(rule_card(scope, x, st.get(x["cle"]), overrides=x["cle"] in gk) for x in data[scope]["regles"])
        cards += "".join(rule_card(scope, x, st.get(x["cle"]), inherited=True) for x in g["regles"] if x["cle"] not in own)
        title, who = f"Règles de {nom(scope)}", nom(scope)
        intro = f"Ce qui s'applique à {nom(scope)} pendant ses heures orange : les règles communes (en pointillés) et ses règles personnelles."
    cards = cards or '<div class="empty">Aucune restriction pour le moment.<br>Cliquez sur « Ajouter une règle » pour commencer.</div>'
    c.close()
    kc = " kid-card" if scope != ALL else ""
    body = f"""{people_tabs("regles", scope, allow_all=True)}
<div class="legend card" style="padding:10px;margin-bottom:16px">
<div style="background:var(--green-soft)"><i class="cV"></i><span><b>Vert</b> · aucune restriction</span></div>
<div style="background:var(--orange-soft)"><i class="cO"></i><span><b>Orange</b> · les règles ci-dessous s'appliquent</span></div>
<div style="background:var(--red-soft)"><i class="cR"></i><span><b>Rouge</b> · pas d'accès à la session</span></div></div>
<div class="stack">
<section class="card stack{kc}"><div><h2>{ic("globe", 20)} Internet pendant l'orange</h2><span class="muted small">Pour {e(who)}</span></div>
<form method="post" data-auto>{hidden(a="internet", s=scope)}<div class="opts">{net}</div></form></section>
<section class="card stack{kc}"><div class="between"><div><h2>{ic("app", 20)} {e(title)}</h2><span class="muted small">{e(intro)}</span></div>
<button class="btn primary" data-open="add-{scope}">{ic("plus", 18)} Ajouter une règle</button></div>
<div class="rules">{cards}</div>
<p class="muted small" style="margin:0">Les durées limitées sont comptées sur toute la journée (le temps passé en vert compte aussi). Le temps sur un site est mesuré d'après l'onglet Firefox au premier plan.</p></section>
{secu_card(scope, data)}
</div>{rule_dialog(scope)}"""
    return shell("regles", "Règles", "Ce qui est permis pendant les heures orange", body, flash, kid=None if scope == ALL else scope)


# ======================================================================
# Statistiques & Aide (déléguées aux modules stats.py et aide.py)
# ======================================================================
def page_stats(q):
    default_vue = "enfant" if (getattr(REQ, "kid", None) and "s" not in q) or "s" in q else "ensemble"
    vue = q.get("vue", [default_vue])[0]
    vue = vue if vue in ("ensemble", "enfant", "app") else "ensemble"
    if vue == "enfant" and "s" not in q and getattr(REQ, "kid", None):
        q = {**q, "s": [REQ.kid]}
    per = q.get("per", ["7"])[0]
    per = per if per in ("1", "7", "30") else "7"
    days = int(per)
    start = (datetime.now().date() - timedelta(days=days - 1)).isoformat()
    d = pick_day(q)
    c = db()
    vue_tabs = "".join(f'<a class="{"on" if k == vue else ""}" href="/?p=stats&vue={k}&per={per}&d={d}">{ic(i, 16)} {lab}</a>'
                       for k, lab, i in (("ensemble", "Ensemble", "chart"), ("enfant", "Par enfant", "users"), ("app", "Par application", "app")))
    fn = {"ensemble": stats_ensemble, "enfant": stats_enfant, "app": stats_app}[vue]
    body, sub, params = fn(q, c, per, days, start, d, people_tabs)
    c.close()
    per_tabs = "".join(f'<a class="{"on" if k == per else ""}" href="{url(params, per=k, d=d, mesure=q.get("mesure", [""])[0])}">{v}</a>'
                       for k, v in (("1", "Aujourd'hui"), ("7", "7 jours"), ("30", "30 jours")))
    head = (f'<div class="stats-bar"><div class="seg">{vue_tabs}</div>'
            f'<div class="seg" title="Période des chiffres et graphiques">{per_tabs}</div></div>')
    return shell("stats", "Statistiques", sub, head + body, kid=params.get("s") if vue == "enfant" else None)


def page_aide(host=""):
    return render_aide(host, V_IMG, shell)


# ======================================================================
# Comptes
# ======================================================================
def langue_session(u):
    """Langue de la session ouverte de l'enfant (lue dans l'environnement de son bureau), ou None."""
    out = dx(f"p=$(pgrep -u {u} -x xfce4-panel | head -1); [ -n \"$p\" ] && tr '\\0' '\\n' < /proc/$p/environ | grep '^LANG='", user=u)
    loc = out.strip().partition("=")[2].split(".")[0]
    return next((k for k, v in i18n.LANGUES.items() if v[1].split(".")[0] == loc), None) if loc else None


def lang_opts(cur):
    return "".join(f'<option value="{k}"{" selected" if k == cur else ""}>{v[0]}</option>' for k, v in i18n.LANGUES.items())


def page_comptes(q, flash=""):
    state = container_state()
    if state != "running":
        body = (f'<div class="card stack"><h2>Les sessions MaranYSE sont arrêtées</h2><p class="muted">Démarrez-les pour gérer les comptes.</p>'
                f'<form method="post">{hidden(a="restart", back="/?p=comptes")}<button class="btn primary">{ic("power")} Démarrer</button></form></div>')
        return shell("comptes", "Comptes", "Comptes des enfants", body, flash)
    load_accounts()
    pws, disp = passwords(), displays()
    regles = load_rules()
    back = "/?p=comptes"
    off = 'disabled title="Il faut garder au moins un compte"' if len(USERS) == 1 else ""
    cards = []
    for u in USERS:
        pres = '<span class="dot on"></span>Session ouverte' if u in disp else '<span class="dot"></span>Pas de session ouverte'
        attente = ""
        if u in disp:
            ls = langue_session(u)
            voulue = regles[u].get("langue", "fr")
            if ls and ls != voulue:
                attente = (f'<form method="post" class="row small" data-confirm="Fermer la session de {e(nom(u))} pour passer son bureau en '
                           f'{e(i18n.LANGUES[voulue][0])} ? Le travail non enregistré sera perdu." data-yes="Fermer et appliquer">'
                           f'{hidden(a="logout", u=u, back=back)}<span class="pill o">{ic("clock", 14)} Bureau encore en '
                           f'<span translate="no">{e(i18n.LANGUES[ls][0])}</span> : nouvelle langue à sa prochaine connexion</span>'
                           f'<button class="btn sm">{ic("power", 16)} Appliquer maintenant</button></form>')
        delete = (f'<button class="btn sm danger" data-open="del-{u}" {off}>'
                  f'{ic("trash", 16)} Supprimer</button>')
        col_cur = kid_hex(u, regles)
        swatches = "".join(
            f'<button type="submit" name="v" value="{c_}" class="color-dot{" on" if c_ == col_cur else ""}" '
            f'style="background:{c_}" title="Choisir cette couleur" aria-label="Couleur {c_}"></button>'
            for c_ in KID_PALETTE)
        cards.append(f"""<section class="card stack" style="border-right:5px solid {col_cur}"><div class="acc">{avatar(u, "lg")}<div class="nm"><h3>{e(nom(u))}</h3>
<div class="presence">{pres}</div></div>
<div class="row"><button class="btn sm" data-open="edit-{u}">{ic("edit", 16)} Modifier</button>{delete}</div></div>
<div class="row small"><span class="muted">Identifiant</span> <code translate="no">{e(u)}</code>
<span class="muted" style="margin-left:10px">Mot de passe</span> <code translate="no">{e(pws.get(u, "?"))}</code></div>
<div class="row small"><span class="muted row" style="gap:6px">{ic("palette", 16)} Couleur</span>
<form method="post" class="color-sw">{hidden(a="couleur", u=u, back=back)}{swatches}</form>
<form method="post" class="row" style="gap:4px">{hidden(a="couleur", u=u, back=back)}<input type="color" name="v" value="{col_cur}" class="color-pick" onchange="this.form.submit()" title="Autre couleur"></form></div>
<form method="post" class="row small">{hidden(a="langue", u=u, back=back)}<span class="muted row" style="gap:6px">{ic("globe", 16)} Langue du bureau</span>
<select name="v" data-submit translate="no" style="width:auto">{lang_opts(regles[u].get("langue", "fr"))}</select></form>{attente}
<dialog id="edit-{u}"><div class="dlg"><h3>{avatar(u, "sm")} Modifier le compte de {e(nom(u))}</h3>
<form method="post" class="stack">{hidden(a="rename", u=u, back=back)}<div class="label" style="margin:0">Prénom affiché</div>
<div class="row" style="flex-wrap:nowrap"><input type="text" name="v" value="{e(nom(u))}" required maxlength="40"><button class="btn primary">{ic("check", 18)} Enregistrer</button></div></form>
<form method="post" class="stack">{hidden(a="pw", u=u, back=back)}<div class="label" style="margin:0">Nouveau mot de passe</div>
<div class="row" style="flex-wrap:nowrap"><input type="text" name="v" placeholder="4 caractères minimum" required minlength="4"><button class="btn primary">{ic("key", 18)} Changer</button></div></form>
<p class="muted small" style="margin:0">L'identifiant <code>{e(u)}</code> ne peut pas être modifié.</p>
<div class="dlg-foot"><button class="btn" data-close>Fermer</button></div></div></dialog>
<dialog id="del-{u}"><form method="post" class="dlg">{hidden(a="delkid", u=u, back=back)}
<h3>{avatar(u, "sm")} Supprimer le compte de {e(nom(u))} ?</h3>
<p style="margin:0">{e(nom(u))} ne pourra plus se connecter. Sa session est fermée tout de suite (le travail non enregistré est perdu),
son planning et ses règles sont effacés.</p>
<label class="check"><input type="checkbox" name="purge" value="1"><span><b>Effacer aussi ses fichiers et ses statistiques</b><br>
<span class="muted small">Documents, images, favoris… Définitif. Sinon ils sont gardés et il les retrouvera si vous recréez un compte « {e(u)} ».</span></span></label>
<div class="dlg-foot"><button type="button" class="btn" data-close>Annuler</button><button class="btn primary" style="background:var(--red);border-color:var(--red)">{ic("trash", 18)} Supprimer le compte</button></div></form></dialog>
</section>""")
    copie = '<option value="">Tout vert, sans règle personnelle (à régler ensuite)</option>' + "".join(
        f'<option value="{e(u)}">Copier le planning et les règles de {e(nom(u))}</option>' for u in USERS)
    add = f"""<section class="card stack"><div><h2>{ic("plus", 18)} Ajouter un enfant</h2>
<span class="muted small">Le compte est utilisable tout de suite avec la Connexion Bureau à distance.</span></div>
<form method="post" class="stack">{hidden(a="addkid", back=back)}<div class="fields">
<label>Prénom<input type="text" id="new-nom" name="nom" required maxlength="40" placeholder="ex. Lina"></label>
<label>Identifiant de connexion<input type="text" id="new-login" name="login" required pattern="[a-z][a-z0-9_]{{1,30}}" maxlength="31"
 autocapitalize="none" spellcheck="false" placeholder="ex. lina"><small>Minuscules sans accent, chiffres ou « _ ».</small></label>
<label>Mot de passe<input type="text" name="pw" minlength="4" maxlength="64" placeholder="Laisser vide : créé automatiquement"
 autocapitalize="none" spellcheck="false"></label>
<label>Réglages de départ<select name="copie">{copie}</select></label>
<label>Langue du bureau<select name="langue" translate="no">{lang_opts("fr")}</select>
<small>Menus, Firefox, LibreOffice, clavier et messages de MaranYSE.</small></label></div>
<div><button class="btn primary">{ic("plus", 18)} Créer le compte</button></div></form></section>"""
    sub = f"{len(USERS)} compte{'s' if len(USERS) > 1 else ''} enfant{'s' if len(USERS) > 1 else ''}"
    return shell("comptes", "Comptes", sub, f'<div class="grid">{"".join(cards)}</div><div style="margin-top:18px">{add}</div>', flash)


# ======================================================================
# Logiciels pour tous les enfants
# ======================================================================
LG_NOTE = """<ul class="lg-notes">
<li><b>Autorisé pour tous par défaut.</b> Un logiciel installé apparaît dans <a href="/?p=regles">Règles</a> → Applications :
vous pouvez le bloquer ou le limiter pour tous ou pour un enfant, comme Firefox ou Tux Paint. Son temps d'utilisation est
compté dans les Statistiques.</li>
<li><b>Pas d'internet</b> pour ces logiciels tant que « Internet pour les programmes autres que Firefox » est interdit
(Règles → Contournements) : jeux en ligne, boutique d'extensions de VS Code… ne fonctionnent pas. C'est voulu.</li>
<li><b>VS Code</b> est préparé pour chaque enfant (dans la langue de l'enfant, extension Python, sans mises à jour ni assistant IA).
Son terminal intégré donne une ligne de commande : bloquer « Terminal » ne le bloque pas, bloquez aussi VS Code si besoin.</li>
<li>Les programmes compilés par les enfants (C, jeux Godot exportés…) ne se lancent que si « Programmes téléchargés » est autorisé.</li>
<li>Les logiciels restent installés après une mise à jour de MaranYSE ; s'il en manque, ils sont réinstallés tout seuls.</li></ul>"""


def lg_job():
    j, d = logiciels.JOB["en_cours"], logiciels.JOB["dernier"]
    if j:
        m = int((time.time() - j["debut"]) // 60)
        return (f'<div class="card lg-job"><span class="spin"></span><div><b>{e(j["action"].capitalize())} : {e(j["nom"])}</b>'
                f'<div class="muted small">En cours depuis {m} min — la page se met à jour toute seule. Les enfants peuvent continuer à travailler.</div></div></div>')
    if d and time.time() - d["fin"] < 1800:
        if d["ok"]:
            txt = ("Disponible dans le menu Applications des enfants." if d["action"] == "installer" else "Fait.")
            return (f'<div class="card lg-job ok">{ic("check", 22)}<div><b>{e(d["nom"])} : {e(d["action"])}, terminé</b>'
                    f'<div class="muted small">{txt}</div></div></div>')
        return (f'<div class="card lg-job err">{ic("ban", 22)}<div><b>{e(d["nom"])} : échec ({e(d["action"])})</b>'
                f'<details><summary class="small">Détails techniques</summary><pre>{e(d["log"][-1200:])}</pre></details></div></div>')
    return ""


def lg_date(d):
    try:
        t = datetime.strptime(d, "%Y-%m-%d %H:%M")
    except ValueError:
        return ""
    return f"le {t.day} {MOIS[t.month - 1]} {t.year}"


def lg_row(cle, i, back, dis):
    b = item_badge("app:" + logiciels.cle_app(cle), 40)
    paq = (' · paquet <code>' + e(" ".join(i["paquets"])) + '</code>') if i.get("perso") else ''
    return f"""<div class="lg-row">{b}<div class="nm"><b>{e(i["nom"])}</b><div class="muted small">Installé {e(lg_date(i.get("date", "")))}{paq}</div></div>
<div class="row"><a class="btn sm" href="/?p=regles">{ic("shield", 16)} Bloquer / limiter</a>
<button class="btn sm danger" data-open="rm-{e(cle)}"{dis}>{ic("trash", 16)} Désinstaller</button></div>
<dialog id="rm-{e(cle)}"><form method="post" class="dlg">{hidden(a="lgremove", cle=cle, back=back)}
<h3>{b} Désinstaller {e(i["nom"])} ?</h3><p style="margin:0">Le logiciel disparaît pour tous les enfants (fermez-le avant s'il est ouvert).
Leurs fichiers sont conservés ; ses règles sont retirées.</p>
<div class="dlg-foot"><button type="button" class="btn" data-close>Annuler</button><button class="btn primary" style="background:var(--red);border-color:var(--red)">{ic("trash", 18)} Désinstaller</button></div></form></dialog></div>"""


def lg_card(cle, i, installe, back, dis):
    col, gl = i["badge"]
    b = f'<span class="item" translate="no" style="--c:{col};width:40px;height:40px">{e(gl)}</span>'
    if installe:
        act = '<span class="pill g">' + ic("check", 14) + ' Installé</span>'
    else:
        act = f'<form method="post">{hidden(a="lginstall", cle=cle, back=back)}<button class="btn sm primary"{dis}>{ic("plus", 16)} Installer</button></form>'
    return (f'<div class="lg-card">{b}<div class="nm"><b>{e(i["nom"])}</b><p>{e(i["desc"])}</p>'
            f'<div class="lg-foot"><span class="muted small">{e(i["taille"])}</span>{act}</div></div></div>')


def page_logiciels(q, flash=""):
    if container_state() != "running":
        body = (f'<div class="card stack"><h2>Les sessions MaranYSE sont arrêtées</h2><p class="muted">Démarrez-les pour installer des logiciels.</p>'
                f'<form method="post">{hidden(a="restart", back="/?p=logiciels")}<button class="btn primary">{ic("power")} Démarrer</button></form></div>')
        return shell("logiciels", "Logiciels", "Outils installés pour tous les enfants", body, flash)
    inst = logiciels.charger()["installes"]
    busy = bool(logiciels.JOB["en_cours"])
    back = "/?p=logiciels"
    dis = ' disabled title="Une installation est en cours"' if busy else ""
    vide = '<p class="muted" style="margin:0">Aucun pour l&#39;instant : choisissez dans le catalogue ci-dessous.</p>'
    installes = (f'<section class="card stack"><div><h2>{ic("box", 18)} Installés pour tous les enfants</h2></div>'
                 + ("".join(lg_row(k, i, back, dis) for k, i in inst.items()) or vide) + '</section>')
    def section(cat):
        items = [(k, i) for k, i in logiciels.CATALOGUE.items() if i["cat"] == cat]
        n_inst = sum(k in inst for k, _ in items)
        return (f'<details class="lg-sec" data-cat="{e(cat)}"><summary><h3 class="lg-cat">{e(cat)}</h3>'
                f'<span class="pill">{len(items)}</span>'
                + (f'<span class="pill g">{ic("check", 14)} {n_inst} installé{"s" if n_inst > 1 else ""}</span>' if n_inst else "")
                + '</summary><div class="lg-grid">' + "".join(lg_card(k, i, k in inst, back, dis) for k, i in items) + '</div></details>')
    cats = "".join(section(cat) for cat in logiciels.CATEGORIES)
    outils = (f'<div class="lg-tools"><input type="search" id="lg-q" placeholder="Rechercher un logiciel…" aria-label="Rechercher un logiciel">'
              f'<button type="button" class="btn sm" id="lg-all">Tout ouvrir</button><button type="button" class="btn sm" id="lg-none">Tout fermer</button></div>')
    autre = f"""<section class="card stack"><div><h2>{ic("plus", 18)} Autre logiciel</h2>
<span class="muted small">N'importe quel paquet de Debian 12 (liste sur <a href="https://packages.debian.org/bookworm/" target="_blank" rel="noopener">packages.debian.org</a>),
par exemple <code>tuxpuck</code>, <code>pingus</code>, <code>lmms</code>. Les outils de contournement (VPN, Tor, proxys) sont refusés.</span></div>
<form method="post" class="row" style="flex-wrap:nowrap">{hidden(a="lginstall", cle="_paquet", back=back)}
<input type="text" name="paquet" required pattern="[a-z0-9][a-z0-9+.\\-]{{1,60}}" placeholder="nom du paquet" autocapitalize="none" spellcheck="false">
<button class="btn primary"{dis}>{ic("plus", 18)} Installer</button></form></section>"""
    body = (lg_job() + f'<div class="grid2">{installes}<section class="card stack"><h2>Bon à savoir</h2>{LG_NOTE}</section></div>'
            f'<section class="card stack" style="margin-top:18px"><div><h2>Catalogue</h2><span class="muted small">Un clic installe le logiciel pour tous les enfants, '
            f'dans leur menu Applications.</span></div>{outils}{cats}<p class="empty" id="lg-rien" hidden>Aucun logiciel ne correspond.</p></section><div style="margin-top:18px">{autre}</div>')
    body += LG_JS
    n = len(inst)
    sub = (f"{n} logiciel{'s' if n > 1 else ''} ajouté{'s' if n > 1 else ''} pour tous les enfants" if n
           else "Installer un outil pour tous les enfants")
    return shell("logiciels", "Logiciels", sub, body, flash, refresh=busy)


# ======================================================================
# Puissance : curseur « part de l'ordinateur pour les enfants »
# ======================================================================
def num(v, d=1):
    s = f"{v:.{d}f}".rstrip("0").rstrip(".") if d else f"{v:.0f}"
    return s.replace(".", ",")


def pw_bar(label, used, lim, total, unit, fmt):
    """Barre = tout l'ordinateur : utilisé maintenant · réservé aux enfants · reste pour Windows."""
    u = min(used or 0, lim)
    return (f'<div class="pw-row"><div class="between"><b>{label}</b><span class="small"><b data-pw="{unit}-txt">{fmt(lim)}</b>'
            f' <span class="muted">sur {fmt(total)}</span></span></div>'
            f'<div class="pw-bar" title="Utilisé maintenant : {fmt(used or 0)}"><i class="pw-use" style="width:{100 * u / total:.2f}%"></i>'
            f'<i class="pw-lim" data-pw="{unit}-bar" style="width:{100 * max(0, lim - u) / total:.2f}%"></i></div>'
            f'<div class="small muted">Utilisé maintenant par les enfants : {fmt(used or 0)}</div></div>')


def disque_card(h):
    """Carte « Espace disque » : quota par enfant (curseur) et place occupée par chacun."""
    total, libre = disque_vm()
    q, qmax = quota_go(), quota_max_go()
    use = STATE.get("quota_use", {})
    n = max(1, len(USERS))
    rows, plein = "", []
    for u in USERS:
        g = use.get(u, 0) / 2**20
        p = min(100, 100 * g / q)
        if p >= 90:
            plein.append(nom(u))
        rows += (f'<div class="pw-kid">{avatar(u, "sm")}<div class="pw-kid-b"><div class="between small"><b>{e(nom(u))}</b>'
                 f'<span><b>{num(g)} Go</b> <span class="muted">sur <span data-q="q">{q}</span> Go</span></span></div>'
                 f'<div class="meter"><i class="{"full" if p >= 90 else ""}" data-q="bar" data-go="{g:.3f}" style="width:{p:.1f}%"></i></div></div></div>')
    hote_txt = (f' · l\'ordinateur a encore {num(h["disque_libre_go"], 0)} Go libres sur son disque' if h.get("disque_libre_go") else "")
    alerte = (f'<span class="pill r pw-alert">{ic("x", 14)} Presque plein pour {e(", ".join(plein))} : quand le quota est atteint, '
              f'plus rien ne peut être enregistré (fichiers, réglages, connexion qui peut échouer).</span>' if plein else "")
    inner = f"""<form method="post" class="stack" id="q-form" data-n="{n}" data-libre="{libre:.1f}">{hidden(a="quota", back="/?p=puissance")}
<div class="range pw-range"><input type="range" name="disque_go" min="{QUOTA_MIN_GO}" max="{max(q, qmax)}" step="1" value="{q}" aria-label="Espace disque par enfant">
<output data-q="out">{q} Go</output></div>
<div class="strip-l"><span>{QUOTA_MIN_GO} Go</span><span>{max(q, qmax)} Go · place libre partagée entre les {n} enfants</span></div>
{rows}
<div class="between"><span class="small">En tout : <b data-q="tot">{q * n} Go</b> pour les {n} enfants, sur {num(libre, 0)} Go libres dans la VM.</span>
<button class="btn primary">{ic("check", 18)} Appliquer</button></div>{alerte}</form>"""
    return card("Espace disque par enfant", f"Disque de la VM : {num(total, 0)} Go, {num(libre, 0)} Go libres{hote_txt}", inner, icon="box")


def page_puissance(q, flash=""):
    h = hote()
    pct, mx = puissance_pct(h), pct_max(h)
    cpus, mem = limites(pct, h)
    st = STATE.get("puiss", {})
    go = lambda mo: f"{num(mo / 1024, 0 if mo >= 10240 else 1)} Go"
    proc = lambda n: f"{num(n)} processeur{'s' if n >= 2 else ''}" if n >= 0.05 else "presque rien"
    n = max(1, len(USERS))
    now = time.time()
    etat = []
    if now - st.get("frein", 0) < 600:
        etat.append(f'<span class="pill o pw-alert">{ic("clock", 14)} Limite de processeur atteinte ces dernières minutes : les programmes des enfants ralentissent</span>')
    if now - st.get("oom", 0) < 86400:
        etat.append(f'<span class="pill r pw-alert">{ic("x", 14)} Mémoire pleine à {datetime.fromtimestamp(st["oom"]):%H:%M} : '
                    f'le programme le plus gourmand a été fermé</span>')
    machine = (f'{e(h["nom"])} · ' if h["nom"] else "") + f'{h["threads"]} processeurs · {num(h["ram_mo"] / 1024, 0)} Go de mémoire'
    data = (f'data-threads="{h["threads"]}" data-ram="{h["ram_mo"]}" data-vmcpu="{h["vm_cpu"]}" '
            f'data-vmram="{h["vm_ram_mo"] - RESERVE_VM_MO}" data-n="{n}"')
    par = mem / n
    conseil = (f'<span class="pill o" data-pw="peu">{ic("clock", 14)} Peu : Firefox et VS Code risquent de ramer</span>'
               if par < 2048 else f'<span class="pill g" data-pw="peu">{ic("check", 14)} Confortable</span>')
    curseur = f"""<form method="post" class="stack" id="pw-form" {data}>{hidden(a="puissance", back="/?p=puissance")}
<div class="range pw-range"><input type="range" name="pct" min="{PCT_MIN}" max="{mx}" step="1" value="{pct}" aria-label="Part de l'ordinateur pour les enfants">
<output data-pw="pct">{pct} %</output></div>
<div class="strip-l"><span>{PCT_MIN} % · léger</span><span>{mx} % · maximum</span></div>
{pw_bar("Processeur", st.get("cpu"), cpus, h["threads"], "cpu", proc)}
{pw_bar("Mémoire", (st.get("mem") or 0) / 1048576, mem, h["ram_mo"], "mem", go)}
<div class="pw-leg small muted"><span><i class="pw-use"></i>utilisé maintenant</span><span><i class="pw-lim"></i>réservé aux enfants</span>
<span><i class="pw-free"></i>reste pour Windows et ses programmes</span></div>
<div class="between"><span class="small">Soit environ <b data-pw="par">{go(par)}</b> de mémoire par enfant si les {n} sont connectés. {conseil}</span>
<button class="btn primary">{ic("check", 18)} Appliquer</button></div></form>"""
    main = card("Part de l'ordinateur pour les enfants", machine, curseur + (f'<div class="row">{"".join(etat)}</div>' if etat else ""),
                icon="cpu")
    note = f"""<section class="card stack"><h2>Bon à savoir</h2><ul class="pw-note">
<li>Le changement s'applique <b>tout de suite</b>, sans fermer les sessions ni perdre de travail.</li>
<li>La limite est partagée entre tous les enfants connectés : ceux qui travaillent prennent ce que les autres n'utilisent pas.</li>
<li><b>Processeur</b> à la limite : les programmes des enfants ralentissent, rien n'est fermé. Windows garde le reste.</li>
<li><b>Mémoire</b> pleine : le programme qui en prend le plus (souvent un onglet ou un jeu) est fermé pour protéger le reste.
Comptez <b>2 Go par enfant</b> pour Firefox et VS Code.</li>
<li>{"Le maximum est fixé à " + str(mx) + " % : Windows garde toujours au moins " + str(100 - mx) + " % de l'ordinateur."
if mx >= PCT_PLAFOND else "Le maximum (" + str(mx) + " %) est ce que la VM a reçu dans Hyper-V. Pour aller au-delà, il faut agrandir la VM (VM arrêtée)."}
La VM dispose de {h["vm_cpu"]} processeurs et jusqu'à {num(h["vm_ram_mo"] / 1024, 0)} Go.</li>
<li><b>Espace disque</b> : chaque enfant ne peut pas dépasser son quota (documents, téléchargements, réglages).
La place occupée est relevée toutes les 5 minutes.</li>
<li>Consommation de chaque enfant : <a href="/?p=stats#ressources">Statistiques → Ressources utilisées</a>.</li></ul></section>"""
    js = """<script>(()=>{const f=document.getElementById('pw-form');if(!f)return;const d=f.dataset,r=f.querySelector('input[type=range]'),
q=k=>f.querySelector('[data-pw="'+k+'"]'),nf=v=>(Math.round(v*10)/10).toString().replace('.',',');
const upd=()=>{const p=+r.value,c=Math.min(+d.vmcpu,d.threads*p/100),m=Math.max(1024,Math.min(+d.vmram,d.ram*p/100)),par=m/d.n;
q('pct').textContent=p+' %';q('cpu-txt').textContent=nf(c)+' '+_t(c>=2?'processeurs':'processeur');q('mem-txt').textContent=(m>=10240?Math.round(m/1024):nf(m/1024))+' '+_t('Go');
for(const[k,v,t]of[['cpu',c,+d.threads],['mem',m/1024,d.ram/1024]]){const b=q(k+'-bar'),u=b.previousElementSibling;
b.style.width=Math.max(0,v/t*100-parseFloat(u.style.width))+'%'}
q('par').textContent=nf(par/1024)+' '+_t('Go');const w=q('peu');w.className='pill '+(par<2048?'o':'g');
w.lastChild.textContent=' '+_t(par<2048?'Peu : Firefox et VS Code risquent de ramer':'Confortable')};
r.addEventListener('input',upd);r.addEventListener('change',()=>f.requestSubmit())})();
(()=>{const f=document.getElementById('q-form');if(!f)return;const r=f.querySelector('input[type=range]');
r.addEventListener('input',()=>{const v=+r.value;f.querySelector('[data-q=out]').textContent=v+' '+_t('Go');
f.querySelector('[data-q=tot]').textContent=v*f.dataset.n+' '+_t('Go');f.querySelectorAll('[data-q=q]').forEach(x=>x.textContent=v);
f.querySelectorAll('[data-q=bar]').forEach(b=>{const p=Math.min(100,100*b.dataset.go/v);b.style.width=p+'%';b.classList.toggle('full',p>=90)})});
r.addEventListener('change',()=>f.requestSubmit())})()</script>"""
    body = f'<div class="grid2 pw">{main}{disque_card(h)}</div><div style="margin-top:18px">{note}</div>{js}'
    return shell("puissance", "Puissance", f"Les enfants peuvent utiliser {pct} % de l'ordinateur", body, flash)


# ======================================================================
# Actions
# ======================================================================
def update(fn):
    with lock:
        data = load_rules()
        msg = fn(data)
        save_rules(data)
    return msg


def do_action(a, form):
    g = lambda k: form.get(k, [""])[0]
    u, v, scope = g("u"), g("v"), g("s")
    now = datetime.now()
    if a == "restart":
        subprocess.run(["docker", "restart", C], capture_output=True, timeout=120)
        STATE["lvl"].clear()
        return "Bureau redémarré."
    if a == "addkid":
        src = g("copie")
        ok, msg, pw = add_account(g("login"), g("nom"), g("pw"))
        if not ok:
            return msg
        login = g("login").strip().lower()
        if g("langue") in i18n.LANGUES and login in USERS:
            update(lambda d: d[login].__setitem__("langue", g("langue")))
        if src in USERS and src != login:
            def f(d):
                d[login].update({k: json.loads(json.dumps(d[src][k])) for k in ("grille", "quota", "internet", "regles")})
                if g("langue") in i18n.LANGUES:
                    d[login]["langue"] = g("langue")
            update(f)
            msg += f" Planning et règles copiés de {nom(src)}."
        return f"{msg} Identifiant : {login} · mot de passe : {pw}"
    if a == "lginstall":
        return logiciels.installer(g("cle"), g("paquet"))
    if a == "puissance":
        try:
            pct = int(g("pct"))
        except ValueError:
            return "Valeur invalide."
        h = hote()
        pct = max(PCT_MIN, min(pct_max(h), pct))
        save_puissance(pct=pct)
        apply_puissance()
        cpus, mem = limites(pct, h)
        return f"Les enfants peuvent maintenant utiliser {pct} % de l'ordinateur : {num(cpus)} processeurs et {num(mem / 1024)} Go de mémoire."
    if a == "quota":
        try:
            go = max(QUOTA_MIN_GO, int(g("disque_go")))
        except ValueError:
            return "Valeur invalide."
        if go > max(quota_max_go(), quota_go()):
            return f"Pas assez de place : au plus {quota_max_go()} Go par enfant."
        save_puissance(disque_go=go)
        apply_quota(uids(), force=True)
        return f"Chaque enfant peut maintenant utiliser jusqu'à {go} Go sur le disque."
    if a == "lgremove":
        return logiciels.desinstaller(g("cle"))
    if a == "rename":
        return rename_account(u, v)
    if a == "langue":
        if u not in USERS or v not in i18n.LANGUES:
            return "Langue inconnue."
        update(lambda d: d[u].__setitem__("langue", v))
        msg = f"Langue du bureau de {nom(u)} : {i18n.LANGUES[v][0]}. Elle s'appliquera à sa prochaine connexion."
        if u in displays():
            msg += f" {nom(u)} est connecté : « Appliquer maintenant » ferme sa session pour changer tout de suite."
        return msg
    if a == "couleur":
        if u not in USERS or not re.fullmatch(r"#[0-9a-fA-F]{6}", v):
            return "Couleur invalide."
        update(lambda d: d[u].__setitem__("couleur", v.lower()))
        return f"Couleur de {nom(u)} enregistrée."
    if a == "delkid":
        return remove_account(u, purge=g("purge") == "1")
    if a == "secu":
        k = g("k")
        if (scope != ALL and scope not in USERS) or k not in SECU or (scope != ALL and not SECU[k][2]) or v not in set(SECU_VAL) | ({"herite"} if scope != ALL else set()):
            return "Choix invalide."
        who = "tous les enfants" if scope == ALL else nom(scope)
        txt = "comme la règle commune" if v == "herite" else SECU_VAL[v].lower()
        return update(lambda d: d[scope]["securite"].update({k: v}) or f"{SECU[k][0]} : {txt} pour {who}.")
    if a in ("addrule", "delrule", "internet"):
        if scope != ALL and scope not in USERS:
            return "Destinataire inconnu."
        who = "tous les enfants" if scope == ALL else nom(scope)
        if a == "internet":
            if v not in set(INTERNET) | ({"herite"} if scope != ALL else set()):
                return "Choix invalide."
            return update(lambda d: d[scope].update(internet=v) or
                          f"Internet en orange pour {who} : {'comme la règle commune' if v == 'herite' else INTERNET[v].lower()}.")
        if a == "delrule":
            cle = g("cle")
            return update(lambda d: d[scope].update(regles=[x for x in d[scope]["regles"] if x["cle"] != cle]) or f"Règle supprimée pour {who}.")
        cle, mode = g("cle"), g("mode")
        if cle == "dom:":
            dom = clean_domain(g("dom"))
            if not dom:
                return "Adresse de site invalide (exemple : minecraft.net)."
            cle = "dom:" + dom
        if not target(cle) or mode not in MODES or (mode == "autoriser" and scope == ALL):
            return "Règle invalide."
        try:
            minutes = max(1, min(1440, int(g("minutes") or 60))) if mode == "limiter" else 0
        except ValueError:
            minutes = 60
        rule = {"cle": cle, "mode": mode, "minutes": minutes}

        def f(d):
            d[scope]["regles"] = [x for x in d[scope]["regles"] if x["cle"] != cle] + [rule]
            txt = {"bloquer": "bloqué", "limiter": f"limité à {dur(minutes * 60)} par jour", "autoriser": "autorisé sans limite"}[mode]
            return f"{target(cle)[1]} : {txt} pour {who}."
        return update(f)
    if a == "msgtous":
        disp = displays()
        sent = 0
        for x in USERS:
            if x in disp:
                popup(x, disp[x], v[:500], auto=False)
                sent += 1
        return f"Message envoyé à {sent} enfant(s) connecté(s)." if sent else "Aucun enfant connecté."
    if a in ("pause15tous", "pause1htous", "pausejourtous"):
        until = {"pause15tous": now + timedelta(minutes=15), "pause1htous": now + timedelta(hours=1)}.get(
            a, datetime.combine(now.date() + timedelta(days=1), datetime.min.time()) + timedelta(hours=7))
        quand = f"{until:%H:%M}" + ("" if until.date() == now.date() else " demain")
        update(lambda d: [d[x].update(pause_jusqu=until.isoformat(timespec="seconds"), bonus_jusqu=None) for x in USERS])
        disp = displays()
        c = db()
        for x in USERS:
            dx(f"usermod -L {x}")
            STATE["lvl"][x] = "P"
            STATE["grace"].pop(x, None)
            if x in disp:
                freeze(x, disp[x], f"{until:%H:%M}")
            event(c, x, "En pause", f"pause des parents jusqu'à {quand}")
        write_locked(set(USERS))
        c.commit()
        c.close()
        return f"Tous les enfants sont en pause jusqu'à {quand}."
    if a == "levertous":
        update(lambda d: [d[x].update(pause_jusqu=None, bonus_jusqu=None) for x in USERS if dt(d[x].get("pause_jusqu"))])
        disp = displays()
        with lock:
            data = load_rules()
        c = db()
        for x in USERS:
            unfreeze(x, disp.get(x))
            lvl = access(x, data[x], now, used_today(c, x))[0]
            if lvl in ("V", "O"):
                dx(f"usermod -U {x}")
            STATE["lvl"].pop(x, None)
        c.close()
        return "La pause a été levée pour tous les enfants."
    if u not in USERS:
        return "Enfant inconnu."
    if a == "logout":
        logout(u)
        return f"Session de {nom(u)} fermée."
    if a == "msg":
        disp = displays().get(u)
        if not disp:
            return f"{nom(u)} n'a pas de session ouverte."
        popup(u, disp, v[:500], auto=False)
        return f"Message envoyé à {nom(u)}."
    if a == "pw":
        if not re.fullmatch(r"[^\s:]{4,64}", v):
            return "Mot de passe refusé : 4 caractères minimum, sans espace ni « : »."
        dx("chpasswd", inp=f"{u}:{v}\n")
        dx(f"sed -i '/^{u}:/d' /secrets/mots_de_passe.txt && cat >> /secrets/mots_de_passe.txt", inp=f"{u}:{v}\n")
        STATE["lvl"].pop(u, None)          # réapplique le verrouillage éventuel
        return f"Mot de passe de {nom(u)} changé."
    if a == "bonus":
        def f(d):
            b = dt(d[u].get("bonus_jusqu"))
            d[u]["bonus_jusqu"] = ((b if b and b > now else now) + timedelta(minutes=30)).isoformat(timespec="seconds")
            d[u]["pause_jusqu"] = None
            return f"30 minutes d'accès complet pour {nom(u)}, jusqu'à {dt(d[u]['bonus_jusqu']):%H:%M}."
        return update(f)
    if a in ("pause15", "pause1h", "pausejour"):
        until = {"pause15": now + timedelta(minutes=15), "pause1h": now + timedelta(hours=1)}.get(
            a, datetime.combine(now.date() + timedelta(days=1), datetime.min.time()) + timedelta(hours=7))
        quand = f"{until:%H:%M}" + ("" if until.date() == now.date() else " demain")
        update(lambda d: d[u].update(pause_jusqu=until.isoformat(timespec="seconds"), bonus_jusqu=None))
        # effet immédiat : compte verrouillé, écran bloqué, applications gardées
        dx(f"usermod -L {u}")
        write_locked({x for x in USERS if x == u or STATE["lvl"].get(x) in ("R", "P")})
        STATE["lvl"][u] = "P"
        STATE["grace"].pop(u, None)
        disp = displays().get(u)
        if disp:
            freeze(u, disp, f"{until:%H:%M}")
        c = db()
        event(c, u, "En pause", f"pause des parents jusqu'à {quand}")
        c.commit()
        c.close()
        return f"{nom(u)} est en pause jusqu'à {quand}." + (" Son écran est bloqué, ses applications restent ouvertes." if disp else "")
    if a == "lever":
        msg = update(lambda d: d[u].update(pause_jusqu=None, bonus_jusqu=None) or f"{nom(u)} peut reprendre.")
        unfreeze(u, displays().get(u))
        with lock:
            data = load_rules()
        c = db()
        lvl = access(u, data[u], now, used_today(c, u))[0]
        c.close()
        if lvl in ("V", "O"):
            dx(f"usermod -U {u}")
        else:
            msg += " Attention : le planning ne l'autorise pas en ce moment (rouge)."
        STATE["lvl"].pop(u, None)
        return msg
    if a == "planning":
        tous = g("tous") == "1"
        cibles = list(USERS) if tous else [u]

        def f(d):
            for x in cibles:
                for i in range(7):
                    gg = g(f"grille_{i}")
                    if re.fullmatch(r"[VOR]{48}|[VOR]{96}|[VOR]{1440}", gg):
                        d[x]["grille"][str(i)] = normalize_grille_day(gg)
                    try:
                        d[x]["quota"][str(i)] = max(0, min(1440, int(g(f"quota_{i}") or 0)))
                    except ValueError:
                        d[x]["quota"][str(i)] = 0
            return "Planning appliqué à tous les enfants." if tous else f"Planning de {nom(u)} enregistré."
        return update(f)
    return "Action inconnue."


_APPS_VUES = [0, set()]


def apps_vues():
    """Noms d'applications des statistiques (30 jours), relus au plus une fois par minute."""
    if time.time() - _APPS_VUES[0] > 60:
        try:
            c = db()
            _APPS_VUES[1] = {r[0] for r in c.execute("SELECT DISTINCT app FROM usage WHERE day>=?",
                                                     ((datetime.now().date() - timedelta(days=30)).isoformat(),))}
            c.close()
        except Exception:
            pass
        _APPS_VUES[0] = time.time()
    return _APPS_VUES[1]


def noms_page():
    """Noms gardés tels quels dans les phrases (prénoms, applications, logiciels, sites) ; s'ils sont aussi une
    phrase du catalogue (« Bureau », « Autres »), ils sont traduits à part."""
    n = {nom(u) for u in USERS} | set(USERS) | set(noms_traduction()) | {"Autres", IDLE} | apps_vues() | {v[0] for v in i18n.LANGUES.values()}
    n |= {i.get("nom", "") for i in logiciels.charger()["installes"].values()} | {i["nom"] for i in logiciels.CATALOGUE.values()}
    return sorted(x for x in n if x and len(x) > 1)


# ======================================================================
# Serveur HTTP (authentification temps-constant, anti-bruteforce, bornes POST)
# ======================================================================
_AUTH_LOCK = threading.Lock()
_AUTH_FAILS = {}                 # ip -> [timestamps des échecs récents]
AUTH_WINDOW = 60
AUTH_MAX_FAILS = 10
MAX_POST_BYTES = 65536


def _rate_limited(ip):
    now = time.time()
    with _AUTH_LOCK:
        ts = [t for t in _AUTH_FAILS.get(ip, ()) if now - t < AUTH_WINDOW]
        if ts:
            _AUTH_FAILS[ip] = ts
        else:
            _AUTH_FAILS.pop(ip, None)
        return len(ts) >= AUTH_MAX_FAILS


def _record_auth(ip, ok):
    now = time.time()
    with _AUTH_LOCK:
        if ok:
            _AUTH_FAILS.pop(ip, None)
        else:
            ts = [t for t in _AUTH_FAILS.get(ip, ()) if now - t < AUTH_WINDOW] + [now]
            _AUTH_FAILS[ip] = ts


class H(BaseHTTPRequestHandler):
    def auth(self):
        ip = self.client_address[0] if self.client_address else ""
        if _rate_limited(ip):
            self.send_response(429)
            self.send_header("Retry-After", str(AUTH_WINDOW))
            self.end_headers()
            return False
        h = self.headers.get("Authorization", "")
        ok = False
        if h.startswith("Basic "):
            try:
                raw = base64.b64decode(h[6:]).decode("utf-8")
                u, sep, pw = raw.partition(":")
                ok = bool(sep) and (secrets.compare_digest(u, LOGIN) & secrets.compare_digest(pw, PASSWORD))
            except Exception:
                ok = False
        if h:
            _record_auth(ip, ok)
        if not ok:
            self.send_response(401)
            self.send_header("WWW-Authenticate", 'Basic realm="MaranYSE - Espace parents", charset="UTF-8"')
            self.end_headers()
        return ok

    def langue(self):  # noqa: E301
        q = parse_qs(urlparse(self.path).query).get("lang", [""])[0]
        if q in i18n.LANGUES:
            self.lang_cookie = q
            return q
        c = re.search(r"(?:^|;\s*)lang=([a-z]{2})", self.headers.get("Cookie", ""))
        if c and c.group(1) in i18n.LANGUES:
            return c.group(1)
        return i18n.langue_navigateur(self.headers.get("Accept-Language"))

    def choisir_theme(self):
        q = parse_qs(urlparse(self.path).query).get("theme", [""])[0]
        if q in themes.CSS:
            self.theme_cookie = q
            return q
        c = re.search(r"(?:^|;\s*)apparence=([a-z]+)", self.headers.get("Cookie", ""))
        return c.group(1) if c and c.group(1) in themes.CSS else themes.DEFAUT

    def enfant_courant(self, q, p):
        s = q.get("s", q.get("u", [""]))[0]
        vue = q.get("vue", [""])[0]
        if s == ALL or (p == "stats" and vue in ("ensemble", "app")):
            self.kid_cookie = ""
            return None
        if s and s in USERS:
            self.kid_cookie = s
            return s
        c = re.search(r"(?:^|;\s*)enfant=([a-z0-9_]+)", self.headers.get("Cookie", ""))
        return c.group(1) if c and c.group(1) in USERS else None

    def send(self, body):
        lang = self.langue()
        try:
            body = i18n.traduire_html(body, lang, noms_page(), urlparse(self.path).query[:80])
        except Exception as ex:                  # une traduction ratée ne doit jamais empêcher d'afficher la page
            print("erreur traduction:", repr(ex), flush=True)
        b = body.encode()
        self.send_response(200)
        if getattr(self, "theme_cookie", None):
            sec_f = "; Secure" if getattr(self.connection, "_is_tls", False) else ""
            self.send_header("Set-Cookie", f"apparence={self.theme_cookie}; Path=/; Max-Age=31536000; SameSite=Lax; HttpOnly{sec_f}")
        if getattr(self, "lang_cookie", None):
            sec_f = "; Secure" if getattr(self.connection, "_is_tls", False) else ""
            self.send_header("Set-Cookie", f"lang={self.lang_cookie}; Path=/; Max-Age=31536000; SameSite=Lax; HttpOnly{sec_f}")
        if getattr(self, "kid_cookie", None) is not None:
            kc = self.kid_cookie
            sec_f = "; Secure" if getattr(self.connection, "_is_tls", False) else ""
            self.send_header("Set-Cookie", f"enfant={kc}; Path=/; Max-Age={2592000 if kc else 0}; SameSite=Lax; HttpOnly{sec_f}")
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "same-origin")
        self.end_headers()
        self.wfile.write(b)

    def _redirect_https(self):
        if getattr(self.connection, "_is_tls", False) or not getattr(self.server, "ssl_ctx", None):
            return False
        if self.client_address and self.client_address[0] == "127.0.0.1":
            return False
        host = self.headers.get("Host", "")
        if not host:
            return False
        self.send_response(301)
        self.send_header("Location", f"https://{host}{self.path}")
        self.end_headers()
        return True

    def do_GET(self):
        if self._redirect_https():
            return
        if not self.auth():
            return
        path = urlparse(self.path).path
        if path == "/maranyse.crt" and os.path.isfile(TLS_CERT):
            data = open(TLS_CERT, "rb").read()
            self.send_response(200)
            self.send_header("Content-Type", "application/x-x509-ca-cert")
            self.send_header("Content-Disposition", 'attachment; filename="maranyse.crt"')
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        if path == "/api/charge":
            try:
                vm = charge_vm()
            except (OSError, ValueError, KeyError):
                vm = None
            b = json.dumps({"vm": vm, "hote": charge_hote()}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(b)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(b)
            return
        images = {"/logo.png": LOGO_PNG, "/favicon.png": FAVICON_PNG, "/embleme.png": EMBLEME_PNG, "/embleme-petit.png": EMBLEME_PETIT_PNG,
                  "/logo-hd.jpg": LOGO_HD_JPG, "/logo-petit.jpg": LOGO_PETIT_JPG, "/titre.jpg": TITRE_JPG, "/slogan.jpg": SLOGAN_JPG, "/banniere.jpg": BANNIERE_JPG}
        if path in images:
            data = images[path]
            self.send_response(200)
            self.send_header("Content-Type", "image/jpeg" if path.endswith(".jpg") else "image/png")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "private, max-age=604800")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(data)
            return
        q = parse_qs(urlparse(self.path).query)
        REQ.theme = self.choisir_theme()
        p, flash = q.get("p", ["live"])[0], q.get("msg", [""])[0]
        REQ.kid = self.enfant_courant(q, p)
        if not USERS and not load_accounts() and p != "comptes":
            p = "live"                      # bureau arrêté au démarrage du tableau : liste encore inconnue
        if p == "aide":
            self.send(page_aide(self.headers.get("Host", "")))
        elif p == "comptes":
            self.send(page_comptes(q, flash))
        elif p == "logiciels":
            self.send(page_logiciels(q, flash))
        elif p == "puissance":
            self.send(page_puissance(q, flash))
        elif p in ("stats", "planning", "regles", "orange") and not USERS:
            self.send(page_live(q, flash))
        elif p == "stats":
            self.send(page_stats(q))
        elif p == "planning":
            self.send(page_planning(q, flash))
        elif p in ("regles", "orange"):
            self.send(page_regles(q, flash))
        else:
            self.send(page_live(q, flash))

    def do_POST(self):
        ip = self.client_address[0] if self.client_address else ""
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = -1
        if length < 0 or length > MAX_POST_BYTES:
            self.send_response(413 if length > MAX_POST_BYTES else 400)
            self.end_headers()
            return
        if urlparse(self.path).path == "/api/charge-hote":           # script de l'ordinateur hôte : jeton, pas de mot de passe
            if _rate_limited(ip):
                self.send_response(429)
                self.end_headers()
                return
            ok = secrets.compare_digest(self.headers.get("X-Jeton", ""), jeton_hote())
            _record_auth(ip, ok)
            if ok:
                try:
                    recevoir_charge_hote(json.loads(self.rfile.read(min(4096, length))))
                except (ValueError, KeyError, TypeError):
                    ok = False
            self.send_response(204 if ok else 403)
            self.end_headers()
            return
        if not self.auth():
            return
        # protection : refuse les formulaires envoyés depuis un autre site
        origin = self.headers.get("Origin") or self.headers.get("Referer") or ""
        if origin and urlparse(origin).netloc != self.headers.get("Host", ""):
            self.send_response(403)
            self.end_headers()
            return
        form = parse_qs(self.rfile.read(length).decode("utf-8", errors="replace"))
        a = form.get("a", [""])[0]
        msg = do_action(a, form)
        back = form.get("back", [""])[0]
        if not back.startswith("/?"):
            s = form.get("s", form.get("u", [""]))[0]
            back = {"planning": f"/?p=planning&s={quote(s)}", "addrule": f"/?p=regles&s={quote(s)}",
                    "delrule": f"/?p=regles&s={quote(s)}", "internet": f"/?p=regles&s={quote(s)}",
                    "secu": f"/?p=regles&s={quote(s)}"}.get(a, "/?p=live")
        self.send_response(303)
        self.send_header("Location", back + "&msg=" + quote(msg))
        self.end_headers()

    def log_message(self, *a):
        pass


TLS_DIR = f"{HOME}/.maranyse-tls"
TLS_CERT = f"{TLS_DIR}/cert.pem"
TLS_KEY = f"{TLS_DIR}/key.pem"


def ensure_tls_cert():
    """Génère automatiquement un certificat TLS auto-signé (SAN : IP locale + localhost) au premier démarrage."""
    if os.path.isfile(TLS_CERT) and os.path.isfile(TLS_KEY):
        return True
    os.makedirs(TLS_DIR, mode=0o700, exist_ok=True)
    ips = {"127.0.0.1"}
    try:
        out = subprocess.run(["hostname", "-I"], capture_output=True, text=True, timeout=5).stdout
        for x in out.split():
            if re.fullmatch(r"\d+\.\d+\.\d+\.\d+", x):
                ips.add(x)
    except Exception:
        pass
    san = ",".join([f"IP:{x}" for x in sorted(ips)] + ["DNS:localhost", "DNS:maranyse.local"])
    cfg = f"{TLS_DIR}/openssl.cnf"
    open(cfg, "w").write(
        "[req]\ndistinguished_name=dn\nx509_extensions=ext\nprompt=no\n"
        "[dn]\nCN=MaranYSE\n"
        f"[ext]\nsubjectAltName={san}\nbasicConstraints=CA:TRUE\nkeyUsage=digitalSignature,keyEncipherment,keyCertSign\n"
    )
    r = subprocess.run(
        ["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "3650",
         "-keyout", TLS_KEY, "-out", TLS_CERT, "-config", cfg],
        capture_output=True, text=True, timeout=30
    )
    if r.returncode == 0:
        os.chmod(TLS_KEY, 0o600)
        return True
    print("TLS désactivé (openssl):", r.stderr.strip()[:200], flush=True)
    return False


class DualHTTPServer(ThreadingHTTPServer):
    """Sert HTTPS nativement sur le port 8080 et redirige automatiquement les navigateurs HTTP vers HTTPS."""
    ssl_ctx = None

    def get_request(self):
        conn, addr = super().get_request()
        if self.ssl_ctx:
            try:
                conn.settimeout(5)
                if conn.recv(1, socket.MSG_PEEK) == b"\x16":
                    conn = self.ssl_ctx.wrap_socket(conn, server_side=True)
                    conn._is_tls = True
            except OSError:
                pass
            finally:
                try:
                    conn.settimeout(None)
                except OSError:
                    pass
        return conn, addr


if __name__ == "__main__":
    db().close()
    load_accounts()
    threading.Thread(target=boucle, daemon=True).start()
    srv = DualHTTPServer(("0.0.0.0", PORT), H)
    if ensure_tls_cert():
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(TLS_CERT, TLS_KEY)
        srv.ssl_ctx = ctx
    srv.serve_forever()
