#!/usr/bin/env python3
"""Public Lua C3 Pending/HTML projection through actual HTTP/TLS, no replay."""
import pathlib,socket,ssl,threading,subprocess,sys,json,tempfile
R=pathlib.Path(__file__).resolve().parents[1];runner,worker=sys.argv[1:3]
HTML=b'\0\xff<!doctype html><html><script>fetch("http://127.0.0.1:1/never")</script><iframe src="http://127.0.0.1:1/never"></iframe>opaque\xe7\xa7\x81</html>'
PENDING=b'{"msg":"queued\\u0000\xc3\xa1\xf0\x9f\x98\x80","big":9007199254740995,"tiny":1.2300e-200,"Case":null,"case":[true,{"x":"extension"}]}'
path=pathlib.Path(tempfile.mkdtemp(prefix='lua-variants-'))/'html-exact.bin';path.write_bytes(HTML)
cases=[('pending',PENDING,'application/json','success')]
for op in ('fileGetNfsePdf','fileGetNfseRpsPdf','fileGetCtePdf','fileGetCteCorrectionPdf','fileGetMdfePdf','fileGetNfcomPdf','fileGetDcePdf'):
 cases.append(('html:'+op,HTML,'TeXt/HtMl; Charset=ISO-8859-1','success'))
for label,body,want in [('wrong-scalar',b'{"msg":false}','response_schema'),('business-false',b'{"msg":"x","error":false}','business'),('duplicate',b'{"msg":"a","msg":"b"}','protocol')]:cases.append((label,body,'application/json',want))
count=0
for tls in (False,True):
 for mode,body,media,want in cases:
  listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(3);listener.settimeout(10);port=listener.getsockname()[1];base=('https://localhost:' if tls else 'http://127.0.0.1:')+str(port);records=[];errors=[]
  if mode.startswith('html:'):
   body=body.replace(b'http://127.0.0.1:1/never',(base+'/never').encode());path.write_bytes(body)
  def serve():
   try:
    conn,_=listener.accept();conn.settimeout(10)
    if tls:
     ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);ctx.load_cert_chain(str(R/'tests/fixtures/tls/leaf.pem'),str(R/'tests/fixtures/tls/leaf.key'));conn=ctx.wrap_socket(conn,server_side=True)
    with conn:
     data=b''
     while b'\r\n\r\n'not in data:data+=conn.recv(65536)
     head=data.split(b'\r\n\r\n',1)[0].decode();records.append(head)
     conn.sendall(f'HTTP/1.1 200 OK\r\nContent-Type: {media}\r\nContent-Length: {len(body)}\r\nConnection: close\r\n\r\n'.encode()+body)
    listener.settimeout(.25)
    try:conn,_=listener.accept();conn.close();records.append('replay')
    except socket.timeout:pass
   except Exception as e:errors.append(repr(e))
  thread=threading.Thread(target=serve);thread.start();p=subprocess.run([runner,str(R/'tests/c3_variants.lua'),mode,base,worker,str(R/'tests/fixtures/tls/ca.pem'),want,str(path)],capture_output=True,timeout=40);thread.join(12);listener.close();assert not thread.is_alive();assert p.returncode==0,(mode,tls,p.returncode,p.stderr.decode());assert not errors,(mode,errors);assert len(records)==1,(mode,records);count+=1;print(('TLS 'if tls else'HTTP ')+mode+' '+want+' PASS',flush=True)
# Exact 16MiB Pending uses normal raw input length and is copied independently.
# It runs once over HTTP: TLS and normal-size Pending were both exercised above.
prefix=b'{"msg":"queued\\u0000\xc3\xa1\xf0\x9f\x98\x80","x":"';suffix=b'"}'
# JSON serialization preserves the UTF-8 string and escaped NUL unchanged.
body=prefix+b'a'*(16*1024*1024-len(prefix)-len(suffix))+suffix
for mode,payload,media in [('pending16',body,'application/json'),('html:fileGetNfsePdf:16',b'H'*(16*1024*1024),'text/html')]:
 listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen();listener.settimeout(15);port=listener.getsockname()[1];errors=[];records=[]
 if mode.startswith('html'):path.write_bytes(payload)
 def serve_large():
  try:
   conn,_=listener.accept();records.append(1)
   with conn:
    data=b''
    while b'\r\n\r\n'not in data:data+=conn.recv(65536)
    conn.sendall(f'HTTP/1.1 200 OK\r\nContent-Type: {media}\r\nContent-Length: {len(payload)}\r\nConnection: close\r\n\r\n'.encode()+payload)
   listener.settimeout(.2)
   try:conn,_=listener.accept();conn.close();records.append(2)
   except socket.timeout:pass
  except Exception as e:errors.append(repr(e))
 thread=threading.Thread(target=serve_large);thread.start();p=subprocess.run([runner,str(R/'tests/c3_variants.lua'),mode,f'http://127.0.0.1:{port}',worker,str(R/'tests/fixtures/tls/ca.pem'),'success',str(path)],capture_output=True,timeout=60);thread.join(20);listener.close();assert p.returncode==0,(mode,p.returncode,p.stderr.decode());assert not thread.is_alive() and not errors and len(records)==1,(mode,errors,records);count+=1;print('HTTP '+mode+' exact 16MiB PASS',flush=True)
print(f'{count} actual Lua C3 variant lanes PASS; exact opaque HTML, owned Pending, no hidden polling/redirect/replay')
# An invalid typed snapshot must fail synchronously before returning a Task;
# validation uses the actual pinned worker and makes zero HTTP requests.
listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen();listener.settimeout(.4);port=listener.getsockname()[1];records=[]
def reject_snapshot_http():
 try:conn,_=listener.accept();records.append(1);conn.close()
 except socket.timeout:pass
thread=threading.Thread(target=reject_snapshot_http);thread.start();p=subprocess.run([runner,str(R/'tests/snapshot.lua'),worker,f'http://127.0.0.1:{port}'],capture_output=True,timeout=20);thread.join(2);listener.close();assert p.returncode==0,(p.returncode,p.stderr.decode());assert not records and not thread.is_alive();print('1 synchronous invalid typed snapshot; no Task returned; zero HTTP PASS',flush=True)
