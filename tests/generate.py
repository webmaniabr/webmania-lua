#!/usr/bin/env python3
"""Generate public Lua consumers; fixtures are synthetic contract evidence."""
import json,pathlib,runpy
R=pathlib.Path(__file__).resolve().parents[1]
meta=json.loads((R/'metadata/api-metadata.json').read_text())
cases={x['operation']:x for x in json.loads((R/'tests/fixtures/operations.json').read_text())['cases']}
def lit(s):
 # Lua quoted bytes: \" and \\ for quote and backslash, three-digit decimal escapes otherwise.
 return '"'+''.join(chr(b) if 32<=b<=126 and b not in (34,92) else '\\'+chr(b) if b in (34,92) else '\\%03d'%b for b in s.encode())+'"'
def jlit(x):return lit(json.dumps(x,ensure_ascii=False,separators=(',',':')))
lines=['local w=require("webmania")','local cfg=w.Config():set_base_url(arg[2]):set_worker_path(arg[4])','local f=assert(io.open(arg[3],"rb"));cfg:set_ca_pem(f:read("a"));f:close();cfg:trust_file_origin(arg[2])','local credentials={w.CompanyCredentials("synthetic-company-key","synthetic-secret","synthetic-token","synthetic-secret2"),w.ResellerCredentials("synthetic-reseller-key","synthetic-secret","synthetic-token","synthetic-secret2"),w.IssuerToken("synthetic-issuer"),w.MonitorToken("synthetic-monitor")}','local clients={Nfe=w.NfeClient(credentials[1],cfg),Reseller=w.ResellerClient(credentials[2],cfg),Emitter=w.EmitterClient(credentials[3],cfg),Monitor=w.MonitorClient(credentials[4],cfg),NfeFiles=w.NfeFilesClient(credentials[1],cfg),EmitterFiles=w.EmitterFilesClient(credentials[3],cfg)}','local which=assert(math.tointeger(arg[1])); local task','if false then']
for i,o in enumerate(meta['operations']):
 c=cases[o['id']];lines+=['elseif which=='+str(i)+' then']
 args=['clients.'+o['scope']]
 for p in o['params']:
  name,t=p['name'],p['type']
  if name in ('query','body'):
   _,_,mod,n=t[1:].split('::');lines+=['local '+name+',error=w.models['+lit(mod+'.'+n)+'].from_json('+jlit(c['query'] if name=='query' else c['request'])+',cfg);assert('+name+',error and error:kind())'];args.append(name)
  elif name=='auth':args.append('w.FileAuth.'+('public_report' if o['id']=='fiscalDownloadReport' else 'company' if o['scope']=='NfeFiles' else 'issuer')+'()')
  elif t=='&str':args.append(lit(str(c['path_params'][name])))
  else:args.append(str(c['path_params'][name]))
 if not o['enabled']:lines+=['local ok,err=pcall(w.'+o['id']+','+','.join(args)+');assert(not ok and type(err)=="string" and err:find("webmania capability: operation not available in this SDK release",1,true),tostring(err));io.write("blocked");os.exit(0)']
 else:lines+=['task=w.'+o['id']+'('+','.join(args)+')']
lines+=['else error("unknown case") end','local value,error=task:await();assert(value,error and error:kind());if value.bytes then local bytes=assert(value:bytes());io.write((bytes:gsub(".",function(c)return string.format("%02x",string.byte(c))end))) else io.write(value:to_json()) end','task:close();value:close();for _,c in pairs(clients) do c:close() end;for _,c in ipairs(credentials) do c:close() end;cfg:close()']
(R/'tests/matrix.lua').write_text('\n'.join(lines)+'\n')
# Typed sample inventory with model construction and semantic projection evidence.
corpus=json.loads((R/'tests/fixtures/model-corpus.json').read_text())['cases']
L=['local w=require("webmania")','local cfg=w.Config():set_worker_path(assert(arg[1]))','local n,fields,arrays,variants=0,0,0,0', '''local function array_roundtrip(x)
 if type(x)~='userdata' or x==w.null or not x:type():match('^wm_array_') then return end
 local copy=w.models[x:type()].new()
 for i=1,x:count() do local element=x:at(i);copy:append(element);if type(element)=='userdata' and element~=w.null then element:close() end end
 assert(copy:to_json()==x:to_json());assert(x:at(x:count()+1)==nil);copy:close();arrays=arrays+1
end''']
modelmap={m['module']+'::'+m['name']:m for m in meta['models']}
for c in corpus:
 m=modelmap[c['model']];klass='w.models['+lit(c['model'].replace('::','.'))+']'
 L+=['do local v,e='+klass+'.from_json('+jlit(c['value'])+',cfg);assert(v,e and e:kind());local before=v:to_json();assert(before);']
 if m['kind']=='struct':
  for f in m['fields']:
   field=lit(f['name'])
   L+=['do local x=v:get('+field+');if x~=nil then assert(v:presence('+field+')~="missing");v:set('+field+',x);assert(v:to_json()==before);array_roundtrip(x);if type(x)=="userdata" and x~=w.null then x:close() end else assert(v:presence('+field+')=="missing") end;fields=fields+1 end']
   if 'Nullable<' in f['type']:
    L+=['do local previous=v:get('+field+');v:set('+field+',w.null);assert(v:get('+field+')==w.null and v:presence('+field+')=="null");'+('if previous==nil then v:unset('+field+') else v:set('+field+',previous) end;' if f['type'].startswith('Option<') else 'v:set('+field+',previous);')+'assert(v:to_json()==before);if type(previous)=="userdata" and previous~=w.null then previous:close() end end']
 else:
  L+=['local matched=false']
  for f in m['fields']:
   field=lit(f['name']);ctor=klass+'['+lit('from_'+f['name'])+']'
   L+=['if not matched then local ok,x=pcall(v.get,v,'+field+',cfg);if ok then local copy='+ctor+'('+('' if f['type']=='Null' else 'x')+');assert(copy:to_json()==before);copy:close();array_roundtrip(x);if type(x)=="userdata" and x~=w.null then x:close() end;matched=true;variants=variants+1 end end']
  L+=['assert(matched,"union projection")']
 L+=['v:close();n=n+1 end']
