"""MaranYSE — calculs statistiques, graphiques SVG et vues de la page Statistiques."""
import math
import os
import re
from datetime import datetime, timedelta
from urllib.parse import quote

from logique import USERS, APPS, IDLE, JOURS, TICK, SITES, db, dur, nom, target, kid_hex
from style import MOIS, APP_SLOT, e, ic, avatar, item_badge, card, more


SITE_PALETTE = ["var(--s1)", "var(--s2)", "var(--s3)", "var(--s4)", "var(--s5)", "var(--s6)", "var(--s7)", "var(--s8)"]


def site_from_title(title):
    """Déduit le nom du site web à partir d'un titre d'onglet Firefox."""
    t = re.sub(r"\s*[—–-]\s*Mozilla Firefox\s*$", "", title or "").strip()
    if not t or t in ("Mozilla Firefox", "Nouvel onglet", "New Tab", "Navigation privée"):
        return "Nouvel onglet"
    low = t.lower()
    for k, (sname, _, kws) in SITES.items():
        if any(w in low for w in kws):
            return sname.split(" (")[0]
    for part in re.split(r"\s+(?:[—–|·]|-\s)\s*", t)[::-1]:
        p = part.strip()
        if 2 <= len(p) <= 32:
            return p
    return t[:32]


def web_stats(c, start, user=None):
    """Agrège les statistiques Firefox (par site, par jour, et pages par site) sur la période."""
    sql = "SELECT day, user, title, sec FROM titles WHERE app='Firefox' AND day>=?"
    args = [start]
    if user:
        sql += " AND user=?"
        args.append(user)
    by_site, by_day, by_user, pages = {}, {}, {}, {}
    for day, u, title, sec in c.execute(sql, args):
        if u not in USERS:
            continue
        site = site_from_title(title)
        by_site[site] = by_site.get(site, 0) + sec
        by_day.setdefault(day, {})[site] = by_day.setdefault(day, {}).get(site, 0) + sec
        by_user[(site, u)] = by_user.get((site, u), 0) + sec
        clean_t = re.sub(r"\s*[—–-]\s*Mozilla Firefox\s*$", "", title or "").strip() or title
        pages.setdefault(site, {})[clean_t] = pages.setdefault(site, {}).get(clean_t, 0) + sec
    return by_site, by_day, by_user, pages


