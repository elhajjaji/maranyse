/* MaranYSE — lanceur de Firefox avec accès internet.
 *
 * Quand le réglage « Internet réservé à Firefox » est actif, le pare-feu refuse internet à tous les
 * programmes d'un enfant, sauf ceux du groupe « internet ». Ce lanceur (setgid internet) fait passer
 * Firefox, et lui seul, dans ce groupe : un script Python ou le terminal restent sans internet,
 * donc sans moyen de contourner le filtrage.
 *
 * - Il ne lance QUE le vrai Firefox (chemin fixe).
 * - Il efface les variables qui permettraient d'y injecter du code (LD_PRELOAD...) ou de le piloter
 *   (toutes les MOZ_*, ex. MOZ_MARIONETTE).
 * - Il retire les options de pilotage à distance / débogage (--marionette, --remote-debugging-port,
 *   --start-debugger-server, -chrome, -app...) : seules les options ordinaires sont gardées.
 * - Il charge sans-internet-ff.so : tout programme que Firefox démarre (« Ouvrir avec... », lien vers une
 *   application) repasse par sans-internet et perd l'accès internet.
 * Le blocage d'application reste valable : si Firefox est interdit à l'enfant (droits du fichier), il ne peut
 * pas être lancé. */
#define _GNU_SOURCE
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <unistd.h>

#define FIREFOX "/usr/lib/firefox-esr/firefox-esr"
#define PRELOAD "/usr/local/lib/maranyse/sans-internet-ff.so"

extern char **environ;

static int option_ok(const char *a) {
    static const char *ok[] = {"new-window", "new-tab", "url", "browser", "search", "preferences",
                               "private-window", "name", "class", "safe-mode", "version", "v", "help", "h",
                               "headless", "screenshot", "window-size", "profile", "no-remote", "new-instance", "kiosk", NULL};
    if (a[0] != '-')
        return 1;                                      /* adresse ou fichier */
    while (*a == '-')
        a++;
    size_t n = strcspn(a, "=");
    for (int i = 0; ok[i]; i++)
        if (strlen(ok[i]) == n && strncasecmp(a, ok[i], n) == 0)
            return 1;
    return 0;
}

static int env_ok(const char *e) {
    static const char *ok[] = {
        "HOME", "USER", "LOGNAME", "SHELL", "PWD", "TERM",
        "DISPLAY", "XAUTHORITY", "XAUTHLOCALHOSTNAME", "DBUS_SESSION_BUS_ADDRESS",
        "LANG", "LANGUAGE", "LC_ALL", "LC_CTYPE", "LC_MESSAGES", "LC_TIME", "LC_NUMERIC",
        "LC_COLLATE", "LC_MONETARY", "LC_PAPER", "LC_NAME", "LC_ADDRESS", "LC_TELEPHONE",
        "LC_MEASUREMENT", "LC_IDENTIFICATION", "TZ",
        "XDG_RUNTIME_DIR", "XDG_SESSION_TYPE", "XDG_CURRENT_DESKTOP", "XDG_SESSION_DESKTOP",
        "XDG_DATA_DIRS", "XDG_CONFIG_DIRS", "XDG_MENU_PREFIX", "XDG_SESSION_CLASS", "XDG_SESSION_ID",
        "GTK_IM_MODULE", "QT_IM_MODULE", "XMODIFIERS", "SDL_IM_MODULE", NULL
    };
    size_t n = strcspn(e, "=");
    if (e[n] != '=')
        return 0;
    for (int i = 0; ok[i]; i++) {
        if (strlen(ok[i]) == n && strncmp(e, ok[i], n) == 0) {
            /* Les modules de saisie (ex. fcitx) ne doivent jamais contenir un chemin vers une bibliothèque */
            if (strstr(ok[i], "IM_MODULE") && strchr(e + n + 1, '/'))
                return 0;
            return 1;
        }
    }
    return 0;
}

int main(int argc, char **argv) {
    gid_t g = getegid();                 /* groupe « internet » donné par le bit setgid */
    if (setregid(g, g) != 0)              /* groupe réel = groupe effectif : Firefox démarre normalement */
        return 1;
    /* Liste blanche stricte de l'environnement : retire LD_*, MOZ_*, GTK_PATH, GIO_MODULE_DIR, GDK_PIXBUF_MODULE_FILE... */
    for (int again = 1; again;) {
        again = 0;
        for (char **e = environ; e && *e; e++)
            if (!env_ok(*e)) {
                char name[256];
                size_t n = strcspn(*e, "=");
                if (n >= sizeof name)
                    n = sizeof name - 1;
                memcpy(name, *e, n);
                name[n] = 0;
                unsetenv(name);
                again = 1;
                break;
            }
    }
    setenv("PATH", "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin", 1);
    setenv("LD_PRELOAD", PRELOAD, 1);
    char **av = calloc((size_t)argc + 1, sizeof *av);
    if (!av)
        return 1;
    int k = 0;
    av[k++] = FIREFOX;
    for (int i = 1; i < argc; i++) {
        if (option_ok(argv[i])) {
            av[k++] = argv[i];
        } else if (!strchr(argv[i], '=') && i + 1 < argc && argv[i + 1][0] != '-' && !strstr(argv[i + 1], "://")) {
            i++;                           /* option retirée : sa valeur aussi (ex. --remote-debugging-port 9222) */
        }
    }
    av[k] = NULL;
    execv(FIREFOX, av);
    return 127;
}
