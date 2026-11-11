#!/usr/bin/env python3
"""Deterministic Lua facade over the public frozen C ABI; no HTTP engine."""
import json,pathlib,re,hashlib
R=pathlib.Path(__file__).resolve().parents[1]
def write_generated(path,text):
 if not path.exists() or path.read_text()!=text:path.write_text(text)
metadata_bytes=(R/'metadata/api-metadata.json').read_bytes()
locked=json.loads((R/'dependency-lock.json').read_text())
if hashlib.sha256(metadata_bytes).hexdigest()!=locked['api_metadata_sha256']:raise ValueError('Frozen C public metadata mismatch')
meta=json.loads(metadata_bytes)
if len(meta['models'])!=1258 or len(meta['operations'])!=103:raise ValueError('Frozen public inventory mismatch')
models=meta['models'];arrays={}
def snake(s):
 s=re.sub(r'([A-Z]+)([A-Z][a-z])',r'\1_\2',s)
 return re.sub(r'([a-z0-9])([A-Z])',r'\1_\2',s).lower()
def unwrap(t):
 while any(t.startswith(x+'<') for x in ('Option','Nullable','Box')):t=t[t.index('<')+1:-1]
 return t
def cn(mod,t):
 t=unwrap(t)
 if t.startswith('crate::models::'):_,_,mod,t=t.split('::')
 if t.startswith('Vec<'):
  inner=t[4:-1];n='wm_array_'+mod+'_'+cn(mod,inner).removeprefix('wm_');arrays[n]=(mod,inner);return n
 return {'String':'char','i64':'int64_t','bool':'bool','Number':'wm_number','Scalar':'wm_scalar','Value':'wm_json','Map':'wm_map'}.get(t,'wm_'+mod+'_'+snake(t))
for m in models:
 for f in m['fields']:
  if f['type']!='Null':cn(m['module'],f['type'])
for o in meta['operations']:
 if o['returns'] not in ('crate::FileResponse','crate::FileOrRedirect'):cn(o['module'],o['returns'])
names=['wm_number','wm_json','wm_map','wm_scalar']+[cn(m['module'],m['name']) for m in models]+list(arrays)
ids={n:i for i,n in enumerate(names)}
def ref(n):return '&types['+str(ids[n])+']'
def funcfield(s):return 'field_'+s if s in 'auto case const continue default do else enum extern float for goto if inline int long register restrict return short signed sizeof static struct switch typedef union unsigned void volatile while'.split() else s
C=['/* Generated from frozen C public model metadata. */','#include "internal.h"','#include <stdlib.h>','#include <string.h>']
registrations=[];desc=[]
def adapters(n,idx,create=False,parse=False,ext=False,count=False):
 base='type'+str(idx)
 C.append('static void '+base+'_free(void*p){'+n+'_free(p);}')
 C.append('static char*'+base+'_json(const void*p){return '+n+'_to_json(p);}')
 if create:C.append('static void*'+base+'_new(void){return '+n+'_new();}')
 if parse:C.append('static void*'+base+'_parse(const char*s,size_t n,const wm_config*c,wm_error**e){return '+n+'_from_json(s,n,c,e);}')
 if count:C.append('static size_t '+base+'_count(const void*p){return '+n+'_count(p);}')
 if ext:
  C.append('static wm_status '+base+'_extension_set(void*p,const char*s,size_t n,const wm_json*v){return '+n+'_set_extension_n(p,s,n,v);}')
  C.append('static wm_json*'+base+'_extension_get(const void*p,const char*s,size_t n){return '+n+'_get_extension_n(p,s,n);}')
 return base
def read(mod,t,index=3):
 b=unwrap(t)
 if b=='String':return 'strict_string(L,'+str(index)+',&length)'
 if b=='i64':return 'integer(L,'+str(index)+')'
 if b=='bool':return 'boolean(L,'+str(index)+')'
 return 'value_check(L,'+str(index)+','+ref(cn(mod,t))+')->ptr'
