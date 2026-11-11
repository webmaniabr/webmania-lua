#!/usr/bin/env python3
"""Actual loopback auth/Unknown/boundaries/redirect/TLS through the Lua facade."""
import json,pathlib,socket,ssl,threading,subprocess,sys,time,urllib.parse,tempfile
R=pathlib.Path(__file__).resolve().parents[1]
runner,worker=sys.argv[1:]
from file_fixtures import PDF,pdf_with_stream
XML=b'<?xml version="1.0"?>\n<nfeProc><NFe/></nfeProc>'
fixture=json.loads((R/'tests/fixtures/operations.json').read_text())['cases']
for tls in (False,True):
 for mode in ('legacy_document','issuer_document','anonymous','wrong_auth','redirect','mutation_cancel','request8','request8_over','json16','file16'):
  listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(4);listener.settimeout(.4 if mode in ('wrong_auth','request8_over') else 10);port=listener.getsockname()[1];base=('https://localhost:' if tls else 'http://127.0.0.1:')+str(port);records=[];errors=[];flag=pathlib.Path(tempfile.mkdtemp(prefix='webmania-integration-'))/'accepted';flag.unlink(missing_ok=True)
  def serve():
   try:
    conn,_=listener.accept();conn.settimeout(10)
    if tls:
     ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);ctx.load_cert_chain(str(R/'tests/fixtures/tls/leaf.pem'),str(R/'tests/fixtures/tls/leaf.key'));conn=ctx.wrap_socket(conn,server_side=True)
    with conn:
     data=b''
     while b'\r\n\r\n'not in data:data+=conn.recv(65536)
     head,body=data.split(b'\r\n\r\n',1);parts=head.decode().split('\r\n');method,target,_=parts[0].split();headers={k.lower():v.strip() for k,v in (x.split(':',1) for x in parts[1:])};size=int(headers.get('content-length','0'))
     while len(body)<size:body+=conn.recv(min(size-len(body),65536))
     records.append((method,target,headers,body));flag.write_text('accepted')
     status=200;extra=b'';reply=b'';media=''
     # mutation_cancel answers nothing, then still runs the replay window below.
     if mode=='mutation_cancel':time.sleep(.3)
     elif mode=='request8':
      assert len(body)==8*1024*1024;assert json.loads(body)['uuid']=='00000000-0000-4000-8000-000000000001';reply=json.dumps(next(c['response'] for c in fixture if c['operation']=='nfeQueryDocument'),separators=(',',':')).encode();media='application/json'
     elif mode=='json16':
      prefix=b'{"status":"online","padding":"';suffix=b'"}';reply=prefix+b'a'*(16*1024*1024-len(prefix)-len(suffix))+suffix;media='application/json'
     elif mode=='file16':
      reply=pdf_with_stream(16*1024*1024,((4096,0),(4097,255)));media='application/octet-stream'
     elif mode=='redirect':reply=b'';media='application/pdf';status=302;extra=('Location: '+base+'/private-marker?token=private-marker\r\n').encode()
     else:reply=PDF if mode=='legacy_document' else XML;media='application/pdf' if mode=='legacy_document' else 'text/xml'
     if mode!='mutation_cancel':conn.sendall(f'HTTP/1.1 {status} OK\r\nContent-Type: {media}\r\nContent-Length: {len(reply)}\r\nConnection: close\r\n'.encode()+extra+b'\r\n'+reply)
    # A retry or redirect transfer would create a second connection.
    listener.settimeout(.2)
    try:conn,_=listener.accept();conn.close();records.append(('REPLAY',))
    except socket.timeout:pass
   except socket.timeout:pass
   except Exception as e:errors.append(repr(e))
  thread=threading.Thread(target=serve);thread.start();p=subprocess.run([runner,str(R/'tests/integration.lua'),mode,base,worker,str(R/'tests/fixtures/tls/ca.pem'),str(flag)],capture_output=True,timeout=30);thread.join(5);listener.close();assert not thread.is_alive();assert p.returncode==0,(mode,tls,p.returncode,p.stderr.decode());assert not errors,(mode,errors)
  if mode in ('wrong_auth','request8_over'):assert not records,(mode,records)
  else:
   assert len(records)==1,(mode,len(records));method,target,headers,body=records[0]
   if mode in ('legacy_document','issuer_document','anonymous','redirect'):
    assert 'authorization' not in headers and 'x-consumer-key' not in headers
    query=urllib.parse.parse_qs(urllib.parse.urlsplit(target).query)
    assert query.get('token')==(['synthetic-document'] if mode.endswith('_document') else None)
  print(('TLS ' if tls else 'HTTP ')+mode+' PASS',flush=True)
