#include <lauxlib.h>
#include <lua.h>
#include <lualib.h>
#include <stdio.h>
#include <stdlib.h>
typedef struct Alloc {
  long remaining;
  size_t blocks;
} Alloc;
static void *alloc(void *data, void *p, size_t old, size_t n) {
  (void)old;
  Alloc *a = data;
  if (!n) {
    if (p)
      a->blocks--;
    free(p);
    return NULL;
  }
  if (a->remaining == 0)
    return NULL;
  if (a->remaining > 0)
    a->remaining--;
  void *q = realloc(p, n);
  if (q && !p)
    a->blocks++;
  return q;
}
int main(int argc, char **argv) {
  if (argc != 2) {
    fprintf(stderr, "usage: allocator PATH_TO_COMPANION\n");
    return 2;
  }
  int failed = 0, passed = 0;
  Alloc a = {-1, 0};
  lua_State *L = lua_newstate(alloc, &a);
  if (!L)
    return 2;
  luaL_openlibs(L);
  lua_pushstring(L, argv[1]);
  lua_setglobal(L, "worker_path");
  if (luaL_dostring(L, "w=require('webmania');v=w.models['api1_fiscal."
                       "NfeLookupRequest'].new();v:set_uuid('00000000-0000-"
                       "4000-8000-000000000001');cfg=w.Config():set_worker_"
                       "path(worker_path):set_base_url('http://"
                       "127.0.0.1:9'):set_timeout_ms(500);c=w.NfeClient(w."
                       "CompanyCredentials('secret-marker','synthetic','"
                       "synthetic','synthetic'),cfg)"))
    return 3;
  const char *code =
      "local s=v:to_json();local x=w.Json(s);local "
      "m=w.Map();m:set_extension('extra',x);local "
      "t=w.nfeGetSefazStatus(c);local value,err=t:await();if value then "
      "value:to_json();value:close() end;if err then err:close() "
      "end;t:close();m:to_json();m:close();x:close()";
  if (luaL_loadstring(L, code))
    return 4;
  for (int budget = 0; budget < 180; budget++) {
    lua_pushvalue(L, 1);
    a.remaining = budget;
    int status = lua_pcall(L, 0, 0, 0);
    a.remaining = -1;
    if (status == LUA_ERRMEM)
      failed++;
    else if (status == LUA_OK)
      passed++;
    else {
      fprintf(stderr, "unexpected Lua error in allocator control\n");
      lua_close(L);
      return 5;
    }
    if (status != LUA_OK)
      lua_pop(L, 1);
    for (int cycle = 0; cycle < 4; cycle++)
      lua_gc(L, LUA_GCCOLLECT, 0);
  }
  lua_close(L);
  if (a.blocks) {
    fprintf(stderr, "Lua blocks retained after lua_close: %zu\n", a.blocks);
    return 6;
  }
  if (!failed || !passed)
    return 7;
  printf("180 shared-VM Lua allocator budgets: %d OOM failures, %d successes; "
         "GC between budgets and lua_close "
         "free all Lua allocations PASS\n",
         failed, passed);
  return 0;
}
