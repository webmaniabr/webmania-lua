#define _POSIX_C_SOURCE 200809L
#include <dirent.h>
#include <lauxlib.h>
#include <lua.h>
#include <lualib.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
static int entries(const char *p) {
  DIR *d = opendir(p);
  if (!d)
    return -1;
  int n = 0;
  struct dirent *e;
  while ((e = readdir(d)))
    if (e->d_name[0] != '.')
      n++;
  closedir(d);
  return n;
}
static int children(void) {
  DIR *d = opendir("/proc/self/task");
  if (!d)
    return -1;
  int n = 0;
  struct dirent *e;
  while ((e = readdir(d))) {
    if (e->d_name[0] == '.')
      continue;
    char p[512];
    snprintf(p, sizeof(p), "/proc/self/task/%s/children", e->d_name);
    FILE *f = fopen(p, "r");
    if (f) {
      long child;
      while (fscanf(f, "%ld", &child) == 1)
        n++;
      fclose(f);
    }
  }
  closedir(d);
  return n;
}
static int counts(lua_State *L) {
  lua_pushinteger(L, entries("/proc/self/fd"));
  lua_pushinteger(L, entries("/proc/self/task"));
  lua_pushinteger(L, children());
  return 3;
}
static int monotonic(lua_State *L) {
  struct timespec t;
  clock_gettime(CLOCK_MONOTONIC, &t);
  lua_pushnumber(L, t.tv_sec + t.tv_nsec / 1e9);
  return 1;
}
static int pause_vm(lua_State *L) {
  lua_Integer n = luaL_checkinteger(L, 1);
  if (n < 0 || n > 10000)
    return luaL_error(L, "sleep bound");
  struct timespec t = {n / 1000, (n % 1000) * 1000000};
  nanosleep(&t, NULL);
  return 0;
}
int main(int argc, char **argv) {
  if (argc < 2)
    return 2;
  lua_State *L = luaL_newstate();
  if (!L)
    return 3;
  luaL_openlibs(L);
  lua_pushcfunction(L, counts);
  lua_setglobal(L, "resource_counts");
  lua_pushcfunction(L, monotonic);
  lua_setglobal(L, "monotonic");
  lua_pushcfunction(L, pause_vm);
  lua_setglobal(L, "sleep_ms");
  lua_newtable(L);
  for (int i = 1; i < argc; i++) {
    lua_pushstring(L, argv[i]);
    lua_rawseti(L, -2, i - 1);
  }
  lua_setglobal(L, "arg");
  int s = luaL_dofile(L, argv[1]);
  if (s)
    fprintf(stderr, "%s\n", lua_tostring(L, -1));
  lua_close(L);
  /* pthread_join returns when the joined thread clears its thread id on exit,
   * but /proc/self/task keeps listing that thread until the kernel finishes
   * its teardown, which can trail the joiner by a scheduling slice. The
   * counts are therefore sampled until they settle, for at most 2 s; a thread
   * or child process still present after that is reported. An unreaped child
   * stays listed, so the wait never hides one. */
  int c = children(), t = entries("/proc/self/task");
  for (int waited = 0; (c || t != 1) && waited < 2000; waited++) {
    struct timespec ms = {0, 1000000};
    nanosleep(&ms, NULL);
    c = children();
    t = entries("/proc/self/task");
  }
  if (c || t != 1) {
    fprintf(stderr, "VM close resources children=%d threads=%d\n", c, t);
    return 4;
  }
  return s ? 1 : 0;
}
