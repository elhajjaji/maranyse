#!/usr/bin/env python3
"""MaranYSE — espace parents : interface web (http://IP:8080) qui pilote les sessions des enfants servies par la VM.
La logique (règles, statistiques, application toutes les 30 s) est dans logique.py."""
import base64, hashlib, html, json, math, os, re, secrets, subprocess, threading, time
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse, quote

from logique import *            # noqa: F401,F403
from logique import STATE, USERS, NAMES, lock, nom  # explicite
from marque import LOGO_PNG, FAVICON_PNG, EMBLEME_PNG, EMBLEME_PETIT_PNG, LOGO_HD_JPG, LOGO_PETIT_JPG, TITRE_JPG, SLOGAN_JPG, BANNIERE_JPG
import logiciels
import i18n
import themes

REQ = threading.local()
V_IMG = hashlib.md5(LOGO_HD_JPG + LOGO_PETIT_JPG + TITRE_JPG + BANNIERE_JPG + FAVICON_PNG).hexdigest()[:8]   # version des images          # requête en cours : apparence choisie

MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]


def e(s):
    return html.escape(str(s), quote=True)


def fmt_ts(ts):
    d = datetime.strptime(ts, "%Y%m%d-%H:%M:%S")
    return f"{d:%H:%M}" if d.date() == datetime.now().date() else f"le {d.day} {MOIS[d.month - 1]} à {d:%H:%M}"


# ======================================================================
# Icônes (traits, 24x24)
# ======================================================================
IC = {
    "home": '<path d="M3 10.5 12 3l9 7.5"/><path d="M5 9.5V21h14V9.5"/><path d="M10 21v-6h4v6"/>',
    "calendar": '<rect x="3" y="4.5" width="18" height="17" rx="2.5"/><path d="M16 2.5v4M8 2.5v4M3 10h18"/>',
    "shield": '<path d="M12 22s8-4 8-10V5.5L12 2.5 4 5.5V12c0 6 8 10 8 10z"/><path d="m9 12 2 2 4-4"/>',
    "chart": '<path d="M3 3v18h18"/><path d="M8 17v-5M13 17V8M18 17v-9"/>',
    "cpu": '<rect x="5" y="5" width="14" height="14" rx="2"/><rect x="9" y="9" width="6" height="6" rx="1"/><path d="M9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3"/>',
    "power": '<path d="M12 2v9"/><path d="M18.4 6.6a9 9 0 1 1-12.8 0"/>',
    "msg": '<path d="M21 14.5a2 2 0 0 1-2 2H8l-5 4.5V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "pause": '<rect x="6" y="4.5" width="4" height="15" rx="1.2"/><rect x="14" y="4.5" width="4" height="15" rx="1.2"/>',
    "logout": '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="m16 17 5-5-5-5M21 12H9"/>',
    "key": '<circle cx="7.5" cy="15.5" r="4.5"/><path d="M10.7 12.3 20 3M16.5 6.5l3 3M14 9l2 2"/>',
    "replier": '<path d="M11 17l-5-5 5-5M18 17l-5-5 5-5"/>',
    "palette": '<path d="M12 2.5a9.5 9.5 0 1 0 0 19c1.3 0 2-.9 2-1.9 0-.5-.2-.9-.5-1.3-.3-.3-.5-.7-.5-1.2 0-1 .8-1.6 1.8-1.6h2.1c2.7 0 4.6-2.1 4.6-4.6C21.5 6.3 17.3 2.5 12 2.5Z"/><circle cx="7.5" cy="11" r="1.2"/><circle cx="10.5" cy="7" r="1.2"/><circle cx="15" cy="7" r="1.2"/>',
    "globe": '<circle cx="12" cy="12" r="9.5"/><path d="M2.5 12h19M12 2.5a14.5 14.5 0 0 1 0 19M12 2.5a14.5 14.5 0 0 0 0 19"/>',
    "trash": '<path d="M3 6h18M8 6V4h8v2M19 6l-1 14.5a1.5 1.5 0 0 1-1.5 1.5h-9A1.5 1.5 0 0 1 6 20.5L5 6"/>',
    "clock": '<circle cx="12" cy="12" r="9.5"/><path d="M12 7v5l3.5 2"/>',
    "more": '<circle cx="5" cy="12" r="1.6"/><circle cx="12" cy="12" r="1.6"/><circle cx="19" cy="12" r="1.6"/>',
    "globe": '<circle cx="12" cy="12" r="9.5"/><path d="M2.5 12h19M12 2.5c2.6 2.8 3.9 6 3.9 9.5S14.6 18.7 12 21.5M12 2.5C9.4 5.3 8.1 8.5 8.1 12s1.3 6.7 3.9 9.5"/>',
    "box": '<path d="M21 8 12 3 3 8v8l9 5 9-5V8Z"/><path d="m3 8 9 5 9-5M12 13v8"/>',
    "help": '<circle cx="12" cy="12" r="9.5"/><path d="M9.3 9.2a2.8 2.8 0 0 1 5.4 1c0 1.9-2.7 2.5-2.7 4"/><circle cx="12" cy="17.3" r=".9" fill="currentColor"/>',
    "users": '<circle cx="9" cy="8" r="3.8"/><path d="M2.5 20.5v-.5a6 6 0 0 1 6-6h1a6 6 0 0 1 6 6v.5"/><path d="M16 4.3a3.8 3.8 0 0 1 0 7.4M21.5 20.5v-.5a6 6 0 0 0-3.5-5.4"/>',
    "wifi": '<path d="M2 8.8a15 15 0 0 1 20 0M5 12.3a10 10 0 0 1 14 0M8.5 15.8a5 5 0 0 1 7 0"/><circle cx="12" cy="19.3" r="1.1"/>',
    "wifioff": '<path d="M2 8.8a15 15 0 0 1 20 0M5 12.3a10 10 0 0 1 14 0M8.5 15.8a5 5 0 0 1 7 0"/><circle cx="12" cy="19.3" r="1.1"/><path d="M3 3l18 18"/>',
    "monitor": '<rect x="2" y="3.5" width="20" height="13.5" rx="2.5"/><path d="M8 21h8M12 17v4"/>',
    "x": '<path d="M18 6 6 18M6 6l12 12"/>',
    "check": '<path d="M20 6 9 17l-5-5"/>',
    "lock": '<rect x="4" y="10.5" width="16" height="11" rx="2.5"/><path d="M8 10.5V7a4 4 0 0 1 8 0v3.5"/>',
    "edit": '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/>',
    "ban": '<circle cx="12" cy="12" r="9.5"/><path d="m5.3 5.3 13.4 13.4"/>',
    "timer": '<circle cx="12" cy="13" r="8.5"/><path d="M12 9v4l2.5 2.5M9.5 2.5h5"/>',
    "app": '<rect x="3" y="3" width="7.5" height="7.5" rx="2"/><rect x="13.5" y="3" width="7.5" height="7.5" rx="2"/><rect x="3" y="13.5" width="7.5" height="7.5" rx="2"/><rect x="13.5" y="13.5" width="7.5" height="7.5" rx="2"/>',
    "eye": '<path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3.2"/>',
    "sparkle": '<path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5 18 18M6 18l2.5-2.5M15.5 8.5 18 6"/>',
}


def ic(name, size=20, cls=""):
    return (f'<svg class="ic {cls}" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{IC[name]}</svg>')


def avatar(u, size="md"):
    i = USERS.index(u) % 8 if u in USERS else 0
    return f'<span class="av av{i} av-{size}" translate="no">{e(nom(u)[:1].upper())}</span>'


# Pastille d'un site ou d'une application : (couleur, contenu)
ITEM = {
    "site:youtube": ("#ff0033", "▶"), "site:tiktok": ("#111827", "♪"), "site:reseaux": ("#8b5cf6", "@"),
    "site:twitch": ("#9146ff", "T"), "site:jeux": ("#16a34a", "J"), "site:streaming": ("#e50914", "N"),
    "app:firefox": ("#ff7139", "F"), "app:office": ("#0f9d58", "L"), "app:gcompris": ("#f59e0b", "G"),
    "app:tuxpaint": ("#3b82f6", "T"), "app:mousepad": ("#64748b", "A"), "app:ristretto": ("#0ea5e9", "V"),
    "app:terminal": ("#334155", "›_"), "app:thonny": ("#3b6fb6", "Py"),
}


def item_badge(cle, size=36):
    col, g = ITEM.get(cle) or (cle.startswith("app:lg_") and logiciels.badge(cle[4:])) or ("#64748b", None)
    if cle.startswith("app:") and cle[4:] in APPS and APPS[cle[4:]][1] in APP_SLOT:
        col = f"var(--s{APP_SLOT[APPS[cle[4:]][1]]})"          # couleur de l'application dans les statistiques
    inner = e(g) if g else ic("globe" if cle.startswith("dom:") else "app", int(size * 0.55))
    return f'<span class="item" translate="no" style="--c:{col};width:{size}px;height:{size}px">{inner}</span>'


WM = {"firefox": "app:firefox", "libreoffice": "app:office", "soffice": "app:office", "gcompris": "app:gcompris",
      "tuxpaint": "app:tuxpaint", "mousepad": "app:mousepad", "ristretto": "app:ristretto", "terminal": "app:terminal",
      "thonny": "app:thonny"}


def wm_item(cls_name):
    low = cls_name.lower()
    return next((v for k, v in WM.items() if k in low), None) or logiciels.wm_item(low) or "autre"


