#ifndef WEBMANIA_LUA_INTERNAL_H
#define WEBMANIA_LUA_INTERNAL_H
#include <lauxlib.h>
#include <lua.h>
#include <pthread.h>
#include <stdatomic.h>
#include <stdint.h>
#include <webmania/webmania.h>
typedef struct Value Value;
typedef struct Type Type;
typedef struct Task Task;
typedef struct Owner Owner;
typedef int (*field_fn)(lua_State *, Value *);
typedef struct Field {
  const char *name;
  field_fn set, get, presence, unset;
} Field;
struct Type {
  const char *name;
  void *(*create)(void);
  void (*destroy)(void *);
  char *(*json)(const void *);
  void *(*parse)(const char *, size_t, const wm_config *, wm_error **);
  const Field *fields;
  size_t nfields;
  int (*append)(lua_State *, Value *);
  int (*at)(lua_State *, Value *);
  size_t (*count)(const void *);
  bool extensible;
  wm_status (*extension_set)(void *, const char *, size_t, const wm_json *);
  wm_json *(*extension_get)(const void *, const char *, size_t);
};
struct Value {
  void *ptr;
  const Type *type;
  int aux;
  char *secret;
};
typedef struct Arg {
  char *text;
  int64_t integer;
  void *ptr;
  void (*release)(void *);
} Arg;
struct Task {
  pthread_t thread;
  atomic_bool done;
  bool started, joined, closed, published;
  Owner *owner;
  Task *next;
  wm_cancel *cancel;
  wm_error *error;
  wm_status status;
  void *result;
  const Type *result_type;
  int result_kind;
  Arg args[5];
  void (*invoke)(Task *);
};
struct Owner {
  void *client;
  wm_config *config;
  int scope;
  bool closed;
  unsigned refs;
  Task *tasks;
};
extern const Type types[];
extern const size_t type_count;
Value *value_new(lua_State *, const Type *);
Value *value_check(lua_State *, int, const Type *);
int invalid(lua_State *);
int push_status(lua_State *, wm_status);
int push_presence(lua_State *, wm_presence);
const char *strict_string(lua_State *, int, size_t *);
const char *cstring(lua_State *, int);
int64_t integer(lua_State *, int);
int boolean(lua_State *, int);
const wm_config *config_arg(lua_State *, int);
Task *task_new(lua_State *, Owner *);
int task_launch(lua_State *, Task *);
Owner *owner_check(lua_State *, int, int);
void *auth_snapshot(lua_State *, int);
void auth_free(void *);
void model_snapshot(lua_State *, Task *, int, int, const Type *);
void register_generated(lua_State *);
#endif
