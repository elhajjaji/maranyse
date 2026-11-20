#!/usr/bin/env python3
"""MaranYSE — parcourt toutes les pages de l'espace parents (toutes vues, tous enfants, toutes périodes).
Usage dans la VM :  python3 i18n_parcours.py              -> phrases de toutes les pages (~/i18n_pages.json)
                    python3 i18n_parcours.py en ja ...    -> part des phrases traduites, par langue"""
import base64, json, os, sys, urllib.request
sys.path.insert(0, os.path.expanduser("~"))
import logique as l                                    # noqa: E402
import i18n                                            # noqa: E402

AUTH = "Basic " + base64.b64encode(f"{l.LOGIN}:{l.PASSWORD}".encode()).decode()
l.load_accounts()
kids = list(l.USERS)
pages = ["/?p=live", "/?p=logiciels", "/?p=puissance", "/?p=comptes", "/?p=aide", "/?p=regles&s=_tous", "/?p=planning"]
for u in kids:
    pages += [f"/?p=planning&s={u}", f"/?p=regles&s={u}"]
for per in ("1", "7", "30"):
    for res in ("cpu", "mem", "net", "disk"):
        pages.append(f"/?p=stats&vue=ensemble&per={per}&res={res}")
    pages.append(f"/?p=stats&vue=ensemble&per={per}&pct=1")
    for u in kids:
        pages.append(f"/?p=stats&vue=enfant&s={u}&per={per}")
    pages.append(f"/?p=stats&vue=app&per={per}")
for app in ("Firefox", "Tux Paint", "Visual Studio Code", "Bureau", "(inactif)"):
    pages.append(f"/?p=stats&vue=app&per=7&app={urllib.request.quote(app)}")


def get(p):
    h = {"Authorization": AUTH, "Cookie": "lang=fr"}
    return urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:8080" + p, headers=h), timeout=60).read().decode()


import tableau                                         # noqa: E402
noms = tableau.noms_page()
toutes = {}
for p in pages:
    for k in i18n.cles(get(p), noms):
        toutes.setdefault(k, p)
langs = sys.argv[1:]
if not langs:
    json.dump(toutes, open(os.path.expanduser("~/i18n_pages.json"), "w"), ensure_ascii=False, indent=0)
    print(len(pages), "pages,", len(toutes), "phrases")
for lg in langs:
    cat = i18n.catalogue(lg)
    manque = [k for k in toutes if k not in cat]
    print(f"{lg} : {len(toutes) - len(manque)}/{len(toutes)} phrases traduites ({100 * (len(toutes) - len(manque)) / max(1, len(toutes)):.1f} %)")
    for k in manque[:15]:
        print("   manque :", k[:110], "  ←", toutes[k])
