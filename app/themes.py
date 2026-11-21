"""MaranYSE — apparences de l'espace parents (choix « Apparence » dans l'en-tête).
Chaque thème est une feuille de style ajoutée après la feuille de base (tableau.CSS) : il redéfinit les couleurs
(variables --bg, --primary…) et la forme de quelques éléments. Couleurs tirées du logo : pétrole #0d5c63,
vert pomme #7cc243, orange #f7a41d, jaune #ffc72c, bleu ciel #3ba6e0, rose #e85a9c."""

DEFAUT = "marque"
NOMS = {"marque": "MaranYSE", "ludique": "Ludique", "nuit": "Nuit", "epure": "Épuré", "classique": "Classique"}

# Polices système locales (aucune requête vers Google Fonts : fonctionne hors-ligne et sans fuite de métadonnées)
POLICES = {}

# couleurs des pastilles d'icônes du menu (dans l'ordre des pages)
_MENU = [("#e3f2ef", "#0d5c63"), ("#fff1d6", "#c77700"), ("#eaf6dc", "#4f9a25"), ("#e2f1fb", "#1f7fbf"),
         ("#fde6f0", "#c2397a"), ("#fff6d6", "#b38600"), ("#ece9fb", "#5b4bc4"), ("#e3f2ef", "#0d5c63")]
_MENU_CSS = "".join(f".menu a:nth-child({i + 1}) .ic,.tabbar a:nth-child({i + 1}) .ic{{background:{b};color:{c}}}" for i, (b, c) in enumerate(_MENU))

_LUDIQUE_VARS = """--bg:#f2f8ee;--surface:#fff;--surface2:#f2f8ed;--text:#103a3f;--text2:#3d5f63;--muted:#7a9396;--border:#e3ecdd;
--primary:#0d5c63;--primary-2:#0a4a50;--primary-soft:#e3f2ef;--on-primary:#fff;--accent:#7cc243;--accent-2:#4f9a25;--accent-soft:#eaf6dc;
--green:#2e9e4f;--green-soft:#e4f5e3;--orange:#d97a00;--orange-soft:#fff1d6;--red:#d94452;--red-soft:#fde6e8;
--g:#6cc04a;--o:#f7a41d;--r:#ec5b5b;--track:#e8f0e3;
--s1:#2a78d6;--s2:#eb6834;--s3:#1baf7a;--s4:#eda100;--s5:#e87ba4;--s6:#008300;--s7:#6250d6;--s8:#e34948;--s-autre:#a3a29b;--s-inactif:#d9dbe0;
--q0:#eef6ea;--q1:#d3ecc3;--q2:#a8d98a;--q3:#6cbb4a;--q4:#2f8a55;--q5:#0d5c63;
--shadow:0 1px 3px rgba(13,92,99,.06),0 12px 32px rgba(13,92,99,.08);--radius:24px;color-scheme:light"""

