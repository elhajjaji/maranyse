"""MaranYSE — langues de l'espace parents et des messages envoyés aux enfants.

Les pages sont écrites en français ; avant l'envoi, traduire_html() découpe la page en phrases (texte et
balises de mise en forme comme <b> ou <a>, attributs title/placeholder/data-confirm…) et remplace chaque phrase
par sa traduction (catalogues i18n/<langue>.json). Dans la clé d'une phrase, les nombres deviennent {n0}, {n1}…,
les prénoms des enfants {u0}…, les jours et mois {d0}… et les balises <t0>…</t0> : une même phrase sert quel que
soit le chiffre ou l'enfant, et la traduction peut changer l'ordre des mots.
Une phrase sans traduction reste en français (et est notée dans ~/i18n_cles.json si ~/.i18n_collecte existe)."""
import functools
import html as _html
import json
import os
import re
import threading

ICI = os.path.dirname(os.path.abspath(__file__))
DOSSIER = os.path.join(ICI, "i18n")

# code : (nom dans la langue, locale Linux du bureau des enfants, sens d'écriture)
LANGUES = {
    "fr": ("Français", "fr_FR.UTF-8", "ltr"),
    "en": ("English", "en_US.UTF-8", "ltr"),
    "es": ("Español", "es_ES.UTF-8", "ltr"),
    "de": ("Deutsch", "de_DE.UTF-8", "ltr"),
    "pt": ("Português", "pt_PT.UTF-8", "ltr"),
    "ru": ("Русский", "ru_RU.UTF-8", "ltr"),
    "ar": ("العربية", "ar_MA.UTF-8", "rtl"),
    "hi": ("हिन्दी", "hi_IN.UTF-8", "ltr"),
    "zh": ("中文", "zh_CN.UTF-8", "ltr"),
    "ja": ("日本語", "ja_JP.UTF-8", "ltr"),
}
DEFAUT = "fr"
VIRGULE = {"fr", "es", "de", "pt", "ru"}          # séparateur décimal : virgule ; sinon point

