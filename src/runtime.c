#define _POSIX_C_SOURCE 200809L
#include "internal.h"
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#define VALUE "webmania.value"
#define CONFIG "webmania.config"
#define CRED "webmania.credential"
#define CLIENT "webmania.client"
#define TASK "webmania.task"
#define ERROR "webmania.error"
#define FILEVALUE "webmania.file"
#define PENDING "webmania.nfse_pdf_pending"
typedef struct Config {
  wm_config *ptr;
  char *text[4];
  char **origins;
  size_t count;
  int64_t numbers[3];
  bool set[3];
} Config;
typedef struct Credential {
  void *ptr;
  int kind;
} Credential;
typedef struct Client {
  Owner *owner;
} Client;
typedef struct Error {
  wm_error *ptr;
  wm_status local_status;
} Error;
typedef struct File {
  void *ptr;
  int kind;
} File;
static int fail(lua_State *L, const char *s) {
  return luaL_error(L, "webmania: %s", s);
}
int invalid(lua_State *L) {
  return fail(L, "invalid value or local allocation failure");
}
const char *strict_string(lua_State *L, int i, size_t *n) {
  if (lua_type(L, i) != LUA_TSTRING)
    luaL_error(L, "webmania: string required");
  return lua_tolstring(L, i, n);
}
const char *cstring(lua_State *L, int i) {
  size_t n;
  const char *s = strict_string(L, i, &n);
  if (memchr(s, 0, n))
    luaL_error(L, "webmania: embedded NUL unsupported by this C argument");
  return s;
}
int64_t integer(lua_State *L, int i) {
  if (!lua_isinteger(L, i))
    luaL_error(L, "webmania: exact integer required; floats are rejected");
  lua_Integer n = lua_tointeger(L, i);
  if (sizeof(lua_Integer) > sizeof(int64_t) && (n > INT64_MAX || n < INT64_MIN))
    luaL_error(L, "webmania: integer range");
  return (int64_t)n;
}
int boolean(lua_State *L, int i) {
  if (lua_type(L, i) != LUA_TBOOLEAN)
    luaL_error(L, "webmania: boolean required");
  return lua_toboolean(L, i);
}
int push_status(lua_State *L, wm_status s) {
  if (s != WM_OK)
    return invalid(L);
  lua_pushboolean(L, 1);
  return 1;
}
int push_presence(lua_State *L, wm_presence p) {
  lua_pushstring(L, p == WM_MISSING        ? "missing"
                    : p == WM_PRESENT_NULL ? "null"
                                           : "present");
  return 1;
}
static int redacted(lua_State *L) {
  lua_pushliteral(L, "webmania<[redacted]>");
  return 1;
}
Value *value_new(lua_State *L, const Type *t) {
  Value *v = lua_newuserdatauv(L, sizeof(*v), 0);
  memset(v, 0, sizeof(*v));
  v->type = t;
  luaL_setmetatable(L, VALUE);
  return v;
}
Value *value_check(lua_State *L, int i, const Type *t) {
  Value *v = luaL_checkudata(L, i, VALUE);
  if (!v->ptr || v->type != t)
    luaL_error(L, "webmania: wrong nominal type or closed value");
  return v;
}
static Value *any_value(lua_State *L) {
  Value *v = luaL_checkudata(L, 1, VALUE);
  if (!v->ptr)
    luaL_error(L, "webmania: closed value");
  return v;
}
static int value_close(lua_State *L) {
  Value *v = luaL_checkudata(L, 1, VALUE);
  if (v->ptr) {
    v->type->destroy(v->ptr);
    v->ptr = NULL;
  }
  if (v->secret) {
    memset(v->secret, 0, strlen(v->secret));
    free(v->secret);
    v->secret = NULL;
  }
  return 0;
}
static int value_json(lua_State *L) {
  Value *v = any_value(L);
  if (v->type == &types[0]) {
    lua_pushstring(L, wm_number_lexeme(v->ptr));
    return 1;
  } /* Create the GC guard before C allocates: Lua OOM can longjmp. */
  Value *g = value_new(L, &types[1]);
  g->secret = v->type->json ? v->type->json(v->ptr) : NULL;
  if (!g->secret)
    return invalid(L);
  lua_pushstring(L, g->secret);
  free(g->secret);
  g->secret = NULL;
  return 1;
}
static int value_type(lua_State *L) {
  Value *v = any_value(L);
  lua_pushstring(L, v->type->name);
  return 1;
}
static const Field *field_find(lua_State *L, Value *v, int index) {
  const char *s = cstring(L, index);
  for (size_t i = 0; i < v->type->nfields; i++)
    if (!strcmp(s, v->type->fields[i].name))
      return &v->type->fields[i];
  luaL_error(L, "webmania: unknown field");
  return NULL;
}
static int value_field(lua_State *L) {
  Value *v = any_value(L);
  const Field *f = field_find(L, v, 2);
  int mode = (int)lua_tointeger(L, lua_upvalueindex(1));
  field_fn fn = mode == 0   ? f->set
                : mode == 1 ? f->get
                : mode == 2 ? f->presence
                            : f->unset;
  if (!fn)
    return fail(L, "field operation unavailable");
  return fn(L, v);
}
static int named_field(lua_State *L) {
  Value *v = any_value(L);
  lua_Integer index = lua_tointeger(L, lua_upvalueindex(1));
  const Type *expected = lua_touserdata(L, lua_upvalueindex(3));
  if (v->type != expected || index < 0 || (size_t)index >= v->type->nfields)
    return fail(L, "wrong nominal method receiver");
  const Field *f = &v->type->fields[index];
  int mode = (int)lua_tointeger(L, lua_upvalueindex(2));
  field_fn fn = mode == 0   ? f->set
                : mode == 1 ? f->get
                : mode == 2 ? f->presence
                            : f->unset;
  if (!fn)
    return fail(L, "field operation unavailable");
  lua_pushnil(L);
  lua_insert(L, 2);
  return fn(L, v);
}
static int extension_set(lua_State *L) {
  Value *v = any_value(L);
  if (!v->type->extension_set)
    return invalid(L);
  size_t n;
  const char *k = strict_string(L, 2, &n);
  Value *x = value_check(L, 3, &types[1]);
  return push_status(L, v->type->extension_set(v->ptr, k, n, x->ptr));
}
static int extension_get(lua_State *L) {
  Value *v = any_value(L);
  if (!v->type->extension_get)
    return invalid(L);
  size_t n;
  const char *k = strict_string(L, 2, &n);
  Value *r = value_new(L, &types[1]);
  r->ptr = v->type->extension_get(v->ptr, k, n);
  if (!r->ptr) {
    lua_pushnil(L);
    return 1;
  }
  return 1;
}
static int value_append(lua_State *L) {
  Value *v = any_value(L);
  if (!v->type->append)
    return invalid(L);
  return v->type->append(L, v);
}
static int value_at(lua_State *L) {
  Value *v = any_value(L);
  if (!v->type->at)
    return invalid(L);
  return v->type->at(L, v);
}
static int value_count(lua_State *L) {
  Value *v = any_value(L);
  if (!v->type->count)
    return invalid(L);
  size_t n = v->type->count(v->ptr);
  if (n > (size_t)LUA_MAXINTEGER)
    return invalid(L);
  lua_pushinteger(L, (lua_Integer)n);
  return 1;
}
static int map_key(lua_State *L) {
  Value *v = value_check(L, 1, &types[2]);
  int64_t i = integer(L, 2);
  size_t n = 0;
  const char *k = i > 0 ? wm_map_key_at(v->ptr, (size_t)(i - 1), &n) : NULL;
  if (!k)
    lua_pushnil(L);
  else
    lua_pushlstring(L, k, n);
  return 1;
}
static int value_index(lua_State *L) {
  Value *v = luaL_checkudata(L, 1, VALUE);
  const char *s = cstring(L, 2);
  struct {
    const char *n;
    lua_CFunction f;
  } methods[] = {
      {"close", value_close},           {"to_json", value_json},
      {"reveal", value_json},           {"type", value_type},
      {"set_extension", extension_set}, {"get_extension", extension_get},
      {"append", value_append},         {"at", value_at},
      {"count", value_count},           {"key_at", map_key}};
  for (size_t i = 0; i < sizeof(methods) / sizeof(methods[0]); i++)
    if (!strcmp(s, methods[i].n)) {
      lua_pushcfunction(L, methods[i].f);
      return 1;
    }
  if (!v->ptr)
    return fail(L, "closed value");
  const char *names[] = {"set", "get", "presence", "unset"};
  for (int mode = 0; mode < 4; mode++) {
    if (!strcmp(s, names[mode])) {
      lua_pushinteger(L, mode);
      lua_pushcclosure(L, value_field, 1);
      return 1;
    }
    size_t n = strlen(names[mode]);
    if (!strncmp(s, names[mode], n) && s[n] == '_')
      for (size_t j = 0; j < v->type->nfields; j++)
        if (!strcmp(s + n + 1, v->type->fields[j].name)) {
          lua_pushinteger(L, (lua_Integer)j);
          lua_pushinteger(L, mode);
          lua_pushlightuserdata(L, (void *)v->type);
          lua_pushcclosure(L, named_field, 3);
          return 1;
        }
  }
  lua_pushnil(L);
  return 1;
}
int class_new(lua_State *L) {
  lua_Integer index = lua_tointeger(L, lua_upvalueindex(1));
  if (index < 0 || (size_t)index >= type_count || lua_gettop(L) != 0)
    return invalid(L);
  const Type *t = &types[index];
  if (!t->create)
    return fail(L, "union requires a named from_variant constructor");
  Value *v = value_new(L, t);
  v->ptr = t->create();
  if (!v->ptr)
    return invalid(L);
  return 1;
}
int class_parse(lua_State *L) {
  lua_Integer index = lua_tointeger(L, lua_upvalueindex(1));
  if (index < 0 || (size_t)index >= type_count)
    return invalid(L);
  const Type *t = &types[index];
  size_t n;
  const char *s = strict_string(L, 1, &n);
  Config *c = lua_isnoneornil(L, 2) ? NULL : luaL_checkudata(L, 2, CONFIG);
  if (c && !c->ptr)
    return invalid(L);
  if (!t->parse)
    return invalid(L); /* Error userdata is allocated before C can allocate. */
  Error *e = lua_newuserdatauv(L, sizeof(*e), 0);
  e->ptr = NULL;
  e->local_status = WM_INVALID;
  luaL_setmetatable(L, ERROR);
  Value *v = value_new(L, t);
  v->ptr = t->parse(s, n, c ? c->ptr : NULL, &e->ptr);
  if (!v->ptr) {
    lua_pushnil(L);
    lua_pushvalue(L, -3);
    return 2;
  }
  return 1;
}
static int number_new(lua_State *L) {
  const char *s = cstring(L, 1);
  Value *v = value_new(L, &types[0]);
  v->ptr = wm_number_parse(s);
  if (!v->ptr)
    return invalid(L);
  return 1;
}
static int json_new(lua_State *L) {
  size_t n;
  const char *s = strict_string(L, 1, &n);
  Value *v = value_new(L, &types[1]);
  v->ptr = wm_json_parse(s, n);
  if (!v->ptr)
    return invalid(L);
  return 1;
}
static int map_new(lua_State *L) {
  bool empty = lua_isnoneornil(L, 1);
  size_t n = 0;
  const char *s = empty ? NULL : strict_string(L, 1, &n);
  Value *v = value_new(L, &types[2]);
  v->ptr = empty ? wm_map_new() : wm_map_from_json(s, n);
  if (!v->ptr)
    return invalid(L);
  return 1;
}
static int scalar_new(lua_State *L) {
  int kind = (int)lua_tointeger(L, lua_upvalueindex(1));
  size_t n = 0;
  const char *s = NULL;
  void *p = NULL;
  bool b = false;
  if (kind == 0)
    s = strict_string(L, 1, &n);
  else if (kind == 1)
    p = value_check(L, 1, &types[0])->ptr;
  else if (kind == 2)
    b = boolean(L, 1);
  Value *v = value_new(L, &types[3]);
  v->ptr = kind == 0   ? (void *)wm_scalar_text_n(s, n)
           : kind == 1 ? (void *)wm_scalar_number(p)
           : kind == 2 ? (void *)wm_scalar_boolean(b)
                       : (void *)wm_scalar_null();
  if (!v->ptr)
    return invalid(L);
  return 1;
}
static void config_clear(Config *c) {
  wm_config_free(c->ptr);
  c->ptr = NULL;
  for (int i = 0; i < 4; i++) {
    free(c->text[i]);
    c->text[i] = NULL;
  }
  for (size_t i = 0; i < c->count; i++)
    free(c->origins[i]);
  free(c->origins);
  c->origins = NULL;
  c->count = 0;
}
static int config_close(lua_State *L) {
  config_clear(luaL_checkudata(L, 1, CONFIG));
  return 0;
}
static wm_status config_text(wm_config *c, int k, const char *s) {
  return k == 0   ? wm_config_set_worker_path(c, s)
         : k == 1 ? wm_config_set_base_url(c, s)
         : k == 2 ? wm_config_set_ca_pem(c, s)
                  : wm_config_trust_file_origin(c, s);
}
static wm_status config_number(wm_config *c, int k, int64_t n) {
  return k == 0   ? wm_config_set_timeout_ms(c, n)
         : k == 1 ? wm_config_set_max_response_bytes(c, n)
                  : wm_config_set_max_header_bytes(c, n);
}
static int config_set(lua_State *L) {
  Config *c = luaL_checkudata(L, 1, CONFIG);
  if (!c->ptr)
    return invalid(L);
  int k = (int)lua_tointeger(L, lua_upvalueindex(1));
  if (k < 4) {
    const char *s = cstring(L, 2);
    char *copy = strdup(s);
    if (!copy)
      return invalid(L);
    if (k == 3) {
      char **grown = realloc(c->origins, (c->count + 1) * sizeof(char *));
      if (!grown) {
        free(copy);
        return invalid(L);
      }
      c->origins = grown;
      wm_status st = config_text(c->ptr, k, s);
      if (st != WM_OK) {
        free(copy);
        return invalid(L);
      }
      c->origins[c->count++] = copy;
    } else {
      wm_status st = config_text(c->ptr, k, s);
      if (st != WM_OK) {
        free(copy);
        return invalid(L);
      }
      free(c->text[k]);
      c->text[k] = copy;
    }
  } else {
    int64_t n = integer(L, 2);
    if (config_number(c->ptr, k - 4, n) != WM_OK)
      return invalid(L);
    c->numbers[k - 4] = n;
    c->set[k - 4] = true;
  }
  lua_pushvalue(L, 1);
  return 1;
}
static wm_config *config_clone(Config *c) {
  wm_config *x = wm_config_new();
  if (!x)
    return NULL;
  if (c) {
    if (!c->ptr)
      goto fail;
    for (int i = 0; i < 3; i++)
      if (c->text[i] && config_text(x, i, c->text[i]) != WM_OK)
        goto fail;
    for (size_t i = 0; i < c->count; i++)
      if (config_text(x, 3, c->origins[i]) != WM_OK)
        goto fail;
    for (int i = 0; i < 3; i++)
      if (c->set[i] && config_number(x, i, c->numbers[i]) != WM_OK)
        goto fail;
  }
  return x;
fail:
  wm_config_free(x);
  return NULL;
}
const wm_config *config_arg(lua_State *L, int i) {
  if (lua_isnoneornil(L, i))
    return NULL;
  Config *c = luaL_checkudata(L, i, CONFIG);
  if (!c->ptr)
    luaL_error(L, "webmania: closed config");
  return c->ptr;
}
static int config_new(lua_State *L) {
  Config *c = lua_newuserdatauv(L, sizeof(*c), 0);
  memset(c, 0, sizeof(*c));
  luaL_setmetatable(L, CONFIG);
  c->ptr = wm_config_new();
  if (!c->ptr)
    return invalid(L);
  return 1;
}
static int credential_close(lua_State *L) {
  Credential *c = luaL_checkudata(L, 1, CRED);
  if (c->ptr) {
    if (c->kind == 0)
      wm_company_credentials_free(c->ptr);
    else if (c->kind == 1)
      wm_reseller_credentials_free(c->ptr);
    else if (c->kind == 2)
      wm_issuer_token_free(c->ptr);
    else
      wm_monitor_token_free(c->ptr);
    c->ptr = NULL;
  }
  return 0;
}
static int credential_new(lua_State *L) {
  int k = (int)lua_tointeger(L, lua_upvalueindex(1));
  const char *a = cstring(L, 1), *b = NULL, *c = NULL, *d = NULL;
  if (k < 2) {
    b = cstring(L, 2);
    c = cstring(L, 3);
    d = cstring(L, 4);
  }
  Credential *x = lua_newuserdatauv(L, sizeof(*x), 0);
  x->ptr = NULL;
  x->kind = k;
  luaL_setmetatable(L, CRED);
  x->ptr = k == 0   ? (void *)wm_company_credentials_new(a, b, c, d)
           : k == 1 ? (void *)wm_reseller_credentials_new(a, b, c, d)
           : k == 2 ? (void *)wm_issuer_token_new(a)
                    : (void *)wm_monitor_token_new(a);
  if (!x->ptr)
    return invalid(L);
  return 1;
}
void auth_free(void *p) { wm_file_auth_free(p); }
static const Type auth_type = {"FileAuth", NULL, auth_free, NULL, NULL,
                               NULL,       0,    NULL,      NULL, NULL,
                               false,      NULL, NULL};