LUDIQUE = f"""
:root{{{_LUDIQUE_VARS}}}
@media (prefers-color-scheme:dark){{:root{{{_LUDIQUE_VARS}}}}}
body{{font-family:Nunito,system-ui,-apple-system,"Segoe UI",sans-serif;font-size:15.5px;
 background:radial-gradient(1100px 520px at 105% -8%,#dff1fb 0,transparent 62%),radial-gradient(900px 480px at -8% 108%,#fff0d2 0,transparent 58%),var(--bg);background-attachment:fixed}}
h1,h2,h3,.kt-num,.kpi b,.kpi-card b,.pw-range output,.dlg h3{{font-family:Fredoka,Nunito,sans-serif;font-weight:600;letter-spacing:0}}
.head h1{{font-size:31px;color:var(--primary)}}.head p{{color:var(--text2)}}
.side{{margin:14px 0 14px 14px;height:calc(100vh - 28px);top:14px;border-radius:30px;border:0;box-shadow:var(--shadow);padding:20px 14px}}
.logo{{max-width:190px}}.logo img{{box-shadow:none;border-radius:0}}
.brand-sub{{color:var(--accent-2);font-weight:800;letter-spacing:.08em}}
.menu{{gap:3px}}.menu a{{font-weight:700;border-radius:16px;padding:7px 10px;color:var(--text)}}
.menu a .ic,.tabbar a .ic{{box-sizing:content-box;padding:6px;border-radius:11px}}
{_MENU_CSS}
.menu a.on{{background:linear-gradient(90deg,#eaf6dc,#f6fbf2);color:var(--primary);box-shadow:inset 4px 0 0 var(--accent)}}
.menu a:hover{{background:#f4f9f0}}
.card{{border:0}}.card h2{{font-size:19px;color:var(--primary)}}
.cico{{background:linear-gradient(135deg,#eaf6dc,#dff1fb);color:var(--accent-2);border-radius:13px;width:38px;height:38px}}
.btn{{border-radius:14px;font-weight:700;border-color:#dfe9d8}}
.btn.primary{{background:linear-gradient(180deg,#8fce55,#5ea82f);border:0;color:#fff;box-shadow:0 4px 12px rgba(94,168,47,.32),inset 0 1px 0 rgba(255,255,255,.35)}}
.btn.primary:hover{{background:linear-gradient(180deg,#99d660,#58a02b)}}
.seg{{background:#eef5e9;border-radius:16px}}.seg a.on,.seg input:checked+span{{color:var(--primary);font-weight:700}}
.people a,.chips2 a{{border:0;box-shadow:var(--shadow)}}.people a.on,.chips2 a.on{{background:var(--accent-soft);color:var(--primary);box-shadow:inset 0 0 0 2px var(--accent)}}
.charge{{border:0;box-shadow:var(--shadow);border-radius:14px}}.lang select{{border-radius:12px}}
.mode{{border-radius:18px}}.mode .mi{{border-radius:13px}}
.now-item{{background:#f4f9f0}}
.ins-card{{background:linear-gradient(135deg,#eaf6dc,#fff 55%,#e2f1fb)}}
.help-hero{{background:linear-gradient(135deg,#eaf6dc,#fff 55%,#e2f1fb)}}.help-hero img{{box-shadow:none;border-radius:0}}
input[type=text],input[type=number],input[type=search],textarea,select{{border-radius:14px;border-color:#dfe9d8}}
.savebar{{border:0}}
dialog{{border-radius:28px}}
#toast{{background:var(--primary);color:#fff}}
@media (max-width:860px){{.tabbar{{left:10px;right:10px;bottom:10px;border:0;border-radius:22px;box-shadow:0 8px 28px rgba(13,92,99,.18)}}
 .tabbar a .ic{{padding:4px}}.head h1{{font-size:25px}}}}
"""

_NUIT_VARS = """--bg:#061b20;--surface:rgba(255,255,255,.055);--surface2:rgba(255,255,255,.085);--text:#ecf7f4;--text2:#bcd6d2;--muted:#82a6a2;
--border:rgba(255,255,255,.10);--primary:#9bd34a;--primary-2:#b3e46b;--primary-soft:rgba(155,211,74,.15);--on-primary:#0b2a10;
--accent:#ffb547;--accent-2:#ffc56b;--accent-soft:rgba(255,181,71,.14);
--green:#7fdc8f;--green-soft:rgba(127,220,143,.14);--orange:#ffb547;--orange-soft:rgba(255,181,71,.15);--red:#ff8080;--red-soft:rgba(255,128,128,.15);
--g:#5ccf7a;--o:#ffad3b;--r:#ff6b6b;--track:rgba(255,255,255,.09);
--s1:#3987e5;--s2:#d95926;--s3:#199e70;--s4:#c98500;--s5:#d55181;--s6:#2f9e2f;--s7:#9085e9;--s8:#e66767;--s-autre:#6f6e68;--s-inactif:#3a3f4a;
--q0:rgba(255,255,255,.05);--q1:#14505a;--q2:#2a7a80;--q3:#4f9fa2;--q4:#82c4c3;--q5:#bfe3df;
--shadow:0 1px 1px rgba(0,0,0,.2),0 14px 40px rgba(0,0,0,.28);--radius:22px;color-scheme:dark"""