def web_card(c, q, params, per, days, start, user=None):
    """Carte dédiée à la navigation web (Firefox) avec niveau de détail réglable (Simple / Détaillé)."""
    detail = q.get("web", ["simple"])[0] == "detail"
    by_site, by_day, by_user, pages = web_stats(c, start, user)
    if not by_site:
        return card("Navigation web (Firefox)", "Temps passé par site", '<div class="empty">Aucune navigation Firefox enregistrée sur cette période.</div>', icon="globe")
    ordered = sorted(by_site.items(), key=lambda x: -x[1])
    tot_web = sum(by_site.values())
    top_sites = [s for s, _ in ordered[:6]]
    scol = lambda s: SITE_PALETTE[top_sites.index(s) % len(SITE_PALETTE)] if s in top_sites else "var(--s-autre)"

    # Sélecteur Simple / Détaillé
    tabs = ('<div class="seg">'
            f'<a class="{"on" if not detail else ""}" href="{url(params, web="simple")}#navigation">Simple</a>'
            f'<a class="{"on" if detail else ""}" href="{url(params, web="detail")}#navigation">Plus de détail</a>'
            '</div>')

    # Barres horizontales par site
    shown_bars = ordered[:8] if not detail else ordered[:25]
    if not detail and len(ordered) > 8:
        shown_bars.append(("Autres sites", sum(v for _, v in ordered[8:])))
    mx = max(v for _, v in shown_bars) or 1
    bars_html = '<div class="bars">' + "".join(
        f'<div class="bar" data-tip="{e(s)} : {dur(v)} ({round(100 * v / tot_web)} %)">'
        f'<span class="lab"><i class="sw" style="--c:{scol(s)}"></i> {e(s)}</span>'
        f'<div class="trk"><div class="fill" style="width:{max(1, 100 * v / mx):.1f}%;background:{scol(s)}"></div></div>'
        f'<span class="val">{dur(v)}</span></div>'
        for s, v in shown_bars) + "</div>"

    # Graphique d'évolution par jour (empilé)
    nd = max(days, 7)
    day_series = {}
    for d_iso, m in by_day.items():
        for s, sec in m.items():
            k = s if s in top_sites else "Autres"
            day_series.setdefault(d_iso, {})[k] = day_series.setdefault(d_iso, {}).get(k, 0) + sec
    order = top_sites + (["Autres"] if any("Autres" in v for v in day_series.values()) else [])
    chart_days = stacked_days(day_series, nd, order, lambda s: "var(--s-autre)" if s == "Autres" else scol(s), lambda s: s)

    extra_detail = ""
    if detail:
        # Courbe d'évolution des principaux sites
        bk, bk_lab = time_buckets(per)
        if per == "1":
            d0 = datetime.combine(datetime.now().date(), datetime.min.time()).isoformat()
            rows_h = [r for r in segs_since(c, d0, "AND app='Firefox'" + (" AND user=?" if user else ""), (user,) if user else ()) if r[0] in USERS]
            h_map = by_hour(rows_h, lambda r: site_from_title(r[2]))
            lseries = [(s, scol(s), [h_map.get(s, [0] * 24)[h] for h, _ in bk]) for s in top_sites]
        else:
            lseries = [(s, scol(s), [by_day.get(k, {}).get(s, 0) for k, _ in bk]) for s in top_sites]
        curve = f'<div><h3>Évolution par site ({bk_lab})</h3>{line_chart([lab for _, lab in bk], lseries)}</div>'

        # Matrice Sites × Enfants (vue globale / Firefox)
        mat = ""
        if not user and len(USERS) > 1:
            th = "".join(f'<th class="n">{avatar(u, "sm")}<br>{e(nom(u))}</th>' for u in USERS)
            m_max = max([by_user.get((s, u), 0) for s, _ in ordered[:15] for u in USERS] + [1])
            mrows = ""
            for s, _ in ordered[:15]:
                cells = ""
                for u in USERS:
                    v = by_user.get((s, u), 0)
                    q_lvl = 0 if v <= 0 else min(5, 1 + int(4 * v / m_max))
                    cells += f'<td class="mx q{q_lvl}" style="background:var(--q{q_lvl})"><a href="/?p=stats&vue=enfant&s={quote(u)}&per={per}&web=detail#navigation">{dur(v) if v else "–"}</a></td>'
                mrows += f'<tr><td class="who"><i class="sw" style="--c:{scol(s)}"></i> {e(s)}</td>{cells}</tr>'
            mat = f'<div><h3>Qui visite quel site ?</h3><div class="tw"><table class="t mxt"><tr><th>Site</th>{th}</tr>{mrows}</table></div></div>'

        # Détail des pages / vidéos consultées par site
        site_blocks = ""
        for s, v in ordered[:15]:
            p_list = sorted(pages.get(s, {}).items(), key=lambda x: -x[1])[:20]
            p_rows = "".join(f'<tr><td translate="no">{e(pt)}</td><td class="n">{dur(ps)}</td></tr>' for pt, ps in p_list)
            site_blocks += more(f'{e(s)} · {dur(v)} ({len(pages.get(s, {}))} page{"s" if len(pages.get(s, {})) > 1 else ""})',
                                f'<div class="tw"><table class="t"><tr><th>Page / Vidéo / Recherche</th><th class="n">Durée</th></tr>{p_rows}</table></div>')
        extra_detail = f'{curve}{mat}<div><h3>Pages consultées par site</h3><div class="stack" style="gap:6px">{site_blocks}</div></div>'

    sub = f"{len(ordered)} site{'s' if len(ordered) > 1 else ''} · total {dur(tot_web)} sur Firefox"
    inner = f'<div class="grid2"><div><h3>Temps par site</h3>{bars_html}</div><div><h3>Par jour ({nd} derniers jours)</h3>{chart_days}</div></div>{extra_detail}'
    return f'<div id="navigation"></div>' + card("Navigation web (Firefox)", sub, inner, tabs, icon="globe")