static void *auth_create(int k, const char *s) {
  return k == 0   ? (void *)wm_file_auth_company()
         : k == 1 ? (void *)wm_file_auth_issuer()
         : k == 2 ? (void *)wm_file_auth_document_token(s)
         : k == 3 ? (void *)wm_file_auth_anonymous()
                  : (void *)wm_file_auth_public_report();
}
static int auth_new(lua_State *L) {
  int k = (int)lua_tointeger(L, lua_upvalueindex(1));
  const char *s = k == 2 ? cstring(L, 1) : NULL;
  Value *v = value_new(L, &auth_type);
  v->aux = k;
  if (s) {
    v->secret = strdup(s);
    if (!v->secret)
      return invalid(L);
  }
  v->ptr = auth_create(k, s);
  if (!v->ptr)
    return invalid(L);
  return 1;
}
void *auth_snapshot(lua_State *L, int i) {
  Value *v = value_check(L, i, &auth_type);
  void *p = auth_create(v->aux, v->secret);
  if (!p)
    luaL_error(L, "webmania: local allocation failure");
  return p;
}
void model_snapshot(lua_State *L, Task *task, int slot, int i, const Type *t) {
  Value *v = value_check(L, i, t);
  char *s = t->json(v->ptr);
  if (!s)
    luaL_error(L, "webmania: local snapshot allocation failure");
  task->args[slot].release = t->destroy;
  task->args[slot].ptr =
      t->parse(s, strlen(s), task->owner->config, &task->error);
  free(s);
  if (!task->args[slot].ptr)
    luaL_error(L,
               "webmania: invalid typed snapshot or local validation failure");
}
static void owner_release(Owner *o) {
  if (!o || --o->refs)
    return;
  switch (o->scope) {
  case 0:
    wm_nfe_client_free(o->client);
    break;
  case 1:
    wm_reseller_client_free(o->client);
    break;
  case 2:
    wm_emitter_client_free(o->client);
    break;
  case 3:
    wm_monitor_client_free(o->client);
    break;
  case 4:
    wm_nfe_files_client_free(o->client);
    break;
  default:
    wm_emitter_files_client_free(o->client);
  }
  wm_config_free(o->config);
  free(o);
}
static void task_join(Task *t) {
  if (t->started && !t->joined) {
    pthread_join(t->thread, NULL);
    t->joined = true;
  }
}
static void owner_close(Owner *o) {
  if (!o || o->closed)
    return;
  o->closed = true;
  for (Task *t = o->tasks; t; t = t->next)
    if (t->cancel)
      wm_cancel_request(t->cancel);
  for (Task *t = o->tasks; t; t = t->next)
    task_join(t);
}
static int client_close(lua_State *L) {
  Client *c = luaL_checkudata(L, 1, CLIENT);
  if (c->owner) {
    owner_close(c->owner);
    owner_release(c->owner);
    c->owner = NULL;
  }
  return 0;
}
static int client_gc(lua_State *L) {
  Client *c = luaL_checkudata(L, 1, CLIENT);
  if (c->owner) {
    owner_release(c->owner);
    c->owner = NULL;
  }
  return 0;
}
Owner *owner_check(lua_State *L, int i, int scope) {
  Client *c = luaL_checkudata(L, i, CLIENT);
  if (!c->owner || c->owner->closed || c->owner->scope != scope)
    luaL_error(L, "webmania: wrong client scope or closed client");
  return c->owner;
}
static int client_new(lua_State *L) {
  int k = (int)lua_tointeger(L, lua_upvalueindex(1));
  Credential *c = NULL;
  if (!lua_isnoneornil(L, 1)) {
    c = luaL_checkudata(L, 1, CRED);
    if (!c->ptr || c->kind != (k == 4 ? 0 : k == 5 ? 2 : k))
      return invalid(L);
  } else if (k < 4)
    return invalid(L);
  Config *cfg = lua_isnoneornil(L, 2) ? NULL : luaL_checkudata(L, 2, CONFIG);
  Client *x = lua_newuserdatauv(L, sizeof(*x), 0);
  x->owner = NULL;
  luaL_setmetatable(L, CLIENT);
  Owner *o = calloc(1, sizeof(*o));
  if (!o)
    return invalid(L);
  x->owner = o;
  o->scope = k;
  o->refs = 1;
  o->config = config_clone(cfg);
  if (!o->config)
    return invalid(L);
  void *p = c ? c->ptr : NULL;
  switch (k) {
  case 0:
    o->client = wm_nfe_client_new(p, o->config);
    break;
  case 1:
    o->client = wm_reseller_client_new(p, o->config);
    break;
  case 2:
    o->client = wm_emitter_client_new(p, o->config);
    break;
  case 3:
    o->client = wm_monitor_client_new(p, o->config);
    break;
  case 4:
    o->client = wm_nfe_files_client_new(p, o->config);
    break;
  default:
    o->client = wm_emitter_files_client_new(p, o->config);
  }
  if (!o->client)
    return invalid(L);
  return 1;
}
static void *task_thread(void *p) {
  Task *t = p;
  t->invoke(t);
  atomic_store_explicit(&t->done, true, memory_order_release);
  return NULL;
}
Task *task_new(lua_State *L, Owner *o) {
  Task *t = lua_newuserdatauv(L, sizeof(*t), 0);
  memset(t, 0, sizeof(*t));
  atomic_init(&t->done, false);
  luaL_setmetatable(L, TASK);
  t->owner = o;
  o->refs++;
  t->next = o->tasks;
  o->tasks = t;
  t->cancel = wm_cancel_new();
  if (!t->cancel)
    luaL_error(L, "webmania: cancellation allocation failure");
  return t;
}
int task_launch(lua_State *L, Task *t) {
  if (pthread_create(&t->thread, NULL, task_thread, t))
    return fail(L, "thread creation failed");
  t->started = true;
  return 1;
}
static void result_free(Task *t) {
  if (!t->result)
    return;
  if (t->result_kind == 1)
    wm_file_response_free(t->result);
  else if (t->result_kind == 2)
    wm_file_or_redirect_free(t->result);
  else
    t->result_type->destroy(t->result);
  t->result = NULL;
}
static int task_close(lua_State *L) {
  Task *t = luaL_checkudata(L, 1, TASK);
  if (t->closed)
    return 0;
  t->closed = true;
  if (t->cancel)
    wm_cancel_request(t->cancel);
  task_join(t);
  result_free(t);
  wm_error_free(t->error);
  t->error = NULL;
  for (int i = 0; i < 5; i++) {
    free(t->args[i].text);
    t->args[i].text = NULL;
    if (t->args[i].release)
      t->args[i].release(t->args[i].ptr);
    t->args[i].ptr = NULL;
  }
  wm_cancel_free(t->cancel);
  t->cancel = NULL;
  if (t->owner) {
    Owner *o = t->owner;
    Task **link = &o->tasks;
    while (*link && *link != t)
      link = &(*link)->next;
    if (*link)
      *link = t->next;
    t->owner = NULL;
    owner_release(o);
  }
  return 0;
}
static int task_cancel(lua_State *L) {
  Task *t = luaL_checkudata(L, 1, TASK);
  if (t->cancel)
    wm_cancel_request(t->cancel);
  return 0;
}
static int error_close(lua_State *L) {
  Error *e = luaL_checkudata(L, 1, ERROR);
  wm_error_free(e->ptr);
  e->ptr = NULL;
  e->local_status = WM_INVALID;
  return 0;
}
static void push_local_error(lua_State *L, wm_status status) {
  Error *e = lua_newuserdatauv(L, sizeof(*e), 0);
  e->ptr = NULL;
  e->local_status = status;
  luaL_setmetatable(L, ERROR);
}
static int error_get(lua_State *L) {
  Error *e = luaL_checkudata(L, 1, ERROR);
  int k = (int)lua_tointeger(L, lua_upvalueindex(1));
  if (!e->ptr) {
    if (k == 0)
      lua_pushstring(L, e->local_status == WM_INVALID ? "validation"
                                                      : "local_allocation");
    else if (k == 1)
      lua_pushboolean(L, e->local_status != WM_INVALID);
    else if (k == 2)
      lua_pushinteger(L, 0);
    else if (k == 3 || k == 4)
      lua_pushnil(L);
    else
      lua_pushliteral(L, "Request failed; details redacted.");
    return 1;
  }
  if (k == 0)
    lua_pushstring(L, wm_error_kind(e->ptr));
  else if (k == 1)
    lua_pushboolean(L, wm_error_outcome_unknown(e->ptr));
  else if (k == 2)
    lua_pushinteger(L, wm_error_status(e->ptr));
  else if (k == 3) {
    const char *s = wm_error_reveal_location(e->ptr);
    if (s)
      lua_pushstring(L, s);
    else
      lua_pushnil(L);
  } else if (k == 4) {
    Value *v = value_new(L, &types[1]);
    v->ptr = wm_error_reveal_recovery(e->ptr);
    if (!v->ptr)
      lua_pushnil(L);
  } else
    lua_pushliteral(L, "Request failed; details redacted.");
  return 1;
}
static int file_close(lua_State *L) {
  File *f = luaL_checkudata(L, 1, FILEVALUE);
  if (f->kind == 1)
    wm_file_response_free(f->ptr);
  else
    wm_file_or_redirect_free(f->ptr);
  f->ptr = NULL;
  return 0;
}
/* Pending owns the C result independently of its Task/client. The payload
 * accessor returns a fresh nominal C copy on every call, guarded before C
 * allocates so a Lua allocation failure cannot strand that copy. */