def output(mod,t,call,length=None,union=False):
 b=unwrap(t);n=cn(mod,t)
 if b=='String':return 'const char*out=NULL;wm_status s='+call+';if(s==WM_ABSENT){lua_pushnil(L);return 1;}if(s==WM_NULL){lua_getfield(L,LUA_REGISTRYINDEX,"webmania.null");return 1;}if(s!=WM_OK)return invalid(L);lua_pushlstring(L,out,'+(length or 'strlen(out)')+');return 1;'
 if b in ('i64','bool'):
  return n+' out=0;wm_status s='+call+';if(s==WM_ABSENT){lua_pushnil(L);return 1;}if(s==WM_NULL){lua_getfield(L,LUA_REGISTRYINDEX,"webmania.null");return 1;}if(s!=WM_OK)return invalid(L);'+('if((int64_t)(lua_Integer)out!=out)return invalid(L);lua_pushinteger(L,(lua_Integer)out);' if b=='i64' else 'lua_pushboolean(L,out);')+'return 1;'
 return 'Value*r=value_new(L,'+ref(n)+');'+n+'*out=NULL;wm_status s='+call+';r->ptr=out;if(s==WM_ABSENT||s==WM_NULL){lua_pop(L,1);if(s==WM_ABSENT)lua_pushnil(L);else lua_getfield(L,LUA_REGISTRYINDEX,"webmania.null");return 1;}if(s!=WM_OK)return invalid(L);return 1;'
for m in models:
 mod=m['module'];n=cn(mod,m['name']);idx=ids[n];entries=[]
 ext=m['kind']=='struct' and bool(m['pointer'])
 adapter=adapters(n,idx,m['kind']=='struct',True,ext)
 create=adapter+'_new' if m['kind']=='struct' else 'NULL'
 for j,f in enumerate(m['fields']):
  field,t=f['name'],f['type'];fn=funcfield(field);base='f'+str(idx)+'_'+str(j);b=unwrap(t)
  if m['kind']=='struct':
   setter=n+'_set_'+fn;v=read(mod,t);extra='size_t length=0;' if b=='String' else ''
   if b=='String':extra+='const char*text='+v+';';v='text'
   call=setter+('_n' if b=='String' else '')+'(v->ptr,'+v+(',length' if b=='String' else '')+')'
   null='if(lua_rawequal(L,3,lua_upvalueindex(2)))return push_status(L,'+setter+'_null(v->ptr));' if 'Nullable<' in t else ''
   # Null sentinel is checked without invoking any metamethod.
   null='lua_getfield(L,LUA_REGISTRYINDEX,"webmania.null");int isnull=lua_rawequal(L,3,-1);lua_pop(L,1);if(isnull)return push_status(L,'+setter+'_null(v->ptr));' if 'Nullable<' in t else ''
   C.append('static int '+base+'_s(lua_State*L,Value*v){'+null+extra+'return push_status(L,'+call+');}')
   getcall=n+'_get_'+fn+'(v->ptr,&out)'
   C.append('static int '+base+'_g(lua_State*L,Value*v){'+output(mod,t,getcall,n+'_length_'+fn+'(v->ptr)' if b=='String' else None)+'}')
   C.append('static int '+base+'_p(lua_State*L,Value*v){return push_presence(L,'+n+'_presence_'+fn+'(v->ptr));}')
   un='NULL'
   if t.startswith('Option<'):
    C.append('static int '+base+'_u(lua_State*L,Value*v){return push_status(L,'+n+'_unset_'+fn+'(v->ptr));}');un=base+'_u'
   entries.append('{'+json.dumps(field)+','+','.join([base+'_s',base+'_g',base+'_p',un])+'}')
  else:
   if t=='Null':call=n+'_from_'+fn+'()'
   else:
    v=read(mod,t,1);call=n+'_from_'+fn+('_n' if b=='String' else '')+'('+v+(',length' if b=='String' else '')+')'
   prefix='size_t length=0;const char*text=strict_string(L,1,&length);' if b=='String' else ''
   if b=='String':call=call.replace('strict_string(L,1,&length)','text')
   C.append('static int '+base+'_ctor(lua_State*L){'+prefix+'Value*r=value_new(L,'+ref(n)+');r->ptr='+call+';if(!r->ptr)return invalid(L);return 1;}')
   registrations.append('lua_pushcfunction(L,'+base+'_ctor);lua_setfield(L,-2,"from_'+field+'");')
   # Union projection uses C semantic checking against pinned backend.
   if t=='Null':body='const wm_config*cfg=config_arg(L,3);wm_error*e=NULL;wm_status s='+n+'_get_'+fn+'(v->ptr,cfg,&e);wm_error_free(e);if(s!=WM_OK)return invalid(L);lua_getfield(L,LUA_REGISTRYINDEX,"webmania.null");return 1;'
   else:
    getcall=n+'_get_'+fn+'(v->ptr,cfg,&out,&e)';body='const wm_config*cfg=config_arg(L,3);wm_error*e=NULL;'+output(mod,t,getcall,n+'_length_'+fn+'(v->ptr)' if b=='String' else None)
    # Always release the independently allocated C error, including failure.
    body=body.replace(';if(s==WM_ABSENT',';wm_error_free(e);if(s==WM_ABSENT')
   C.append('static int '+base+'_g(lua_State*L,Value*v){'+body+'}')
   entries.append('{'+json.dumps(field)+',NULL,'+base+'_g,NULL,NULL}')
 C.append('static const Field fields'+str(idx)+'[]={'+(','.join(entries) if entries else '{NULL,NULL,NULL,NULL,NULL}')+'};')
 desc.append('{'+json.dumps(mod+'.'+m['name'])+','+create+','+adapter+'_free,'+adapter+'_json,'+adapter+'_parse,fields'+str(idx)+','+str(len(entries))+',NULL,NULL,NULL,'+('true,'+adapter+'_extension_set,'+adapter+'_extension_get' if ext else 'false,NULL,NULL')+'}')
 registrations.append('@'+str(idx)+'@')