def bars(rows):
    if not rows:
        return '<div class="empty">Pas encore de données pour cette période.</div>'
    mx = max(v for _, v in rows) or 1
    return '<div class="bars">' + "".join(
        f'<div class="bar" title="{e(k)} : {dur(v)}"><span class="lab">{e(k)}</span>'
        f'<div class="trk"><div class="fill" style="width:{max(1, 100 * v / mx):.1f}%"></div></div><span class="val">{dur(v)}</span></div>'
        for k, v in rows) + "</div>"


DEBUT_DETAIL = "8 novembre 2026"      # le détail heure par heure est enregistré depuis cette mise à jour
PER_LAB = {"1": "aujourd'hui", "7": "sur 7 jours", "30": "sur 30 jours"}
PREV_LAB = {"1": "hier", "7": "les 7 jours d'avant", "30": "les 30 jours d'avant"}


def app_color(app):
    if app == IDLE:
        return "var(--s-inactif)"
    return f"var(--s{APP_SLOT[app]})" if app in APP_SLOT else "var(--s-autre)"


def kid_color(u):
    return kid_hex(u) if u in USERS else "var(--s-autre)"


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
    grid = "".join(f'<div class="vgl" style="bottom:{p}%"><span>{fax(top * p / 100)}</span></div>' for p in (0, 50, 100))
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


def stats_ensemble(q, c, per, days, start, d, people_tabs_fn=None):
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
            + web_card(c, q, {**params, "d": d}, per, days, start)
            + "</div>")
    return body, "Vue d'ensemble de tous les enfants", params


def stats_enfant(q, c, per, days, start, d, people_tabs_fn):
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
    body = (f'{people_tabs_fn("stats", u, f"&vue=enfant&per={per}&d={d}")}{tiles}{insights(lines)}<div class="stack">'
            + card("Évolution par application", f"Temps passé sur chaque application, {time_buckets(per)[1]}",
                   evo_apps_for(c, per, u, pct(q)), mesure_tabs({**params, "d": d}, pct(q)), icon="chart")
            + card(f"Chronologie · {e(day_label(d))}", f"Quelle application {e(nom(u))} a utilisée, et à quelle heure",
                   chrono_inner, day_nav(params, d), icon="clock")
            + '<div class="grid2">'
            + card("Temps par jour", f"Empilé par application, {nd} derniers jours", stacked_days(per_day, nd, order, colf, lambda a: a), icon="calendar")
            + card("Jours et heures", "Temps actif par heure · cliquez un jour pour sa chronologie", heat(heat_rows), icon="clock")
            + "</div>"
            + res_card(c, q, {**params, "d": d, "mesure": q.get("mesure", [""])[0]}, [u])
            + web_card(c, q, {**params, "d": d}, per, days, start, user=u)
            + '<div class="grid2">'
            + card("Applications", f"Temps total {pl} · « (inactif) » : sans toucher la souris ni le clavier depuis 2 min", app_bars(by_app), icon="app")
            + card("Sites suivis (règles)", "Catégories et sites surveillés", bars(site_rows), icon="shield")
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


def stats_app(q, c, per, days, start, d, people_tabs_fn=None):
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
            + (web_card(c, q, {**params, "d": d}, per, days, start) if app == "Firefox" else "")
            + card("Qui l'a utilisée, et quand", f"Périodes d'utilisation {pl}, de la plus récente à la plus ancienne",
                   more(f"Voir les {len(lst)} périodes", f'<div class="tw"><table class="t"><tr><th>Enfant</th><th class="n">Jour</th><th class="n">Début</th>'
                        f'<th class="n">Fin</th><th class="n">Durée</th><th>Fenêtres et pages</th></tr>{t_rows}</table></div>', len(lst) <= 8)
                   if t_rows else '<div class="empty">Pas encore de détail pour cette période.</div>', icon="users")
            + "</div>")
    return body, f"Utilisation de {app}", params