NUIT = f"""
:root{{{_NUIT_VARS}}}
@media (prefers-color-scheme:dark){{:root{{{_NUIT_VARS}}}}}
body{{font-family:Nunito,system-ui,-apple-system,"Segoe UI",sans-serif;font-size:15.5px;
 background:radial-gradient(900px 600px at 85% -10%,rgba(124,194,67,.18) 0,transparent 60%),radial-gradient(800px 600px at -10% 100%,rgba(59,166,224,.16) 0,transparent 60%),
 linear-gradient(160deg,#0a2a30,#061b20 55%,#071822);background-attachment:fixed}}
h1,h2,h3,.kt-num,.kpi b,.kpi-card b,.pw-range output,.dlg h3{{font-family:Fredoka,Nunito,sans-serif;font-weight:600;letter-spacing:0}}
.head h1{{font-size:31px}}
.side{{margin:14px 0 14px 14px;height:calc(100vh - 28px);top:14px;border-radius:30px;border:1px solid var(--border);background:rgba(255,255,255,.04);
 backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px)}}
.card,.savebar,.charge{{backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px)}}
.wm-a{{color:#eef8f5}}.hero{{background:linear-gradient(115deg,rgba(155,211,74,.16),rgba(255,255,255,.03) 55%,rgba(59,166,224,.14))}}.hero h2{{color:var(--text)}}.hero-kid{{background:rgba(255,255,255,.08)}}.hero-img{{filter:drop-shadow(0 10px 24px rgba(0,0,0,.4))}}
.brand-sub{{color:var(--primary);letter-spacing:.08em;font-weight:800}}
.menu a{{font-weight:700;border-radius:14px;color:var(--text2)}}.menu a:hover{{background:rgba(255,255,255,.06)}}
.menu a.on{{background:linear-gradient(90deg,rgba(155,211,74,.22),rgba(155,211,74,.04));color:#eaffd0;box-shadow:inset 3px 0 0 var(--primary)}}
.btn.primary{{background:linear-gradient(180deg,#a8dc5c,#7cc243);border:0;color:#0b2a10;box-shadow:0 6px 18px rgba(124,194,67,.3)}}
.btn{{border-radius:14px;font-weight:700}}
.cico{{background:rgba(155,211,74,.15);color:var(--primary)}}
dialog{{background:#0c272d;border:1px solid var(--border)}}
select option{{background:#0c272d;color:var(--text)}}
#vtip{{background:#ecf7f4;color:#0b2328}}#toast{{background:var(--primary);color:#0b2a10}}
.stats-bar{{background:transparent;backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px)}}
.mxt td.mx.q4 a,.mxt td.mx.q5 a{{color:#0e1015}}
.tabbar{{background:#0c272d}}
.help-hero,.ins-card{{background:linear-gradient(135deg,rgba(155,211,74,.14),rgba(255,255,255,.03) 60%)}}.help-hero img{{border-radius:22px}}
@media (max-width:860px){{.tabbar{{left:10px;right:10px;bottom:10px;border:1px solid var(--border);border-radius:22px}}.head h1{{font-size:25px}}}}
"""

_EPURE_VARS = """--bg:#f6f7f9;--surface:#fff;--surface2:#f3f5f7;--text:#0f1c1f;--text2:#4b5b5e;--muted:#8a979a;--border:#e6e9ed;
--primary:#0d5c63;--primary-2:#0a4a50;--primary-soft:#e9f3f2;--on-primary:#fff;--accent:#7cc243;--accent-2:#4f9a25;--accent-soft:#eef7e6;
--green:#1f9d55;--green-soft:#e7f6ec;--orange:#d97a00;--orange-soft:#fff3e0;--red:#d6404e;--red-soft:#fdeaec;
--g:#34b36b;--o:#f2a03d;--r:#e5544f;--track:#eef1f3;
--s1:#2a78d6;--s2:#eb6834;--s3:#1baf7a;--s4:#eda100;--s5:#e87ba4;--s6:#008300;--s7:#6250d6;--s8:#e34948;--s-autre:#a3a29b;--s-inactif:#d9dbe0;
--q0:#eef3f3;--q1:#cfe5e3;--q2:#9ccac6;--q3:#5aa29f;--q4:#2a7a80;--q5:#0d5c63;
--shadow:0 1px 2px rgba(16,24,40,.04),0 1px 3px rgba(16,24,40,.04);--radius:14px;color-scheme:light"""