for n,(mod,t) in arrays.items():
 idx=ids[n];b=unwrap(t);v=read(mod,t,2)
 adapter=adapters(n,idx,True,False,False,True)
 prefix='size_t length=0;const char*text='+v+';' if b=='String' else ''
 if b=='String':v='text'
 null='lua_getfield(L,LUA_REGISTRYINDEX,"webmania.null");int isnull=lua_rawequal(L,2,-1);lua_pop(L,1);if(isnull)return push_status(L,'+n+'_append_null(v->ptr));' if 'Nullable<' in t else ''
 C.append('static int a'+str(idx)+'_append(lua_State*L,Value*v){'+null+prefix+'return push_status(L,'+n+'_append'+('_n' if b=='String' else '')+'(v->ptr,'+v+(',length' if b=='String' else '')+'));}')
 C.append('static int a'+str(idx)+'_at(lua_State*L,Value*v){int64_t i=integer(L,2);if(i<1)return invalid(L);'+output(mod,t,n+'_get(v->ptr,(size_t)(i-1),&out)',n+'_length_at(v->ptr,(size_t)(i-1))' if b=='String' else None)+'}')
 desc.append('{'+json.dumps(n)+','+adapter+'_new,'+adapter+'_free,'+adapter+'_json,NULL,NULL,0,a'+str(idx)+'_append,a'+str(idx)+'_at,'+adapter+'_count,false,NULL,NULL}')
