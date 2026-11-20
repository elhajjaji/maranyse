#!/usr/bin/env python3
"""qui : affiche qui est connecté au bureau des enfants et ce qu'il a ouvert.
Tourne dans la VM (utilisateur parent, groupe docker)."""
import re, subprocess, sys
from datetime import datetime

C = "bureau-enfants"
USERS = subprocess.run(["docker", "exec", "bureau-enfants", "sh", "-c", "cut -d: -f1 /secrets/comptes.txt"],
                       capture_output=True, text=True).stdout.split()        # comptes des enfants


def dx(cmd, user=None, env=None):
    a = ["docker", "exec"]
    if user:
        a += ["-u", user]
    for k, v in (env or {}).items():
        a += ["-e", f"{k}={v}"]
    r = subprocess.run(a + [C, "sh", "-c", cmd], capture_output=True, text=True)
    return r.stdout


def active_connections():
    """Couples (ip, port) des clients RDP connectés en ce moment."""
    out = set()
    for line in dx("cat /proc/net/tcp6 /proc/net/tcp 2>/dev/null").splitlines()[1:]:
        f = line.split()
        if len(f) < 4 or f[3] != "01":           # 01 = ESTABLISHED
            continue
        loc, rem = f[1], f[2]
        if int(loc.split(":")[1], 16) != 3389:
            continue
        h, p = rem.split(":")
        b = bytes.fromhex(h[-8:])
        ip = ".".join(str(x) for x in b[::-1])   # adresse IPv4 (ou IPv4 dans IPv6)
        out.add((ip, int(p, 16)))
    return out


def sessions_from_log():
    """Dernière connexion connue par utilisateur : heure, ip, port, appareil."""
    names = {}
    for l in dx("cat /var/log/xrdp.log 2>/dev/null").splitlines():
        m = re.match(r"\[(\d{8}-\d\d:\d\d:\d\d)\].*Connected client computer name: (.*)", l)
        if m:
            names[m.group(1)] = m.group(2).strip()
    last = {}
    for l in dx("cat /var/log/xrdp-sesman.log 2>/dev/null").splitlines():
        m = re.match(r"\[(\d{8}-\d\d:\d\d:\d\d)\].*created session.*username (\S+), ip (?:::ffff:)?([\d.]+):(\d+)", l)
        if m:
            ts, u, ip, port = m.groups()
            last[u] = dict(ts=ts, ip=ip, port=int(port), name=names.get(ts, "?"))
    return last


def displays():
    d = {}
    for l in dx("ps -eo user:32,args | grep '[X]org :'").splitlines():
        m = re.match(r"(\S+)\s+\S*Xorg (:\d+)", l)
        if m:
            d[m.group(1)] = m.group(2)
    return d


def windows(user, disp):
    out = dx("wmctrl -lx 2>/dev/null", user=user,
             env={"DISPLAY": disp, "XAUTHORITY": f"/home/{user}/.Xauthority"})
    res = []
    for l in out.splitlines():
        f = l.split(None, 4)
        if len(f) < 5 or f[1] == "-1":            # -1 = bureau / panneau
            continue
        cls = f[2].split(".")[-1]
        title = f[4]
        res.append(f"{title}  [{cls}]")
    return res


def hm(ts):
    return datetime.strptime(ts, "%Y%m%d-%H:%M:%S").strftime("%d.%m %H:%M")


def main():
    act = active_connections()
    last = sessions_from_log()
    disp = displays()
    print(f"=== Bureau des enfants - {datetime.now():%d.%m.%Y %H:%M} ===\n")
    for u in USERS:
        s = last.get(u)
        connected = s is not None and (s["ip"], s["port"]) in act
        if u not in disp:
            print(f"{u:16} -- aucune session")
            continue
        if connected:
            print(f"{u:16} ** CONNECTE ** depuis {hm(s['ts'])}  appareil {s['ip']} ({s['name']})")
        else:
            info = f" (derniere connexion {hm(s['ts'])} depuis {s['ip']} ({s['name']}))" if s else ""
            print(f"{u:16} session ouverte mais deconnecte{info}")
        ws = windows(u, disp[u])
        if ws:
            for w in ws:
                print(f"{'':18}- {w}")
        else:
            print(f"{'':18}(aucune fenetre ouverte)")
    print()


if __name__ == "__main__":
    sys.exit(main())
