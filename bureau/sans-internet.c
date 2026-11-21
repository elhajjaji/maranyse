/* MaranYSE — lance un programme SANS l'accès internet de Firefox.
 *
 * Firefox tourne dans le groupe « internet » (voir firefox-net.c). Un programme qu'il démarre en hériterait.
 * sans-internet-ff.so (chargé dans Firefox) fait passer ces programmes par ici : on remet l'identité normale
 * de l'enfant (son groupe et ses groupes habituels), puis on lance le programme.
 *
 * Il est setuid root uniquement pour pouvoir quitter le groupe « internet » (un programme ordinaire ne peut
 * plus changer de groupe après le lancement de Firefox). Il ne fait rien d'autre que DESCENDRE à l'identité de
 * l'utilisateur qui l'appelle, et vérifie que c'est fait avant de lancer quoi que ce soit.
 *
 * Usage : sans-internet [-p] PROGRAMME ARGV0 [ARGS...]     (-p : chercher PROGRAMME dans le PATH) */
#define _GNU_SOURCE
#include <grp.h>
#include <pwd.h>
#include <string.h>
#include <unistd.h>

#define INTERNET_GID 2000

int main(int argc, char **argv) {
    int i = 1, search = 0;
    if (argc > 1 && strcmp(argv[1], "-p") == 0) {
        search = 1;
        i = 2;
    }
    if (argc < i + 1)
        return 127;
    uid_t u = getuid();
    struct passwd *pw = getpwuid(u);
    if (!pw)
        return 126;
    gid_t g = pw->pw_gid;
    if (initgroups(pw->pw_name, g) != 0 || setresgid(g, g, g) != 0 || setresuid(u, u, u) != 0)
        return 126;
    gid_t r, e, s, gs[512];
    if (getresgid(&r, &e, &s) != 0 || r != g || e != g || s != g || geteuid() != u || getuid() != u)
        return 126;
    int n = getgroups(512, gs);
    if (n < 0)
        return 126;
    for (int k = 0; k < n; k++)
        if (gs[k] == INTERNET_GID && g != INTERNET_GID)
            return 126;
    if (g == INTERNET_GID)
        return 126;
    char *prog = argv[i];
    char *fallback[] = {prog, NULL};
    char **av = (argc > i + 1) ? argv + i + 1 : fallback;
    if (search)
        execvp(prog, av);
    else
        execv(prog, av);
    return 127;
}