# ======================================================================
# Squelette de page
# ======================================================================
CSS = """
:root{--bg:#f3f7f6;--surface:#fff;--surface2:#ecf3f1;--text:#13292c;--text2:#3d5659;--muted:#768b8e;--border:#dce7e4;
--primary:#1b5c63;--primary-2:#144a50;--primary-soft:#e1f0ed;--on-primary:#fff;--accent:#7fb446;--accent-2:#3d8833;--accent-soft:#eef6e4;
--green:#1f9d55;--green-soft:#e2f5ea;--orange:#e7820f;--orange-soft:#fff0dc;--red:#e0464b;--red-soft:#fde8e8;
--g:#2fae64;--o:#f39a2c;--r:#e5544f;--track:#e5eeec;
--s1:#2a78d6;--s2:#eb6834;--s3:#1baf7a;--s4:#eda100;--s5:#e87ba4;--s6:#008300;--s7:#6250d6;--s8:#e34948;--s-autre:#a3a29b;--s-inactif:#d9dbe0;
--q0:#ecf2f1;--q1:#cde6e2;--q2:#9dcec8;--q3:#5ca8a4;--q4:#2a7a80;--q5:#14505a;
--shadow:0 1px 2px rgba(20,25,40,.05),0 4px 16px rgba(20,25,40,.06);--radius:18px}
@media (prefers-color-scheme:dark){:root{--bg:#0c1416;--surface:#132023;--surface2:#1a2a2d;--text:#e6f0ef;--text2:#b2c6c7;--muted:#7b9396;--border:#24373b;
--primary:#5fb5bc;--primary-2:#7cc6cc;--primary-soft:#173a3e;--on-primary:#0a1a1c;--accent:#95c75c;--accent-2:#7fb446;--accent-soft:#1f3318;
--green:#4cc77f;--green-soft:#14301f;--orange:#f6a548;--orange-soft:#38280f;--red:#f26b6f;--red-soft:#3a1b1d;
--g:#3fbf72;--o:#f5a142;--r:#ee6260;--track:#223235;
--s1:#3987e5;--s2:#d95926;--s3:#199e70;--s4:#c98500;--s5:#d55181;--s6:#008300;--s7:#9085e9;--s8:#e66767;--s-autre:#6f6e68;--s-inactif:#3a3f4a;
--q0:#1c2b2e;--q1:#14505a;--q2:#2a7a80;--q3:#4f9fa2;--q4:#82c4c3;--q5:#bfe3df;--shadow:0 1px 2px rgba(0,0,0,.3),0 6px 20px rgba(0,0,0,.25)}}
@media (prefers-color-scheme:dark){.mxt td.mx.q4 a,.mxt td.mx.q5 a{color:#0e1015}}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--text);font:15px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
a{color:var(--primary);text-decoration:none}
.ic{flex:none;vertical-align:middle}
.app{display:flex;min-height:100vh}
.side{width:248px;flex:none;position:sticky;top:0;height:100vh;padding:22px 16px;display:flex;flex-direction:column;gap:22px;
 background:var(--surface);border-right:1px solid var(--border)}
.brand{display:flex;gap:12px;align-items:center;padding:0 8px}
.brand{flex-direction:column;align-items:flex-start;gap:10px}
.brand{align-items:center}
.logo{display:block;width:100%;max-width:200px;margin:0 auto}
.logo img{display:block;width:100%;height:auto;border-radius:22%;box-shadow:0 2px 6px rgba(20,40,40,.08),0 8px 24px rgba(20,40,40,.08)}
.brand-sub{display:block;text-align:center;color:var(--muted);font-size:12.5px;font-weight:600;letter-spacing:.04em;text-transform:uppercase}
.brand b{display:block;font-size:22px;font-weight:800;letter-spacing:-.02em;line-height:1.1}.brand small{color:var(--muted);font-size:12.5px}
.wm-a{color:var(--primary)}.wm-b{color:var(--accent)}
.menu a.on{box-shadow:inset 3px 0 0 var(--accent)}
.menu{display:flex;flex-direction:column;gap:4px}
.menu a{display:flex;gap:12px;align-items:center;padding:10px 12px;border-radius:12px;color:var(--text2);font-weight:550}
.menu a:hover{background:var(--surface2)}
.menu a.on{background:var(--primary-soft);color:var(--primary)}
.side-foot{margin-top:auto}
.side-tog{position:absolute;top:30px;right:-14px;z-index:30;width:28px;height:28px;border-radius:50%;border:1px solid var(--border);background:var(--surface);
 color:var(--text2);display:grid;place-items:center;cursor:pointer;box-shadow:0 2px 8px rgba(0,0,0,.18);padding:0;transition:transform .2s}
.side-tog:hover{color:var(--primary)}.side{transition:width .2s,padding .2s}
.menu-replie .side{width:84px;padding-left:12px;padding-right:12px}.menu-replie .side-tog{transform:rotate(180deg)}
.menu-replie .side .menu a span,.menu-replie .side .brand-sub,.menu-replie .side-foot span{display:none}
.menu-replie .side .menu a,.menu-replie .side-foot .btn{justify-content:center!important;padding-left:0;padding-right:0}
.menu-replie .side .brand-l{padding:6px!important;border-radius:14px!important}.menu-replie .side .brand-l .emb{width:48px!important}
.main{flex:1;min-width:0;padding:28px 32px 48px;max-width:1240px}
.head{display:flex;justify-content:space-between;align-items:flex-end;gap:16px;flex-wrap:wrap;margin-bottom:22px}
.head h1{font-size:26px;letter-spacing:-.02em;margin:0}.head p{margin:2px 0 0;color:var(--muted)}
.charge{display:flex;gap:7px;align-items:center;padding:4px 9px;border:1px solid var(--border);border-radius:10px;background:var(--surface);font-size:12.5px;cursor:default}
.charge b{font-size:11.5px;color:var(--muted);letter-spacing:.04em}.charge .ch-v{font-variant-numeric:tabular-nums;min-width:34px;text-align:right;font-weight:650}
.ch-b{display:flex;flex-direction:column;gap:2px;width:46px}.ch-b i{display:block;height:5px;border-radius:3px;background:var(--g);transition:width .6s}
.ch-b i.m{height:3px;opacity:.75}.ch-b i.o{background:var(--o)}.ch-b i.r{background:var(--r)}.charge.off{opacity:.55}
.brand-l{display:flex;flex-direction:column;align-items:center;gap:6px;color:inherit}
.brand-l .emb{width:150px;height:auto;display:block}.brand-l .wm-img{width:170px;height:auto;display:block}
.wm{font-family:Fredoka,Nunito,system-ui,sans-serif;font-weight:700;font-size:30px;line-height:1;letter-spacing:-.01em}
.wm-a{color:var(--primary)}.wm-b{color:var(--accent)}
.m-brand{display:none}
.hero{position:relative;overflow:hidden;display:flex;align-items:center;justify-content:space-between;gap:24px;padding:26px 30px;margin-bottom:18px;
 background:linear-gradient(115deg,var(--accent-soft),var(--surface) 52%,var(--primary-soft))}
.hero::before{content:"";position:absolute;right:-70px;top:-90px;width:360px;height:360px;border-radius:50%;border:16px solid var(--accent);opacity:.22}
.hero::after{content:"";position:absolute;left:-60px;bottom:-120px;width:240px;height:240px;border-radius:50%;background:var(--accent);opacity:.08}
.hero-t{position:relative;z-index:1;min-width:0}.hero-k{font-weight:800;color:var(--accent-2);text-transform:uppercase;letter-spacing:.08em;font-size:12.5px}
.hero-ban{display:block;flex:none;width:min(440px,42%);height:auto;position:relative;z-index:1}.hero .hero-st{font-size:17px;font-weight:700;color:var(--text)}.hero-slogan{display:block;width:min(540px,100%);height:auto;margin:0 0 16px}
.card.hero h2{font-size:29px;margin:4px 0 6px;color:var(--primary);line-height:1.2}.hero p{margin:0;color:var(--text2)}.hero .hero-tm{margin:2px 0 14px}.hero-tm b{color:var(--text)}
.hero-kids{display:flex;gap:8px;flex-wrap:wrap}
.hero-kid{display:inline-flex;gap:8px;align-items:center;padding:4px 12px 4px 4px;border-radius:99px;background:var(--surface);color:var(--text);font-weight:700;font-size:14px;box-shadow:var(--shadow)}
.hero-img{position:relative;z-index:1;width:190px;height:190px;flex:none;object-fit:contain;filter:drop-shadow(0 8px 18px rgba(13,92,99,.18))}
.head-r{display:flex;gap:14px;align-items:center;flex-wrap:wrap;justify-content:flex-end}
.lang{display:flex;gap:6px;align-items:center;color:var(--muted)}.lang select{width:auto;padding:5px 8px;font-size:13.5px}
.clock{color:var(--muted);font-size:14px;display:flex;gap:6px;align-items:center}
.tabbar{display:none}
.card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);box-shadow:var(--shadow);padding:20px;min-width:0}
.card h2{font-size:17px;margin:0 0 4px;letter-spacing:-.01em}.card h3{font-size:15px;margin:0}
.muted{color:var(--muted)}.small{font-size:13px}
.grid{display:grid;gap:18px;grid-template-columns:repeat(auto-fill,minmax(340px,1fr))}
.stack{display:flex;flex-direction:column;gap:14px}.row{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.between{display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap}
.btn{display:inline-flex;gap:8px;align-items:center;justify-content:center;padding:9px 14px;border-radius:12px;border:1px solid var(--border);
 background:var(--surface);color:var(--text);font:inherit;font-weight:550;cursor:pointer;white-space:nowrap;transition:background .15s,transform .05s}
.btn:hover{background:var(--surface2)}.btn:active{transform:scale(.98)}
.btn.primary{background:var(--primary);border-color:var(--primary);color:var(--on-primary)}.btn.primary:hover{background:var(--primary-2)}
.btn.danger{color:var(--red)}.btn.ghost{border-color:transparent;background:transparent}.btn.ghost:hover{background:var(--surface2)}
.btn.icon{padding:9px}.btn.sm{padding:6px 10px;font-size:13.5px;border-radius:10px}.btn.block{width:100%}
form{margin:0}
input[type=text],input[type=number],input[type=search],textarea,select{width:100%;padding:10px 12px;border:1px solid var(--border);border-radius:12px;background:var(--surface);color:var(--text);font:inherit}
input:focus,textarea:focus,select:focus{outline:2px solid var(--primary);outline-offset:-1px;border-color:transparent}
textarea{resize:vertical;min-height:80px}
.av{display:inline-grid;place-items:center;border-radius:50%;color:#fff;font-weight:700;flex:none}
.av-sm{width:28px;height:28px;font-size:13px}.av-md{width:46px;height:46px;font-size:19px}.av-lg{width:56px;height:56px;font-size:23px}
.av0{background:var(--s1)}.av1{background:var(--s2)}.av2{background:var(--s3)}
.av3{background:var(--s4)}.av4{background:var(--s5)}.av5{background:var(--s6)}.av6{background:var(--s7)}.av7{background:var(--s8)}
.avall{background:linear-gradient(135deg,#fb923c,#f43f5e)}
/* comptes */
.acc{display:flex;gap:14px;align-items:center;flex-wrap:wrap}.acc .nm{flex:1;min-width:180px}.acc .nm h3{font-size:17px}
.acc code{background:var(--surface2);padding:2px 7px;border-radius:7px;font-size:13.5px}
.fields{display:grid;gap:14px;grid-template-columns:repeat(auto-fit,minmax(220px,1fr))}
.fields label{display:flex;flex-direction:column;gap:6px;font-weight:550;font-size:14px}.fields small{color:var(--muted);font-weight:400;font-size:12.5px}
.check{display:flex;gap:10px;align-items:flex-start;padding:12px 14px;border-radius:14px;border:1px solid var(--border);cursor:pointer}
.check input{margin-top:3px;accent-color:var(--red);width:17px;height:17px}
.pill{display:inline-flex;gap:6px;align-items:center;padding:4px 10px;border-radius:99px;font-size:12.5px;font-weight:600;background:var(--surface2);color:var(--text2);white-space:nowrap}
.pill.g{background:var(--green-soft);color:var(--green)}.pill.o{background:var(--orange-soft);color:var(--orange)}.pill.r{background:var(--red-soft);color:var(--red)}
.pill.p{background:var(--primary-soft);color:var(--primary)}
.dot{width:8px;height:8px;border-radius:50%;background:var(--muted);display:inline-block}.dot.on{background:var(--green);box-shadow:0 0 0 3px var(--green-soft)}
.dot.idle{background:var(--orange)}
/* carte enfant */
.kid{display:flex;flex-direction:column;gap:16px}
.kid-head{display:flex;gap:14px;align-items:center}.kid-head h2{font-size:19px;margin:0}
.presence{display:flex;gap:7px;align-items:center;color:var(--muted);font-size:13.5px}
.mode{border-radius:14px;padding:14px 16px;display:flex;gap:12px;align-items:flex-start}
.mode .mi{width:36px;height:36px;border-radius:11px;display:grid;place-items:center;color:#fff;flex:none}
.mode b{display:block;font-size:15.5px}.mode span{font-size:13px;color:var(--text2)}
.mode-V{background:var(--green-soft)}.mode-V .mi{background:var(--g)}.mode-V b{color:var(--green)}
.mode-O{background:var(--orange-soft)}.mode-O .mi{background:var(--o)}.mode-O b{color:var(--orange)}
.mode-R{background:var(--red-soft)}.mode-R .mi{background:var(--r)}.mode-R b{color:var(--red)}
.mode-P{background:var(--primary-soft)}.mode-P .mi{background:var(--primary)}.mode-P b{color:var(--primary)}
.sep{height:1px;background:var(--border)}
.chips{display:flex;gap:6px;flex-wrap:wrap;margin-top:8px}
.chip{display:inline-flex;gap:6px;align-items:center;padding:3px 9px 3px 4px;border-radius:99px;background:var(--surface);font-size:12.5px;color:var(--text2);border:1px solid var(--border)}
.chip .item{border-radius:50%;font-size:10px}
.kpis{display:flex;gap:22px;flex-wrap:wrap}
.kpi b{font-size:22px;letter-spacing:-.02em;display:block;line-height:1.2}.kpi span{font-size:12.5px;color:var(--muted)}
.now-list{display:flex;flex-direction:column;gap:6px}
.now-item{display:flex;gap:10px;align-items:center;padding:8px 10px;border-radius:12px;background:var(--surface2);font-size:13.5px;min-width:0}
.now-item .t{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1}
.label{font-size:12px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.04em;margin-bottom:6px}
.strip{display:grid;grid-template-columns:repeat(48,1fr);gap:1.5px}.strip i{height:10px;border-radius:2px}
.strip i.now{outline:2px solid var(--text);outline-offset:1px;border-radius:2px}
.strip-l{display:flex;justify-content:space-between;color:var(--muted);font-size:11px;margin-top:3px}
.kid-actions{display:flex;gap:8px;flex-wrap:wrap;border-top:1px solid var(--border);padding-top:14px}
.meter{height:7px;border-radius:9px;background:var(--track);overflow:hidden;min-width:60px}.meter i{display:block;height:100%;background:var(--o);border-radius:9px}
.meter i.full{background:var(--r)}
.cV{background:var(--g)}.cO{background:var(--o)}.cR{background:var(--r)}
/* onglets */
.seg{display:inline-flex;gap:4px;padding:4px;border-radius:14px;background:var(--surface2);flex-wrap:wrap}
.seg a,.seg label{display:inline-flex;gap:8px;align-items:center;padding:7px 14px;border-radius:10px;color:var(--text2);font-weight:550;cursor:pointer;font-size:14px}
.seg a.on,.seg input:checked+span{background:var(--surface);color:var(--text);box-shadow:var(--shadow)}
.seg input{position:absolute;opacity:0;pointer-events:none}.seg label{padding:0}.seg label span{display:inline-flex;gap:8px;align-items:center;padding:7px 14px;border-radius:10px}
.people{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:18px}
.people a{display:inline-flex;gap:9px;align-items:center;padding:6px 14px 6px 6px;border-radius:99px;background:var(--surface);border:1px solid var(--border);color:var(--text2);font-weight:600}
.people a.on{border-color:var(--primary);background:var(--primary-soft);color:var(--primary)}
/* options internet */
.opts{display:grid;gap:10px;grid-template-columns:repeat(auto-fit,minmax(170px,1fr))}
.opt{position:relative}.opt input{position:absolute;opacity:0}
.opt span{display:flex;flex-direction:column;gap:4px;padding:14px;border-radius:14px;border:1.5px solid var(--border);cursor:pointer;height:100%}
.opt span b{display:flex;gap:8px;align-items:center}.opt span small{color:var(--muted);font-size:12.5px}
.opt input:checked+span{border-color:var(--primary);background:var(--primary-soft)}
.opt input:focus-visible+span{outline:2px solid var(--primary)}
/* règles */
.rules{display:flex;flex-direction:column;gap:8px}
.garanti{padding:12px 14px;border-radius:14px;background:color-mix(in srgb,var(--surface) 60%,transparent);border:1px dashed var(--border);font-size:.9em}
.garanti>b{display:flex;gap:6px;align-items:center}
.garanti ul{list-style:none;margin:8px 0 0;padding:0;display:flex;flex-direction:column;gap:6px}
.garanti li{display:flex;gap:8px;align-items:flex-start}.garanti li .ic{flex:none;margin-top:3px;color:#1f9d55}
.rule{display:flex;gap:14px;align-items:center;padding:12px 14px;border-radius:14px;border:1px solid var(--border);background:var(--surface)}
.rule.inh{background:var(--surface2);border-style:dashed}
.rule .nm{flex:1;min-width:0}.rule .nm b{display:block}.rule .nm small{color:var(--muted);font-size:12.5px}
.rule .st{display:flex;flex-direction:column;align-items:flex-end;gap:5px;min-width:120px}
.item{display:inline-grid;place-items:center;border-radius:11px;background:var(--c);color:#fff;font-weight:800;font-size:14px;flex:none}
.empty{padding:22px;text-align:center;color:var(--muted);border:1.5px dashed var(--border);border-radius:14px}
.legend{display:flex;gap:10px;flex-wrap:wrap}
.legend div{display:flex;gap:10px;align-items:center;padding:10px 14px;border-radius:14px;flex:1;min-width:200px}
.legend i{width:14px;height:14px;border-radius:4px;flex:none}
/* dialogues */
dialog{border:0;border-radius:22px;padding:0;background:var(--surface);color:var(--text);width:min(560px,calc(100vw - 24px));box-shadow:0 20px 60px rgba(0,0,0,.3);max-height:calc(100vh - 32px)}
dialog::backdrop{background:rgba(15,18,30,.45);backdrop-filter:blur(3px)}
.dlg{padding:22px;display:flex;flex-direction:column;gap:16px}
.dlg h3{font-size:19px;margin:0;display:flex;gap:10px;align-items:center}
.dlg-foot{display:flex;justify-content:flex-end;gap:8px}
.tiles{display:grid;gap:8px;grid-template-columns:repeat(auto-fill,minmax(150px,1fr))}
.tile{position:relative}.tile input{position:absolute;opacity:0}
.tile span{display:flex;gap:10px;align-items:center;padding:10px;border-radius:14px;border:1.5px solid var(--border);cursor:pointer;font-size:13.5px;font-weight:550;height:100%}
.tile input:checked+span{border-color:var(--primary);background:var(--primary-soft)}
.quick{display:flex;gap:6px;flex-wrap:wrap}
.pw-bar{display:flex;height:14px;border-radius:9px;background:var(--track);overflow:hidden;margin:6px 0 4px}
.pw-bar i{display:block;height:100%;transition:width .15s}.pw-use{background:var(--primary)}.pw-lim{background:var(--accent)}
.pw-leg{display:flex;gap:4px 14px;flex-wrap:wrap}.pw-leg i{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:6px;vertical-align:-1px}
.pw-leg .pw-free{background:var(--track);border:1px solid var(--border)}.pw-range output{font-size:22px}.pw-range input{height:28px}
.pw-alert{white-space:normal;border-radius:12px;align-items:flex-start;line-height:1.4}.pw-alert svg{flex:none;margin-top:2px}
.pw-kid{display:flex;gap:10px;align-items:center}.pw-kid-b{flex:1;min-width:0;display:flex;flex-direction:column;gap:5px}
.pw-note{margin:0;padding-left:18px;display:flex;flex-direction:column;gap:8px;line-height:1.5}
.range{display:flex;gap:12px;align-items:center}.range input{flex:1;accent-color:var(--primary)}.range output{font-weight:700;min-width:70px;text-align:right}
.choice{display:grid;gap:8px}
.choice button{justify-content:flex-start;padding:14px}
/* planning */
.brushes{display:grid;gap:8px;grid-template-columns:repeat(auto-fit,minmax(190px,1fr))}
.brush{display:flex;gap:12px;align-items:center;padding:12px 14px;border-radius:14px;border:1.5px solid var(--border);background:var(--surface);cursor:pointer;text-align:left;font:inherit;color:var(--text)}
.brush i{width:22px;height:22px;border-radius:7px;flex:none}.brush b{display:block}.brush small{color:var(--muted);font-size:12.5px}
.brush.on{border-color:var(--primary);box-shadow:0 0 0 3px var(--primary-soft)}
.pgw{overflow-x:auto;-webkit-overflow-scrolling:touch}
table.pg{border-collapse:separate;border-spacing:4px 1.5px;width:100%;min-width:420px;user-select:none;-webkit-user-select:none}
.pg th{font-size:11px;color:var(--muted);font-weight:500;text-align:right;padding:0 8px 0 0;white-space:nowrap;line-height:1;width:46px}
.pg thead th{text-align:center;padding:0 0 8px;font-size:13px;font-weight:650;color:var(--text2)}
.pg thead th.today{color:var(--primary)}
.pg td{height:14px;padding:0;border-radius:3px;cursor:crosshair;touch-action:none;transition:filter .1s}
.pg td:hover{filter:brightness(1.12)}
.pg tr.h td{box-shadow:0 -1.5px 0 var(--surface)}
.pg td.now{outline:2.5px solid var(--text);outline-offset:0}
.pg tr.q td{height:auto;background:none;cursor:default;touch-action:auto;padding-top:10px}
.pg tr.q th{line-height:1.25;padding-top:10px;font-size:11px}
.pg tr.q input{padding:6px 2px;font-size:13px;text-align:center;border-radius:9px}
.savebar{position:sticky;bottom:12px;margin-top:16px;display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;
 padding:12px 16px;border-radius:16px;background:var(--surface);border:1px solid var(--border);box-shadow:var(--shadow)}
.savebar .dirty{color:var(--orange);font-weight:600;display:none}.savebar.is-dirty .dirty{display:inline}
/* statistiques */
.kpi-grid{display:grid;gap:14px;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));margin-bottom:18px}
.kpi-card{padding:18px}.kpi-card b{font-size:28px;letter-spacing:-.03em;display:block}.kpi-card span{color:var(--muted);font-size:13px}
.bars{display:flex;flex-direction:column;gap:9px;margin-top:12px}
.bar{display:grid;grid-template-columns:minmax(90px,160px) 1fr 68px;gap:12px;align-items:center;font-size:14px}
.bar .lab{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--text2)}
.bar .trk{height:12px;background:var(--track);border-radius:6px;overflow:hidden}
.bar .fill{height:100%;background:var(--primary);border-radius:6px;min-width:3px}
.bar .val{text-align:right;color:var(--text2);font-variant-numeric:tabular-nums}
.bar:hover .fill{filter:brightness(1.12)}
table.t{width:100%;border-collapse:collapse;font-size:14px}.t th,.t td{text-align:left;padding:9px 8px;border-bottom:1px solid var(--border);vertical-align:top}
.t th{color:var(--muted);font-weight:550;font-size:12.5px}.t td.n{text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}
.tw{overflow-x:auto}
/* chronologie (statistiques détaillées) */
.gantt{display:flex;flex-direction:column;gap:8px;margin-top:14px}
.grow{display:grid;grid-template-columns:minmax(110px,180px) 1fr 62px;gap:12px;align-items:center;font-size:13.5px}
.grow .lab{display:flex;gap:8px;align-items:center;min-width:0;overflow:hidden;white-space:nowrap;text-overflow:ellipsis;color:var(--text2)}
.grow .val{text-align:right;color:var(--text2);font-variant-numeric:tabular-nums}
.gtrack{position:relative;height:22px;background:var(--track);border-radius:7px}
.gtrack i{position:absolute;top:3px;bottom:3px;border-radius:4px;background:var(--c);min-width:3px}
.gtrack i:hover{filter:brightness(1.15);box-shadow:0 0 0 2px var(--text)}
.gtrack .nowl{position:absolute;top:-4px;bottom:-4px;width:2px;background:var(--text);border-radius:2px;min-width:0}
.gscale{position:relative;height:16px;font-size:11px;color:var(--muted)}
.gscale span{position:absolute;transform:translateX(-50%);white-space:nowrap}
.chips2{display:flex;gap:6px;flex-wrap:wrap}
.chips2 a{display:inline-flex;gap:7px;align-items:center;padding:4px 12px 4px 4px;border-radius:99px;border:1px solid var(--border);background:var(--surface);color:var(--text2);font-weight:600;font-size:13.5px}
.chips2 a.on{border-color:var(--primary);background:var(--primary-soft);color:var(--primary)}
.chips2 a.txt{padding:4px 12px}
.daynav{display:flex;gap:6px;align-items:center;flex-wrap:wrap}.daynav input{width:auto;padding:6px 10px}
.t td .tt{color:var(--muted);font-size:12.5px;display:block;max-width:520px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.t td.who{white-space:nowrap}.t td.who a{display:inline-flex;gap:8px;align-items:center;color:var(--text);font-weight:600}
/* graphiques */
.sw{display:inline-block;width:11px;height:11px;border-radius:3px;background:var(--c);flex:none}
.vlegend{display:flex;gap:6px 14px;flex-wrap:wrap;font-size:13px;color:var(--text2)}.vlegend span{display:inline-flex;gap:6px;align-items:center}
.vchart{position:relative;height:220px;margin:6px 0 4px 58px}
.vgrid{position:absolute;inset:0 0 22px 0}
.vgl{position:absolute;left:0;right:0;border-top:1px solid var(--border)}
.vgl span{position:absolute;right:calc(100% + 8px);top:-8px;font-size:11px;color:var(--muted);white-space:nowrap}
.vcols{position:absolute;inset:0;display:flex;gap:4px;align-items:stretch}
.vcol{flex:1;min-width:0;display:flex;flex-direction:column;align-items:center;cursor:default}
.vstack{flex:1;width:100%;max-width:44px;display:flex;flex-direction:column-reverse;gap:2px;border-radius:4px 4px 0 0;overflow:hidden}
.vstack i{display:block;background:var(--c);flex:none}
.vcol:hover .vstack{filter:brightness(1.1)}
.vx{height:22px;line-height:22px;font-size:11px;color:var(--muted);white-space:nowrap}.vx.today{color:var(--primary);font-weight:700}
.heat{display:flex;flex-direction:column;gap:3px;overflow-x:auto}
.hrow{display:grid;grid-template-columns:minmax(78px,140px) repeat(24,minmax(9px,1fr)) 54px;gap:2px;align-items:center;font-size:13px;min-width:430px}
.hrow i{height:22px;border-radius:3px}.hrow i:hover{box-shadow:0 0 0 2px var(--text)}
.hrow .lab{display:flex;gap:8px;align-items:center;min-width:0;overflow:hidden;white-space:nowrap;color:var(--text2)}
.hrow .val{text-align:right;color:var(--text2);font-variant-numeric:tabular-nums;font-size:12.5px}
.hhead b{font-size:11px;color:var(--muted);font-weight:500;text-align:left}
.hleg{display:flex;gap:4px;align-items:center;font-size:12px;color:var(--muted);margin-top:4px}.hleg i{width:18px;height:12px;border-radius:3px}
.mxt td.mx{text-align:center;font-variant-numeric:tabular-nums;padding:0}.mxt td.mx a{display:block;padding:9px 8px;color:var(--text)}
.mxt td.mx.q4 a,.mxt td.mx.q5 a{color:#fff;font-weight:600}
.mxt th.n{text-align:center;font-size:12px}
.lchart{position:relative;margin:6px 0 4px 58px}.lchart.withend{margin-right:120px}
.lplot{position:absolute;inset:0 0 22px 0}
.lplot svg{position:absolute;inset:0;width:100%;height:100%;overflow:visible}
.lhit{position:absolute;top:0;bottom:0;transform:translateX(-50%);z-index:2}
.lhit:hover::after{content:"";position:absolute;left:50%;top:0;bottom:0;border-left:1px solid var(--text2)}
.ldot{position:absolute;width:8px;height:8px;border-radius:50%;background:var(--c);box-shadow:0 0 0 2px var(--surface);transform:translate(-50%,-50%);z-index:1}
.lend{position:absolute;left:calc(100% + 10px);transform:translateY(-50%);font-size:12px;color:var(--text2);white-space:nowrap;display:flex;gap:5px;align-items:center}
.lx{position:absolute;bottom:0;transform:translateX(-50%);font-size:11px;color:var(--muted);white-space:nowrap}
.mults{display:grid;gap:18px 22px;grid-template-columns:repeat(auto-fill,minmax(320px,1fr))}
.mult .mh{display:inline-flex;gap:8px;align-items:center;font-weight:650;color:var(--text);margin-bottom:2px}
.stats-bar{display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap;margin-bottom:18px;position:sticky;top:0;z-index:5;
 padding:8px 0;background:var(--bg)}
.chead{display:flex;gap:12px;align-items:flex-start}.chead h2{margin:0 0 2px}
.cico{width:34px;height:34px;border-radius:10px;display:grid;place-items:center;background:var(--primary-soft);color:var(--primary);flex:none}
.lg-sec{border-top:1px solid var(--border);padding:4px 0}.lg-sec:first-of-type{border-top:0}
.lg-sec>summary{list-style:none;cursor:pointer;display:flex;gap:10px;align-items:center;padding:10px 4px;border-radius:12px}
.lg-sec>summary::-webkit-details-marker{display:none}.lg-sec>summary:hover{background:var(--surface2)}
.lg-sec>summary::before{content:"";width:9px;height:9px;border-right:2.5px solid var(--muted);border-bottom:2.5px solid var(--muted);transform:rotate(-45deg);transition:transform .15s;margin:0 4px}
.lg-sec[open]>summary::before{transform:rotate(45deg)}.lg-sec>summary .lg-cat{margin:0;flex:none}.lg-sec .lg-grid{padding:4px 0 14px}
.lg-tools{display:flex;gap:8px;align-items:center;flex-wrap:wrap}.lg-tools input{flex:1;min-width:200px}.lg-card[hidden],.lg-sec[hidden]{display:none}
.lg-grid{display:grid;gap:12px;grid-template-columns:repeat(auto-fill,minmax(min(100%,260px),1fr))}
.lg-card{display:flex;gap:12px;align-items:flex-start;padding:14px;border:1px solid var(--border);border-radius:14px;background:var(--surface)}
.lg-card .nm{flex:1;min-width:0;display:flex;flex-direction:column;align-self:stretch}.lg-card p{margin:3px 0 10px;font-size:13px;color:var(--text2);flex:1}
.lg-foot{display:flex;justify-content:space-between;align-items:center;gap:8px}.lg-cat{margin:14px 0 8px;font-size:13px;text-transform:uppercase;letter-spacing:.06em;color:var(--text2)}
.lg-row{display:flex;gap:12px;align-items:center;flex-wrap:wrap;padding:10px 0;border-top:1px solid var(--border)}.lg-row:first-of-type{border-top:0}.lg-row .nm{flex:1;min-width:160px}
.lg-notes{margin:0;padding-left:18px;display:grid;gap:8px;font-size:13.5px;color:var(--text2)}
.lg-job{display:flex;gap:14px;align-items:center;margin-bottom:18px}.lg-job.ok{border-color:var(--green)}.lg-job.err{border-color:var(--red)}
.lg-job pre{white-space:pre-wrap;font-size:11.5px;max-height:220px;overflow:auto}
.spin{width:22px;height:22px;border-radius:50%;border:3px solid var(--primary-soft);border-top-color:var(--primary);animation:spin 1s linear infinite;flex:none}
@keyframes spin{to{transform:rotate(360deg)}}
.grid2{display:grid;gap:18px;grid-template-columns:repeat(auto-fit,minmax(min(100%,460px),1fr))}
.ktiles{display:grid;gap:14px;grid-template-columns:repeat(auto-fit,minmax(min(100%,230px),1fr));margin-bottom:18px}
.ktile{display:flex;flex-direction:column;gap:4px;color:var(--text);transition:transform .12s,box-shadow .12s}
.ktile:hover{transform:translateY(-2px);box-shadow:0 2px 4px rgba(20,25,40,.06),0 10px 28px rgba(20,25,40,.1)}
.kt-head{display:flex;gap:12px;align-items:center;margin-bottom:6px}.kt-head b{display:block;font-size:16px}
.fav{display:inline-flex;gap:6px;align-items:center;font-size:12.5px;color:var(--text2)}
.kt-num{font-size:30px;font-weight:750;letter-spacing:-.03em;line-height:1.1}.kt-sub{font-size:13px;color:var(--muted)}
.delta{font-size:12.5px;color:var(--text2);font-weight:600}
.spark{width:100%;height:34px;margin-top:8px;display:block}
.kpi-card .spark{margin-top:10px}.kpi-card b{display:flex;gap:8px;align-items:center}.kpi-card .delta{display:block;margin-top:4px}
.ins-card{background:linear-gradient(135deg,var(--primary-soft),var(--surface) 70%);margin-bottom:18px}
.insights{margin:0;padding:0;list-style:none;display:grid;gap:8px}
.insights li{position:relative;padding-left:22px;line-height:1.5}
.insights li::before{content:"";position:absolute;left:4px;top:.55em;width:8px;height:8px;border-radius:50%;background:var(--accent)}
.insights .delta{font-weight:500}
details.more{border-top:1px solid var(--border);padding-top:10px}
details.more summary{cursor:pointer;font-weight:600;color:var(--primary);list-style:none;display:inline-flex;gap:6px;align-items:center}
details.more summary::-webkit-details-marker{display:none}
details.more summary::before{content:"▸";transition:transform .15s;display:inline-block}details.more[open] summary::before{transform:rotate(90deg)}
details.more[open] summary{margin-bottom:10px}
.bar .lab{display:flex;gap:7px;align-items:center}
/* aide */
.help-layout{display:grid;grid-template-columns:210px 1fr;gap:18px;align-items:start}
.toc{position:sticky;top:12px;display:flex;flex-direction:column;gap:2px;padding:12px}
.toc a{padding:7px 10px;border-radius:9px;color:var(--text2);font-weight:550;font-size:14px}.toc a:hover{background:var(--surface2);color:var(--primary)}
.help-sec{scroll-margin-top:16px}.help-sec p{margin:0;line-height:1.6}.help-sec code{background:var(--surface2);padding:1px 6px;border-radius:6px;font-size:13px;word-break:break-all}
.help-hero{display:flex;gap:22px;align-items:center;background:linear-gradient(135deg,var(--primary-soft),var(--surface) 65%)}
.help-hero img{width:150px;height:auto;border-radius:22%;flex:none;box-shadow:0 4px 16px rgba(20,40,40,.12)}
.help-hero h2{font-size:21px;margin:0 0 8px;line-height:1.3}.help-hero p{margin:0 0 8px;line-height:1.6}
.help-goals{display:grid;gap:12px;grid-template-columns:repeat(auto-fit,minmax(min(100%,220px),1fr))}
.help-goals>div{padding:14px;border-radius:14px;background:var(--surface2)}.help-goals p{margin:4px 0 0;font-size:14px;color:var(--text2)}
.arch{display:flex;flex-direction:column;gap:8px;align-items:stretch}
.arch-users{display:grid;grid-template-columns:1fr 1fr;gap:10px}.arch-arrow{text-align:center;color:var(--accent);font-size:18px;line-height:1}
.arch-box{display:flex;flex-direction:column;gap:4px;padding:12px 14px;border-radius:14px;border:1.5px solid var(--border);background:var(--surface)}
.arch-box span{font-size:13px;color:var(--text2)}.arch-box .ic{color:var(--primary)}
.arch-box.kid,.arch-box.parent{background:var(--accent-soft);border-color:transparent}
.arch-host{border:2px dashed var(--border);border-radius:18px;padding:12px}.arch-vm{border:2px solid var(--primary);border-radius:16px;padding:12px;background:var(--primary-soft)}
.arch-title{font-size:12.5px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.04em;margin-bottom:8px}
.arch-vm .arch-title{color:var(--primary)}.arch-row{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.help-steps{margin:0;padding-left:22px;display:grid;gap:10px;line-height:1.6}
.help-list{margin:0;padding-left:20px;display:grid;gap:8px;line-height:1.55}
.help-pages{display:grid;gap:12px}.help-page{display:flex;gap:12px;align-items:flex-start}.help-page p{margin:2px 0 0;color:var(--text2);font-size:14px}
.help-legend{display:flex;gap:10px;flex-wrap:wrap}.help-legend div{display:flex;gap:10px;align-items:center;padding:10px 14px;border-radius:14px;flex:1;min-width:200px}
.help-legend i{width:14px;height:14px;border-radius:4px;flex:none}
details.faq{padding:10px 0 0}details.faq p{margin:0 0 6px 18px;color:var(--text2)}
@media (max-width:860px){.help-layout{grid-template-columns:1fr}.toc{position:static;flex-direction:row;flex-wrap:wrap}.arch-users,.arch-row{grid-template-columns:1fr}
 .help-hero{flex-direction:column;align-items:flex-start}.help-hero img{width:110px}}
#vtip{position:fixed;z-index:60;pointer-events:none;max-width:320px;padding:8px 11px;border-radius:10px;background:var(--text);color:var(--surface);
 font-size:12.5px;line-height:1.45;white-space:pre-line;opacity:0;transition:opacity .1s;box-shadow:0 6px 20px rgba(0,0,0,.25)}
/* notifications */
#toast{position:fixed;top:18px;left:50%;transform:translate(-50%,-250%);z-index:50;display:flex;gap:10px;align-items:center;max-width:min(560px,calc(100vw - 24px));
 padding:12px 18px;border-radius:14px;background:var(--text);color:var(--surface);box-shadow:0 10px 30px rgba(0,0,0,.25);font-weight:550;transition:transform .35s cubic-bezier(.2,.9,.3,1.2)}
#toast.show{transform:translate(-50%,0)}#toast:empty{display:none}
@media (max-width:860px){
 .side{display:none}.main{padding:18px 16px 96px}
 .head h1{font-size:22px}
 .tabbar{display:flex;position:fixed;bottom:0;left:0;right:0;z-index:20;background:var(--surface);border-top:1px solid var(--border);padding:6px 4px calc(6px + env(safe-area-inset-bottom))}
 .tabbar a{flex:1;display:flex;flex-direction:column;align-items:center;gap:2px;font-size:11px;color:var(--muted);padding:4px;border-radius:10px;font-weight:600}
 .tabbar a.on{color:var(--primary)}
 .grid,.grid2,.ktiles,.mults{grid-template-columns:minmax(0,1fr)}
 .head-r{justify-content:flex-start;gap:8px;width:100%}
 .m-brand{display:flex;flex-direction:row;gap:8px;margin-bottom:10px}.m-brand{align-items:center;background:#fff;border-radius:14px;padding:6px 12px;width:max-content;box-shadow:var(--shadow)}.m-brand .emb{width:64px}.m-brand .wm-img{width:140px}
 .hero{padding:20px;gap:12px;flex-direction:column-reverse;align-items:stretch}.hero-ban{width:100%}.hero-img{width:96px;height:96px;align-self:flex-start}.card.hero h2{font-size:21px}.head-r .clock{display:none}.lang select{max-width:118px}
 .main{overflow-x:hidden}
 .bar{grid-template-columns:92px 1fr 58px}
 .rule .st{min-width:0}
}
"""

