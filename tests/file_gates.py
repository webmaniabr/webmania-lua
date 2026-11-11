"""Actual installed frontend FILE01/02 pairs; no worker replacement or injection."""
import pathlib,socket,ssl,subprocess,sys,threading,tempfile,json
from file_gate_cases import file_gate_cases
R=pathlib.Path(__file__).resolve().parents[1];runner,worker,language=sys.argv[1:4];memory='--memory'in sys.argv;results=[]
with tempfile.TemporaryDirectory(prefix='frontend-files-')as tmp:
 for tls in ((False,)if memory else(False,True)):
  for label,body,media,want,kind in file_gate_cases():
   if memory and label not in('plain-pdf','protected-pdf','canonical-xlsx'):continue
   path=pathlib.Path(tmp)/'expected.bin';path.write_bytes(body)
   listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(3);listener.settimeout(30);base=('https://localhost:'if tls else'http://127.0.0.1:')+str(listener.getsockname()[1]);records=[];errors=[]
   def serve():
    try:
     conn,_=listener.accept();conn.settimeout(30)
     if tls:
      ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);ctx.load_cert_chain(str(R/'tests/fixtures/tls/leaf.pem'),str(R/'tests/fixtures/tls/leaf.key'));conn=ctx.wrap_socket(conn,server_side=True)
     with conn:
      request=b''
      while b'\r\n\r\n'not in request:request+=conn.recv(65536)
      records.append(request);conn.sendall(f'HTTP/1.1 200 OK\r\nContent-Type: {media}\r\nContent-Length: {len(body)}\r\nConnection: close\r\n\r\n'.encode()+body)
      if tls:
       try:conn.unwrap().close()
       except(ssl.SSLError,OSError):pass
     listener.settimeout(.2)
     try:conn,_=listener.accept();conn.close();records.append(b'REPLAY')
     except socket.timeout:pass
    except Exception as e:errors.append(repr(e))
   thread=threading.Thread(target=serve);thread.start();script=str(R/'tests/file_gates.lua')if language=='lua'else str(R/'tests/consumer/file_gates.R')
   p=subprocess.run([runner,script,base,worker,str(R/'tests/fixtures/tls/ca.pem'),want,kind or'none',str(path)],capture_output=True,timeout=120);thread.join(31);listener.close()
   assert p.returncode==0,(label,tls,p.returncode,p.stdout.decode(),p.stderr.decode());assert not thread.is_alive()and not errors and len(records)==1,(label,errors,records)
   assert records[0].split(b' ',2)[0]==b'GET' and b'/relatorio/'in records[0].split(b' ',2)[1]
   assert b'authorization:'not in records[0].lower()and b'x-consumer-key:'not in records[0].lower()
   results.append({'case':label,'tls':tls,'classification':kind or want,'requests':1,'exact_bytes':want=='file'});print(('TLS 'if tls else'HTTP ')+label+' '+(kind or want)+' PASS',flush=True)
if len(sys.argv)>4 and sys.argv[4]!='--memory':pathlib.Path(sys.argv[4]).write_text(json.dumps({'cases':len(results),'requests':len(results),'results':results},indent=2)+'\n')
print(str(len(results))+' installed frontend file gate pairs PASS')
