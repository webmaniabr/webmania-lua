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
int main(void) {
  int failed = 0, passed = 0;
  Alloc a = {-1, 0};
  lua_State *L = lua_newstate(alloc, &a);
  if (!L)
    return 2;
  luaL_openlibs(L);
  if (luaL_dostring(L,
                    "w=require('webmania');cfg=w.Config():set_worker_path('/"
                    "sdk/tests/c3_companion.py'):set_base_url('http://"
                    "127.0.0.1:9'):set_timeout_ms(2000);c=w.EmitterFilesClient("
                    "nil,cfg);auth=w.FileAuth.anonymous()"))
    return 3;
  const char *code =
      "local t=w.fileGetNfsePdf(c,'00000000-0000-4000-8000-000000000001',auth);"
      "local v,e=t:await();assert(v);local a=v:value();local "
      "b=v:payload();v:status();v:media_type();a:to_json();a:get_msg();a:close("
      ");v:close();b:to_json();b:close();t:close();"
      "t=w.fileGetCtePdf(c,'00000000-0000-4000-8000-000000000001',auth);v,e=t:"
      "await();assert(v);v:bytes();v:close();t:close()";
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
  printf("180 shared-VM Pending/Html allocator budgets: %d OOM failures, %d "
         "successes; "
         "GC between budgets and lua_close "
         "free all Lua allocations PASS\n",
         failed, passed);
  return 0;
}