JS = """const _t=s=>(window.I18N&&I18N[s])||s;
{const ls=document.getElementById('lang-sel');if(ls){ls.value=document.documentElement.lang||'fr';
 ls.onchange=()=>{const u=new URL(location);u.searchParams.set('lang',ls.value);u.searchParams.delete('msg');location=u}}}
{const maj=d=>{for(const k of ['vm','hote']){const el=document.getElementById('ch-'+k);if(!el)continue;const x=d[k];
 el.classList.toggle('off',!x);const b=el.querySelectorAll('.ch-b i'),n=v=>v>=85?'r':v>=60?'o':'g';
 if(x){b[0].style.width=x.cpu+'%';b[0].className=n(x.cpu);b[1].style.width=x.mem+'%';b[1].className='m '+n(x.mem);
  el.querySelector('.ch-v').textContent=x.cpu+' %';el.dataset.tip=_t('Processeur')+' '+x.cpu+' % · '+_t('Mémoire')+' '+x.mem+' %'}
 else{b[0].style.width=b[1].style.width='0';el.querySelector('.ch-v').textContent='—';el.dataset.tip=_t('Pas de nouvelles du PC hôte (script charge_hote.ps1 arrêté ?)')}}};
 if(document.getElementById('ch-vm'))setInterval(()=>{if(document.hidden)return;fetch('/api/charge',{cache:'no-store'}).then(r=>r.ok&&r.json()).then(d=>d&&maj(d)).catch(()=>{})},5000)}
{const ts=document.getElementById('theme-sel');if(ts)ts.onchange=()=>{const u=new URL(location);u.searchParams.set('theme',ts.value);u.searchParams.delete('msg');location=u}}
{const b=document.getElementById('side-tog');if(b)b.onclick=()=>{const r=document.body.classList.toggle('menu-replie');
 try{localStorage.setItem('maranyse-menu',r?'replie':'ouvert')}catch(e){}}}
document.querySelectorAll('select[data-submit]').forEach(s=>s.onchange=()=>s.form.requestSubmit());
const $=(s,r=document)=>r.querySelector(s),$$=(s,r=document)=>[...r.querySelectorAll(s)];
$$('[data-open]').forEach(b=>b.addEventListener('click',()=>{const d=document.getElementById(b.dataset.open);if(b.dataset.preset)preset(d,JSON.parse(b.dataset.preset));d.showModal()}));
$$('dialog').forEach(d=>{d.addEventListener('click',ev=>{if(ev.target===d)d.close()});$$('[data-close]',d).forEach(b=>b.addEventListener('click',()=>d.close()))});
const cd=$('#dlg-confirm');
$$('form[data-confirm]').forEach(f=>f.addEventListener('submit',ev=>{if(f.dataset.ok)return;ev.preventDefault();
 $('#cf-text').textContent=f.dataset.confirm;$('#cf-yes').textContent=f.dataset.yes||_t('Confirmer');cd.showModal();
 $('#cf-yes').onclick=()=>{f.dataset.ok=1;cd.close();f.requestSubmit()}}));
$$('[data-fill-text]').forEach(b=>b.addEventListener('click',()=>{const t=b.closest('form').querySelector('textarea');t.value=b.dataset.fillText;t.focus()}));
$$('[data-auto] input').forEach(i=>i.addEventListener('change',()=>i.form.submit()));
// règle : afficher le champ du site libre et la durée
function sync(d){const c=$('input[name=cle]:checked',d),m=$('input[name=mode]:checked',d);
 $('.dom',d).style.display=c&&c.value==='dom:'?'':'none';$('.mins',d).style.display=m&&m.value==='limiter'?'':'none';
 const o=$('output',d),r=$('input[type=range]',d);if(o&&r){const v=+r.value;o.textContent=v>=60?Math.floor(v/60)+' '+_t('h')+(v%60?' '+String(v%60).padStart(2,'0'):''):v+' '+_t('min')}}
function preset(d,p){const c=$(`input[name=cle][value="${p.cle}"]`,d);if(c)c.checked=true;else{$('input[name=cle][value="dom:"]',d).checked=true;$('.dom input',d).value=p.cle.slice(4)}
 const m=$(`input[name=mode][value="${p.mode}"]`,d);if(m)m.checked=true;if(p.minutes)$('input[type=range]',d).value=p.minutes;sync(d)}
$$('dialog.rule-dlg').forEach(d=>{d.addEventListener('input',()=>sync(d));sync(d)});
// nouveau compte : identifiant proposé d'après le prénom
const pn=$('#new-nom'),pl=$('#new-login');if(pn&&pl){pn.addEventListener('input',()=>{if(!pl.dataset.touched)pl.value=pn.value.normalize('NFD')
 .replace(/[\\u0300-\\u036f]/g,'').toLowerCase().replace(/[^a-z0-9]+/g,'_').replace(/^[^a-z]+/,'').replace(/_+$/,'').slice(0,31)});
 pl.addEventListener('input',()=>pl.dataset.touched=pl.value?1:'')}
// info-bulles des graphiques (survol, ou toucher sur téléphone)
const vt=document.createElement('div');vt.id='vtip';document.body.appendChild(vt);
const showTip=ev=>{const t=ev.target.closest&&ev.target.closest('[data-tip]');if(!t){vt.style.opacity=0;return}
 vt.textContent=t.dataset.tip;vt.style.opacity=1;const w=vt.offsetWidth,h=vt.offsetHeight;
 let x=ev.clientX+14,y=ev.clientY+14;if(x+w>innerWidth-8)x=ev.clientX-w-14;if(y+h>innerHeight-8)y=ev.clientY-h-14;
 vt.style.left=Math.max(8,x)+'px';vt.style.top=Math.max(8,y)+'px'};
addEventListener('pointermove',showTip);addEventListener('pointerdown',showTip);addEventListener('scroll',()=>vt.style.opacity=0,{passive:true});
// notification
const t=$('#toast');if(t&&t.textContent.trim()){setTimeout(()=>t.classList.add('show'),60);setTimeout(()=>t.classList.remove('show'),4200);
 const u=new URL(location);u.searchParams.delete('msg');history.replaceState(null,'',u)}
// actualisation automatique (accueil)
if(document.body.dataset.refresh){setInterval(()=>{if(!$('dialog[open]')&&!document.activeElement.matches('input,textarea,select'))location.reload()},20000)}
"""


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