C+=['static void number_free(void*p){wm_number_free(p);}','static void json_free(void*p){wm_json_free(p);}','static char*json_json(const void*p){return wm_json_to_string(p);}','static void*map_new(void){return wm_map_new();}','static void map_free(void*p){wm_map_free(p);}','static char*map_json(const void*p){return wm_map_to_json(p);}','static size_t map_count(const void*p){return wm_map_count(p);}','static wm_status map_set(void*p,const char*k,size_t n,const wm_json*v){return wm_map_set_n(p,k,n,v);}','static wm_json*map_get(const void*p,const char*k,size_t n){return wm_map_get_n(p,k,n);}','static void scalar_free(void*p){wm_scalar_free(p);}','static char*scalar_json(const void*p){return wm_scalar_to_json(p);}']
core=['{"Number",NULL,number_free,NULL,NULL,NULL,0,NULL,NULL,NULL,false,NULL,NULL}', '{"Json",NULL,json_free,json_json,NULL,NULL,0,NULL,NULL,NULL,false,NULL,NULL}', '{"Map",map_new,map_free,map_json,NULL,NULL,0,NULL,NULL,map_count,true,map_set,map_get}', '{"Scalar",NULL,scalar_free,scalar_json,NULL,NULL,0,NULL,NULL,NULL,false,NULL,NULL}']
C+=['const Type types[]={'+',\n'.join(core+desc)+'};','const size_t type_count=sizeof(types)/sizeof(types[0]);']
# Operation thunks own copied text and parse models without touching the Lua VM.
scopes={'NfeClient':0,'ResellerClient':1,'EmitterClient':2,'MonitorClient':3,'NfeFilesClient':4,'EmitterFilesClient':5}
opsreg=[]
for oi,o in enumerate(meta['operations']):
 args=['t->owner->client'];cleanup=[];start=[];pre=[]
 if not o['enabled']:
  C.append('static int op'+str(oi)+'(lua_State*L){(void)L;return luaL_error(L,"webmania capability: operation not available in this SDK release");}')
 else:
  for j,p in enumerate(o['params']):
   pn,t=p['name'],p['type'];li=j+2
   if t.startswith('&crate::models::'):
    n=cn(o['module'],t[1:]);start.append('model_snapshot(L,t,'+str(j)+','+str(li)+','+ref(n)+');')
    args.append('t->args['+str(j)+'].ptr')
   elif t=='&crate::FileAuth':
    start.append('t->args['+str(j)+'].release=auth_free;t->args['+str(j)+'].ptr=auth_snapshot(L,'+str(li)+');');args.append('t->args['+str(j)+'].ptr')
   elif t=='&str':start.append('t->args['+str(j)+'].text=strdup(cstring(L,'+str(li)+'));if(!t->args['+str(j)+'].text)return invalid(L);');args.append('t->args['+str(j)+'].text')
   elif t=='i64':start.append('t->args['+str(j)+'].integer=integer(L,'+str(li)+');');args.append('t->args['+str(j)+'].integer')
  ret=o['returns'];rn={'crate::FileResponse':'wm_file_response','crate::FileOrRedirect':'wm_file_or_redirect'}.get(ret) or cn(o['module'],ret)
  # Variables initialized before any goto, making all partial parses cleanup-safe.
  decl=[];pre2=[]
  for p in pre:
   a,b=p.split('=',1);var=a.split('*')[-1];decl.append(a+'=NULL;');pre2.append(var+'='+b)
  C.append('static void invoke'+str(oi)+'(Task*t){'+rn+'*result=NULL;'+''.join(decl)+''.join(pre2)+'t->status=wm_'+snake(o['id'])+'('+','.join(args+['t->cancel','&result','&t->error'])+');t->result=result;'+('done:' if pre else '')+''.join(cleanup)+';}')
  # Ensure invalid args cannot strand a native task or borrowed client.
  C.append('static int op'+str(oi)+'(lua_State*L){if(lua_gettop(L)!='+str(1+len(o['params']))+')return luaL_error(L,"webmania: operation argument count");Owner*o=owner_check(L,1,'+str(scopes[o['client']])+');Task*t=task_new(L,o);'+''.join(start)+'t->invoke=invoke'+str(oi)+';'+('t->result_type='+ref(rn)+';' if ret not in ('crate::FileResponse','crate::FileOrRedirect') else 't->result_kind='+('1' if ret=='crate::FileResponse' else '2')+';')+'return task_launch(L,t);}')
 opsreg.append('lua_pushcfunction(L,op'+str(oi)+');lua_setfield(L,-2,'+json.dumps(o['id'])+');')
C.append('extern int class_new(lua_State*);extern int class_parse(lua_State*);')
C.append('void register_generated(lua_State*L){lua_newtable(L);')
pending=[]
for x in registrations:
 if x.startswith('@'):
  idx=int(x.strip('@'));m=models[idx-4];n=names[idx]
  C.append('lua_newtable(L);lua_pushinteger(L,'+str(idx)+');lua_pushcclosure(L,class_new,1);lua_setfield(L,-2,"new");lua_pushinteger(L,'+str(idx)+');lua_pushcclosure(L,class_parse,1);lua_setfield(L,-2,"from_json");'+''.join(pending)+'lua_pushvalue(L,-1);lua_setfield(L,-3,'+json.dumps(n)+');lua_setfield(L,-2,'+json.dumps(m['module']+'.'+m['name'])+');');pending=[]
 else:pending.append(x)
for n in arrays:
 C.append('lua_newtable(L);lua_pushinteger(L,'+str(ids[n])+');lua_pushcclosure(L,class_new,1);lua_setfield(L,-2,"new");lua_setfield(L,-2,'+json.dumps(n)+');')