# Unknown CA and wrong hostname are rejected by the unchanged C/Rust TLS lane.
for label,certificate in [('unknown-ca','unknown-leaf'),('wrong-host','other')]:
 listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen();port=listener.getsockname()[1]
 def reject_tls():
  conn,_=listener.accept();ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);ctx.load_cert_chain(str(R/'tests/fixtures/tls'/f'{certificate}.pem'),str(R/'tests/fixtures/tls'/f'{certificate}.key'))
  try:ctx.wrap_socket(conn,server_side=True).close()
  except ssl.SSLError:conn.close()
 thread=threading.Thread(target=reject_tls);thread.start();p=subprocess.run([runner,str(R/'tests/integration.lua'),'bad_tls',f'https://localhost:{port}',worker,str(R/'tests/fixtures/tls/ca.pem')],capture_output=True,timeout=10);thread.join(5);listener.close();assert p.returncode==0,(label,p.stderr.decode());assert not thread.is_alive();print(label+' PASS',flush=True)
print('22 auth/Unknown/boundary/redirect/TLS integration lanes PASS')
# The homologation example over the same facade. The origin allow-list is mandatory; its
# guard reads the decoded top-level "ambiente" of the request it sends, before any network;
# WEBMANIA_LIVE_POLL_ATTEMPTS only accepts 1 to 20; the consult after an NF-e or NFS-e
# cancellation is repeated while the document is processing (NFS-e: also
# processando_cancelamento) and succeeds only for the status "cancelado"; a cancellation
# still pending when the consults run out, and an unknown cancellation, are recorded as
# "unknown" with the cancel operation, without a resend; the NF-e cancellation XML is
# requested only once a consult showed "cancelado".
import atexit,os,http.server,shutil
example=str(R/'examples/homologacao/main.lua');requests={c['operation']:c['request'] for c in fixture};responses={c['operation']:c['response'] for c in fixture}
work=pathlib.Path(tempfile.mkdtemp(prefix='webmania-example-'));atexit.register(shutil.rmtree,work,True)
def run_example(env):
 full={k:v for k,v in os.environ.items() if not k.startswith('WEBMANIA_')};full.update({'WEBMANIA_LIVE':'1','WEBMANIA_WORKER_PATH':worker,'WEBMANIA_LIVE_ALLOWED_HOSTS':'127.0.0.1'},**env);full={k:v for k,v in full.items() if v is not None}
 p=subprocess.run([runner,example],capture_output=True,timeout=60,env=full);return p.returncode,[json.loads(x) for x in p.stdout.decode().splitlines()],p.stderr.decode()
def payload_file(name,text):path=work/name;path.write_text(text);return str(path)
def bypass(request):
 # The escaped top-level key decodes to "ambiente":1; the only literal "ambiente" is nested.
 rest=json.dumps({k:v for k,v in request.items() if k!='ambiente'});return '{"\\u0061mbiente":1,'+rest[1:-1]+',"extensao_teste":{"ambiente":2}}'
silent=socket.socket();silent.bind(('127.0.0.1',0));silent.listen(4);silent.setblocking(False);quiet='http://127.0.0.1:'+str(silent.getsockname()[1])
for label,allowed,reason in [('absent',None,'WEBMANIA_LIVE_ALLOWED_HOSTS not configured'),('empty','','WEBMANIA_LIVE_ALLOWED_HOSTS not configured'),('blank',' , ','configured origin outside WEBMANIA_LIVE_ALLOWED_HOSTS')]:
 code,lines,err=run_example({'WEBMANIA_LIVE_ALLOWED_HOSTS':allowed,'WEBMANIA_API1_BASE_URL':quiet,'WEBMANIA_FILES_BASE_URL':quiet,'WEBMANIA_API2_BASE_URL':quiet})
 assert code==77 and lines==[{'result':'blocked','reason':reason}],(label,code,lines,err)
 print('example allow-list '+label+' PASS',flush=True)
