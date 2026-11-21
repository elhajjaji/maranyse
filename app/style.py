"""MaranYSE — icônes SVG, pastilles, feuille de style CSS de base et scripts JS de l'espace parents."""
import html
from logique import USERS, APPS, nom, kid_hex
import logiciels

MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]

# Couleurs des séries (palette validée daltonisme, clair et sombre) : la couleur suit l'objet, jamais son rang.
APP_SLOT = {"Firefox": 1, "LibreOffice": 2, "GCompris": 3, "Tux Paint": 4, "Éditeur de texte": 5,
            "Visionneuse d'images": 6, "Terminal": 7, "Thonny": 8}


def e(s):
    return html.escape(str(s), quote=True)


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
    return f'<span class="av av{i} av-{size}" style="background:{kid_hex(u)}" translate="no">{e(nom(u)[:1].upper())}</span>'


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


def card(title, sub, inner, extra="", icon=None, cls=""):
    """Carte de graphique : pastille d'icône, titre, sous-titre, contrôles à droite."""
    sub_html = f'<span class="muted small">{sub}</span>' if sub else ""
    ico = f'<span class="cico">{ic(icon, 18)}</span>' if icon else ""
    return (f'<section class="card stack {cls}"><div class="between"><div class="chead">{ico}<div><h2>{title}</h2>{sub_html}</div></div>{extra}</div>'
            f'{inner}</section>')


def more(label, inner, open_=False):
    return f'<details class="more"{" open" if open_ else ""}><summary>{label}</summary>{inner}</details>'


# ======================================================================
# Feuille de style de base
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
.rdp-tip{position:relative;display:inline-flex;align-items:center;gap:5px;padding:2px 8px;border-radius:99px;background:var(--surface2);color:var(--primary);font-size:12px;font-weight:600;cursor:help;border:1px solid var(--border)}
.rdp-tip .tip-pop{display:none;position:absolute;left:0;top:calc(100% + 6px);z-index:40;min-width:230px;padding:10px 12px;border-radius:12px;background:var(--surface);color:var(--text);border:1px solid var(--border);box-shadow:0 8px 24px rgba(15,23,42,.18);font-weight:400;font-size:12.5px;line-height:1.5;flex-direction:column;gap:4px;white-space:nowrap}
.rdp-tip:hover .tip-pop,.rdp-tip:focus .tip-pop,.rdp-tip:focus-within .tip-pop{display:flex}
.rdp-tip .tip-pop code{background:var(--surface2);padding:1px 6px;border-radius:6px;font-size:12.5px;user-select:all}
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
.strip{display:flex;position:relative;height:10px;border-radius:4px;overflow:hidden;background:var(--track)}.strip i{display:block;height:100%}
.strip .now-m{position:absolute;top:0;bottom:0;width:2px;background:var(--text);z-index:2}
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
.pg td{height:10px}
.pg-seg{display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap;padding:10px 12px;border-radius:12px;border:1px solid var(--border);background:var(--surface2)}
.pg-seg-add{display:flex;align-items:flex-end;gap:10px;flex-wrap:wrap;padding:12px;border-radius:12px;border:1px dashed var(--border);background:var(--surface2)}
.pg-seg-add label{display:flex;flex-direction:column;gap:4px;font-size:12.5px;color:var(--text2);font-weight:550}
.pg-seg-add input[type=time],.pg-seg-add select,.pg-seg select,.pg-seg input[type=time]{width:auto;padding:5px 8px;font-size:13px;border-radius:9px}
.min-num{width:68px!important;padding:6px 6px!important;text-align:center;font-weight:700}
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
/* bandeau & bande droite quand un enfant est sélectionné */
.kid-band{position:fixed;top:0;right:0;bottom:0;width:10px;background:var(--kid-c);z-index:45;pointer-events:none;box-shadow:-2px 0 10px color-mix(in srgb,var(--kid-c) 35%,transparent)}
.kid-focus .main{padding-right:38px}
.kid-focus .main .card:not(.legend){border-right:5px solid var(--kid-c)!important;box-shadow:0 2px 6px rgba(15,46,51,.06),0 12px 30px color-mix(in srgb,var(--kid-c) 16%,rgba(15,46,51,.08))}
.kid-pill{display:inline-flex;gap:8px;align-items:center;padding:4px 12px 4px 5px;border-radius:99px;font-weight:700;font-size:13.5px;
 background:color-mix(in srgb,var(--kid-c) 14%,var(--surface));border:1.5px solid var(--kid-c);color:var(--text)}