def shell(active, title, sub, body, flash="", refresh=False):
    now = datetime.now()
    theme = getattr(REQ, "theme", themes.DEFAUT)
    police = (f'<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link rel="stylesheet" href="{themes.POLICES[theme]}">'
              if theme in themes.POLICES else "")
    links = "".join(f'<a href="/?p={k}" class="{"on" if k == active else ""}" title="{lab}">{ic(i)}<span>{lab}</span></a>' for k, lab, i in PAGES)
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#1b5c63"><title>MaranYSE · Parents</title><link rel="icon" type="image/png" href="/favicon.png?v={V_IMG}">{police}<style>{CSS}{themes.CSS.get(theme, "")}</style></head>
<body{' data-refresh="1"' if refresh else ''}><script>try{{if(localStorage.getItem('maranyse-menu')==='replie')document.body.classList.add('menu-replie')}}catch(e){{}}</script><div class="app">
<aside class="side"><button type="button" class="side-tog" id="side-tog" title="Réduire ou agrandir le menu" aria-label="Réduire ou agrandir le menu">{ic("replier", 16)}</button><div class="brand"><a class="brand-l" translate="no" href="/?p=live" title="MaranYSE"><img class="emb" src="/logo-hd.jpg?v={V_IMG}" alt="MaranYSE"></a><small class="brand-sub">Espace parents</small></div>
<nav class="menu">{links}</nav>
<div class="side-foot"><form method="post" data-confirm="Redémarrer le bureau ? Toutes les sessions ouvertes seront fermées." data-yes="Redémarrer">
{hidden(a="restart", back=f"/?p={active}")}<button class="btn ghost block" style="justify-content:flex-start;color:var(--muted)" title="Redémarrer le bureau">{ic("power", 18)}<span>Redémarrer le bureau</span></button></form></div></aside>
<main class="main"><a class="brand-l m-brand" translate="no" href="/?p=live" title="MaranYSE"><img class="emb" src="/logo-petit.jpg?v={V_IMG}" alt=""><img class="wm-img" src="/titre.jpg?v={V_IMG}" alt="MaranYSE"></a><div class="head"><div><h1>{title}</h1><p>{sub}</p></div>
<div class="head-r">{charge_html()}<div class="clock">{ic("clock", 16)} {JOURS[now.weekday()]} {now.day} {MOIS[now.month - 1]} · {now:%H:%M}</div>
<label class="lang" title="Apparence de l'espace parents">{ic("palette", 16)}<select id="theme-sel" aria-label="Apparence">{themes.options(theme)}</select></label>
<label class="lang" title="Langue de l'espace parents">{ic("globe", 16)}<select id="lang-sel" translate="no" aria-label="Langue">{LANG_OPTIONS}</select></label></div></div>{body}</main></div>
<nav class="tabbar">{links}</nav>
<div id="toast" role="status">{ic("check", 18) + e(flash) if flash else ""}</div>
<dialog id="dlg-confirm"><div class="dlg"><h3>Confirmation</h3><p id="cf-text" style="margin:0"></p>
<div class="dlg-foot"><button class="btn" data-close>Annuler</button><button class="btn primary" id="cf-yes">Confirmer</button></div></div></dialog>
<script>{JS}</script></body></html>"""


def hidden(**kw):
    return "".join(f'<input type="hidden" name="{k}" value="{e(v)}">' for k, v in kw.items())


def people_tabs(page, cur, extra="", allow_all=False):
    out = ""
    if allow_all:
        out += f'<a href="/?p={page}&s={ALL}{extra}" class="{"on" if cur == ALL else ""}"><span class="av avall av-sm">{ic("users", 15)}</span>Tous les enfants</a>'
    out += "".join(f'<a href="/?p={page}&s={quote(u)}{extra}" class="{"on" if u == cur else ""}">{avatar(u, "sm")}{e(nom(u))}</a>' for u in USERS)
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
    g, cur = r["grille"][str(now.weekday())], (now.hour * 60 + now.minute) // 30
    cells = "".join(f'<i class="c{g[k]}{" now" if k == cur else ""}" title="{hhmm(k)} : {ETAT[g[k]]}"></i>' for k in range(SLOTS))
    return (f'<div><div class="label">Planning du jour</div><div class="strip">{cells}</div>'
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
    more = f"""<dialog id="more-{u}"><div class="dlg"><h3>{avatar(u, "sm")} Compte de {e(nom(u))}</h3>
<div><div class="label">Identifiant</div><code translate="no">{e(u)}</code></div>
<div><div class="label">Mot de passe actuel</div><code style="font-size:16px" translate="no">{e(pw)}</code></div>
<form method="post" class="stack">{hidden(a="pw", u=u, back=back)}<div class="label" style="margin:0">Nouveau mot de passe</div>
<input type="text" name="v" placeholder="4 caractères minimum" required minlength="4">
<div class="dlg-foot"><button type="button" class="btn" data-close>Fermer</button><button class="btn primary">{ic("key", 18)} Changer</button></div></form>
<a href="/?p=comptes" class="small">{ic("users", 15)} Ajouter, renommer ou supprimer des comptes</a></div></dialog>"""
    return msg + pause + more


def c2_total():
    """Temps d'écran de toute la famille aujourd'hui (secondes)."""
    c = db()
    try:
        return sum(used_today(c, u) for u in USERS)
    finally:
        c.close()


def banniere(total, online):
    """Bannière d'accueil : emblème MaranYSE, salutation, résumé du jour et enfants en ligne."""
    h = datetime.now().hour
    salut = "Bonsoir" if h >= 18 or h < 5 else "Bonjour"
    disp = displays()
    kids = "".join(f'<a class="hero-kid" href="/?p=stats&vue=enfant&s={quote(u)}">{avatar(u, "sm")}<span>{e(nom(u))}</span>'
                   f'<i class="dot{" on" if u in disp else ""}"></i></a>' for u in USERS)
    etat = f"{online} enfant{'s' if online > 1 else ''} en ligne" if online else "Aucun enfant connecté pour le moment"
    return (f'<section class="card hero"><div class="hero-t"><p class="hero-st">{etat}</p>'
            f'<p class="hero-tm"><b>{dur(total)}</b> d\'écran aujourd\'hui pour toute la famille</p><div class="hero-kids">{kids}</div></div>'
            f'<img class="hero-ban" src="/banniere.jpg?v={V_IMG}" alt="MaranYSE — One VM, Many Accounts" translate="no"></section>')


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
    cards, online = [], 0
    for u in USERS:
        s, used = last.get(u), used_today(c, u)
        connected = bool(s and (s["ip"], s["port"]) in act and u in disp)
        online += connected
        lvl, why, left = access(u, data[u], datetime.now(), used)
        prof = profile(data, u, lvl, c)
        if connected:
            pres = f'<span class="dot on"></span>En ligne depuis {fmt_ts(s["ts"])} · {e(s["name"] or s["ip"])}'
        elif u in disp:
            pres = f'<span class="dot idle"></span>Session ouverte, déconnecté'
        else:
            pres = f'<span class="dot"></span>Hors ligne' + (f' · vu {fmt_ts(s["ts"])}' if s else "")
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
    return shell("live", "Accueil", sub, banniere(c2_total(), online) + f'<div class="grid">{"".join(cards)}</div>', flash, refresh=True)


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
}