def literal(request,text):
 # The same request with the top-level "ambiente" written as the given JSON text.
 rest=json.dumps({k:v for k,v in request.items() if k!='ambiente'});return '{"ambiente":'+text+','+rest[1:-1]+'}'
for scope,variable,operation in [('nfe','WEBMANIA_LIVE_NFE_PAYLOAD','nfeIssueDocument'),('nfse','WEBMANIA_LIVE_NFSE_PAYLOAD','emitterIssueNfse')]:
 for label,text,reason in [('bypass',bypass(requests[operation]),'payload ambiente must be 2'),('string',json.dumps({**requests[operation],'ambiente':'2'}),'payload ambiente must be 2'),('fraction',literal(requests[operation],'2.0'),'payload ambiente must be 2'),('exponent',literal(requests[operation],'2e0'),'payload ambiente must be 2'),('homologation',json.dumps(requests[operation]),'company credentials not configured')]:
  code,lines,err=run_example({'WEBMANIA_LIVE_SCOPE':scope,variable:payload_file(scope+'-'+label+'.json',text),'WEBMANIA_LIVE_LEDGER':str(work/(scope+'-'+label+'.ledger')),'WEBMANIA_API1_BASE_URL':quiet,'WEBMANIA_FILES_BASE_URL':quiet,'WEBMANIA_API2_BASE_URL':quiet})
  assert code==77 and lines==[{'result':'blocked','reason':reason}],(scope,label,code,lines,err)
  assert (work/(scope+'-'+label+'.ledger')).exists()==(label=='homologation'),(scope,label)
  print('example '+scope+' ambiente '+label+' PASS',flush=True)
 # A mutation scope needs a writable ledger before any credential is read.
 for label,ledger,reason in [('absent',None,'WEBMANIA_LIVE_LEDGER not configured'),('unwritable',str(work/'missing'/'ledger.jsonl'),'ledger unwritable')]:
  code,lines,err=run_example({'WEBMANIA_LIVE_SCOPE':scope,variable:payload_file(scope+'-ledger.json',json.dumps(requests[operation])),'WEBMANIA_LIVE_LEDGER':ledger,'WEBMANIA_API1_BASE_URL':quiet,'WEBMANIA_FILES_BASE_URL':quiet,'WEBMANIA_API2_BASE_URL':quiet})
  assert code==77 and lines==[{'result':'blocked','reason':reason}],(scope,label,code,lines,err)
  print('example '+scope+' ledger '+label+' PASS',flush=True)
# The read-only scope makes no mutation and needs no ledger.
code,lines,err=run_example({'WEBMANIA_LIVE_SCOPE':'readonly','WEBMANIA_API1_BASE_URL':quiet,'WEBMANIA_FILES_BASE_URL':quiet,'WEBMANIA_API2_BASE_URL':quiet})
assert code==77 and lines==[{'result':'blocked','reason':'company credentials not configured'}],(code,lines,err)
print('example readonly without ledger PASS',flush=True)
# WEBMANIA_LIVE_POLL_ATTEMPTS can only lower the consults: anything but 1 to 20 is refused before any network.
for attempts in ('0','21','100','-1','+3',' 3','x','1.5'):
 code,lines,err=run_example({'WEBMANIA_LIVE_SCOPE':'readonly','WEBMANIA_LIVE_POLL_ATTEMPTS':attempts,'WEBMANIA_API1_BASE_URL':quiet,'WEBMANIA_FILES_BASE_URL':quiet,'WEBMANIA_API2_BASE_URL':quiet})
 assert code==77 and lines==[{'result':'blocked','reason':'WEBMANIA_LIVE_POLL_ATTEMPTS must be 1 to 20'}],(attempts,code,lines,err)
