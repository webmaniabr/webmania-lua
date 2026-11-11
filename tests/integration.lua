local w=require('webmania')
local mode,base,worker,ca,flag=arg[1],arg[2],arg[3],arg[4],arg[5]
local cfg=w.Config():set_base_url(base):set_worker_path(worker):set_timeout_ms(3000):trust_file_origin(base)
local f=assert(io.open(ca,'rb'));cfg:set_ca_pem(f:read('a'));f:close()
local task
if mode=='mutation_cancel' then
 local c=w.NfeClient(w.CompanyCredentials('synthetic','private-marker','synthetic','private-marker'),cfg)
 local body=w.models['api1_fiscal.NfeCancelRequest'].new();body:set_uuid('00000000-0000-4000-8000-000000000001');body:set_motivo('Synthetic cancellation fixture only')
 task=w.nfeCancelDocument(c,body);body:close()
 local start=monotonic();while true do local file=io.open(flag,'rb');if file then file:close();break end;assert(monotonic()-start<2);sleep_ms(5)end
 task:cancel();local value,error=task:await();assert(value==nil and error:outcome_unknown());local recovery=assert(error:reveal_recovery());assert(recovery:to_json():find('00000000'));assert(not tostring(error):find('00000000'));assert(not error:message():find('00000000'));recovery:close();error:close();task:close();c:close();print('in-flight Unknown/recovery, no replay PASS');return
elseif mode=='request8' or mode=='request8_over' then
 local c=w.NfeClient(w.CompanyCredentials('synthetic','synthetic','synthetic','synthetic'),cfg)
 local body=w.models['api1_fiscal.NfeLookupRequest'].new();body:set_uuid('00000000-0000-4000-8000-000000000001');body:set_extension('padding',w.Json('""'))
 local size=8*1024*1024+(mode=='request8_over' and 1 or 0);local padding=string.rep('a',size-#body:to_json());body:set_extension('padding',w.Json('"'..padding..'"'));assert(#body:to_json()==size)
 local ok,t=pcall(w.nfeQueryDocument,c,body)
 if mode=='request8_over' then if ok then local value,error=t:await();assert(value==nil and error);assert(error:kind()=='request_limit',error:kind());error:close();t:close() end;print('8MiB+1 rejected before HTTP PASS') else assert(ok);local value,error=t:await();assert(value,error and error:kind());value:close();t:close();print('exact 8MiB request PASS') end
 body:close();c:close();return
elseif mode=='json16' then
 local c=w.NfeClient(w.CompanyCredentials('synthetic','synthetic','synthetic','synthetic'),cfg);task=w.nfeGetSefazStatus(c)
 local value,error=task:await();assert(value,error and error:kind());assert(#value:to_json()==16*1024*1024);value:close();task:close();c:close();print('actual exact 16MiB JSON response PASS');return
elseif mode=='file16' then
 local c=w.MonitorClient(w.MonitorToken('synthetic'),cfg);task=w.monitorDownloadReport(c,'00000000-0000-4000-8000-000000000001')
 local value,error=task:await();assert(value,error and error:kind());local bytes=value:bytes();assert(#bytes==16*1024*1024 and bytes:sub(4097,4098)=='\0\255');value:close();task:close();c:close();print('actual exact 16MiB file response NUL/FF PASS');return
elseif mode=='redirect' then
 local c=w.EmitterFilesClient(nil,cfg);task=w.fileGetNfsePdf(c,'00000000-0000-4000-8000-000000000001',w.FileAuth.anonymous());local value,error=task:await();assert(value,error and error:kind());assert(value:is_redirect());assert(value:reveal_location():find('private%-marker'));assert(not tostring(value):find('private'));assert(value:bytes()==nil);value:close();task:close();c:close();print('protected redirect no follow PASS');return
elseif mode=='legacy_document' then
 local c=w.NfeFilesClient(nil,cfg);task=w.nfeDownloadDanfe(c,'00000000-0000-4000-8000-000000000001',w.FileAuth.document_token('synthetic-document'));c=nil
elseif mode=='issuer_document' or mode=='anonymous' then
 local c=w.EmitterFilesClient(nil,cfg);task=w.fileGetCteXml(c,'00000000-0000-4000-8000-000000000001',mode=='anonymous' and w.FileAuth.anonymous() or w.FileAuth.document_token('synthetic-document'));c=nil
elseif mode=='wrong_auth' then
 local c=w.EmitterFilesClient(nil,cfg);task=w.fileGetMdfeXml(c,'00000000-0000-4000-8000-000000000001',w.FileAuth.anonymous());local value,error=task:await();assert(value==nil and error:kind()=='capability');error:close();task:close();c:close();print('undeclared auth mode rejects before accept PASS');return
elseif mode=='bad_tls' then
 local c=w.NfeClient(w.CompanyCredentials('synthetic','synthetic','synthetic','synthetic'),cfg);task=w.nfeGetSefazStatus(c);local value,error=task:await();assert(value==nil and error:kind()=='tls');error:close();task:close();c:close();print('invalid TLS rejects PASS');return
end
local value,error=task:await();assert(value,error and error:kind());assert(#value:bytes()>0);value:close();task:close();print(mode..' auth PASS')
