#!/usr/bin/env python3
"""Vérifie un catalogue de traduction MaranYSE : python verifier.py <langue> [fichier des clés]
- chaque clé du fichier des clés a une traduction (non vide) ;
- chaque traduction garde exactement les mêmes repères que la clé : {n0} {u0} {d0}, <t0> </t0> <t105/>.
Affiche les problèmes ; code de sortie 0 si tout est bon."""
import collections, json, os, re, sys

ICI = os.path.dirname(os.path.abspath(__file__))
REP = re.compile(r"\{[nud]\d+\}|</?t\d+/?>")


def reperes(s):
    return collections.Counter(REP.findall(s))


def main():
    lang = sys.argv[1]
    cles = json.load(open(sys.argv[2] if len(sys.argv) > 2 else os.path.join(ICI, "_a_traduire.json"), encoding="utf-8"))
    cat = json.load(open(os.path.join(ICI, f"{lang}.json"), encoding="utf-8"))
    pb = []
    for k in cles:
        if k not in cat:
            pb.append(f"MANQUE   {k[:100]}")
        elif not isinstance(cat[k], str) or not cat[k].strip():
            pb.append(f"VIDE     {k[:100]}")
        elif reperes(k) != reperes(cat[k]):
            pb.append(f"REPÈRES  {k[:80]}  →  {cat[k][:80]}")
    for p in pb[:60]:
        print(p)
    print(f"{lang} : {len(cles) - len(pb)}/{len(cles)} correctes")
    sys.exit(1 if pb else 0)


if __name__ == "__main__":
    main()