print('example poll attempts refused PASS',flush=True)
try:silent.accept();raise AssertionError('the example guard opened a connection')
except BlockingIOError:pass
silent.close()
UUID='00000000-0000-4000-8000-000000000001'
class Api(http.server.BaseHTTPRequestHandler):
 """After the cancellation the consult answers `after` in order, repeating the last entry; 'drop' closes the cancellation."""
 after=['cancelado'];seen=[]
 def log_message(self,*_):pass
 def reply(self,body,media='application/json',status=200):
  data=body if isinstance(body,bytes) else json.dumps(body).encode()
  self.send_response(status);self.send_header('Content-Type',media);self.send_header('Content-Length',str(len(data)));self.send_header('Connection','close');self.end_headers();self.wfile.write(data)
 def consulted(self,cancelled):
  if not cancelled:return 'aprovado'
  # Consults since the cancellation, this one included.
  sent=[m for m,_,_ in Api.seen].index('PUT')
  n=sum(1 for m,p,_ in Api.seen[sent+1:] if m=='GET' and p in ('/1/nfe/consulta/','/2/nfse/consulta/'+UUID))
  return Api.after[min(n,len(Api.after))-1]
 def route(self):
  size=int(self.headers.get('Content-Length','0'));body=json.loads(self.rfile.read(size)) if size else None;path=urllib.parse.urlsplit(self.path).path
  cancelled=any(m=='PUT' for m,_,_ in Api.seen);Api.seen.append((self.command,path,body))
  reads={'/1/nfe/sefaz/':'nfeGetSefazStatus','/1/nfe/certificado/':'nfeGetCertificateValidity','/1/nfe/classe-imposto/':'nfeListTaxClasses','/2/nfse/status':'emitterGetNfseProviderStatus'}
  if path in reads:return self.reply(responses[reads[path]])
  if Api.after==['drop'] and self.command=='PUT':return
  if path=='/2/nfse/emissao':return self.reply({'uuid':UUID,'modelo':'nfse','status':'processando'})
  if path=='/2/nfse/consulta/'+UUID:return self.reply({**responses['emitterGetNfse'],'uuid':UUID,'status':self.consulted(cancelled)})
  if path=='/2/nfse/cancelar':return self.reply({'uuid':UUID,'modelo':'nfse','status':'processando_cancelamento'})
  if path=='/xmlnfse/'+UUID:return self.reply(XML,'text/xml')
  if path in ('/nfse/'+UUID,'/darps/'+UUID):return self.reply(PDF,'application/pdf')
  if path=='/1/nfe/emissao/':return self.reply({'uuid':UUID,'status':'processando','modelo':'55'})
  if path=='/1/nfe/consulta/':return self.reply({'uuid':UUID,'status':'aprovado' if self.command=='POST' else self.consulted(cancelled),'modelo':'55'})
  if path=='/1/nfe/cancelar/':return self.reply({'status':'processando'})
  if path in ('/danfe/'+UUID+'/','/danfe/simples/'+UUID+'/'):return self.reply(PDF,'application/pdf')
  if path in ('/xmlnfe/'+UUID+'/','/xmlnfe/'+UUID+'/cancelamento'):return self.reply(XML,'application/xml')
  return self.reply({'error':'unexpected route'},status=404)
 do_GET=do_POST=do_PUT=route
cycles=[('nfse','cancelado',['cancelado'],None),('nfse','cancelling',['processando_cancelamento','cancelado'],None),
        ('nfse','stuck',['processando_cancelamento'],'2'),('nfse','not_cancelled',['aprovado'],None),('nfse','drop',['drop'],None),
        ('nfe','cancelling',['processando','cancelado'],None),('nfe','stuck',['processando'],'2'),('nfe','not_cancelled',['aprovado'],None),
        ('nfe','drop',['drop'],None)]