# Jours et mois (écrits par le tableau : « Mardi 10 novembre », « Mar 10 », « mardi 10 »)
JOURS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
DATES = {
    "en": (["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"], ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
           ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]),
    "es": (["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"], ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"],
           ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]),
    "de": (["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"], ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"],
           ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"]),
    "pt": (["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"],
           ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"],
           ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]),
    "ru": (["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"], ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"],
           ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"]),
    "ar": (["الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"], ["اثنين", "ثلاثاء", "أربعاء", "خميس", "جمعة", "سبت", "أحد"],
           ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو", "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"]),
    "hi": (["सोमवार", "मंगलवार", "बुधवार", "गुरुवार", "शुक्रवार", "शनिवार", "रविवार"], ["सोम", "मंगल", "बुध", "गुरु", "शुक्र", "शनि", "रवि"],
           ["जनवरी", "फ़रवरी", "मार्च", "अप्रैल", "मई", "जून", "जुलाई", "अगस्त", "सितंबर", "अक्टूबर", "नवंबर", "दिसंबर"]),
    "zh": (["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"], ["周一", "周二", "周三", "周四", "周五", "周六", "周日"],
           ["1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月", "9月", "10月", "11月", "12月"]),
    "ja": (["月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日", "日曜日"], ["月", "火", "水", "木", "金", "土", "日"],
           ["1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月", "9月", "10月", "11月", "12月"]),
}
_MOT_DATE = {}
for _i, _j in enumerate(JOURS):
    _MOT_DATE[_j] = ("jour", _i)
    _MOT_DATE[_j.lower()] = ("jour", _i)
    _MOT_DATE[_j[:3]] = ("abr", _i)
for _i, _m in enumerate(MOIS):
    _MOT_DATE[_m] = ("mois", _i)
# abréviations (« Jeu 12 ») seulement devant un numéro : sinon « Jeu de construction » serait pris pour jeudi
_ABR = [k for k, v in _MOT_DATE.items() if v[0] == "abr"]
_RE_DATE = re.compile(r"(?<![\w])(?:(" + "|".join(sorted(map(re.escape, (k for k in _MOT_DATE if k not in _ABR)), key=len, reverse=True))
                      + r")(?![\w])|(" + "|".join(map(re.escape, _ABR)) + r")(?= \d))")
_RE_NOMBRE = re.compile(r"(?<![\w{])(?:\d{1,2}h(?:\d{2})?|\d+(?:[.,:]\d+)*)(?![\w}])")   # 12, 4,5, 20:30, 8h30, 18h
_RE_LETTRE = re.compile(r"[^\W\d_]")


def mot_date(mot, lang):
    if lang == "fr" or lang not in DATES:
        return mot
    t, i = _MOT_DATE[mot]
    j, a, m = DATES[lang]
    return {"jour": j, "abr": a, "mois": m}[t][i]


# ----------------------------------------------------------------------
# Catalogues
# ----------------------------------------------------------------------
_CAT = {}
_CAT_T = {}
_lock = threading.Lock()
COLLECTE = os.path.exists(os.path.expanduser("~/.i18n_collecte"))      # mode collecte : phrases sans traduction notées
_VUES = {}                                       # clé -> exemple de page (mode collecte)
_FICHIER_COLLECTE = os.path.expanduser("~/i18n_cles.json")


def catalogue(lang):
    f = os.path.join(DOSSIER, f"{lang}.json")
    try:
        m = os.stat(f).st_mtime
    except OSError:
        return {}
    if _CAT_T.get(lang) != m:                    # catalogue rechargé s'il a changé
        try:
            _CAT[lang] = json.load(open(f, encoding="utf-8"))
        except (OSError, ValueError):
            _CAT[lang] = {}
        _CAT_T[lang] = m
    return _CAT[lang]


_capture = threading.local()


def cles(page, noms=()):
    """Toutes les phrases à traduire d'une page (clés), pour mesurer la couverture d'un catalogue."""
    _capture.liste = []
    try:
        traduire_html(page, "__", noms)
        return list(dict.fromkeys(_capture.liste))
    finally:
        _capture.liste = None


def _noter(cle, ou):
    if getattr(_capture, "liste", None) is not None:
        _capture.liste.append(cle)
        return
    if not COLLECTE or cle in _VUES:
        return
    with _lock:
        _VUES[cle] = ou
        if len(_VUES) % 20 == 0:
            sauver_collecte()


def sauver_collecte():
    try:
        old = json.load(open(_FICHIER_COLLECTE, encoding="utf-8"))
    except (OSError, ValueError):
        old = {}
    old.update({k: v for k, v in _VUES.items() if k not in old})
    tmp = _FICHIER_COLLECTE + ".tmp"
    json.dump(old, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    os.replace(tmp, _FICHIER_COLLECTE)


# ----------------------------------------------------------------------
# Une phrase : clé (avec {n}, {u}, {d}) + valeurs à remettre
# ----------------------------------------------------------------------
@functools.lru_cache(maxsize=16)
def _re_noms(noms):
    return re.compile(r"(?<![\w])(" + "|".join(sorted(map(re.escape, noms), key=len, reverse=True)) + r")(?![\w])")


def _cle(texte, noms):
    vals = {}
    k = texte
    if noms:
        rn = _re_noms(tuple(noms))
        i = [0]

        def fu(m):
            p = f"{{u{i[0]}}}"
            vals[p] = ("nom", m.group(0))
            i[0] += 1
            return p
        k = rn.sub(fu, k)
    j = [0]

    def fd(m):
        p = f"{{d{j[0]}}}"
        vals[p] = ("date", m.group(0))
        j[0] += 1
        return p
    k = _RE_DATE.sub(fd, k)
    n = [0]

    def fn(m):
        p = f"{{n{n[0]}}}"
        vals[p] = ("nombre", m.group(0))
        n[0] += 1
        return p
    k = _RE_NOMBRE.sub(fn, k)
    return k, vals


def _remettre(trad, vals, lang):
    def f(m):
        v = vals.get(m.group(0))
        if v is None:
            return m.group(0)
        t, s = v
        if t == "date":
            return mot_date(s, lang)
        if t == "nom":                           # prénom : inchangé ; nom d'application qui est un mot (« Bureau ») : traduit
            return catalogue(lang).get(s, s)
        if t == "nombre" and lang not in VIRGULE and re.fullmatch(r"\d+,\d+", s):
            return s.replace(",", ".")
        return s
    return re.sub(r"\{[nud]\d+\}", f, trad)


def traduire_texte(texte, lang, noms=(), ou="texte"):
    """Une phrase sans balises (message à un enfant, attribut title…)."""
    if lang == DEFAUT or not texte.strip() or not _RE_LETTRE.search(texte):
        return texte
    debut = texte[:len(texte) - len(texte.lstrip())]
    fin = texte[len(texte.rstrip()):]
    coeur = re.sub(r"\s+", " ", texte.strip())
    cle, vals = _cle(coeur, noms)
    if not _RE_LETTRE.search(re.sub(r"\{[nud]\d+\}", "", cle)):
        return texte.replace(coeur, _remettre(cle, vals, lang)) if vals else texte
    t = catalogue(lang).get(cle)
    if t is None:
        _noter(cle, ou)
        return texte
    return debut + _remettre(t, vals, lang) + fin


def traduire_lignes(texte, lang, noms=()):
    """Message de plusieurs lignes (popups des enfants) : ligne par ligne, et morceau par morceau autour de « : » et « ; »
    (« Mode restreint : internet filtré ; bloqué : YouTube »)."""
    return "\n".join("".join(p if p in (" : ", " ; ") else traduire_texte(p, lang, noms, "message enfant")
                             for p in re.split(r"( : | ; )", l)) for l in texte.split("\n"))


# ----------------------------------------------------------------------
# Pages HTML
# ----------------------------------------------------------------------
INLINE = {"b", "strong", "i", "em", "a", "code", "small", "span", "u", "kbd", "br", "sup", "sub", "abbr", "time", "mark", "s", "q", "label"}
BRUT = {"script", "style", "textarea", "pre"}
ATTRS = ("title", "placeholder", "aria-label", "alt", "data-confirm", "data-yes", "data-tip")
_RE_TOK = re.compile(r"<!--.*?-->|<![^>]*>|<(/?)([a-zA-Z][a-zA-Z0-9-]*)((?:[^>\"']|\"[^\"]*\"|'[^']*')*)>|[^<]+|<", re.S)
_RE_ATTR = re.compile(r"(\s(?:" + "|".join(map(re.escape, ATTRS)) + r')=")([^"]*)(")')


def _attrs(tag, lang, noms, ou):
    if "=\"" not in tag:
        return tag
    def f(m):
        v = _html.unescape(m.group(2))
        t = "\n".join(traduire_texte(x, lang, noms, ou) for x in v.split("\n"))     # infobulles : ligne par ligne
        return m.group(0) if t == v else m.group(1) + _html.escape(t, quote=True) + m.group(3)
    return _RE_ATTR.sub(f, tag)


def _phrase(run, lang, noms, ou):
    """run : liste de (type, chaîne, nom de balise, fermante) ; renvoie le HTML traduit."""
    if not any(t == "txt" and _RE_LETTRE.search(s) for t, s, *_ in run):
        return "".join(s if t == "txt" else _attrs(s, lang, noms, ou) for t, s, *_ in run)
    # balises appariées dans la phrase
    pile, paire = [], {}
    for i, (t, s, nom, ferme) in enumerate(run):
        if t != "tag" or nom == "br":
            continue
        if not ferme:
            pile.append((nom, i))
        else:
            for k in range(len(pile) - 1, -1, -1):
                if pile[k][0] == nom:
                    paire[pile[k][1]] = i
                    paire[i] = pile[k][1]
                    del pile[k:]
                    break
    a, z = 0, len(run)

    def vide(x):
        t, s, nom, ferme = run[x]
        return t == "txt" and not s.strip()
    while True:                                    # bords : espaces, balises sans paire, balise qui enveloppe tout
        if a < z and (vide(a) or (run[a][0] == "tag" and paire.get(a, -1) not in range(a, z))):
            a += 1
        elif a < z and (vide(z - 1) or (run[z - 1][0] == "tag" and paire.get(z - 1, -1) not in range(a, z))):
            z -= 1
        elif a < z - 1 and run[a][0] == "tag" and paire.get(a) == z - 1:
            a += 1
            z -= 1
        else:
            break
    if a >= z:
        return "".join(s if t == "txt" else _attrs(s, lang, noms, ou) for t, s, *_ in run)
    # clé : texte + balises numérotées
    num, orig, parts = {}, {}, []
    for i in range(a, z):
        t, s, nom, ferme = run[i]
        if t == "txt":
            parts.append(re.sub(r"\s+", " ", _html.unescape(s)))
        elif i in paire:
            o = min(i, paire[i])
            if o not in num:
                num[o] = len(num)
                orig[num[o]] = (_attrs(run[o][1], lang, noms, ou), run[paire[o]][1])
            parts.append(f"</t{num[o]}>" if ferme else f"<t{num[o]}>")
        else:
            k = len(num) + 100 + i
            num[i] = k
            orig[k] = (_attrs(s, lang, noms, ou), "")
            parts.append(f"<t{k}/>")
    coeur = "".join(parts)
    lead = coeur[:len(coeur) - len(coeur.lstrip())]
    trail = coeur[len(coeur.rstrip()):]
    cle, vals = _cle(coeur.strip(), noms)
    t = catalogue(lang).get(cle)
    if t is None and lang in DATES and not _RE_LETTRE.search(re.sub(r"\{[nud]\d+\}|</?t\d+/?>", "", cle)):
        t = cle                                  # seulement des dates, nombres et noms (« Mardi 10 novembre · 22:52 ») : jours et mois traduits
    avant = "".join(s if tt == "txt" else _attrs(s, lang, noms, ou) for tt, s, *_ in run[:a])
    apres = "".join(s if tt == "txt" else _attrs(s, lang, noms, ou) for tt, s, *_ in run[z:])
    if t is None:
        if _RE_LETTRE.search(re.sub(r"\{[nud]\d+\}|</?t\d+/?>", "", cle)):
            _noter(cle, ou)
        milieu = "".join(s if tt == "txt" else _attrs(s, lang, noms, ou) for tt, s, *_ in run[a:z])
        return avant + milieu + apres
    out = _html.escape(_remettre(t, vals, lang), quote=False)
    # balises remises (le texte a été échappé : &lt;t0&gt;)
    out = re.sub(r"&lt;(/?)t(\d+)(/?)&gt;", lambda m: (orig[int(m.group(2))][1] if m.group(1) else orig[int(m.group(2))][0])
                 if int(m.group(2)) in orig else "", out)
    return avant + lead + out + trail + apres


def traduire_html(page, lang, noms=(), ou="page"):
    if lang == DEFAUT:
        if not COLLECTE:
            return page
        lang_c = "__"                             # collecte seulement : aucune traduction ne sera trouvée
    else:
        lang_c = lang
    out, run = [], []
    brut = None
    for m in _RE_TOK.finditer(page):
        s = m.group(0)
        if brut:
            out.append(s)
            if m.group(2) and m.group(1) and m.group(2).lower() == brut:
                brut = None
            continue
        if s.startswith("<!"):
            out.append(s)
            continue
        if m.group(2) is None:
            run.append(("txt", s if s != "<" else "&lt;", None, False))
            continue
        nom, ferme = m.group(2).lower(), bool(m.group(1))
        if nom in INLINE and 'translate="no"' not in s:
            run.append(("tag", s, nom, ferme))
            continue
        if run:
            out.append(_phrase(run, lang_c, noms, ou))
            run = []
        if 'translate="no"' in s and not ferme:
            out.append(s)                         # contenu laissé tel quel (prénoms, titres de fenêtres…)
            brut = nom
            continue
        out.append(_attrs(s, lang_c, noms, ou))
        if nom in BRUT and not ferme:
            brut = nom
    if run:
        out.append(_phrase(run, lang_c, noms, ou))
    res = "".join(out)
    if lang not in LANGUES or lang == DEFAUT:
        return page
    d = LANGUES[lang][2]
    res = res.replace('<html lang="fr">', f'<html lang="{lang}" dir="{d}">', 1)
    js = {k: v for k, v in catalogue(lang).items() if k.startswith("js:")}
    if js:
        res = res.replace("<script>", "<script>window.I18N=" + json.dumps({k[3:]: v for k, v in js.items()}, ensure_ascii=False)
                          .replace("</", "<\\/") + ";</script><script>", 1)
    return res


def langue_navigateur(accept):
    for part in (accept or "").split(","):
        code = part.split(";")[0].strip().lower()[:2]
        if code in LANGUES:
            return code
    return DEFAUT
