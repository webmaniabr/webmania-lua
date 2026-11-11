#!/usr/bin/python3
"""Offline ownership/OOM companion; no transport and no projection opt-in."""
import json,struct,sys
r=sys.stdin.buffer
h=r.read(4)
if len(h)!=4:raise SystemExit(2)
n=struct.unpack('>I',h)[0];v=json.loads(r.read(n));assert 'projection_hints' not in v
if v['action']=='validate':result={'kind':'json','value':json.loads(v['value_json'])}
elif v['operation']=='fileGetNfsePdf':result={'kind':'pending','status':200,'media_type':'application/json','value':{'msg':'queued\0á😀','extra':False}}
else:result={'kind':'file','status':200,'media_type':'text/html','file_kind':'Html','bytes_hex':b'\0\xff<script>opaque</script>'.hex()}
b=json.dumps({'protocol':1,'ok':True,'result':result},separators=(',',':')).encode();sys.stdout.buffer.write(struct.pack('>I',len(b))+b);sys.stdout.buffer.flush()