for model,label,after,attempts in cycles:
 Api.after=after;Api.seen=[];server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Api);thread=threading.Thread(target=server.serve_forever);thread.start();origin='http://127.0.0.1:'+str(server.server_address[1]);ledger=work/(model+'-'+label+'.ledger')
 variable,operation,issue,cancel,consult,cancel_op={'nfse':('WEBMANIA_LIVE_NFSE_PAYLOAD','emitterIssueNfse','/2/nfse/emissao','/2/nfse/cancelar','/2/nfse/consulta/'+UUID,'emitterCancelNfse'),
                                                   'nfe':('WEBMANIA_LIVE_NFE_PAYLOAD','nfeIssueDocument','/1/nfe/emissao/','/1/nfe/cancelar/','/1/nfe/consulta/','nfeCancelDocument')}[model]
 try:code,lines,err=run_example({'WEBMANIA_LIVE_SCOPE':model,variable:payload_file(model+'.json',json.dumps(requests[operation])),'WEBMANIA_LIVE_LEDGER':str(ledger),'WEBMANIA_LIVE_POLL_ATTEMPTS':attempts,'WEBMANIA_API1_BASE_URL':origin,'WEBMANIA_FILES_BASE_URL':origin,'WEBMANIA_API2_BASE_URL':origin,'WEBMANIA_CONSUMER_KEY':'synthetic','WEBMANIA_CONSUMER_SECRET':'synthetic','WEBMANIA_ACCESS_TOKEN':'synthetic','WEBMANIA_ACCESS_TOKEN_SECRET':'synthetic','WEBMANIA_ISSUER_TOKEN':'synthetic'})
 finally:server.shutdown();server.server_close();thread.join(5)
 issued=[b for m,p,b in Api.seen if (m,p)==('POST',issue)];assert len(issued)==1 and issued[0]['ambiente']==2,(model,label,Api.seen)
 # The cancellation is sent once and never repeated.
 assert [p for m,p,_ in Api.seen if m=='PUT']==[cancel],(model,label,Api.seen)
 consults=[p for m,p,_ in Api.seen[[m for m,_,_ in Api.seen].index('PUT')+1:] if m=='GET' and p==consult]
 step=[x for x in lines if x.get('step')==model+'.consult_cancelled'];last=json.loads(ledger.read_text().splitlines()[-1])
 xml=[p for m,p,_ in Api.seen if (m,p)==('GET','/xmlnfe/'+UUID+'/cancelamento')]
 assert len(xml)==(1 if model=='nfe' and label=='cancelling' else 0),(model,label,'cancellation XML only after cancelado',Api.seen)
 if label=='drop':
  # The connection closes after the cancellation arrived: the outcome is unknown.
  sent=[x for x in lines if x.get('step')==model+'.cancel']
  assert len(sent)==1 and sent[0]['ok'] is False and sent[0]['outcome']=='unknown' and not step and not consults,(model,label,lines,err)
  assert last=={'model':model,'identifier':UUID,'status':'unknown','operation':cancel_op},(model,label,last)
  assert code==1,(model,label,code,lines,err)
 else:
  outcome={'stuck':'unknown','not_cancelled':'not_cancelled'}.get(label,'success')
  assert len(step)==1 and step[0]['ok'] is (outcome=='success') and step[0]['outcome']==outcome,(model,label,lines,err)
  # Consulted again only while the cancellation is processing, at most WEBMANIA_LIVE_POLL_ATTEMPTS times.
  assert len(consults)=={'cancelling':2,'stuck':2}.get(label,1),(model,label,Api.seen)
  if label=='stuck':
   # Never success: the cancellation stays in the ledger as unknown for reconciliation by consult.
   assert last=={'model':model,'identifier':UUID,'status':'unknown','operation':cancel_op},(model,label,last)
  else:
   assert last=={'model':model,'identifier':UUID,'status':after[-1],'operation':'emitterGetNfse' if model=='nfse' else 'nfeGetDocument'},(model,label,last)
  failed=[x['step'] for x in lines if x.get('ok') is False]
  assert failed==([] if outcome=='success' else [model+'.consult_cancelled']),(model,label,failed,lines,err)
  assert code==(0 if outcome=='success' else 1),(model,label,code,lines,err)
 print('example '+model+' post-cancel '+label+' PASS',flush=True)
print('28 homologation example lanes PASS')
# examples/homologacao/run.sh, offline, with stand-ins for luarocks and lua.
subprocess.run([sys.executable,str(R/'tests/example_run.py')],check=True,timeout=300)