L+=['assert(n=='+str(len(meta['models']))+');print(n.." nominal models, "..fields.." field roundtrips, "..arrays.." typed array copies, "..variants.." named union constructors PASS")'];(R/'tests/models.lua').write_text('\n'.join(L)+'\n')
# Map exact pinned semantic pointers to the same public nominal types.
lookup={(m['module'],m['pointer']):m for m in meta['models'] if m['pointer']}
semantic=json.loads((R/'tests/fixtures/semantic_cases.json').read_text())['cases'];mapped=[]
for c in semantic:
 key=(c['module'],c['pointer'])
 if key in lookup:mapped.append((c,lookup[key]))
S=['local w=require("webmania")','local cfg=w.Config():set_worker_path(assert(arg[1]))','local n=0']
for c,m in mapped:S+=['do local v,e=w.models['+lit(m['module']+'.'+m['name'])+'].from_json('+jlit(c['instance'])+',cfg);assert((v~=nil)=='+str(c['valid']).lower()+');if v then v:close() elseif e then e:close() end;n=n+1 end']
S+=['print(n.." mapped semantic cases PASS")'];(R/'tests/semantic.lua').write_text('\n'.join(S)+'\n')
# Lua wrapper is conventional executable entry for reusable fixture harness.
print('Generated',len(meta['operations']),'Lua matrix cases;',len(corpus),'models;',len(mapped),'mapped semantics')
# Exercise every array constructor and copy, rather than only arrays populated
# by the model corpus. Values are typed and retain exact scalar representations.
g=runpy.run_path(str(R/'scripts/generate.py'))
values={c['model']:c['value'] for c in corpus}
def sample(mod,t):
 t=g['unwrap'](t)
 if t.startswith('crate::models::'):_,_,mod,t=t.split('::')
 if t.startswith('Vec<'):
  inner=t[4:-1];name=g['cn'](mod,t)
  return '(function() local a=w.models['+lit(name)+'].new();local v='+sample(mod,inner)+';a:append(v);dispose(v);return a end)()'
 if t=='String':return lit('exact\0á😀')
 if t=='i64':return 'math.mininteger'
 if t=='bool':return 'false'
 if t=='Number':return "w.Number('9007199254740993.000000000000000001')"
 if t=='Scalar':return "w.Scalar.text('scalar\\0exact')"
 if t=='Value':return "w.Json('{\"false\":false,\"null\":null}')"
 if t=='Map':return "w.Map('{\"false\":false,\"null\":null}')"
 return 'assert(w.models['+lit(mod+'.'+t)+'].from_json('+jlit(values[mod+'::'+t])+',cfg))'
T=['local w=require("webmania")','local cfg=w.Config():set_worker_path(assert(arg[1]))','local function dispose(v) if type(v)=="userdata" and v~=w.null then v:close() end end','local n=0']
for name,(mod,t) in g['arrays'].items():
 T+=['do local a=w.models['+lit(name)+'].new();assert(a:count()==0);local v='+sample(mod,t)+';a:append(v);local before=a:to_json();dispose(v);assert(a:count()==1);local x=a:at(1);local b=w.models['+lit(name)+'].new();b:append(x);dispose(x);assert(b:to_json()==before);assert(a:at(2)==nil);a:close();assert(b:to_json()==before);b:close();n=n+1 end']
T+=['assert(n==255);cfg:close();print(n.." typed array constructors, appends, independent getters and copies PASS")']
(R/'tests/arrays.lua').write_text('\n'.join(T)+'\n')