static int pending_close(lua_State *L) {
  File *f = luaL_checkudata(L, 1, PENDING);
  wm_file_or_redirect_free(f->ptr);
  f->ptr = NULL;
  return 0;
}
static int pending_get(lua_State *L) {
  File *f = luaL_checkudata(L, 1, PENDING);
  if (!f->ptr)
    return invalid(L);
  int k = (int)lua_tointeger(L, lua_upvalueindex(1));
  if (k == 0)
    lua_pushinteger(L, wm_file_or_redirect_pending_status(f->ptr));
  else if (k == 1)
    lua_pushstring(L, wm_file_or_redirect_pending_media_type(f->ptr));
  else if (k == 2) {
    const Type *type = NULL;
    for (size_t i = 0; i < type_count; i++)
      if (!strcmp(types[i].name, "api2_emitter_files.NfsePdfPending")) {
        type = &types[i];
        break;
      }
    if (!type)
      return invalid(L);
    Value *v = value_new(L, type);
    v->ptr = wm_file_or_redirect_pending(f->ptr);
    if (!v->ptr)
      return invalid(L);
  } else if (k == 3)
    lua_pushliteral(L, "NfsePdfPending");
  else
    lua_pushboolean(L, 1);
  return 1;
}
static int file_get(lua_State *L) {
  File *f = luaL_checkudata(L, 1, FILEVALUE);
  if (!f->ptr)
    return invalid(L);
  int k = (int)lua_tointeger(L, lua_upvalueindex(1));
  if (k == 0) {
    lua_pushboolean(L, f->kind == 2 && wm_file_or_redirect_is_redirect(f->ptr));
    return 1;
  }
  if (k == 1) {
    const char *s =
        f->kind == 2 ? wm_file_or_redirect_reveal_location(f->ptr) : NULL;
    if (s)
      lua_pushstring(L, s);
    else
      lua_pushnil(L);
    return 1;
  }
  if (f->kind == 2) {
    if (wm_file_or_redirect_is_redirect(f->ptr)) {
      lua_pushnil(L);
      return 1;
    }
    File *child = lua_newuserdatauv(L, sizeof(*child), 0);
    child->ptr = NULL;
    child->kind = 1;
    luaL_setmetatable(L, FILEVALUE);
    child->ptr = wm_file_or_redirect_file(f->ptr);
    if (!child->ptr)
      return invalid(L);
    f = child;
  }
  if (k == 2) {
    size_t n;
    const unsigned char *b = wm_file_response_bytes(f->ptr, &n);
    lua_pushlstring(L, (const char *)b, n);
  } else if (k == 3)
    lua_pushinteger(L, wm_file_response_status(f->ptr));
  else
    lua_pushstring(L, k == 4 ? wm_file_response_media_type(f->ptr)
                             : wm_file_response_kind(f->ptr));
  return 1;
}
static int task_result(lua_State *L) {
  Task *t = luaL_checkudata(L, 1, TASK);
  if (t->closed || t->published)
    return fail(L, "task closed or result already consumed");
  bool wait = lua_tointeger(L, lua_upvalueindex(1)) != 0;
  if (!wait && !atomic_load_explicit(&t->done, memory_order_acquire)) {
    lua_pushboolean(L, 0);
    return 1;
  }
  task_join(t);
  if (!wait)
    lua_pushboolean(L, 1);
  if (t->status != WM_OK) {
    lua_pushnil(L);
    if (t->error) {
      Error *e = lua_newuserdatauv(L, sizeof(*e), 0);
      e->ptr = NULL;
      e->local_status = WM_INVALID;
      luaL_setmetatable(L, ERROR);
      e->ptr = t->error;
      t->error = NULL;
    } else {
      push_local_error(L, t->status);
    }
    t->published = true;
    return wait ? 2 : 3;
  }
  if (t->result_kind) {
    File *f = lua_newuserdatauv(L, sizeof(*f), 0);
    f->ptr = NULL;
    f->kind = t->result_kind;
    luaL_setmetatable(L, t->result_kind == 2 &&
                                 wm_file_or_redirect_is_pending(t->result)
                             ? PENDING
                             : FILEVALUE);
    f->ptr = t->result;
  } else {
    Value *v = value_new(L, t->result_type);
    v->ptr = t->result;
  }
  t->result = NULL;
  t->published = true;
  lua_pushnil(L);
  return wait ? 2 : 3;
}
static void metatable(lua_State *L, const char *n, lua_CFunction gc) {
  luaL_newmetatable(L, n);
  lua_pushcfunction(L, gc);
  lua_setfield(L, -2, "__gc");
  lua_pushcfunction(L, gc);
  lua_setfield(L, -2, "__close");
  lua_pushcfunction(L, redacted);
  lua_setfield(L, -2, "__tostring");
  lua_pushliteral(L, "webmania protected metatable");
  lua_setfield(L, -2, "__metatable");
  lua_pushvalue(L, -1);
  lua_setfield(L, -2, "__index");
}
static void method(lua_State *L, const char *n, lua_CFunction fn) {
  lua_pushcfunction(L, fn);
  lua_setfield(L, -2, n);
}
static void closure(lua_State *L, const char *n, lua_CFunction fn, int k) {
  lua_pushinteger(L, k);
  lua_pushcclosure(L, fn, 1);
  lua_setfield(L, -2, n);
}
int luaopen_webmania(lua_State *L) {
  metatable(L, VALUE, value_close);
  method(L, "__index", value_index);
  lua_pop(L, 1);
  metatable(L, CONFIG, config_close);
  method(L, "close", config_close);
  const char *cfg[] = {"set_worker_path",     "set_base_url",
                       "set_ca_pem",          "trust_file_origin",
                       "set_timeout_ms",      "set_max_response_bytes",
                       "set_max_header_bytes"};
  for (int i = 0; i < 7; i++)
    closure(L, cfg[i], config_set, i);
  lua_pop(L, 1);
  metatable(L, CRED, credential_close);
  method(L, "close", credential_close);
  lua_pop(L, 1);
  metatable(L, CLIENT, client_gc);
  method(L, "__close", client_close);
  method(L, "close", client_close);
  lua_pop(L, 1);
  metatable(L, TASK, task_close);
  method(L, "close", task_close);
  method(L, "cancel", task_cancel);
  closure(L, "poll", task_result, 0);
  closure(L, "await", task_result, 1);
  lua_pop(L, 1);
  metatable(L, ERROR, error_close);
  method(L, "close", error_close);
  const char *err[] = {"kind",
                       "outcome_unknown",
                       "status",
                       "reveal_location",
                       "reveal_recovery",
                       "message"};
  for (int i = 0; i < 6; i++)
    closure(L, err[i], error_get, i);
  lua_pop(L, 1);
  metatable(L, FILEVALUE, file_close);
  method(L, "close", file_close);
  const char *files[] = {"is_redirect", "reveal_location", "bytes",
                         "status",      "media_type",      "kind"};
  for (int i = 0; i < 6; i++)
    closure(L, files[i], file_get, i);
  lua_pop(L, 1);
  metatable(L, PENDING, pending_close);
  method(L, "close", pending_close);
  closure(L, "status", pending_get, 0);
  closure(L, "media_type", pending_get, 1);
  closure(L, "value", pending_get, 2);
  closure(L, "payload", pending_get, 2);
  closure(L, "kind", pending_get, 3);
  closure(L, "is_pending", pending_get, 4);
  lua_pop(L, 1);
  lua_newtable(L);
  method(L, "Config", config_new);
  method(L, "Number", number_new);
  method(L, "Json", json_new);
  method(L, "Map", map_new);
  const char *creds[] = {"CompanyCredentials", "ResellerCredentials",
                         "IssuerToken", "MonitorToken"};
  for (int i = 0; i < 4; i++)
    closure(L, creds[i], credential_new, i);
  const char *clients[] = {"NfeClient",      "ResellerClient",
                           "EmitterClient",  "MonitorClient",
                           "NfeFilesClient", "EmitterFilesClient"};
  for (int i = 0; i < 6; i++)
    closure(L, clients[i], client_new, i);
  lua_newtable(L);
  const char *auth[] = {"company", "issuer", "document_token", "anonymous",
                        "public_report"};
  for (int i = 0; i < 5; i++)
    closure(L, auth[i], auth_new, i);
  lua_setfield(L, -2, "FileAuth");
  lua_newtable(L);
  const char *scalar[] = {"text", "number", "boolean", "null"};
  for (int i = 0; i < 4; i++)
    closure(L, scalar[i], scalar_new, i);
  lua_setfield(L, -2, "Scalar");
  lua_newuserdatauv(L, 1, 0);
  lua_newtable(L);
  method(L, "__tostring", redacted);
  lua_pushliteral(L, "webmania null");
  lua_setfield(L, -2, "__metatable");
  lua_setmetatable(L, -2);
  lua_pushvalue(L, -1);
  lua_setfield(L, LUA_REGISTRYINDEX, "webmania.null");
  lua_setfield(L, -2, "null");
  register_generated(L);
  lua_pushliteral(L, "0.1.0-alpha.5");
  lua_setfield(L, -2, "version");
  return 1;
}
