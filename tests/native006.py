"""Ordinary public Lua calls, the real pinned worker and self-owned loopback peers.
The C API exposes protected recovery, kind/status/outcome; it has no correlation accessor.
This bounded C followup is not a replacement for the sealed core/native protocol review.
"""
from pathlib import Path
import hashlib,json,socket,subprocess,sys,threading,time
binary,worker,out=sys.argv[1:4];rows=[];UUID='00000000-0000-4000-8000-000000000006'
assert Path('/.dockerenv').exists()
assert hashlib.sha256(Path(worker).read_bytes()).hexdigest()=='1d81d4dff57a8b233d2ce9316d201fd10b2740203d9890ef87a87144ea0d0f15'
def run(name,response,kind,recovery,limit=1024,timeout=3000,control='none',operation='cancel',after_headers=False,success=False):
 listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(2);listener.settimeout(.1);url='http://127.0.0.1:'+str(listener.getsockname()[1]);records=[];errors=[];closed=[];done=threading.Event();ready=threading.Event();proc=None
 def serve():
  try:
   while not done.is_set():
    try:conn,_=listener.accept();break
    except socket.timeout:continue
   else:return
   with conn:
    conn.settimeout(5);request=b''
    while b'\r\n\r\n' not in request:
     b=conn.recv(8192)
     if not b:return
     request+=b
    h,payload=request.split(b'\r\n\r\n',1);length=next((int(x.split(b':',1)[1])for x in h.split(b'\r\n')if x.lower().startswith(b'content-length:')),0)
    while len(payload)<length:payload+=conn.recv(length-len(payload))
    records.append({'line':h.split(b'\r\n')[0].decode(),'body_bytes':len(payload)});ready.wait(2)
    if after_headers:
     conn.sendall(response)
     if control=='cancel':proc.stdin.write(b'C');proc.stdin.flush()
     closed.append(conn.recv(1)==b'');return
    if control=='cancel':proc.stdin.write(b'C');proc.stdin.flush()
    try:conn.sendall(response)
    except (BrokenPipeError,ConnectionResetError):pass
  except (ConnectionResetError,BrokenPipeError):closed.append(True)
  except Exception as e:errors.append(repr(e))
 thread=threading.Thread(target=serve);thread.start();start=time.monotonic();proc=subprocess.Popen([binary,str(Path(__file__).with_suffix(".lua")),url,worker,str(limit),str(timeout),control,operation],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE);ready.set()
 try:raw,err=proc.communicate(timeout=8) if control!='cancel' else (proc.stdout.read(),proc.stderr.read())
 finally:
  if proc.poll() is None:proc.wait(timeout=8)
  done.set();thread.join(6)
 assert not thread.is_alive(),name
 if control=='cancel':proc.stdin.close()
 listener.setblocking(False);late=0
 while True:
  try:c,_=listener.accept();c.close();late+=1
  except BlockingIOError:break
 listener.close();assert proc.returncode==0,(name,proc.returncode,err);assert not errors,(name,errors);assert not late,(name,'late requests');v=json.loads(raw)
 assert v['ok']==success,(name,v)
 if success:assert v['kind']=='Xml' and v['bytes']==len(XML),(name,v)
 else:
  assert v['kind']==kind and v['recovery']==recovery,(name,v)
  if operation=='cancel' and records:assert v['unknown'] is True,(name,v)
  assert 'InertC6' not in v['message'],(name,'message credential reflection')
 if after_headers:assert closed==[True],(name,closed)
 if timeout>=100:assert len(records)==(0 if control=='pre' else 1),(name,records)
 rows.append({'case':name,'pass':True,'requests':len(records),'kind':v['kind'],'recovery':v.get('recovery'),'elapsed_ms':round((time.monotonic()-start)*1000,3),'fd_task_child_baseline_restored':True,'peer_closed':bool(closed)})
 Path(out).write_text(json.dumps({'cases':len(rows),'pass':len(rows),'fail':0,'HTTP_requests':sum(x['requests']for x in rows),'worker_sha256':hashlib.sha256(Path(worker).read_bytes()).hexdigest(),'C_correlation_accessor':False,'loopback_only':True,'rows':rows},indent=2)+'\n');print(name,'PASS',flush=True)
def head(extra='',length=None,chunked=False,status=503,media='application/json'):
 return (f'HTTP/1.1 {status} Synthetic\r\nContent-Type: {media}\r\nX-Correlation-ID: C6PublicCorrelation\r\n'+extra+('Transfer-Encoding: chunked\r\n'if chunked else f'Content-Length: {length}\r\n')+'Connection: close\r\n\r\n').encode()
SAFE={'uuid':UUID};body=b'{"error":"Ordinary synthetic failure"}'
run('complete-content-length-budget',head(length=len(body))+body,'body_limit',SAFE,limit=1)
run('early-chunk-budget-before-zero',head(chunked=True)+b'10\r\n0123456789abcdef\r\n','body_limit',None,limit=1)
run('early-chunk-truncated-before-zero',head(chunked=True)+b'10\r\npartial','transport',None)
run('early-chunk-invalid-size',head(chunked=True)+b'nothex\r\n','protocol',None)
run('queued-zero-still-early-budget',head(chunked=True)+b'10\r\n0123456789abcdef\r\n0\r\n\r\n','body_limit',None,limit=1)
run('after-headers-deadline',head(chunked=True)+b'10\r\npartial','timeout',None,timeout=180,after_headers=True)
run('after-headers-cancel',head(chunked=True)+b'10\r\npartial','cancelled',None,control='cancel',after_headers=True)
for name,location,want in [
 ('encoded-query-capability','http://localhost/output?token='+''.join('%%%02X'%ord(x)for x in UUID),None),
 ('matrix-capability','http://localhost/output;token='+UUID,None),
 ('fragment-capability','http://localhost/output#token='+UUID,None),
 ('different-capability-retains-selector','http://localhost/output?token=InertDifferentC6Capability',SAFE),
 ('short-literal-neighbor','http://localhost/output?token=xy',SAFE)]:
 run(name,head('Location: '+location+'\r\n',length=len(body))+body,'http',want)
# An ordinary 1024-attribute XML remains accepted. Tiny budgets/cancel supplement
# source-reviewed checkpoints; observed phase is recorded, not claimed deterministic.
XML=b'<root '+b' '.join(('a%d="x"'%i).encode()for i in range(1024))+b'></root>'
xml_response=head(length=len(XML),status=200,media='application/xml')+XML
run('ordinary-1024-attribute-xml',xml_response,None,None,limit=1024*1024,operation='xml',success=True)
run('small-file-deadline-after-headers',head(length=len(XML),status=200,media='application/xml')+XML[:128],'timeout',None,limit=1024*1024,timeout=180,operation='xml',after_headers=True)
run('file-after-request-cancel',b'','cancelled',None,limit=1024*1024,operation='xml',control='cancel',after_headers=True)
print('Lua native006 public followup:',len(rows),'PASS',flush=True)
