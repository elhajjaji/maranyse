/* MaranYSE — chargé dans Firefox (LD_PRELOAD, par firefox-net) : tout programme que Firefox démarre,
 * sauf Firefox lui-même (ses processus internes), passe par sans-internet et perd l'accès internet.
 * Ex. « Ouvrir avec... » un fichier téléchargé, ou un lien vers une application : sans cela, un script
 * Python ouvert depuis Firefox aurait internet sans filtrage. */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <limits.h>
#include <spawn.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#define INTERNET_GID 2000
#define HELPER "/usr/local/lib/maranyse/sans-internet"
#define FFDIR "/usr/lib/firefox-esr/"

extern char **environ;

static int actif(void) { return getegid() == INTERNET_GID || getgid() == INTERNET_GID; }

static int firefox(const char *p) {
    char r[PATH_MAX];
    if (!p || !strchr(p, '/') || !realpath(p, r))
        return 0;
    return strncmp(r, FFDIR, strlen(FFDIR)) == 0;
}

static char **emballer(const char *prog, char *const argv[], int search) {
    int n = 0;
    while (argv && argv[n])
        n++;
    char **v = malloc(sizeof(char *) * (size_t)(n + 5));
    if (!v)
        return NULL;
    int k = 0;
    v[k++] = (char *)HELPER;
    if (search)
        v[k++] = (char *)"-p";
    v[k++] = (char *)prog;
    if (n == 0)
        v[k++] = (char *)prog;
    for (int i = 0; i < n; i++)
        v[k++] = argv[i];
    v[k] = NULL;
    return v;
}

#define REEL(type, nom, ...) static type (*reel_##nom)(__VA_ARGS__); \
    if (!reel_##nom) reel_##nom = (type (*)(__VA_ARGS__))dlsym(RTLD_NEXT, #nom)

int execve(const char *path, char *const argv[], char *const envp[]) {
    REEL(int, execve, const char *, char *const[], char *const[]);
    if (actif() && !firefox(path)) {
        char **v = emballer(path, argv, 0);
        if (!v) { errno = ENOMEM; return -1; }
        return reel_execve(HELPER, v, envp);
    }
    return reel_execve(path, argv, envp);
}

int execv(const char *path, char *const argv[]) { return execve(path, argv, environ); }

int execvpe(const char *file, char *const argv[], char *const envp[]) {
    REEL(int, execvpe, const char *, char *const[], char *const[]);
    if (strchr(file, '/'))
        return execve(file, argv, envp);
    if (actif()) {
        char **v = emballer(file, argv, 1);
        if (!v) { errno = ENOMEM; return -1; }
        REEL(int, execve, const char *, char *const[], char *const[]);
        return reel_execve(HELPER, v, envp);
    }
    return reel_execvpe(file, argv, envp);
}

int execvp(const char *file, char *const argv[]) { return execvpe(file, argv, environ); }

static char **va_args(const char *a0, va_list ap, char ***envp) {
    int n = 1;
    va_list c;
    va_copy(c, ap);
    while (va_arg(c, char *))
        n++;
    va_end(c);
    char **v = malloc(sizeof(char *) * (size_t)(n + 1));
    if (!v)
        return NULL;
    v[0] = (char *)a0;
    for (int i = 1; i < n; i++)
        v[i] = va_arg(ap, char *);
    v[n] = NULL;
    (void)va_arg(ap, char *);
    if (envp)
        *envp = va_arg(ap, char **);
    return v;
}

int execl(const char *path, const char *a0, ...) {
    va_list ap; va_start(ap, a0);
    char **v = va_args(a0, ap, NULL); va_end(ap);
    if (!v) { errno = ENOMEM; return -1; }
    return execve(path, v, environ);
}

int execlp(const char *file, const char *a0, ...) {
    va_list ap; va_start(ap, a0);
    char **v = va_args(a0, ap, NULL); va_end(ap);
    if (!v) { errno = ENOMEM; return -1; }
    return execvpe(file, v, environ);
}

int execle(const char *path, const char *a0, ...) {
    va_list ap; va_start(ap, a0);
    char **env = NULL;
    char **v = va_args(a0, ap, &env); va_end(ap);
    if (!v) { errno = ENOMEM; return -1; }
    return execve(path, v, env);
}

int fexecve(int fd, char *const argv[], char *const envp[]) {
    REEL(int, fexecve, int, char *const[], char *const[]);
    if (actif()) { errno = EACCES; return -1; }
    return reel_fexecve(fd, argv, envp);
}

int execveat(int dirfd, const char *path, char *const argv[], char *const envp[], int flags) {
    REEL(int, execveat, int, const char *, char *const[], char *const[], int);
    if (actif()) {
        if (path[0] == '/' && !(flags & 0x1000 /* AT_EMPTY_PATH */))
            return execve(path, argv, envp);
        errno = EACCES;
        return -1;
    }
    return reel_execveat(dirfd, path, argv, envp, flags);
}

int posix_spawn(pid_t *pid, const char *path, const posix_spawn_file_actions_t *fa,
                const posix_spawnattr_t *at, char *const argv[], char *const envp[]) {
    REEL(int, posix_spawn, pid_t *, const char *, const posix_spawn_file_actions_t *,
         const posix_spawnattr_t *, char *const[], char *const[]);
    if (actif() && !firefox(path)) {
        char **v = emballer(path, argv, 0);
        if (!v) return ENOMEM;
        int r = reel_posix_spawn(pid, HELPER, fa, at, v, envp);
        free(v);
        return r;
    }
    return reel_posix_spawn(pid, path, fa, at, argv, envp);
}

int posix_spawnp(pid_t *pid, const char *file, const posix_spawn_file_actions_t *fa,
                 const posix_spawnattr_t *at, char *const argv[], char *const envp[]) {
    REEL(int, posix_spawnp, pid_t *, const char *, const posix_spawn_file_actions_t *,
         const posix_spawnattr_t *, char *const[], char *const[]);
    if (strchr(file, '/'))
        return posix_spawn(pid, file, fa, at, argv, envp);
    if (actif()) {
        char **v = emballer(file, argv, 1);
        if (!v) return ENOMEM;
        REEL(int, posix_spawn, pid_t *, const char *, const posix_spawn_file_actions_t *,
             const posix_spawnattr_t *, char *const[], char *const[]);
        int r = reel_posix_spawn(pid, HELPER, fa, at, v, envp);
        free(v);
        return r;
    }
    return reel_posix_spawnp(pid, file, fa, at, argv, envp);
}

/* system() et popen() lancent /bin/sh par un chemin interne de la libc : on leur fait lancer sans-internet. */
static char *commande(const char *cmd) {
    size_t n = strlen(cmd);
    char *q = malloc(n * 4 + 64);
    if (!q)
        return NULL;
    char *o = q + sprintf(q, "exec " HELPER " /bin/sh sh -c '");
    for (const char *c = cmd; *c; c++) {
        if (*c == '\'') { memcpy(o, "'\\''", 4); o += 4; }
        else *o++ = *c;
    }
    strcpy(o, "'");
    return q;
}

int system(const char *cmd) {
    REEL(int, system, const char *);
    if (cmd && actif()) {
        char *q = commande(cmd);
        if (!q) return -1;
        int r = reel_system(q);
        free(q);
        return r;
    }
    return reel_system(cmd);
}

FILE *popen(const char *cmd, const char *mode) {
    REEL(FILE *, popen, const char *, const char *);
    if (actif()) {
        char *q = commande(cmd);
        if (!q) return NULL;
        FILE *f = reel_popen(q, mode);
        free(q);
        return f;
    }
    return reel_popen(cmd, mode);
}
