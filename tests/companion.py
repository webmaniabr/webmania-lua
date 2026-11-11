#!/usr/bin/python3
"""Offline lifecycle companion. Synthetic data only; no HTTP."""
import json,struct,sys,time,select,pathlib
r=sys.stdin.buffer
h=r.read(4)
if len(h)!=4:sys.exit(2)
n=struct.unpack('>I',h)[0]
v=json.loads(r.read(n))
mode=pathlib.Path(sys.argv[0]).stem
if mode=='slow':
 # Real C cancel/EOF controller may send C or terminate; no fake Lua callback.
 while True:
  ready,_,_=select.select([r],[],[],.1)
  if ready:
   if r.read(1) in (b'C',b''):break
 reply={'protocol':1,'ok':False,'error':{'kind':'cancelled','message':'Call cancelled.'}}
 b=json.dumps(reply,separators=(',',':')).encode();sys.stdout.buffer.write(struct.pack('>I',len(b))+b);sys.stdout.buffer.flush();sys.exit(0)
if v['action']=='validate':
 value=json.loads(v['value_json']);result={'kind':'json','value':value}
else:
 good=v['credentials']['consumer_key']=='secret-marker' and v['config']['base_url']=='http://127.0.0.1:9'
 result={'kind':'json','value':{'status':'online' if good else 'bad'}}
 if v['operation']=='nfeGetDocument':
  q=json.loads(v['query_json']);assert q['uuid']=='00000000-0000-4000-8000-000000000001'
  cases=json.loads((pathlib.Path(__file__).resolve().parent/'fixtures/operations.json').read_text())['cases']
  result={'kind':'json','value':next(c['response'] for c in cases if c['operation']==v['operation'])}
reply={'protocol':1,'ok':True,'result':result}
b=json.dumps(reply,separators=(',',':')).encode();sys.stdout.buffer.write(struct.pack('>I',len(b))+b);sys.stdout.buffer.flush()
