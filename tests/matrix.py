#!/usr/bin/env python3
"""Real installed C API HTTP/TLS calls, synthetic loopback services only."""
import json,pathlib,socket,ssl,threading,subprocess,urllib.parse,sys
R=pathlib.Path(__file__).resolve().parents[1]
meta=json.loads((R/'metadata/api-metadata.json').read_text())
cases={x['operation']:x for x in json.loads((R/'tests/fixtures/operations.json').read_text())['cases']}
from file_fixtures import PDF,pdf_with_stream
XML=b'<?xml version="1.0"?>\n<!-- fiscal -->\n<nfeProc><NFe/></nfeProc>'
CSV=b'uuid,status\r\na1234567-1234-4234-8234-123456789abc,emitido\r\n'
def file_for(media):return {'application/pdf':PDF,'application/octet-stream':PDF,'application/xml':XML,'text/xml':XML,'text/csv':CSV,'application/zip':b'PK\x05\x06'+bytes(18)}[media]
def run(binary,worker):
 total=0;selected=set(sys.argv[3:])
 for tls in (False,True):
  for index,o in enumerate(meta['operations']):
   if selected and o['id']not in selected:continue
   case=cases[o['id']];records=[];errors=[];listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(2);listener.settimeout(10 if selected else .4)
   port=listener.getsockname()[1];base=('https://localhost:' if tls else 'http://127.0.0.1:')+str(port)
   def serve():
    try:
     conn,_=listener.accept();conn.settimeout(5)
     if tls:
      ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);ctx.load_cert_chain(str(R/'tests/fixtures/tls/leaf.pem'),str(R/'tests/fixtures/tls/leaf.key'));conn=ctx.wrap_socket(conn,server_side=True)
     with conn:
      data=b''
      while b'\r\n\r\n' not in data:data+=conn.recv(65536)
      header,body=data.split(b'\r\n\r\n',1);parts=header.decode().split('\r\n');method,target,_=parts[0].split();headers={k.lower():v.strip() for k,v in (x.split(':',1) for x in parts[1:])};length=int(headers.get('content-length','0'))
      while len(body)<length:body+=conn.recv(length-len(body))
      records.append((method,target,headers,body))
      reply=file_for(case['media_type']) if case['binary'] else json.dumps(case['response'],ensure_ascii=False,separators=(',',':')).encode()
      conn.sendall(f'HTTP/1.1 {case["status"]} OK\r\nContent-Type: {case["media_type"]}\r\nContent-Length: {len(reply)}\r\nConnection: close\r\n\r\n'.encode()+reply)
      if tls:
       try:conn.unwrap().close()
       except (ssl.SSLError,OSError):pass
    except socket.timeout:pass
    except Exception as e:errors.append(repr(e))
   thread=threading.Thread(target=serve);thread.start()
   p=subprocess.run([binary,str(index),base,str(R/'tests/fixtures/tls/ca.pem'),worker],capture_output=True,timeout=60 if selected else 15)
   thread.join(6);listener.close();assert not thread.is_alive(),o['id'];assert p.returncode==0,(o['id'],tls,p.returncode,p.stderr.decode());assert not errors,(o['id'],errors)
   if not case['enabled']:assert not records;continue
   assert len(records)==1,(o['id'],records);method,target,headers,body=records[0];expected=case['path']
   for k,v in case['path_params'].items():expected=expected.replace('{'+k+'}',str(v))
   assert method==case['http_method'] and target.split('?')[0]==expected,(o['id'],target,expected)
   actualquery=urllib.parse.parse_qs(urllib.parse.urlsplit(target).query,keep_blank_values=True)
   for k,v in case['query'].items():assert actualquery.get(k)==[str(v).lower() if isinstance(v,bool) else str(v)],(o['id'],actualquery)
   assert headers['accept-encoding']=='identity' and headers['connection']=='close'
   if case['has_request']:assert json.loads(body)==case['request'],o['id']
   else:assert not body,o['id']
   scope=o['scope'];legacy=headers.get('x-consumer-key');bearer=headers.get('authorization')
   if scope=='Reseller':assert legacy=='synthetic-reseller-key' and not bearer
   elif scope=='Nfe' or (scope=='NfeFiles' and o['id']!='fiscalDownloadReport'):assert legacy=='synthetic-company-key' and not bearer
   elif scope.startswith('Emitter'):assert bearer=='Bearer synthetic-issuer' and not legacy
   elif scope=='Monitor':assert bearer=='Bearer synthetic-monitor' and not legacy
   else:assert not legacy and not bearer
   if case['binary']:assert bytes.fromhex(p.stdout.decode())==file_for(case['media_type']),o['id']
   else:assert json.loads(p.stdout)==case['response'],o['id']
   total+=1;print(('TLS' if tls else 'HTTP')+' '+o['id']+' PASS',flush=True)
 expected=sum(1 for o in meta['operations'] if o['enabled'] and (not selected or o['id']in selected));assert total==expected*2;print(f'Installed C matrix: {expected} HTTP + {expected} TLS; exact routes, bodies, credentials, files PASS',flush=True)
if __name__=='__main__':run(sys.argv[1],sys.argv[2])