EPURE = f"""
:root{{{_EPURE_VARS}}}
@media (prefers-color-scheme:dark){{:root{{{_EPURE_VARS}}}}}
body{{font-family:Inter,system-ui,-apple-system,"Segoe UI",sans-serif;font-size:14.5px;letter-spacing:-.005em}}
h1,h2,h3{{font-weight:650;letter-spacing:-.02em}}.head h1{{font-size:24px}}
.side{{width:232px;padding:18px 12px;background:#fbfcfd}}
.brand{{padding:14px 10px 16px;border-radius:16px;background:linear-gradient(160deg,#eef7e6,#e9f3f2)}}.brand-l .emb{{width:84px;height:84px}}.wm{{font-family:Inter,sans-serif;font-weight:750;font-size:24px}}
.logo{{max-width:150px}}.logo img{{box-shadow:none;border-radius:0}}
.brand-sub{{color:var(--primary);font-size:11.5px;letter-spacing:.1em}}
.menu a{{padding:8px 10px;border-radius:9px;font-weight:550;font-size:14px}}
.menu a.on{{background:var(--surface);color:var(--text);box-shadow:0 1px 2px rgba(16,24,40,.08),inset 3px 0 0 var(--accent)}}
.card{{box-shadow:var(--shadow)}}.card h2{{font-size:16px}}
.btn{{border-radius:9px;font-weight:550;padding:8px 13px}}.btn.primary{{background:var(--primary)}}
.cico{{border-radius:9px;width:30px;height:30px}}
.seg{{border-radius:10px}}.seg a,.seg label span{{border-radius:7px}}
input[type=text],input[type=number],input[type=search],textarea,select{{border-radius:9px}}
.mode{{border-radius:12px}}.pill{{border-radius:7px}}
dialog{{border-radius:16px}}
"""

_MARQUE_VARS = """--bg:#f3f6f5;--surface:#fff;--surface2:#f1f5f4;--text:#0f2e33;--text2:#40595c;--muted:#7d9093;--border:#e3e9e8;
--primary:#0d5c63;--primary-2:#0a4a50;--primary-soft:#e6f1f1;--on-primary:#fff;--accent:#7cc243;--accent-2:#4f9a25;--accent-soft:#eef7e6;
--green:#2e9e4f;--green-soft:#e9f6ec;--orange:#d97a00;--orange-soft:#fff3e2;--red:#d6404e;--red-soft:#fdecee;
--g:#4caf50;--o:#f39c12;--r:#e5544f;--track:#e9efee;
--s1:#2a78d6;--s2:#eb6834;--s3:#1baf7a;--s4:#eda100;--s5:#e87ba4;--s6:#008300;--s7:#6250d6;--s8:#e34948;--s-autre:#a3a29b;--s-inactif:#d9dbe0;
--q0:#eef3f2;--q1:#cfe4e2;--q2:#9ccac6;--q3:#5aa29f;--q4:#2a7a80;--q5:#0d5c63;
--shadow:0 1px 2px rgba(15,46,51,.05),0 6px 20px rgba(15,46,51,.06);--radius:20px;color-scheme:light"""