.color-sw{display:inline-flex;gap:6px;align-items:center;flex-wrap:wrap}
.color-dot{width:24px;height:24px;border-radius:50%;border:2px solid var(--surface);box-shadow:0 0 0 1px var(--border);cursor:pointer;padding:0}
.color-dot.on{box-shadow:0 0 0 2.5px var(--text)}
input[type=color].color-pick{width:34px;height:28px;padding:2px;border-radius:8px;border:1px solid var(--border);background:var(--surface);cursor:pointer}
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
// garde si modifications non enregistrées (ex. Planning) avant de changer d'enfant ou de page
const df=$('#dlg-dirty');
if(df){
 let nextUrl='';
 $$('a[href^="/?"]').forEach(a=>a.addEventListener('click',ev=>{
  const bar=$('.savebar.is-dirty');
  if(!bar||a.closest('.savebar'))return;
  ev.preventDefault();nextUrl=a.getAttribute('href');df.showModal();
 }));
 $('#df-leave').onclick=()=>{const b=$('.savebar');if(b)b.classList.remove('is-dirty');df.close();location=nextUrl};
 $('#df-save').onclick=()=>{const f=$('.savebar').closest('form');let bi=$('input[name=back]',f);
  if(!bi){bi=document.createElement('input');bi.type='hidden';bi.name='back';f.appendChild(bi)}
  bi.value=nextUrl;df.close();f.requestSubmit()};
}
$$('[data-fill-text]').forEach(b=>b.addEventListener('click',()=>{const t=b.closest('form').querySelector('textarea');t.value=b.dataset.fillText;t.focus()}));
$$('[data-auto] input').forEach(i=>i.addEventListener('change',()=>i.form.submit()));
// règle : afficher le champ du site libre et la durée (au pas de 1 min + champ numérique)
function fmtMins(v){return v>=60?Math.floor(v/60)+' '+_t('h')+(v%60?' '+String(v%60).padStart(2,'0'):''):v+' '+_t('min')}
function sync(d){const c=$('input[name=cle]:checked',d),m=$('input[name=mode]:checked',d);
 $('.dom',d).style.display=c&&c.value==='dom:'?'':'none';$('.mins',d).style.display=m&&m.value==='limiter'?'':'none';
 const o=$('output',d),r=$('input[type=range]',d),num=$('.min-num',d);
 if(r){const v=Math.max(1,Math.min(1440,+(num&&document.activeElement===num?num.value:r.value)||1));
  if(num&&document.activeElement!==num)num.value=v;if(document.activeElement===num)r.value=Math.min(240,v);
  if(o)o.textContent=fmtMins(v)}}
function preset(d,p){const c=$(`input[name=cle][value="${p.cle}"]`,d);if(c)c.checked=true;else{$('input[name=cle][value="dom:"]',d).checked=true;$('.dom input',d).value=p.cle.slice(4)}
 const m=$(`input[name=mode][value="${p.mode}"]`,d);if(m)m.checked=true;
 const v=p.minutes||60;const r=$('input[type=range]',d),num=$('.min-num',d);if(r)r.value=Math.min(240,v);if(num)num.value=v;sync(d)}
$$('dialog.rule-dlg').forEach(d=>{
 d.addEventListener('input',ev=>{const r=$('input[type=range]',d),num=$('.min-num',d);
  if(ev.target===r&&num)num.value=r.value;else if(ev.target===num&&r)r.value=Math.min(240,Math.max(1,+num.value||1));sync(d)});
 $$('.min-step',d).forEach(b=>b.onclick=()=>{const num=$('.min-num',d),r=$('input[type=range]',d);
  const v=Math.max(1,Math.min(1440,(+(num?num.value:r.value)||1)+(+b.dataset.d)));if(num)num.value=v;if(r)r.value=Math.min(240,v);sync(d)});
 $$('.min-quick',d).forEach(b=>b.onclick=()=>{const num=$('.min-num',d),r=$('input[type=range]',d);
  const v=+b.dataset.v;if(num)num.value=v;if(r)r.value=Math.min(240,v);sync(d)});
 sync(d)});
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
