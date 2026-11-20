#!/bin/bash
# Crée les comptes enfants (si absents) puis lance xrdp au premier plan.
# USERS="nom1 nom2 ..."  -> mots de passe générés et stockés dans /secrets/mots_de_passe.txt
set -e

mkdir -p /secrets
PWFILE=/secrets/mots_de_passe.txt
touch "$PWFILE"; chmod 600 "$PWFILE"

# Liste des comptes (« identifiant:Nom affiché »), gérée depuis l'espace parents.
# $USERS ne sert qu'à la créer la première fois.
ACC=/secrets/comptes.txt
[ -s "$ACC" ] || for u in $USERS; do echo "$u:"; done > "$ACC"
chmod 600 "$ACC"
USERS=$(cut -d: -f1 "$ACC" | grep -E '^[a-z][a-z0-9_]{1,30}$' || true)

# Langue de chaque enfant (page Comptes) : lue par maranyse-session ; le tableau de bord la tient à jour ensuite
mkdir -p /etc/maranyse && { cp /secrets/langues.txt /etc/maranyse/langues 2>/dev/null || : > /etc/maranyse/langues; } && chmod 644 /etc/maranyse/langues

for u in $USERS; do
    if ! id "$u" >/dev/null 2>&1; then
        # Réutilise l'UID déjà présent dans /home (volume persistant) si le conteneur est recréé
        if [ -d "/home/$u" ]; then
            useradd -u "$(stat -c %u "/home/$u")" -s /bin/bash "$u"
        else
            useradd -m -K UID_MIN=1001 -K GID_MIN=1001 -s /bin/bash "$u"    # 1000 = compte « parent » de la VM (quotas disque)
        fi
    fi
    pw=$(grep "^$u:" "$PWFILE" | cut -d: -f2- || true)
    if [ -z "$pw" ]; then
        pw=$(tr -dc 'a-km-np-z2-9' </dev/urandom | head -c 8)
        echo "$u:$pw" >> "$PWFILE"
    fi
    echo "$u:$pw" | chpasswd
    # ouverture de session MaranYSE (français, bureau façon Windows) ; remplace l'ancien « startxfce4 »
    if [ ! -f "/home/$u/.xsession" ] || [ "$(cat "/home/$u/.xsession")" = startxfce4 ]; then
        echo 'exec /usr/local/bin/maranyse-session' > "/home/$u/.xsession"; chown "$u:" "/home/$u/.xsession"
    fi
    chmod 700 "/home/$u"          # un enfant ne peut pas lire les fichiers des autres
    # Thonny (programmation Python) en français, sans l'écran de réglages du premier lancement
    if [ ! -f "/home/$u/.config/Thonny/configuration.ini" ]; then
        mkdir -p "/home/$u/.config/Thonny" && printf '[general]
language = fr_FR
' > "/home/$u/.config/Thonny/configuration.ini"
        chown -R "$u:" "/home/$u/.config"
    fi
done

# Internet fermé par défaut pour les enfants tant que le tableau de bord n'a pas posé leurs règles (≤ 30 s) :
# au démarrage, rien ne passe sans filtre (IPv4 et IPv6).
rm -f /run/kids-net /run/kids-dns-*.pid
iptables -N KIDS 2>/dev/null; iptables -F KIDS; iptables -C OUTPUT -j KIDS 2>/dev/null || iptables -I OUTPUT -j KIDS
ip6tables -N KIDS 2>/dev/null; ip6tables -F KIDS; ip6tables -C OUTPUT -j KIDS 2>/dev/null || ip6tables -I OUTPUT -j KIDS 2>/dev/null || true
for u in $USERS; do
    uid="$(id -u "$u")"
    iptables -A KIDS ! -o lo -m owner --uid-owner "$uid" -j REJECT 2>/dev/null || true
    iptables -A KIDS -p tcp --dport 8080 -m owner --uid-owner "$uid" -j REJECT 2>/dev/null || true
    ip6tables -A KIDS ! -o lo -m owner --uid-owner "$uid" -j REJECT 2>/dev/null || true
    ip6tables -A KIDS -p tcp --dport 8080 -m owner --uid-owner "$uid" -j REJECT 2>/dev/null || true
done

# Comptes en pause ou hors horaire : ils restent verrouillés après un redémarrage du bureau
for u in $(cat /secrets/verrouilles.txt 2>/dev/null); do usermod -L "$u" 2>/dev/null || true; done

echo "== Comptes et mots de passe (aussi dans le volume secrets) =="
cat "$PWFILE"

rm -f /var/run/xrdp/*.pid /var/run/xrdp.pid /var/run/xrdp-sesman.pid
# Dossier des prises de connexion xrdp (monté en mémoire, sans exécution) : chaque session doit pouvoir y écrire,
# sinon écran noir à la connexion. Les droits ne survivent pas toujours à un redémarrage du conteneur.
mkdir -p /run/xrdp/sockdir && chmod 3777 /run/xrdp/sockdir

# Relais vers PyPI pour « pip install » (seuls pypi.org et files.pythonhosted.org sont acceptés)
mkdir -p /run/tinyproxy /var/log/tinyproxy && chown tinyproxy: /run/tinyproxy /var/log/tinyproxy
tinyproxy -c /etc/tinyproxy/maranyse.conf || echo "ATTENTION : relais pip (tinyproxy) non démarré"
mkdir -p /run/dbus && rm -f /run/dbus/pid && dbus-daemon --system --fork

/usr/sbin/xrdp-sesman
exec /usr/sbin/xrdp --nodaemon