MARQUE = f"""
:root{{{_MARQUE_VARS}}}
@media (prefers-color-scheme:dark){{:root{{{_MARQUE_VARS}}}}}
body{{font-family:Nunito,system-ui,-apple-system,"Segoe UI",sans-serif;font-size:15.5px;background:var(--bg)}}
h1,h2,h3,.kt-num,.kpi b,.kpi-card b,.pw-range output,.dlg h3,.wm{{font-family:Fredoka,Nunito,sans-serif;font-weight:600;letter-spacing:0}}
/* menu latéral : couleur du logo */
.side{{background:linear-gradient(180deg,#0f6870 0%,#0b4f55 100%);border:0;color:#fff;padding:24px 14px}}
.side .brand-l{{background:#fff;border-radius:22px;padding:14px 12px 12px;width:100%;gap:4px;box-shadow:0 12px 30px rgba(0,0,0,.22)}}
.side .brand-l .emb{{width:196px}}
.brand-sub{{color:rgba(255,255,255,.6);font-weight:800;letter-spacing:.14em;font-size:11.5px}}
.menu{{gap:4px}}.menu a{{color:rgba(255,255,255,.82);font-weight:700;border-radius:14px;padding:10px 12px}}
.menu a .ic{{color:rgba(255,255,255,.9)}}.menu a:hover{{background:rgba(255,255,255,.08);color:#fff}}
.menu a.on{{background:#fff;color:var(--primary);box-shadow:0 6px 16px rgba(0,0,0,.18)}}.menu a.on .ic{{color:var(--accent-2)}}
.side-foot .btn{{color:rgba(255,255,255,.7)!important}}.side-foot .btn:hover{{background:rgba(255,255,255,.08)}}
/* en-tête */
.head{{align-items:center}}.head h1{{font-size:32px;color:var(--primary)}}.head p{{color:var(--muted)}}
.charge,.lang select{{background:#fff;border:1px solid var(--border);border-radius:12px;box-shadow:none}}
.lang select{{padding:6px 10px;font-weight:600;color:var(--text2)}}
/* bannière */
.card.hero{{background:#fff;border:1px solid var(--border);padding:26px 34px 28px;box-shadow:0 14px 34px rgba(13,92,99,.12)}}
.card.hero{{background:linear-gradient(90deg,#0d5c63,#14808a 45%,#7cc243) top/100% 6px no-repeat,#fff}}
.hero::before,.hero::after{{display:none}}
.hero-k{{color:var(--accent-2)}}
.hero-kid{{background:var(--surface2);border:1px solid var(--border);box-shadow:none}}

/* cartes */
.card{{border:1px solid var(--border)}}.card h2{{color:var(--text)}}
.cico{{background:var(--primary-soft);color:var(--primary);border-radius:12px}}
.kid-head h2{{font-size:21px}}
.mode{{background:var(--surface)!important;border:1px solid var(--border);border-left:5px solid var(--g);border-radius:14px;padding:12px 14px}}
.mode .mi{{width:30px;height:30px;border-radius:9px}}.mode b{{font-size:15px}}
.mode-O{{border-left-color:var(--o)}}.mode-R{{border-left-color:var(--r)}}.mode-P{{border-left-color:var(--primary)}}
.btn{{border-radius:12px;font-weight:700}}.btn.primary{{background:var(--primary);border-color:var(--primary)}}.btn.primary:hover{{background:var(--primary-2)}}
.seg{{background:#e9efee}}.people a.on,.chips2 a.on{{background:var(--primary);color:#fff;border-color:var(--primary)}}
#toast{{background:var(--primary);color:#fff}}
@media (max-width:860px){{.tabbar{{background:#0b4f55;border:0}}.tabbar a{{color:rgba(255,255,255,.7)}}.tabbar a.on{{color:#fff}}
 .card.hero{{padding:20px}}.hero-img{{display:none}}}}
"""

CSS = {"marque": MARQUE, "ludique": LUDIQUE, "nuit": NUIT, "epure": EPURE, "classique": ""}


