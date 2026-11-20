# MaranYSE — bureau Linux multi-sessions (XFCE + xrdp) pour les enfants

# Étape de compilation : lanceur de Firefox avec accès internet (voir firefox-net.c)
FROM debian:bookworm-slim AS lanceur
RUN apt-get update && apt-get install -y --no-install-recommends gcc libc6-dev && rm -rf /var/lib/apt/lists/*
COPY firefox-net.c sans-internet.c sans-internet-ff.c /src/
RUN gcc -O2 -Wall -o /firefox-net /src/firefox-net.c     && gcc -O2 -Wall -o /sans-internet /src/sans-internet.c     && gcc -O2 -Wall -shared -fPIC -o /sans-internet-ff.so /src/sans-internet-ff.c -ldl

FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=fr_FR.UTF-8 \
    LC_ALL=fr_FR.UTF-8 \
    TZ=Europe/Zurich

# L'image Debian « slim » retire toutes les traductions : sans elles le bureau reste en anglais.
# On garde les langues proposées aux enfants (page Comptes) pour tous les paquets installés ensuite.
RUN for l in fr fr_FR de de_DE es es_ES pt pt_PT ru ru_RU ar hi hi_IN zh_CN ja ja_JP en_GB; do \
        echo "path-include /usr/share/locale/$l/*"; done > /etc/dpkg/dpkg.cfg.d/zz-maranyse-langues

RUN apt-get update && apt-get install -y --no-install-recommends \
        locales tzdata ca-certificates dbus dbus-x11 sudo procps \
        xrdp xorgxrdp xserver-xorg-core \
        xfce4 xfce4-terminal thunar mousepad ristretto wmctrl zenity \
        fonts-dejavu fonts-noto-color-emoji fonts-noto-core \
        xfce4-whiskermenu-plugin orchis-gtk-theme papirus-icon-theme librsvg2-common xdg-user-dirs x11-xserver-utils \
        firefox-esr firefox-esr-l10n-fr \
        gcompris-qt tuxpaint \
        libreoffice-writer libreoffice-calc libreoffice-impress libreoffice-gtk3 libreoffice-l10n-fr \
        at-spi2-core xdg-utils \
        firefox-esr-l10n-ar firefox-esr-l10n-zh-cn firefox-esr-l10n-es-es firefox-esr-l10n-hi-in firefox-esr-l10n-de \
        firefox-esr-l10n-pt-pt firefox-esr-l10n-ru firefox-esr-l10n-ja \
        libreoffice-l10n-ar libreoffice-l10n-zh-cn libreoffice-l10n-es libreoffice-l10n-hi libreoffice-l10n-de \
        libreoffice-l10n-pt libreoffice-l10n-ru libreoffice-l10n-ja fonts-noto-cjk \
        fcitx5 fcitx5-chinese-addons fcitx5-mozc fcitx5-frontend-gtk3 fcitx5-frontend-qt5 \
        iptables acl xdotool xprintidle xinput dnsmasq-base \
    && for l in fr_FR en_US es_ES de_DE pt_PT ru_RU ar_MA hi_IN zh_CN ja_JP; do echo "$l.UTF-8 UTF-8"; done >> /etc/locale.gen && locale-gen \
    && rm -f /etc/xdg/autostart/org.fcitx.Fcitx5.desktop \
    && update-alternatives --set x-session-manager /usr/bin/xfce4-session \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Programmation pour les enfants : Thonny (éditeur Python pour débuter), tortue (tk), jeux (pygame)
RUN apt-get update && apt-get install -y --no-install-recommends thonny python3-tk python3-pygame     && apt-get clean && rm -rf /var/lib/apt/lists/*

# pip limité à PyPI : les scripts des enfants n'ont pas internet, sauf ce relais local (tinyproxy, 127.0.0.1:8888)
# qui n'accepte que pypi.org et files.pythonhosted.org. Une bibliothèque installée ne peut donc se connecter nulle part.
RUN apt-get update && apt-get install -y --no-install-recommends tinyproxy python3-pip python3-venv \
    && apt-get clean && rm -rf /var/lib/apt/lists/* \
    && printf '%s\n' 'User tinyproxy' 'Group tinyproxy' 'Port 8888' 'Listen 127.0.0.1' 'Timeout 600' 'MaxClients 40' \
         'Allow 127.0.0.1' 'ConnectPort 443' 'FilterDefaultDeny Yes' 'FilterType ere' 'Filter "/etc/tinyproxy/pypi.txt"' \
         'LogFile "/var/log/tinyproxy/tinyproxy.log"' 'LogLevel Connect' 'PidFile "/run/tinyproxy/tinyproxy.pid"' \
         > /etc/tinyproxy/maranyse.conf \
    && printf '%s\n' '^pypi\.org$' '^files\.pythonhosted\.org$' > /etc/tinyproxy/pypi.txt \
    && printf '%s\n' '[global]' 'proxy = http://127.0.0.1:8888' 'break-system-packages = true' \
         'disable-pip-version-check = true' '[install]' 'user = true' > /etc/pip.conf

# Internet réservé à Firefox (réglage des parents) : Firefox passe par un lanceur du groupe « internet »,
# le pare-feu refuse internet aux autres programmes des enfants (scripts, terminal...).
COPY --from=lanceur /firefox-net /usr/local/bin/firefox-net
# Un programme démarré par Firefox (« Ouvrir avec... ») perd l'accès internet (voir sans-internet.c)
COPY --from=lanceur /sans-internet /sans-internet-ff.so /usr/local/lib/maranyse/
RUN chown root:root /usr/local/lib/maranyse/sans-internet /usr/local/lib/maranyse/sans-internet-ff.so     && chmod 4755 /usr/local/lib/maranyse/sans-internet && chmod 644 /usr/local/lib/maranyse/sans-internet-ff.so
RUN groupadd -g 2000 internet     && chown root:internet /usr/local/bin/firefox-net && chmod 2755 /usr/local/bin/firefox-net     && ln -sf /usr/local/bin/firefox-net /usr/bin/firefox-esr     && sed -i 's#^Exec=/usr/lib/firefox-esr/firefox-esr#Exec=/usr/local/bin/firefox-net#; s#^Exec=firefox-esr#Exec=/usr/local/bin/firefox-net#'            /usr/share/applications/firefox-esr.desktop     && grep -q firefox-net /usr/share/applications/firefox-esr.desktop

# Heure et langue des sessions (xrdp ne transmet pas TZ/LANG aux sessions) ; dossiers personnels privés
RUN ln -sf /usr/share/zoneinfo/Europe/Zurich /etc/localtime && echo Europe/Zurich > /etc/timezone \
    && printf 'LANG=fr_FR.UTF-8\nLANGUAGE=fr_FR:fr\n' > /etc/default/locale \
    && (grep -q '^HOME_MODE' /etc/login.defs || printf 'HOME_MODE\t0700\n' >> /etc/login.defs)

# Clavier suisse romand par défaut dans les sessions RDP, chaque utilisateur peut changer
RUN printf 'XKBLAYOUT="ch"\nXKBVARIANT="fr"\n' > /etc/default/keyboard \
    && printf 'allowed_users=anybody\nneeds_root_rights=no\n' > /etc/X11/Xwrapper.config \
    && echo 'exec /usr/local/bin/maranyse-session' > /etc/skel/.xsession \
    && mkdir -p /usr/lib/firefox-esr/distribution \
    && echo '{"policies":{"DNSOverHTTPS":{"Enabled":false,"Locked":true},"DisableAppUpdate":true,"BlockAboutConfig":true,"DisablePrivateBrowsing":true,"Proxy":{"Mode":"none","Locked":true},"ExtensionSettings":{"*":{"installation_mode":"blocked","blocked_install_message":"Les extensions sont désactivées par tes parents."},"langpack-fr@firefox-esr.mozilla.org":{"installation_mode":"allowed"},"langpack-ar@firefox-esr.mozilla.org":{"installation_mode":"allowed"},"langpack-zh-CN@firefox-esr.mozilla.org":{"installation_mode":"allowed"},"langpack-es-ES@firefox-esr.mozilla.org":{"installation_mode":"allowed"},"langpack-hi-IN@firefox-esr.mozilla.org":{"installation_mode":"allowed"},"langpack-de@firefox-esr.mozilla.org":{"installation_mode":"allowed"},"langpack-pt-PT@firefox-esr.mozilla.org":{"installation_mode":"allowed"},"langpack-ru@firefox-esr.mozilla.org":{"installation_mode":"allowed"},"langpack-ja@firefox-esr.mozilla.org":{"installation_mode":"allowed"}}}}' \
       > /usr/lib/firefox-esr/distribution/policies.json \
    && printf '// MaranYSE : pas de console privilegiee ni de debogage a distance (ils permettraient de piloter Firefox)\npref("devtools.chrome.enabled", false, locked);\npref("devtools.debugger.remote-enabled", false, locked);\n// Firefox dans la langue de la session de l enfant (packs de langue firefox-esr-l10n-*)\npref("intl.locale.requested", "");\n' \
       > /usr/lib/firefox-esr/defaults/pref/maranyse.js

# Logiciels ajoutés par les parents (page Logiciels) : script généré depuis ~/logiciels.json par installer_controle.sh
COPY logiciels.sh /opt/maranyse/logiciels.sh
RUN sh /opt/maranyse/logiciels.sh

# Bureau « façon Windows » : barre des tâches en bas avec menu Démarrer, thème clair, icônes, fond MaranYSE.
# Réglages par défaut dans /etc/xdg ; maranyse-session les (ré)applique à chaque enfant (voir ce fichier).
COPY bureau/ /opt/maranyse/bureau/
RUN cd /opt/maranyse/bureau && sed -i 's/\r$//' maranyse-session *.xml *.svg *.rc theme/* icones/* \
    && install -m 755 maranyse-session /usr/local/bin/maranyse-session \
    && install -D -m 644 xfce4-panel.xml /etc/xdg/xfce4/panel/default.xml \
    && install -m 644 whiskermenu-1.rc /etc/xdg/xfce4/panel/whiskermenu-1.rc \
    && install -D -m 644 theme/index.theme /usr/share/themes/MaranYSE/index.theme \
    && install -D -m 644 theme/gtk.css /usr/share/themes/MaranYSE/gtk-3.0/gtk.css \
    && ln -s /usr/share/themes/Orchis-Light/gtk-2.0 /usr/share/themes/MaranYSE/gtk-2.0 \
    && ln -s /usr/share/themes/Orchis-Light/xfwm4 /usr/share/themes/MaranYSE/xfwm4 \
    && install -D -m 644 icones/index.theme /usr/share/icons/MaranYSE/index.theme \
    && for e in emblem-readonly emblem-symbolic-link emblem-unreadable; do \
         install -D -m 644 icones/vide.svg /usr/share/icons/MaranYSE/emblems/$e.svg; done \
    && install -m 644 xsettings.xml xfwm4.xml xfce4-desktop.xml /etc/xdg/xfce4/xfconf/xfce-perchannel-xml/ \
    && install -D -m 644 fond.svg /usr/share/backgrounds/maranyse/fond.svg \
    && install -D -m 644 demarrer.svg /usr/share/maranyse/demarrer.svg \
    && mkdir -p /usr/share/maranyse/lanceurs \
    && for a in firefox-esr libreoffice-writer org.kde.gcompris tuxpaint org.thonny.Thonny com.microsoft.VSCode; do \
         if [ -f /usr/share/applications/$a.desktop ]; then install -m 755 /usr/share/applications/$a.desktop /usr/share/maranyse/lanceurs/; fi; \
       done \
    && sed -i -E 's/^Name(\[[^]]*\])?=.*/Name\1=Firefox/' /usr/share/maranyse/lanceurs/firefox-esr.desktop \
    && ls /usr/share/maranyse/lanceurs

COPY entrypoint.sh /entrypoint.sh
RUN sed -i 's/\r$//' /entrypoint.sh && chmod +x /entrypoint.sh

EXPOSE 3389
ENTRYPOINT ["/entrypoint.sh"]