C.append('lua_setfield(L,-2,"models");'+''.join(opsreg)+'}')
write_generated(R/'src/generated.c','\n'.join(C)+'\n')
# Lua Language Server annotations are a shipped, nonexecuted nominal API inventory.
A=['---@meta','---@class webmania.Config','---@class webmania.Null','---@class webmania.Error','---@class webmania.Model','---@field close fun(self:webmania.Model)','---@field to_json fun(self:webmania.Model):string','---@field type fun(self:webmania.Model):string','---@class webmania.Number:webmania.Model','---@class webmania.Json:webmania.Model','---@class webmania.Map:webmania.Model','---@class webmania.Scalar:webmania.Model','---@class webmania.Task','---@field close fun(self:webmania.Task)','---@field cancel fun(self:webmania.Task)','---@field poll fun(self:webmania.Task):boolean,any,webmania.Error?','---@field await fun(self:webmania.Task):any,webmania.Error?']
def annotation(mod,t):
 if t.startswith('Option<'):return annotation(mod,t[7:-1])+'|nil'
 if t.startswith('Nullable<'):return annotation(mod,t[9:-1])+'|webmania.Null'
 if t.startswith('Box<'):return annotation(mod,t[4:-1])
 if t.startswith('crate::models::'):_,_,mod,t=t.split('::')
 if t.startswith('Vec<'):return 'webmania.'+cn(mod,t)
 return {'String':'string','i64':'integer','bool':'boolean','Number':'webmania.Number','Scalar':'webmania.Scalar','Map':'webmania.Map','Value':'webmania.Json','Null':'webmania.Null'}.get(t,'webmania.'+mod+'.'+t)
for m in models:
 klass='webmania.'+m['module']+'.'+m['name'];A.append('---@class '+klass+':webmania.Model')
 for f in m['fields']:
  field,t=f['name'],f['type'];a=annotation(m['module'],t)
  A.append('---@field get_'+field+' fun(self:'+klass+(', config?:webmania.Config' if m['kind']=='enum' else '')+'):'+a)
  if m['kind']=='struct':
   A+=['---@field set_'+field+' fun(self:'+klass+', value:'+a+'):boolean','---@field presence_'+field+' fun(self:'+klass+'):"missing"|"null"|"present"']
   if t.startswith('Option<'):A.append('---@field unset_'+field+' fun(self:'+klass+'):boolean')
 A+=['---@class '+klass+'Constructor','---@field from_json fun(json:string, config?:webmania.Config):'+klass+'?,webmania.Error?']
 if m['kind']=='struct':A.append('---@field new fun():'+klass)
 else:
  for f in m['fields']:A.append('---@field from_'+f['name']+' fun('+('' if f['type']=='Null' else 'value:'+annotation(m['module'],f['type']))+'):'+klass)
for n,(mod,t) in arrays.items():A+=['---@class webmania.'+n+':webmania.Model','---@field append fun(self:webmania.'+n+', value:'+annotation(mod,t)+'):boolean','---@field at fun(self:webmania.'+n+', index:integer):'+annotation(mod,t)+'|nil','---@field count fun(self:webmania.'+n+'):integer']
A+=['---@class webmania.File','---@field close fun(self:webmania.File)','---@field bytes fun(self:webmania.File):string?','---@field kind fun(self:webmania.File):string','---@field status fun(self:webmania.File):integer','---@field media_type fun(self:webmania.File):string','---@class webmania.NfsePdfPending','---@field close fun(self:webmania.NfsePdfPending)','---@field is_pending fun(self:webmania.NfsePdfPending):true','---@field kind fun(self:webmania.NfsePdfPending):"NfsePdfPending"','---@field status fun(self:webmania.NfsePdfPending):integer','---@field media_type fun(self:webmania.NfsePdfPending):string','---@field value fun(self:webmania.NfsePdfPending):webmania.api2_emitter_files.NfsePdfPending','---@field payload fun(self:webmania.NfsePdfPending):webmania.api2_emitter_files.NfsePdfPending','local M = {}','M.models = {}']
for m in models:A+=['---@type webmania.'+m['module']+'.'+m['name']+'Constructor','M.models['+json.dumps(m['module']+'.'+m['name'])+'] = {}']
for o in meta['operations']:
 for p in o['params']:A.append('---@param '+p['name']+' '+('string' if p['type']=='&str' else 'integer' if p['type']=='i64' else 'userdata' if p['type']=='&crate::FileAuth' else annotation(o['module'],p['type'][1:])))
 A+=['---@return webmania.Task','function M.'+o['id']+'(client'+''.join(', '+p['name'] for p in o['params'])+') end']
A+=['return M'];write_generated(R/'lua/webmania_annotations.lua','\n'.join(A)+'\n')
print('Generated',len(models),'nominal models,',len(arrays),'arrays and',len(meta['operations']),'named operations')