# --- Variantes de couleur du thème MaranYSE (même agencement, autre couleur de menu et d'accent)
# (dégradé du menu haut, bas, couleur principale, foncée, pâle, dégradé du liseré de la bannière)
_VARIANTES = {
    "foret":  ("#2f7a35", "#1d4f22", "#2e7d32", "#1b5e20", "#e8f5e9", "#1d4f22,#3c8d2f 45%,#9bd34a"),
    "ocean":  ("#1f6fc4", "#0d3c75", "#1565c0", "#0d47a1", "#e3f0fc", "#0d3c75,#1e88e5 45%,#7cc243"),
    "prune":  ("#6a43a8", "#3b2160", "#5e35b1", "#4527a0", "#efe9fb", "#3b2160,#7e57c2 45%,#f7a41d"),
    "corail": ("#d4561c", "#7c2d12", "#c2410c", "#9a3412", "#fdeee6", "#7c2d12,#ea580c 45%,#7cc243"),
}


def _variante(haut, bas, prim, prim2, pale, liseré):
    c = MARQUE.replace("#0f6870 0%,#0b4f55 100%", f"{haut} 0%,{bas} 100%").replace("#0d5c63,#14808a 45%,#7cc243", liseré)
    c = c.replace("--primary:#0d5c63;--primary-2:#0a4a50;--primary-soft:#e6f1f1;", f"--primary:{prim};--primary-2:{prim2};--primary-soft:{pale};")
    return c.replace(".tabbar{background:#0b4f55;", f".tabbar{{background:{bas};")


for _k, _v in _VARIANTES.items():
    CSS[_k] = _variante(*_v)

# --- MaranYSE sombre : même agencement sur fond foncé (la bannière reste sur sa carte blanche)
_SOMBRE_VARS = """--bg:#0b1a1d;--surface:#122428;--surface2:#183035;--text:#e8f3f1;--text2:#b5cbc8;--muted:#7f9b98;--border:#22393d;
--primary:#5fc2c9;--primary-2:#86d6db;--primary-soft:#163a3e;--on-primary:#06221f;--accent:#9bd34a;--accent-2:#b5e57a;--accent-soft:#1f3318;
--green:#5fd38a;--green-soft:#15301f;--orange:#f6a548;--orange-soft:#38280f;--red:#f27a7e;--red-soft:#3a1b1d;
--g:#4cc77f;--o:#f5a142;--r:#ee6260;--track:#22393d;
--s1:#3987e5;--s2:#d95926;--s3:#199e70;--s4:#c98500;--s5:#d55181;--s6:#2f9e2f;--s7:#9085e9;--s8:#e66767;--s-autre:#6f6e68;--s-inactif:#3a3f4a;
--q0:#183035;--q1:#14505a;--q2:#2a7a80;--q3:#4f9fa2;--q4:#82c4c3;--q5:#bfe3df;
--shadow:0 1px 2px rgba(0,0,0,.3),0 8px 24px rgba(0,0,0,.3);--radius:20px;color-scheme:dark"""
SOMBRE = MARQUE.replace(_MARQUE_VARS, _SOMBRE_VARS).replace("#0f6870 0%,#0b4f55 100%", "#0c3a40 0%,#061a1d 100%") + """
.charge,.lang select{background:var(--surface);color:var(--text)}.seg{background:var(--surface2)}
.menu a.on{background:var(--primary);color:var(--on-primary)}.menu a.on .ic{color:var(--on-primary)}
.card.hero .hero-st,.card.hero .hero-tm,.card.hero .hero-tm b{color:#0f2e33}.card.hero .hero-kid{background:#f1f5f4;color:#0f2e33;border-color:#e3e9e8}
.mxt td.mx.q4 a,.mxt td.mx.q5 a{color:#0e1015}select option{background:#122428;color:#e8f3f1}
"""
CSS["sombre"] = SOMBRE
NOMS = {"marque": "MaranYSE · Pétrole", "foret": "MaranYSE · Forêt", "ocean": "MaranYSE · Océan", "prune": "MaranYSE · Prune",
        "corail": "MaranYSE · Corail", "sombre": "MaranYSE · Sombre", "ludique": "Ludique", "nuit": "Nuit", "epure": "Épuré", "classique": "Classique"}


def options(cur):
    return "".join(f'<option value="{k}"{" selected" if k == cur else ""}>{v}</option>' for k, v in NOMS.items())