def planning_grid(r):
    now = datetime.now()
    cur = (now.weekday(), (now.hour * 60 + now.minute) // 30)
    head = "<thead><tr><th></th>" + "".join(f'<th class="{"today" if d == now.weekday() else ""}">{j[:3]}</th>' for d, j in enumerate(JOURS)) + "</tr></thead>"
    rows = []
    for k in range(SLOTS):
        cells = "".join(
            f'<td class="c{r["grille"][str(d)][k]}{" now" if (d, k) == cur else ""}" data-d="{d}" '
            f'title="{JOURS[d]} {hhmm(k)}–{hhmm(k + 1) if k < SLOTS - 1 else "24:00"}"></td>' for d in range(7))
        rows.append(f"<tr{' class=h' if k % 2 == 0 else ''}><th>{hhmm(k) if k % 2 == 0 else ''}</th>{cells}</tr>")
    quota = ('<tr class="q"><th>Écran<br>max/jour<br>(min)</th>' +
             "".join(f'<td><input type="number" min="0" max="1440" step="15" name="quota_{d}" value="{int(r["quota"].get(str(d)) or 0)}" '
                     f'title="Temps d\'écran maximum le {JOURS[d]} (0 = pas de limite)"></td>' for d in range(7)) + "</tr>")
    hid = "".join(f'<input type="hidden" name="grille_{d}" value="{r["grille"][str(d)]}">' for d in range(7))
    tpl = json.dumps({k: v[2] for k, v in TEMPLATES.items()})
    tpl_btns = "".join(f'<button type="button" class="btn sm" data-tpl="{k}" title="{e(v[1])}">{ic("sparkle", 15)} {e(v[0])}</button>' for k, v in TEMPLATES.items())
    return f"""
<div class="brushes">
 <button type="button" class="brush on" data-b="V"><i class="cV"></i><div><b>Vert</b><small>Accès complet</small></div></button>
 <button type="button" class="brush" data-b="O"><i class="cO"></i><div><b>Orange</b><small>Accès avec les règles</small></div></button>
 <button type="button" class="brush" data-b="R"><i class="cR"></i><div><b>Rouge</b><small>Pas d'accès</small></div></button>
</div>
<div class="between"><span class="muted small">Choisissez une couleur, puis cliquez ou glissez sur les cases (1 case = 30 min).</span>
<div class="row"><span class="muted small">Modèles :</span>{tpl_btns}</div></div>
<div class="row"><button type="button" class="btn sm" data-copy="0:0-4">Copier lundi → lun–ven</button>
<button type="button" class="btn sm" data-copy="5:6">Copier samedi → dimanche</button></div>
<div class="pgw"><table class="pg" id="pg">{head}<tbody>{''.join(rows)}{quota}</tbody></table></div>{hid}
<script>(()=>{{const t=document.getElementById('pg');let b='V',down=false;const T={tpl};
const dirty=()=>{{const bar=document.querySelector('.savebar');if(bar)bar.classList.add('is-dirty')}};
document.querySelectorAll('.brush').forEach(x=>x.onclick=()=>{{b=x.dataset.b;document.querySelectorAll('.brush').forEach(y=>y.classList.toggle('on',y===x))}});
const cells=d=>[...t.querySelectorAll('td[data-d="'+d+'"]')];
const get=d=>cells(d).map(td=>td.className.match(/c([VOR])/)[1]).join('');
const setc=(td,s)=>{{td.className=td.className.replace(/c[VOR]/,'c'+s)}};
const set=(d,s)=>cells(d).forEach((td,i)=>setc(td,s[i]));
const sync=()=>{{for(let d=0;d<7;d++)document.querySelector('input[name=grille_'+d+']').value=get(d);dirty()}};
const paint=td=>{{if(td&&td.dataset.d!==undefined){{setc(td,b);sync()}}}};
t.addEventListener('pointerdown',ev=>{{const td=ev.target.closest('td[data-d]');if(!td)return;down=true;ev.preventDefault();paint(td)}});
t.addEventListener('pointermove',ev=>{{if(down){{const el=document.elementFromPoint(ev.clientX,ev.clientY);paint(el&&el.closest('td[data-d]'))}}}});
addEventListener('pointerup',()=>down=false);addEventListener('pointercancel',()=>down=false);
t.addEventListener('input',dirty);
document.querySelectorAll('[data-copy]').forEach(x=>x.onclick=()=>{{const[src,dst]=x.dataset.copy.split(':');const[a,z]=dst.split('-');
 const s=get(src),q=document.querySelector('input[name=quota_'+src+']').value;
 for(let d=+a;d<=+(z??a);d++){{set(d,s);document.querySelector('input[name=quota_'+d+']').value=q}}sync()}});
document.querySelectorAll('[data-tpl]').forEach(x=>x.onclick=()=>{{T[x.dataset.tpl].forEach((s,d)=>set(d,s));sync()}});
}})()</script>"""


def page_planning(q, flash=""):
    u = q.get("s", q.get("u", [USERS[0]]))[0]
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
<section class="card stack"><div class="between"><div class="row">{avatar(u)}<div><h2>Semaine de {e(nom(u))}</h2>
<span class="muted small">La case encadrée correspond à maintenant</span></div></div><div style="max-width:420px;flex:1">{status}</div></div>
{planning_grid(data[u])}
<p class="muted small" style="margin:0">La dernière ligne limite le temps d'écran total de la journée (0 = pas de limite). Un avertissement s'affiche 5 minutes avant chaque fin d'accès.</p></section>
<div class="savebar"><span><span class="dirty">● Modifications non enregistrées</span></span>
<div class="row"><a class="btn" href="/?p=planning&s={quote(u)}">Annuler</a><button class="btn primary">{ic("check", 18)} Enregistrer</button></div></div></form>"""
    return shell("planning", "Planning", "Quand chaque enfant peut utiliser son bureau", body, flash)


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
<div class="range"><input type="range" name="minutes" min="15" max="240" step="15" value="60"><output>1 h</output></div></div>
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
        choix = ([("herite", "users", f"Comme tous ({SECU_VAL[g[k]].lower()})")] if scope != ALL else []) +                 [("interdit", "ban", "Interdire"), ("autorise", "check", "Autoriser")]
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
    scope = q.get("s", [ALL])[0]
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
    cards = cards or f'<div class="empty">Aucune restriction pour le moment.<br>Cliquez sur « Ajouter une règle » pour commencer.</div>'
    c.close()
    body = f"""{people_tabs("regles", scope, allow_all=True)}
<div class="legend card" style="padding:10px;margin-bottom:16px">
<div style="background:var(--green-soft)"><i class="cV"></i><span><b>Vert</b> · aucune restriction</span></div>
<div style="background:var(--orange-soft)"><i class="cO"></i><span><b>Orange</b> · les règles ci-dessous s'appliquent</span></div>
<div style="background:var(--red-soft)"><i class="cR"></i><span><b>Rouge</b> · pas d'accès à la session</span></div></div>
<div class="stack">
<section class="card stack"><div><h2>{ic("globe", 20)} Internet pendant l'orange</h2><span class="muted small">Pour {e(who)}</span></div>
<form method="post" data-auto>{hidden(a="internet", s=scope)}<div class="opts">{net}</div></form></section>
<section class="card stack"><div class="between"><div><h2>{ic("app", 20)} {e(title)}</h2><span class="muted small">{e(intro)}</span></div>
<button class="btn primary" data-open="add-{scope}">{ic("plus", 18)} Ajouter une règle</button></div>
<div class="rules">{cards}</div>
<p class="muted small" style="margin:0">Les durées limitées sont comptées sur toute la journée (le temps passé en vert compte aussi). Le temps sur un site est mesuré d'après l'onglet Firefox au premier plan.</p></section>
{secu_card(scope, data)}
</div>{rule_dialog(scope)}"""
    return shell("regles", "Règles", "Ce qui est permis pendant les heures orange", body, flash)


# ======================================================================
# Statistiques
# ======================================================================
def bars(rows):
    if not rows:
        return '<div class="empty">Pas encore de données pour cette période.</div>'
    mx = max(v for _, v in rows) or 1
    return '<div class="bars">' + "".join(
        f'<div class="bar" title="{e(k)} : {dur(v)}"><span class="lab">{e(k)}</span>'
        f'<div class="trk"><div class="fill" style="width:{max(1, 100 * v / mx):.1f}%"></div></div><span class="val">{dur(v)}</span></div>'
        for k, v in rows) + "</div>"


DEBUT_DETAIL = "8 novembre 2026"      # le détail heure par heure est enregistré depuis cette mise à jour
# Couleurs des séries (palette validée daltonisme, clair et sombre) : la couleur suit l'objet, jamais son rang.
# Les mêmes couleurs servent aux pastilles des applications et des enfants, partout dans le tableau.
APP_SLOT = {"Firefox": 1, "LibreOffice": 2, "GCompris": 3, "Tux Paint": 4, "Éditeur de texte": 5,
            "Visionneuse d'images": 6, "Terminal": 7, "Thonny": 8}
PER_LAB = {"1": "aujourd'hui", "7": "sur 7 jours", "30": "sur 30 jours"}
PREV_LAB = {"1": "hier", "7": "les 7 jours d'avant", "30": "les 30 jours d'avant"}


def app_color(app):
    if app == IDLE:
        return "var(--s-inactif)"
    return f"var(--s{APP_SLOT[app]})" if app in APP_SLOT else "var(--s-autre)"


def kid_color(u):
    return f"var(--s{USERS.index(u) % 8 + 1})" if u in USERS else "var(--s-autre)"


def app_badge(app, size=26):
    cle = next((f"app:{k}" for k, v in APPS.items() if v[1] == app), None)
    if cle:
        return item_badge(cle, size)
    g = "…" if app == IDLE else (app or "?")[:1].upper()
    return f'<span class="item" translate="no" style="--c:{app_color(app)};width:{size}px;height:{size}px;font-size:{int(size * .5)}px">{e(g)}</span>'


def swatch(col):
    return f'<i class="sw" style="--c:{col}"></i>'


def legend(items):
    return '<div class="vlegend">' + "".join(f'<span>{swatch(c)}{e(l)}</span>' for l, c in items) + "</div>"


def fmt_axis(sec):
    """Graduation compacte : « 16 h », « 1 h 30 », « 45 min »."""
    m = int(round(sec / 60))
    if m >= 60:
        return f"{m // 60} h" + (f" {m % 60:02d}" if m % 60 else "")
    return f"{m} min"


def merge(rows, gap=90):
    """Regroupe les relevés successifs d'une même application chez un même enfant en périodes d'utilisation."""
    out = []
    for u, app, title, site, st, en in rows:
        st, en = datetime.fromisoformat(st), datetime.fromisoformat(en)
        o = out[-1] if out else None
        if o and o["user"] == u and o["app"] == app and (st - o["end"]).total_seconds() <= gap:
            o["end"] = max(o["end"], en)
        else:
            o = {"user": u, "app": app, "start": st, "end": en, "titles": {}}
            out.append(o)
        if title:
            o["titles"][title] = o["titles"].get(title, 0) + (en - st).total_seconds()
    return out


def by_hour(rows, key):
    """Secondes par (clé, heure 0-23) à partir des relevés détaillés (une période peut chevaucher plusieurs heures)."""
    m = {}
    for r in rows:
        st, en = datetime.fromisoformat(r[4]), datetime.fromisoformat(r[5])
        k = key(r)
        while st < en:
            nxt = min(en, st.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1))
            m.setdefault(k, [0] * 24)[st.hour] += (nxt - st).total_seconds()
            st = nxt
    return m


def titles_txt(o, n=3):
    ts = sorted(o["titles"].items(), key=lambda x: -x[1])
    if not ts:
        return ""
    txt = " · ".join(t for t, _ in ts[:n]) + (f" (+{len(ts) - n})" if len(ts) > n else "")
    full = "\n".join(f"{t} ({dur(s)})" for t, s in ts)
    return f'<span class="tt" translate="no" data-tip="{e(full)}">{e(txt)}</span>'


def day_label(d):
    return f"{JOURS[d.weekday()]} {d.day} {MOIS[d.month - 1]}"


def pick_day(q):
    try:
        d = datetime.fromisoformat(q.get("d", [""])[0]).date()
    except ValueError:
        d = datetime.now().date()
    return min(d, datetime.now().date())


def url(params, **more):
    return "/?" + "&".join(f"{k}={quote(str(v))}" for k, v in {**params, **more}.items() if v not in (None, ""))


def day_nav(params, d):
    """Choix de la journée : veille / calendrier / lendemain."""
    today = datetime.now().date()
    hid = "".join(f'<input type="hidden" name="{k}" value="{e(v)}">' for k, v in params.items())
    return (f'<div class="daynav"><a class="btn sm" href="{url(params, d=d - timedelta(days=1))}" title="Jour précédent">‹</a>'
            f'<form method="get" data-auto>{hid}<input type="date" name="d" value="{d}" max="{today}" aria-label="Choisir le jour"></form>'
            + (f'<a class="btn sm" href="{url(params, d=d + timedelta(days=1))}" title="Jour suivant">›</a><a class="btn sm" href="{url(params)}">Aujourd\'hui</a>'
               if d < today else '<span class="btn sm" style="opacity:.4">›</span>') + '</div>')


def nice_max(v):
    """Maximum « rond » de l'axe, en secondes."""
    m = max(1, v / 60)
    for step in (5, 10, 15, 30, 60, 120, 180, 240, 360, 480, 720, 960, 1440):
        if m <= step:
            return step * 60
    return m * 60


def card(title, sub, inner, extra="", icon=None, cls=""):
    """Carte de graphique : pastille d'icône, titre, sous-titre, contrôles à droite."""
    sub_html = f'<span class="muted small">{sub}</span>' if sub else ""
    ico = f'<span class="cico">{ic(icon, 18)}</span>' if icon else ""
    return (f'<section class="card stack {cls}"><div class="between"><div class="chead">{ico}<div><h2>{title}</h2>{sub_html}</div></div>{extra}</div>'
            f'{inner}</section>')


def more(label, inner, open_=False):
    return f'<details class="more"{" open" if open_ else ""}><summary>{label}</summary>{inner}</details>'


# ======================================================================
# Chiffres : totaux, comparaison avec la période précédente, phrases « En bref »
# ======================================================================
def period_range(per, offset=0):
    """(premier jour, dernier jour) de la période, ou de la précédente si offset=1."""
    n = int(per)
    last = datetime.now().date() - timedelta(days=n * offset)
    return (last - timedelta(days=n - 1)).isoformat(), last.isoformat()


def total(c, per, offset=0, user=None, app=None, active=True):
    a, b = period_range(per, offset)
    sql, args = "SELECT COALESCE(SUM(sec),0) FROM usage WHERE day>=? AND day<=?", [a, b]
    if user:
        sql, args = sql + " AND user=?", args + [user]
    if app:
        sql, args = sql + " AND app=?", args + [app]
    elif active:
        sql, args = sql + " AND app!=?", args + [IDLE]
    return c.execute(sql, args).fetchone()[0]


def delta_html(cur, prev, per):
    """Évolution par rapport à la période précédente, en texte neutre (plus d'écran n'est ni « bien » ni « mal »)."""
    if not prev:
        return f'<span class="delta">nouveau par rapport à {PREV_LAB[per]}</span>' if cur else ""
    p = round(100 * (cur - prev) / prev)
    if abs(p) < 3:
        return f'<span class="delta">≈ stable par rapport à {PREV_LAB[per]}</span>'
    return f'<span class="delta">{"▲" if p > 0 else "▼"} {abs(p)} % par rapport à {PREV_LAB[per]}</span>'


def daily(c, n, user=None, app=None):
    """Temps actif par jour sur les n derniers jours (pour les mini-courbes)."""
    start = (datetime.now().date() - timedelta(days=n - 1)).isoformat()
    sql, args = "SELECT day, SUM(sec) FROM usage WHERE day>=?", [start]
    if user:
        sql, args = sql + " AND user=?", args + [user]
    sql, args = (sql + " AND app=?", args + [app]) if app else (sql + " AND app!=?", args + [IDLE])
    got = dict(c.execute(sql + " GROUP BY day", args).fetchall())
    return [got.get((datetime.now().date() - timedelta(days=i)).isoformat(), 0) for i in range(n - 1, -1, -1)]


def sparkline(vals, col):
    if not any(vals) or len(vals) < 2:
        return ""
    mx = max(vals) or 1
    pts = " ".join(f"{i / (len(vals) - 1) * 100:.1f},{30 - v / mx * 26:.1f}" for i, v in enumerate(vals))
    return (f'<svg class="spark" viewBox="0 0 100 32" preserveAspectRatio="none" aria-hidden="true">'
            f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="2" vector-effect="non-scaling-stroke" stroke-linejoin="round"/></svg>')


def top_app_of(c, per, user):
    a, b = period_range(per)
    r = c.execute("SELECT app, SUM(sec) s FROM usage WHERE user=? AND day>=? AND day<=? AND app!=? GROUP BY app ORDER BY s DESC LIMIT 1",
                  (user, a, b, IDLE)).fetchone()
    return r


def kid_tile(c, per, u, link):
    cur, prev = total(c, per, 0, u), total(c, per, 1, u)
    n = int(per)
    top = top_app_of(c, per, u)
    fav = (f'<span class="fav">{app_badge(top[0], 20)} surtout {e(top[0])}</span>' if top else '<span class="fav muted">rien cette période</span>')
    avg = f'{dur(cur / n)} par jour en moyenne' if n > 1 else "temps actif aujourd'hui"
    return (f'<a class="card ktile" href="{link}"><div class="kt-head">{avatar(u, "md")}<div><b>{e(nom(u))}</b>{fav}</div></div>'
            f'<div class="kt-num">{dur(cur)}</div><div class="kt-sub">{avg}</div>{delta_html(cur, prev, per)}'
            f'{sparkline(daily(c, max(n, 7), u), kid_color(u))}</a>')


def peak_hour(rows):
    hrs = by_hour(rows, lambda r: 0).get(0)
    if not hrs or not any(hrs):
        return None
    h = max(range(24), key=lambda i: hrs[i])
    return h


def longest_session(rows):
    """Plus longue période d'écran continue (toutes applications, pauses de moins de 3 min ignorées)."""
    best, cur = None, None
    for r in sorted(rows, key=lambda r: (r[0], r[4])):
        st, en = datetime.fromisoformat(r[4]), datetime.fromisoformat(r[5])
        if cur and cur[0] == r[0] and (st - cur[2]).total_seconds() <= 180:
            cur = (cur[0], cur[1], max(cur[2], en))
        else:
            cur = (r[0], st, en)
        if not best or (cur[2] - cur[1]) > (best[2] - best[1]):
            best = cur
    return best


def insights(lines):
    lines = [l for l in lines if l]
    if not lines:
        return ""
    return card("En bref", "", '<ul class="insights">' + "".join(f"<li>{l}</li>" for l in lines) + "</ul>", icon="sparkle", cls="ins-card")


def b(x):
    return f"<b>{e(x)}</b>"


# ======================================================================
# Graphiques
# ======================================================================
def stacked_days(series_by_day, days, order, color, label_of=lambda k: k):
    """Barres empilées par jour. series_by_day : {jour iso: {clé: secondes}}. Une barre par jour, une couleur par clé."""
    today = datetime.now().date()
    keys = [today - timedelta(days=i) for i in range(days - 1, -1, -1)]
    totals = [sum(series_by_day.get(k.isoformat(), {}).values()) for k in keys]
    if not any(totals):
        return '<div class="empty">Pas encore de données pour cette période.</div>'
    top = nice_max(max(totals))
    grid = "".join(f'<div class="vgl" style="bottom:{p}%"><span>{fmt_axis(top * p / 100)}</span></div>' for p in (0, 50, 100))
    cols = ""
    every = 1 if days <= 10 else 5
    for i, (k, tot) in enumerate(zip(keys, totals)):
        vals = series_by_day.get(k.isoformat(), {})
        segs = "".join(f'<i style="--c:{color(s)};height:{vals[s] / top * 100:.2f}%"></i>' for s in order if vals.get(s))
        lab = f"{JOURS[k.weekday()][:3]} {k.day}" if (days - 1 - i) % every == 0 else ""
        tip_ = f"{day_label(k)} : {dur(tot)}" + "".join(f"\n{label_of(s)} : {dur(vals[s])}" for s in order if vals.get(s))
        cols += (f'<div class="vcol" data-tip="{e(tip_)}"><div class="vstack">{segs}</div>'
                 f'<span class="vx{" today" if k == today else ""}">{lab}</span></div>')
    used = [s for s in order if any(series_by_day.get(k.isoformat(), {}).get(s) for k in keys)]
    return (f'{legend([(label_of(s), color(s)) for s in used]) if len(used) > 1 else ""}'
            f'<div class="vchart"><div class="vgrid">{grid}</div><div class="vcols">{cols}</div></div>')


def heat(rows):
    """Carte de chaleur : lignes = enfants / jours, colonnes = heures. rows : [(étiquette html, [24 secondes])]"""
    if not any(sum(v) for _, v in rows):
        return '<div class="empty">Pas encore de détail heure par heure pour cette période.</div>'
    mx = max(max(v) for _, v in rows) or 1
    step = lambda s: 0 if s <= 0 else min(5, 1 + int(4 * s / mx))
    head = '<div class="hrow hhead"><span></span>' + "".join(f'<b>{f"{h}h" if h % 3 == 0 else ""}</b>' for h in range(24)) + "<span></span></div>"
    body = ""
    for lab, v in rows:
        cells = "".join(f'<i style="background:var(--q{step(s)})" data-tip="{e(f"{h}h–{h + 1}h : {dur(s)}")}"></i>' for h, s in enumerate(v))
        body += f'<div class="hrow"><span class="lab">{lab}</span>{cells}<span class="val">{dur(sum(v))}</span></div>'
    leg = ('<div class="hleg"><span>moins</span>' + "".join(f'<i style="background:var(--q{i})"></i>' for i in range(6)) + '<span>plus</span></div>')
    return f'<div class="heat">{head}{body}</div>{leg}'


def matrix(apps, users, val, link):
    """Tableau croisé applications × enfants, cases colorées selon le temps (valeur toujours écrite)."""
    mx = max([val(a, u) for a in apps for u in users] + [1])
    th = "".join(f'<th class="n">{avatar(u, "sm")}<br>{e(nom(u))}</th>' for u in users)
    rows = ""
    for a in apps:
        cells = ""
        for u in users:
            s = val(a, u)
            k = 0 if s <= 0 else min(5, 1 + int(4 * s / mx))
            cells += (f'<td class="mx q{k}" style="background:var(--q{k})" data-tip="{e(f"{nom(u)} · {a} : {dur(s)}")}">'
                      f'<a href="{link(a, u)}">{dur(s) if s else "–"}</a></td>')
        rows += f'<tr><td class="who">{app_badge(a, 22)} {e(a)}</td>{cells}</tr>'
    return f'<div class="tw"><table class="t mxt"><tr><th>Application</th>{th}</tr>{rows}</table></div>'


def gantt(rows, d):
    """Chronologie : une ligne par enfant ou par application, une barre par période d'utilisation.
    rows : [(étiquette html, [(début, fin, couleur, info-bulle)])]"""
    d0 = datetime.combine(d, datetime.min.time())
    d1 = d0 + timedelta(days=1)
    segs = [(max(a, d0), min(b_, d1)) for _, ss in rows for a, b_, _, _ in ss]
    segs = [(a, b_) for a, b_ in segs if b_ > a]
    if not segs:
        return '<div class="empty">Aucune utilisation enregistrée ce jour-là.</div>'
    h0 = min(a for a, _ in segs).hour
    h1 = int(min(24, max((b_ - d0).total_seconds() for _, b_ in segs) // 3600 + 1))
    h0, h1 = (max(0, h1 - 3), h1) if h1 - h0 < 3 else (h0, h1)
    span = (h1 - h0) * 60
    pos = lambda t: max(0.0, min(100.0, ((t - d0).total_seconds() / 60 - h0 * 60) / span * 100))
    step = 1 if h1 - h0 <= 8 else 2 if h1 - h0 <= 16 else 3
    scale = "".join(f'<span style="left:{(h - h0) * 60 / span * 100:.2f}%">{h}h</span>' for h in range(h0, h1 + 1, step))
    now = datetime.now()
    nowl = f'<i class="nowl" style="left:{pos(now):.2f}%"></i>' if d == now.date() and h0 * 60 <= now.hour * 60 + now.minute <= h1 * 60 else ""
    out = ""
    for lab, ss in rows:
        tot = sum((min(b_, d1) - max(a, d0)).total_seconds() for a, b_, _, _ in ss if min(b_, d1) > max(a, d0))
        bars_ = "".join(f'<i style="--c:{col};left:{pos(max(a, d0)):.3f}%;width:{max(0.25, pos(min(b_, d1)) - pos(max(a, d0))):.3f}%" translate="no" data-tip="{e(tp)}"></i>'
                        for a, b_, col, tp in ss if min(b_, d1) > max(a, d0))
        out += f'<div class="grow"><span class="lab">{lab}</span><div class="gtrack">{bars_}{nowl}</div><span class="val">{dur(tot)}</span></div>'
    return f'<div class="gantt">{out}<div class="grow"><span></span><div class="gscale">{scale}</div><span></span></div></div>'


def tip(o, who=True):
    t = f"{nom(o['user'])} · " if who else ""
    t += f"{o['app']} · {o['start']:%H:%M}–{o['end']:%H:%M} ({dur((o['end'] - o['start']).total_seconds())})"
    best = sorted(o["titles"].items(), key=lambda x: -x[1])[:3]
    return t + "".join(f"\n{x}" for x, _ in best)


# --- courbes d'évolution
def time_buckets(per):
    """Axe du temps : heures d'aujourd'hui (période « Aujourd'hui ») ou jours de la période."""
    today = datetime.now().date()
    if per == "1":
        return [(h, f"{h}h") for h in range(24)], "heure par heure"
    n = int(per)
    ds = [today - timedelta(days=i) for i in range(n - 1, -1, -1)]
    return [(x.isoformat(), f"{JOURS[x.weekday()][:3]} {x.day}") for x in ds], "jour par jour"


def usage_series(c, per):
    """{(enfant, application): {repère: secondes}} et le temps actif {enfant: {repère: secondes}} sur la période."""
    data, act = {}, {}
    if per == "1":
        d0 = datetime.combine(datetime.now().date(), datetime.min.time()).isoformat()
        rows = [r for r in c.execute("SELECT user, app, title, site, start, end FROM segments WHERE end>=? ORDER BY user, start", (d0,))
                if r[0] in USERS and r[1] != IDLE]
        for (u, a), hrs in by_hour(rows, lambda r: (r[0], r[1])).items():
            for h, s in enumerate(hrs):
                if s:
                    data.setdefault((u, a), {})[h] = s
                    act.setdefault(u, {})[h] = act.setdefault(u, {}).get(h, 0) + s
    else:
        start = (datetime.now().date() - timedelta(days=int(per) - 1)).isoformat()
        for day, u, a, s in c.execute("SELECT day, user, app, SUM(sec) FROM usage WHERE day>=? AND app!=? GROUP BY day, user, app", (start, IDLE)):
            if u in USERS:
                data.setdefault((u, a), {})[day] = s
                act.setdefault(u, {})[day] = act.setdefault(u, {}).get(day, 0) + s
    return data, act


def nice_up(v):
    """Maximum « rond » de l'axe pour une grandeur quelconque : 1, 2, 2,5 ou 5 × 10^k."""
    k = 10 ** math.floor(math.log10(v)) if v > 0 else 1
    return next(m * k for m in (1, 2, 2.5, 5, 10) if m * k >= v)


def line_chart(labels, series, pct=False, h=240, ymax=None, direct=True, show_legend=True, fmt=None):
    """Courbes : series = [(nom, couleur, [valeurs])] — secondes, pourcentages si pct, ou toute grandeur
    affichée par fmt. None = pas de mesure ce jour-là (la courbe s'interrompt).
    Une seule échelle ; repère vertical + info-bulle listant toutes les courbes au point survolé."""
    series = [s for s in series if any(s[2])]
    if not series:
        return '<div class="empty">Pas encore de données pour cette période.</div>'
    n = len(labels)
    vmax = max(x for _, _, v in series for x in v if x is not None)
    top = ymax or (nice_up(vmax) if fmt else 100 if pct else nice_max(vmax))
    fax = fmt or ((lambda v: f"{v:.0f} %") if pct else fmt_axis)
    fmt = fmt or ((lambda v: f"{v:.0f} %") if pct else dur)
    X = lambda i: i / (n - 1) * 100 if n > 1 else 50.0
    Y = lambda v: 100 - min(v, top) / top * 100

    def runs(vals):                                   # morceaux de courbe sans trou
        cur = []
        for i, v in enumerate(vals):
            if v is None:
                if cur:
                    yield cur
                cur = []
            else:
                cur.append(f"{X(i) * 10:.1f},{Y(v):.2f}")
        if cur:
            yield cur
    lines = "".join(
        f'<polyline fill="none" stroke="{col}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" vector-effect="non-scaling-stroke" '
        f'points="{" ".join(pts if len(pts) > 1 else pts * 2)}"/>' for _, col, vals in series for pts in runs(vals))
    dots = ""
    if n <= 10:
        dots = "".join(f'<i class="ldot" style="--c:{col};left:{X(i):.2f}%;top:{Y(v):.2f}%"></i>'
                       for _, col, vals in series for i, v in enumerate(vals) if v)
    else:                                             # point isolé (entouré de jours sans mesure) : sinon invisible
        dots = "".join(f'<i class="ldot" style="--c:{col};left:{X(i):.2f}%;top:{Y(v):.2f}%"></i>'
                       for _, col, vals in series for i, v in enumerate(vals)
                       if v is not None and (i == 0 or vals[i - 1] is None) and (i == n - 1 or vals[i + 1] is None))
    grid ="".join(f'<div class="vgl" style="bottom:{p}%"><span>{fax(top * p / 100)}</span></div>' for p in (0, 50, 100))
    w = 100 / (n - 1) if n > 1 else 100
    hits = ""
    for i, lab in enumerate(labels):
        vals = sorted(((nm, v[i]) for nm, _, v in series), key=lambda x: -(x[1] or 0))
        tip_ = lab + "".join(f"\n{nm} : {fmt(v)}" for nm, v in vals if v) + ("" if any(v for _, v in vals) else "\n(rien)")
        hits += f'<div class="lhit" style="left:{X(i):.2f}%;width:{w:.2f}%" data-tip="{e(tip_)}"></div>'
    every = 1 if n <= 10 else 3 if n <= 24 else 5
    xl = "".join(f'<span class="lx" style="left:{X(i):.2f}%">{e(lab)}</span>' for i, lab in enumerate(labels) if (n - 1 - i) % every == 0)
    ends = ""
    if direct and len(series) <= 4:                      # étiquettes directes en bout de courbe (texte neutre, pastille de couleur)
        pos = sorted(((Y(next((x for x in reversed(v) if x is not None), 0)), nm, col) for nm, col, v in series), key=lambda x: x[0])
        last = -99
        for y, nm, col in pos:
            y = max(y, last + 9)
            last = y
            ends += f'<span class="lend" style="top:{min(y, 100):.1f}%">{swatch(col)}{e(nm)}</span>'
    leg = legend([(nm, col) for nm, col, _ in series]) if len(series) > 1 and show_legend else ""
    return (f'{leg}<div class="lchart{" withend" if ends else ""}" style="height:{h}px"><div class="lplot">{grid}'
            f'<svg viewBox="0 0 1000 100" preserveAspectRatio="none" aria-hidden="true">{lines}</svg>{dots}{hits}{ends}</div>{xl}</div>')


def mesure_tabs(params, pct_):
    return ('<div class="seg">' + "".join(
        f'<a class="{"on" if (k == "pct") == pct_ else ""}" href="{url(params, mesure=k)}">{lab}</a>'
        for k, lab in (("min", "Minutes"), ("pct", "% du temps"))) + "</div>")


def evo_values(bk, d, pct_, denom):
    return [(100 * d.get(x, 0) / denom.get(x, 1) if denom.get(x) else 0) if pct_ else d.get(x, 0) for x, _ in bk]


def top_apps(data, users, k=6):
    tot = {}
    for (u, a), d in data.items():
        if u in users:
            tot[a] = tot.get(a, 0) + sum(d.values())
    return sorted(tot, key=lambda a: -tot[a])[:k]


def evo_apps_for(c, per, u, pct_):
    """Courbes d'un enfant : une par application (les 6 plus utilisées + « Autres »)."""
    bk, _ = time_buckets(per)
    data, act = usage_series(c, per)
    apps = top_apps(data, [u])
    rest = {}
    for (uu, a), d in data.items():
        if uu == u and a not in apps:
            for x, s in d.items():
                rest[x] = rest.get(x, 0) + s
    series = [(a, app_color(a), evo_values(bk, data.get((u, a), {}), pct_, act.get(u, {}))) for a in apps]
    if any(rest.values()):
        series.append(("Autres", "var(--s-autre)", evo_values(bk, rest, pct_, act.get(u, {}))))
    return line_chart([lab for _, lab in bk], series, pct_)


def evo_kids_for(c, per, app, pct_):
    """Courbes d'une application : une par enfant."""
    bk, _ = time_buckets(per)
    data, act = usage_series(c, per)
    series = [(nom(u), kid_color(u), evo_values(bk, data.get((u, app), {}), pct_, act.get(u, {}))) for u in USERS]
    return line_chart([lab for _, lab in bk], series, pct_)


def evo_multiples(c, per, pct_):
    """Petits graphiques : un par enfant, une courbe par application, même échelle pour tous (comparaison directe)."""
    bk, _ = time_buckets(per)
    data, act = usage_series(c, per)
    apps = top_apps(data, USERS)
    if not apps:
        return '<div class="empty">Pas encore de données pour cette période.</div>'
    allv = [v for u in USERS for a in apps for v in evo_values(bk, data.get((u, a), {}), pct_, act.get(u, {}))]
    ymax = 100 if pct_ else nice_max(max(allv + [1]))
    cells = ""
    for u in USERS:
        series = [(a, app_color(a), evo_values(bk, data.get((u, a), {}), pct_, act.get(u, {}))) for a in apps]
        inner = line_chart([lab for _, lab in bk], series, pct_, h=170, ymax=ymax, direct=False, show_legend=False)
        cells += f'<div class="mult"><a class="mh" href="/?p=stats&vue=enfant&s={quote(u)}&per={per}">{avatar(u, "sm")}{e(nom(u))}</a>{inner}</div>'
    return legend([(a, app_color(a)) for a in apps]) + f'<div class="mults">{cells}</div>'


# --- Ressources par enfant, 30 derniers jours (relevées par logique.ressources)
def fmt_mo(mo):
    if mo >= 1024:
        return f"{mo / 1024:.1f} Go".replace(".", ",")
    return f"{mo:.1f} Mo".replace(".", ",") if 0 < mo < 10 else f"{mo:.0f} Mo"


def fmt_pc(v):
    return f"{v:.1f} %".replace(".", ",") if 0 < v < 10 else f"{v:.0f} %"


RES = {   # clé -> (onglet, explication, format)
    "cpu": ("Processeur", "part moyenne de la puissance de l'ordinateur utilisée par ses programmes, session ouverte", fmt_pc),
    "mem": ("Mémoire", "mémoire moyenne occupée par ses programmes, session ouverte", fmt_mo),
    "net": ("Internet", "volume échangé avec internet dans la journée (reçu + envoyé)", fmt_mo),
    "disk": ("Disque", "taille de son dossier personnel (documents, réglages, téléchargements)", fmt_mo),
}
RES_JOURS = 30


def res_data(c, users):
    """{enfant: {jour: {cpu, mem, net, disk}}}, pics de mémoire {enfant: (Mo, jour)} et premier jour mesuré."""
    days = [datetime.now().date() - timedelta(days=i) for i in range(RES_JOURS - 1, -1, -1)]
    ncpu = os.cpu_count() or 1
    raw, peak = {}, {}
    first = c.execute("SELECT MIN(hour) FROM ressources").fetchone()[0]
    for hour, u, cpu, ms, mx, n, ni, no, dk in c.execute(
            "SELECT hour, user, cpu, mem_sum, mem_max, n, net_in, net_out, disk FROM ressources WHERE hour>=? ORDER BY hour",
            (days[0].isoformat(),)):
        if u not in users:
            continue
        a = raw.setdefault(u, {}).setdefault(hour[:10], [0.0, 0.0, 0, 0, None])
        a[0] += cpu
        a[1] += ms
        a[2] += n
        a[3] += ni + no
        a[4] = dk if dk is not None else a[4]
        if mx > peak.get(u, (0, ""))[0]:
            peak[u] = (mx, hour[:10])
    out = {}
    for u in users:
        for d in days:
            k = d.isoformat()
            a = raw.get(u, {}).get(k)
            if not first or k < first[:10]:
                v = {x: None for x in RES}                      # avant le début des mesures
            elif not a:
                v = {"cpu": None, "mem": None, "net": 0, "disk": None}    # pas de session : pas de moyenne
            else:
                v = {"cpu": 100 * a[0] / (a[2] * TICK) / ncpu if a[2] else None, "mem": a[1] / a[2] if a[2] else None,
                     "net": a[3] / 1048576, "disk": a[4]}
            out.setdefault(u, {})[k] = v
    return days, out, peak


def res_card(c, q, params, users):
    key = q.get("res", ["cpu"])[0]
    key = key if key in RES else "cpu"
    days, data, peak = res_data(c, users)
    lab, expl, fmt = RES[key]
    series = [(nom(u), kid_color(u), [data[u][d.isoformat()][key] for d in days]) for u in users]
    labels = [f"{JOURS[d.weekday()][:3]} {d.day}" for d in days]
    tabs = ('<div class="seg">' + "".join(
        f'<a class="{"on" if k == key else ""}" href="{url(params, res=k)}#ressources">{v[0]}</a>' for k, v in RES.items()) + "</div>")
    chart = line_chart(labels, series, h=220, fmt=fmt, direct=False)
    note = ""
    if key == "mem" and peak:
        note = ('<p class="muted small">Pic de mémoire : ' + " · ".join(
            f"{e(nom(u))} {fmt_mo(m)} ({day_label(datetime.fromisoformat(d).date()).lower()})"
            for u, (m, d) in sorted(peak.items(), key=lambda x: -x[1][0])) + "</p>")
    if key == "cpu":
        note = f'<p class="muted small">100 % = toute la puissance de l\'ordinateur ({os.cpu_count() or 1} cœurs) pour un seul enfant.</p>'
    return f'<div id="ressources"></div>' + card(f"Ressources utilisées : {lab.lower()}",
                                                  f"{'Par enfant, ' if len(users) > 1 else ''}{RES_JOURS} derniers jours · {expl}",
                                                  chart + note, tabs, icon="cpu")


# ======================================================================
# Page Statistiques : trois vues
# ======================================================================
def pct(q):
    return q.get("mesure", ["min"])[0] == "pct"


def segs_since(c, start, where="", args=()):
    return c.execute(f"SELECT user, app, title, site, start, end FROM segments WHERE start>=? {where} ORDER BY user, start",
                     (start, *args)).fetchall()


def page_stats(q):
    vue = q.get("vue", ["ensemble"])[0]
    vue = vue if vue in ("ensemble", "enfant", "app") else "ensemble"
    per = q.get("per", ["7"])[0]
    per = per if per in ("1", "7", "30") else "7"
    days = int(per)
    start = (datetime.now().date() - timedelta(days=days - 1)).isoformat()
    d = pick_day(q)
    c = db()
    vue_tabs = "".join(f'<a class="{"on" if k == vue else ""}" href="/?p=stats&vue={k}&per={per}&d={d}">{ic(i, 16)} {lab}</a>'
                       for k, lab, i in (("ensemble", "Ensemble", "chart"), ("enfant", "Par enfant", "users"), ("app", "Par application", "app")))
    fn = {"ensemble": stats_ensemble, "enfant": stats_enfant, "app": stats_app}[vue]
    body, sub, params = fn(q, c, per, days, start, d)
    c.close()
    per_tabs = "".join(f'<a class="{"on" if k == per else ""}" href="{url(params, per=k, d=d, mesure=q.get("mesure", [""])[0])}">{v}</a>'
                       for k, v in (("1", "Aujourd'hui"), ("7", "7 jours"), ("30", "30 jours")))
    head = (f'<div class="stats-bar"><div class="seg">{vue_tabs}</div>'
            f'<div class="seg" title="Période des chiffres et graphiques">{per_tabs}</div></div>')
    return shell("stats", "Statistiques", sub, head + body)


def stats_ensemble(q, c, per, days, start, d):
    params = {"p": "stats", "vue": "ensemble", "per": per}
    nd = max(days, 7)
    st7 = (datetime.now().date() - timedelta(days=nd - 1)).isoformat()
    per_day = {}
    for day, u, s in c.execute("SELECT day, user, SUM(sec) FROM usage WHERE day>=? AND app!=? GROUP BY day, user", (st7, IDLE)):
        if u in USERS:
            per_day.setdefault(day, {})[u] = s
    raw = [r for r in segs_since(c, start) if r[0] in USERS and r[1] != IDLE]
    hours = by_hour(raw, lambda r: r[0])
    mval = {}
    for a, u, s in c.execute("SELECT app, user, SUM(sec) FROM usage WHERE day>=? AND app!=? GROUP BY app, user", (start, IDLE)):
        if u in USERS:
            mval[(a, u)] = s
    apps = sorted({a for a, _ in mval}, key=lambda a: -sum(mval.get((a, u), 0) for u in USERS))[:12]
    pl = PER_LAB[per]
    # --- phrases « En bref »
    cur, prev = total(c, per), total(c, per, 1)
    lines = []
    if cur:
        tot_u = {u: total(c, per, 0, u) for u in USERS}
        big = max(tot_u, key=tot_u.get)
        tb = top_app_of(c, per, big)
        lines.append(f"Les enfants ont passé {b(dur(cur))} devant l'écran {pl}" + (f" ({delta_html(cur, prev, per)})" if prev else "") + ".")
        lines.append(f"{b(nom(big))} est celui qui a le plus utilisé l'ordinateur ({dur(tot_u[big])})"
                     + (f", surtout {b(tb[0])}." if tb else "."))
        if apps:
            a0 = apps[0]
            who = max(USERS, key=lambda u: mval.get((a0, u), 0))
            lines.append(f"Application la plus utilisée : {b(a0)} ({dur(sum(mval.get((a0, u), 0) for u in USERS))}), surtout par {b(nom(who))}.")
        ph = peak_hour(raw)
        if ph is not None:
            lines.append(f"Moment le plus chargé : entre {b(f'{ph}h')} et {b(f'{ph + 1}h')}.")
    tiles = "".join(kid_tile(c, per, u, f"/?p=stats&vue=enfant&s={quote(u)}&per={per}") for u in USERS)
    body = (f'<div class="ktiles">{tiles}</div>{insights(lines)}<div class="stack">'
            + card("Évolution de chaque application, pour chaque enfant", f"{time_buckets(per)[1].capitalize()}, {pl} · même échelle pour tous",
                   evo_multiples(c, per, pct(q)), mesure_tabs({**params, "d": d}, pct(q)), icon="chart")
            + res_card(c, q, {**params, "d": d, "mesure": q.get("mesure", [""])[0]}, USERS)
            + '<div class="grid2">'
            + card("Temps d'écran par jour", f"Par enfant, {nd} derniers jours", stacked_days(per_day, nd, USERS, kid_color, nom), icon="calendar")
            + card("À quelle heure ?", f"Temps actif par heure de la journée, {pl}",
                   heat([(f'{avatar(u, "sm")}<a href="/?p=stats&vue=enfant&s={quote(u)}&per={per}" style="color:inherit">{e(nom(u))}</a>',
                          hours.get(u, [0] * 24)) for u in USERS]), icon="clock")
            + "</div>"
            + card("Qui utilise quoi", f"Temps par application et par enfant, {pl} · cliquez une case pour voir quand",
                   matrix(apps, USERS, lambda a, u: mval.get((a, u), 0), lambda a, u: f"/?p=stats&vue=app&app={quote(a)}&per={per}")
                   if apps else '<div class="empty">Pas encore de données pour cette période.</div>', icon="app")
            + "</div>")
    return body, "Vue d'ensemble de tous les enfants", params


def stats_enfant(q, c, per, days, start, d):
    u = q.get("s", q.get("u", [USERS[0]]))[0]
    u = u if u in USERS else USERS[0]
    filt = q.get("app", [""])[0]
    params = {"p": "stats", "vue": "enfant", "s": u, "per": per}
    pl = PER_LAB[per]
    by_app = c.execute("SELECT app, SUM(sec) s FROM usage WHERE user=? AND day>=? GROUP BY app ORDER BY s DESC", (u, start)).fetchall()
    tot_all = sum(v for _, v in by_app)
    active = sum(v for k, v in by_app if k != IDLE)
    by_site = c.execute("SELECT cle, SUM(sec) s FROM sites WHERE user=? AND day>=? GROUP BY cle ORDER BY s DESC", (u, start)).fetchall()
    tops = c.execute("SELECT title, app, SUM(sec) s FROM titles WHERE user=? AND day>=? GROUP BY title, app ORDER BY s DESC LIMIT 30", (u, start)).fetchall()
    evs = c.execute("SELECT ts, kind, detail FROM events WHERE user=? AND ts>=? ORDER BY ts DESC LIMIT 50", (u, start)).fetchall()
    nd = max(days, 7)
    per_day = {}
    for day, a, s in c.execute("SELECT day, app, SUM(sec) FROM usage WHERE user=? AND day>=? GROUP BY day, app",
                               (u, (datetime.now().date() - timedelta(days=nd - 1)).isoformat())):
        k = a if a in APP_SLOT or a == IDLE else "Autres"
        per_day.setdefault(day, {})[k] = per_day.setdefault(day, {}).get(k, 0) + s
    order = list(APP_SLOT) + ["Autres", IDLE]
    colf = lambda a: "var(--s-autre)" if a == "Autres" else app_color(a)
    raw_p = [r for r in segs_since(c, start, "AND user=?", (u,)) if r[1] != IDLE]
    hours = by_hour(raw_p, lambda r: r[4][:10])
    dlist = [datetime.now().date() - timedelta(days=i) for i in range(days)]
    heat_rows = [(f'<a href="{url(params, d=x)}" style="color:inherit">{JOURS[x.weekday()][:3]} {x.day}</a>', hours.get(x.isoformat(), [0] * 24))
                 for x in dlist]
    # --- chronologie de la journée choisie
    d0 = datetime.combine(d, datetime.min.time())
    raw = c.execute("SELECT user, app, title, site, start, end FROM segments WHERE user=? AND end>=? AND start<? ORDER BY start",
                    (u, d0.isoformat(), (d0 + timedelta(days=1)).isoformat())).fetchall()
    periods = merge(raw)
    apps_day = {}
    for o in periods:
        apps_day[o["app"]] = apps_day.get(o["app"], 0) + (o["end"] - o["start"]).total_seconds()
    aorder = sorted(apps_day, key=lambda a: (a == IDLE, -apps_day[a]))
    shown = [o for o in periods if not filt or o["app"] == filt]
    grows = [(f'{app_badge(a, 22)}<a href="/?p=stats&vue=app&app={quote(a)}&d={d}" style="color:inherit">{e(a)}</a>',
              [(o["start"], o["end"], app_color(a), tip(o, False)) for o in periods if o["app"] == a])
             for a in aorder if not filt or a == filt]
    chips = (f'<a class="txt {"on" if not filt else ""}" href="{url(params, d=d)}">Toutes</a>' +
             "".join(f'<a class="{"on" if a == filt else ""}" href="{url(params, d=d, app=a)}">{app_badge(a, 22)}{e(a)}</a>' for a in aorder)) if aorder else ""
    t_rows = "".join(
        f'<tr><td class="n">{o["start"]:%H:%M}</td><td class="n">{o["end"]:%H:%M}</td><td class="n">{dur((o["end"] - o["start"]).total_seconds())}</td>'
        f'<td class="who"><a href="/?p=stats&vue=app&app={quote(o["app"])}&d={d}">{app_badge(o["app"], 22)}{e(o["app"])}</a></td><td>{titles_txt(o)}</td></tr>'
        for o in reversed(shown))
    chrono_inner = (f'{f"<div class=chips2>{chips}</div>" if chips else ""}{gantt(grows, d)}'
                    + (more(f"Voir le détail ({len(shown)} période{'s' if len(shown) > 1 else ''})",
                            f'<div class="tw"><table class="t"><tr><th class="n">Début</th><th class="n">Fin</th><th class="n">Durée</th><th>Application</th>'
                            f'<th>Fenêtres et pages</th></tr>{t_rows}</table></div>', open_=bool(filt)) if shown else "")
                    + ("" if raw else f'<p class="muted small" style="margin:0">Le détail heure par heure est enregistré depuis le {DEBUT_DETAIL}.</p>'))
    # --- chiffres et phrases
    prev = total(c, per, 1, u)
    nconn = sum(1 for _, k, _ in evs if k == "connexion")
    top = top_app_of(c, per, u)
    lines = []
    if active:
        lines.append(f"{b(nom(u))} a utilisé l'ordinateur {b(dur(active))} {pl}" + (f" ({delta_html(active, prev, per)})" if prev else "") + ".")
        if top:
            lines.append(f"Application préférée : {b(top[0])}, {round(100 * top[1] / active)} % du temps.")
        ph = peak_hour(raw_p)
        if ph is not None:
            lines.append(f"{e(nom(u))} utilise surtout l'ordinateur entre {b(f'{ph}h')} et {b(f'{ph + 1}h')}.")
        ls = longest_session(raw_p)
        if ls and (ls[2] - ls[1]).total_seconds() >= 600:
            lines.append(f"Plus longue session sans pause : {b(dur((ls[2] - ls[1]).total_seconds()))}, "
                         f"{JOURS[ls[1].weekday()].lower()} {ls[1].day} de {ls[1]:%H:%M} à {ls[2]:%H:%M}.")
        if days > 1:
            sans = sum(1 for x in dlist if not hours.get(x.isoformat()) or not any(hours[x.isoformat()]))
            if sans:
                lines.append(f"{sans} jour{'s' if sans > 1 else ''} sans écran {pl}.")
    n = days
    tiles = (f'<div class="kpi-grid"><div class="card kpi-card"><b>{dur(active)}</b><span>Temps actif {pl}</span>{delta_html(active, prev, per)}'
             f'{sparkline(daily(c, nd, u), kid_color(u))}</div>'
             f'<div class="card kpi-card"><b>{dur(active / n) if n > 1 else dur(tot_all)}</b><span>{"Moyenne par jour" if n > 1 else "Temps d’écran (avec inactif)"}</span></div>'
             f'<div class="card kpi-card"><b>{f"{app_badge(top[0], 26)} {e(top[0])}" if top else "–"}</b><span>Application préférée</span></div>'
             f'<div class="card kpi-card"><b>{nconn}</b><span>Connexions</span></div></div>')
    site_rows = [((target(k) or (0, k))[1], v) for k, v in by_site]
    tt_rows = "".join(f'<tr><td translate="no">{e(t)}</td><td class="muted">{e(a)}</td><td class="n">{dur(s)}</td></tr>' for t, a, s in tops)
    ev_rows = "".join(f'<tr><td class="n">{datetime.fromisoformat(t):%d.%m %H:%M}</td><td>{e(k)}</td><td class="muted">{e(x)}</td></tr>' for t, k, x in evs)
    body = (f'{people_tabs("stats", u, f"&vue=enfant&per={per}&d={d}")}{tiles}{insights(lines)}<div class="stack">'
            + card("Évolution par application", f"Temps passé sur chaque application, {time_buckets(per)[1]}",
                   evo_apps_for(c, per, u, pct(q)), mesure_tabs({**params, "d": d}, pct(q)), icon="chart")
            + card(f"Chronologie · {e(day_label(d))}", f"Quelle application {e(nom(u))} a utilisée, et à quelle heure",
                   chrono_inner, day_nav(params, d), icon="clock")
            + '<div class="grid2">'
            + card("Temps par jour", f"Empilé par application, {nd} derniers jours", stacked_days(per_day, nd, order, colf, lambda a: a), icon="calendar")
            + card("Jours et heures", "Temps actif par heure · cliquez un jour pour sa chronologie", heat(heat_rows), icon="clock")
            + "</div>"
            + res_card(c, q, {**params, "d": d, "mesure": q.get("mesure", [""])[0]}, [u])
            + '<div class="grid2">'
            + card("Applications", f"Temps total {pl} · « (inactif) » : sans toucher la souris ni le clavier depuis 2 min", app_bars(by_app), icon="app")
            + card("Sites suivis", "D'après l'onglet Firefox au premier plan", bars(site_rows), icon="globe")
            + "</div>" + '<div class="grid2">'
            + card("Pages et fenêtres les plus utilisées", "",
                   more(f"Voir les {len(tops)} titres", f'<div class="tw"><table class="t"><tr><th>Titre</th><th>Application</th><th class="n">Durée</th></tr>{tt_rows}</table></div>', True)
                   if tops else '<div class="empty">Pas encore de données.</div>', icon="monitor")
            + card("Historique", "Connexions, pauses, limites atteintes",
                   more(f"Voir les {len(evs)} événements", f'<div class="tw"><table class="t"><tr><th>Quand</th><th>Événement</th><th>Détail</th></tr>{ev_rows}</table></div>')
                   if evs else '<div class="empty">Aucun événement.</div>', icon="calendar")
            + "</div></div>")
    return body, f"Utilisation de {nom(u)}", params


def app_bars(rows):
    """Barres horizontales colorées par application (même couleur que dans les graphiques)."""
    if not rows:
        return '<div class="empty">Pas encore de données pour cette période.</div>'
    mx = max(v for _, v in rows) or 1
    return '<div class="bars">' + "".join(
        f'<div class="bar" data-tip="{e(k)} : {dur(v)}"><span class="lab">{app_badge(k, 20)} {e(k)}</span>'
        f'<div class="trk"><div class="fill" style="width:{max(1, 100 * v / mx):.1f}%;background:{app_color(k)}"></div></div><span class="val">{dur(v)}</span></div>'
        for k, v in rows) + "</div>"


def stats_app(q, c, per, days, start, d):
    apps = [a for a, _ in c.execute("SELECT app, SUM(sec) s FROM usage WHERE day>=? AND app!=? GROUP BY app ORDER BY s DESC",
                                    ((datetime.now().date() - timedelta(days=29)).isoformat(), IDLE)).fetchall()]
    app = q.get("app", [""])[0]
    if app not in apps:
        app = apps[0] if apps else ""
    params = {"p": "stats", "vue": "app", "app": app, "per": per}
    if not app:
        return '<div class="empty">Aucune application utilisée ces 30 derniers jours.</div>', "Par application", params
    pl = PER_LAB[per]
    chips = "".join(f'<a class="{"on" if a == app else ""}" href="{url(params, app=a, d=d)}">{app_badge(a, 22)}{e(a)}</a>' for a in apps)
    nd = max(days, 7)
    per_day = {}
    for day, u, s in c.execute("SELECT day, user, SUM(sec) FROM usage WHERE app=? AND day>=? GROUP BY day, user",
                               (app, (datetime.now().date() - timedelta(days=nd - 1)).isoformat())):
        if u in USERS:
            per_day.setdefault(day, {})[u] = s
    rawp = [r for r in segs_since(c, start, "AND app=?", (app,)) if r[0] in USERS]
    hours = by_hour(rawp, lambda r: r[0])
    d0 = datetime.combine(d, datetime.min.time())
    raw = c.execute("SELECT user, app, title, site, start, end FROM segments WHERE app=? AND end>=? AND start<? ORDER BY user, start",
                    (app, d0.isoformat(), (d0 + timedelta(days=1)).isoformat())).fetchall()
    periods = merge(raw)
    users = [u for u in USERS if any(o["user"] == u for o in periods)]
    grows = [(f'{avatar(u, "sm")}<a href="/?p=stats&vue=enfant&s={quote(u)}&d={d}" style="color:inherit">{e(nom(u))}</a>',
              [(o["start"], o["end"], kid_color(u), tip(o)) for o in periods if o["user"] == u]) for u in users]
    lst = sorted(merge(rawp), key=lambda o: o["start"], reverse=True)[:300]
    t_rows = "".join(
        f'<tr><td class="who"><a href="/?p=stats&vue=enfant&s={quote(o["user"])}&d={o["start"].date()}">{avatar(o["user"], "sm")}{e(nom(o["user"]))}</a></td>'
        f'<td class="n">{JOURS[o["start"].weekday()][:3]} {o["start"]:%d.%m}</td><td class="n">{o["start"]:%H:%M}</td><td class="n">{o["end"]:%H:%M}</td>'
        f'<td class="n">{dur((o["end"] - o["start"]).total_seconds())}</td><td>{titles_txt(o)}</td></tr>' for o in lst)
    # --- phrases et fiches par enfant
    cur, prev = total(c, per, app=app), total(c, per, 1, app=app)
    tot_u = {u: total(c, per, 0, u, app) for u in USERS}
    lines = []
    if cur:
        share = round(100 * cur / (total(c, per) or 1))
        lines.append(f"{b(app)} a été utilisé {b(dur(cur))} {pl}, soit {b(f'{share} %')} du temps d'écran de tous les enfants"
                     + (f" ({delta_html(cur, prev, per)})" if prev else "") + ".")
        big = max(tot_u, key=tot_u.get)
        lines.append(f"{b(nom(big))} l'utilise le plus ({dur(tot_u[big])})."
                     + "".join(f" {e(nom(u))} : {dur(tot_u[u])}." for u in USERS if u != big and tot_u[u]))
        ph = peak_hour(rawp)
        if ph is not None:
            lines.append(f"Surtout utilisé entre {b(f'{ph}h')} et {b(f'{ph + 1}h')}.")
        ls = longest_session(rawp)
        if ls and (ls[2] - ls[1]).total_seconds() >= 600:
            lines.append(f"Plus longue utilisation d'affilée : {b(dur((ls[2] - ls[1]).total_seconds()))} par {e(nom(ls[0]))}, "
                         f"{JOURS[ls[1].weekday()].lower()} {ls[1].day} de {ls[1]:%H:%M} à {ls[2]:%H:%M}.")
    tiles = ""
    for u in USERS:
        if not tot_u[u] and not total(c, per, 1, u, app):
            continue
        tiles += (f'<a class="card ktile" href="/?p=stats&vue=enfant&s={quote(u)}&per={per}&app={quote(app)}">'
                  f'<div class="kt-head">{avatar(u, "md")}<div><b>{e(nom(u))}</b><span class="fav">{app_badge(app, 20)} {e(app)}</span></div></div>'
                  f'<div class="kt-num">{dur(tot_u[u])}</div><div class="kt-sub">{pl}</div>{delta_html(tot_u[u], total(c, per, 1, u, app), per)}'
                  f'{sparkline(daily(c, nd, u, app), kid_color(u))}</a>')
    body = (f'<div class="chips2" style="margin-bottom:18px">{chips}</div>'
            + (f'<div class="ktiles">{tiles}</div>' if tiles else "") + insights(lines) + '<div class="stack">'
            + card(f"Évolution de {e(app)} pour chaque enfant", f"Temps passé, {time_buckets(per)[1]}",
                   evo_kids_for(c, per, app, pct(q)), mesure_tabs({**params, "d": d}, pct(q)), icon="chart")
            + card(f"Chronologie · {e(day_label(d))}", f"Qui a utilisé {e(app)} ce jour-là, et à quelle heure",
                   gantt(grows, d) + ("" if rawp or raw else f'<p class="muted small" style="margin:0">Le détail heure par heure est enregistré depuis le {DEBUT_DETAIL}.</p>'),
                   day_nav(params, d), icon="clock")
            + '<div class="grid2">'
            + card(f"{e(app)} par jour", f"Empilé par enfant, {nd} derniers jours", stacked_days(per_day, nd, USERS, kid_color, nom), icon="calendar")
            + card("À quelle heure ?", f"Temps passé sur {e(app)} par heure, {pl}",
                   heat([(f'{avatar(u, "sm")}{e(nom(u))}', hours.get(u, [0] * 24)) for u in USERS]), icon="clock")
            + "</div>"
            + card("Qui l'a utilisée, et quand", f"Périodes d'utilisation {pl}, de la plus récente à la plus ancienne",
                   more(f"Voir les {len(lst)} périodes", f'<div class="tw"><table class="t"><tr><th>Enfant</th><th class="n">Jour</th><th class="n">Début</th>'
                        f'<th class="n">Fin</th><th class="n">Durée</th><th>Fenêtres et pages</th></tr>{t_rows}</table></div>', len(lst) <= 8)
                   if t_rows else '<div class="empty">Pas encore de détail pour cette période.</div>', icon="users")
            + "</div>")
    return body, f"Utilisation de {app}", params


# ======================================================================
# Aide
# ======================================================================
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
<div class="arch-box parent">{IC_MONITOR}<b>Parents</b><span>Navigateur<br><code>http://{VM}:8080</code></span></div></div>
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
<li><b>Ouvrir l'espace parents</b> : <code>http://{VM}:8080</code> (identifiant et mot de passe parent). Astuce : ajoutez-le à l'écran d'accueil du téléphone.</li>
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
<li><b>Limites par application ou site</b> : comptées sur toute la journée ; quand la limite est atteinte, l'application est fermée et bloquée jusqu'au lendemain.</li>
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

AIDE_DEPLOIEMENT = r"""<p>Fichiers du projet sur le PC Windows : <code>F:\vm_enfants</code>.</p>
<div class="tw"><table class="t"><tr><th>Étape</th><th>Comment</th></tr>
<tr><td><b>1. Créer la machine virtuelle</b></td><td>PowerShell <b>en administrateur</b> :<br><code>powershell -ExecutionPolicy Bypass -File F:\vm_enfants\vm\creer_vm.ps1</code><br>
Active Hyper-V si besoin, crée la VM Debian sur le Wi-Fi (adresse propre sur la box), démarrage automatique avec Windows.</td></tr>
<tr><td><b>2. Installer ou mettre à jour MaranYSE</b></td><td>Git Bash :<br><code>bash F:/vm_enfants/vm/installer_controle.sh</code><br>
Reconstruit le bureau des enfants (<code>container/</code>), met à jour l'espace parents (<code>vm/tableau.py</code>, <code>logique.py</code>, <code>marque.py</code>).
<b>Ferme les sessions ouvertes</b> : prévenez les enfants (bouton Message) avant.</td></tr>
<tr><td><b>3. Vérifier</b></td><td>Scénario de test graphique (vraies sessions, captures) : <code>tests/scenario.py</code>, lancé dans la VM.
Comptes de test temporaires, rapport HTML avec captures ; vos réglages sont restaurés à la fin.</td></tr>
</table></div>
<p class="muted small">Dans la VM : comptes et mots de passe dans <code>/srv/bureau/secrets</code>, dossiers des enfants dans <code>/srv/bureau/home</code>,
règles dans <code>~/controle.json</code>, statistiques dans <code>~/stats.db</code> (utilisateur <code>parent</code>).</p>"""

AIDE_MAINTENANCE = r"""<ul class="help-list">
<li><b>Redémarrer le bureau</b> (bas du menu) : ferme toutes les sessions et redémarre le bureau des enfants. Utile si quelque chose semble bloqué.</li>
<li><b>Sauvegarde</b> : copier <code>/srv/bureau/home</code> (fichiers des enfants), <code>/srv/bureau/secrets</code> (comptes), <code>~/controle.json</code> (règles)
et <code>~/stats.db</code> (statistiques). Le disque de la VM est <code>F:\vm_enfants\vm\bureau-enfants.vhdx</code>.</li>
<li><b>Mémoire</b> : la VM utilise la mémoire dynamique de Hyper-V ; compter environ 1,5 Go par enfant connecté avec Firefox.</li>
<li><b>Mises à jour de sécurité</b> : reconstruire le bureau de temps en temps (étape 2 ci-dessus) récupère les dernières versions de Debian et Firefox.</li>
</ul>"""

AIDE_DEPANNAGE = r"""<details class="more faq"><summary>Écran noir à la connexion</summary><p>Attendez 30 secondes puis reconnectez-vous :
MaranYSE répare automatiquement les droits du dossier de connexion. Si ça persiste : « Redémarrer le bureau ».</p></details>
<details class="more faq"><summary>Un enfant n'arrive pas à se connecter</summary><p>Vérifiez sur l'Accueil : <b>rouge</b> (horaire ou temps du jour épuisé)
ou <b>pause</b> → le compte est verrouillé, c'est normal (« +30 min » ou « Reprendre » pour débloquer). Sinon, vérifiez son mot de passe dans Comptes.</p></details>
<details class="more faq"><summary>Un site devrait être bloqué mais s'ouvre encore</summary><p>Le blocage s'applique en moins de 30 s, mais Firefox garde
parfois l'adresse en mémoire quelques minutes : fermez et rouvrez Firefox. Vérifiez aussi que l'enfant est bien en <b>orange</b> (en vert, rien n'est bloqué).</p></details>
<details class="more faq"><summary>Une application ne s'ouvre pas</summary><p>Elle est peut-être bloquée ou sa limite du jour est atteinte (page Règles de l'enfant).</p></details>
<details class="more faq"><summary>L'espace parents ne répond plus</summary><p>Vérifiez que la VM tourne (Gestionnaire Hyper-V) et que le PC Windows est allumé.
Elle redémarre toute seule avec Windows.</p></details>"""

AIDE_LIMITES = r"""<ul class="help-list">
<li>Le filtrage des sites passe par le DNS : visiter un site <b>par son adresse IP</b> reste possible dans Firefox (sans intérêt pour les grands sites).</li>
<li>L'espace parents est en <b>HTTP</b> (non chiffré) : à utiliser uniquement sur le Wi-Fi de la maison.</li>
<li>Recherche sécurisée imposée sur Google et YouTube, pas sur Bing. Pas d'alertes envoyées au téléphone.</li>
<li>En <b>vert</b>, l'internet n'est pas filtré : les sites proxy y sont accessibles (c'est le principe de l'accès complet).</li>
<li>Avec « Programmes téléchargés : Interdit », Netflix et Disney+ peuvent ne pas fonctionner dans Firefox (module de lecture protégé).</li>
</ul>"""

APROPOS = r"""<p><b>MaranYSE</b> · un ordinateur partagé, des comptes pour chaque enfant, sous le contrôle des parents.</p>
<p class="muted small">Logiciels libres utilisés : Debian, XFCE, xrdp, Firefox ESR, Docker, dnsmasq, iptables, Thonny, GCompris, Tux Paint, LibreOffice.
Filtrage familial par CleanBrowsing Family. Relais pip : tinyproxy.</p>"""


def page_aide(host=""):
    vm = (host or "192.168.1.15:8080").split(":")[0]
    toc = "".join(f'<a href="#{k}">{e(v)}</a>' for k, v in AIDE_SECTIONS)
    sec = lambda k, title, body, icon: (f'<section class="card stack help-sec" id="{k}"><div class="chead"><span class="cico">{ic(icon, 18)}</span>'
                                       f'<h2>{title}</h2></div>{body}</section>')
    pages = [("home", "Accueil", "Chaque enfant d'un coup d'œil : en ligne ou non, ce qui est ouvert, son niveau d'accès et le temps du jour. "
              "Boutons rapides : <b>Pause</b>, <b>Message</b>, <b>+30 min</b>, <b>Déconnecter</b>, et « … » pour son mot de passe."),
             ("calendar", "Planning", "Une grille par enfant, case par case (30 min) : <b>vert</b>, <b>orange</b> ou <b>rouge</b>. Modèles École / Vacances, "
              "copie d'un jour sur la semaine, et un <b>temps d'écran maximum par jour</b>."),
             ("shield", "Règles", "Ce qui s'applique en orange : internet libre, filtré ou coupé ; sites et applications <b>bloqués</b>, <b>limités</b> "
              "(minutes par jour) ou <b>autorisés</b>. Règles communes + exceptions par enfant. En bas : les <b>contournements</b>."),
             ("chart", "Statistiques", "Vues <b>Ensemble</b>, <b>Par enfant</b>, <b>Par application</b> : courbes d'évolution, temps par jour, heures d'utilisation, "
              "chronologie heure par heure (qui a utilisé quoi, quand), pages et fenêtres, historique."),
             ("box", "Logiciels", "Installer un outil pour tous les enfants d'un clic (VS Code, Scratch, Stellarium…) ou n'importe quel "
              "paquet Debian ; le désinstaller."),
             ("cpu", "Puissance", "Un <b>curseur</b> règle la part de l'ordinateur (processeur et mémoire) que les enfants peuvent utiliser, "
              "en pourcentage de ce que l'ordinateur possède ; un second fixe l'<b>espace disque</b> de chaque enfant. "
              "Appliqué tout de suite, sans fermer les sessions."),
             ("users", "Comptes", "Ajouter un enfant (avec copie des réglages d'un autre), renommer, changer un mot de passe, supprimer "
              "(en gardant ou non ses fichiers et statistiques).")]
    pages_html = "".join(f'<div class="help-page"><span class="cico">{ic(i, 18)}</span><div><b>{t}</b><p>{d}</p></div></div>' for i, t, d in pages)
    body = f"""<div class="help-layout"><nav class="toc card">{toc}</nav><div class="stack">

<section class="card help-hero"><img src="/logo-hd.jpg?v={V_IMG}" alt="MaranYSE"><div>
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
    return shell("aide", "Aide", "Comprendre et utiliser MaranYSE", body)


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
        cards.append(f"""<section class="card stack"><div class="acc">{avatar(u, "lg")}<div class="nm"><h3>{e(nom(u))}</h3>
<div class="presence">{pres}</div></div>
<div class="row"><button class="btn sm" data-open="edit-{u}">{ic("edit", 16)} Modifier</button>{delete}</div></div>
<div class="row small"><span class="muted">Identifiant</span> <code translate="no">{e(u)}</code>
<span class="muted" style="margin-left:10px">Mot de passe</span> <code translate="no">{e(pws.get(u, "?"))}</code></div>
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


# Catalogue : catégories repliables (ouvertes/fermées mémorisées dans ce navigateur) et recherche
LG_JS = """<script>(()=>{const secs=[...document.querySelectorAll('.lg-sec')];if(!secs.length)return;
const K='maranyse-logiciels-ouverts';let m={};try{m=JSON.parse(localStorage.getItem(K)||'{}')}catch(e){}
secs.forEach((d,i)=>{const c=d.dataset.cat;d.open=c in m?m[c]:i===0;d.addEventListener('toggle',()=>{if(q.value)return;m[c]=d.open;try{localStorage.setItem(K,JSON.stringify(m))}catch(e){}})});
const q=document.getElementById('lg-q'),rien=document.getElementById('lg-rien');
const tous=o=>secs.forEach(d=>{d.open=o;m[d.dataset.cat]=o});
document.getElementById('lg-all').onclick=()=>{tous(true);try{localStorage.setItem(K,JSON.stringify(m))}catch(e){}};
document.getElementById('lg-none').onclick=()=>{tous(false);try{localStorage.setItem(K,JSON.stringify(m))}catch(e){}};
const norm=s=>s.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'');
q.addEventListener('input',()=>{const v=norm(q.value.trim());let n=0;
 secs.forEach(d=>{let k=0;d.querySelectorAll('.lg-card').forEach(c=>{const ok=!v||norm(c.textContent).includes(v);c.hidden=!ok;if(ok)k++});
  d.hidden=v&&!k;if(v)d.open=k>0;else d.open=m[d.dataset.cat]??false;n+=k});rien.hidden=!v||n>0})})()</script>"""


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
    if a == "delkid":
        return remove_account(u, purge=g("purge") == "1")
    if a == "secu":
        k = g("k")
        if (scope != ALL and scope not in USERS) or k not in SECU or (scope != ALL and not SECU[k][2])                 or v not in set(SECU_VAL) | ({"herite"} if scope != ALL else set()):
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
            minutes = max(5, min(1440, int(g("minutes") or 60))) if mode == "limiter" else 0
        except ValueError:
            minutes = 60
        rule = {"cle": cle, "mode": mode, "minutes": minutes}

        def f(d):
            d[scope]["regles"] = [x for x in d[scope]["regles"] if x["cle"] != cle] + [rule]
            txt = {"bloquer": "bloqué", "limiter": f"limité à {dur(minutes * 60)} par jour", "autoriser": "autorisé sans limite"}[mode]
            return f"{target(cle)[1]} : {txt} pour {who}."
        return update(f)
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
        def f(d):
            for i in range(7):
                gg = g(f"grille_{i}")
                if re.fullmatch(f"[VOR]{{{SLOTS}}}", gg):
                    d[u]["grille"][str(i)] = gg
                try:
                    d[u]["quota"][str(i)] = max(0, min(1440, int(g(f"quota_{i}") or 0)))
                except ValueError:
                    d[u]["quota"][str(i)] = 0
            return f"Planning de {nom(u)} enregistré."
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


class H(BaseHTTPRequestHandler):
    def auth(self):
        h = self.headers.get("Authorization", "")
        try:
            ok = h.startswith("Basic ") and base64.b64decode(h[6:]).decode() == f"{LOGIN}:{PASSWORD}"
        except Exception:
            ok = False
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

    def send(self, body):
        lang = self.langue()
        try:
            body = i18n.traduire_html(body, lang, noms_page(), urlparse(self.path).query[:80])
        except Exception as ex:                  # une traduction ratée ne doit jamais empêcher d'afficher la page
            print("erreur traduction:", repr(ex), flush=True)
        b = body.encode()
        self.send_response(200)
        if getattr(self, "theme_cookie", None):
            self.send_header("Set-Cookie", f"apparence={self.theme_cookie}; Path=/; Max-Age=31536000; SameSite=Lax")
        if getattr(self, "lang_cookie", None):
            self.send_header("Set-Cookie", f"lang={self.lang_cookie}; Path=/; Max-Age=31536000; SameSite=Lax")
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if not self.auth():
            return
        path = urlparse(self.path).path
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
            self.end_headers()
            self.wfile.write(data)
            return
        q = parse_qs(urlparse(self.path).query)
        REQ.theme = self.choisir_theme()
        p, flash = q.get("p", ["live"])[0], q.get("msg", [""])[0]
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
        if urlparse(self.path).path == "/api/charge-hote":           # script de l'ordinateur hôte : jeton, pas de mot de passe
            ok = secrets.compare_digest(self.headers.get("X-Jeton", ""), jeton_hote())
            if ok:
                try:
                    recevoir_charge_hote(json.loads(self.rfile.read(min(4096, int(self.headers.get("Content-Length", 0))))))
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
        form = parse_qs(self.rfile.read(int(self.headers.get("Content-Length", 0))).decode())
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


if __name__ == "__main__":
    db().close()
    load_accounts()
    threading.Thread(target=boucle, daemon=True).start()
    ThreadingHTTPServer(("0.0.0.0", PORT), H).serve_forever()
