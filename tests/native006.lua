local w=require('webmania')
assert(w.version=='0.1.0-alpha.5')
local url,worker,limit,timeout,control,operation=table.unpack(arg,1,6)
local fd,threads,children=resource_counts()
local cfg=w.Config():set_base_url(url):trust_file_origin(url):set_worker_path(worker):set_timeout_ms(assert(tonumber(timeout))):set_max_response_bytes(assert(tonumber(limit)))
local credentials=w.CompanyCredentials('InertC6Key','InertC6Secret','InertC6Access','InertC6AccessSecret')
local task,client,body,query,auth
local uuid='00000000-0000-4000-8000-000000000006'
if operation=='xml' then
 client=w.NfeFilesClient(nil,cfg);query=w.models['api1_files.NfeDownloadXmlQuery'].new();auth=w.FileAuth.document_token('InertC6Document');task=w.nfeDownloadXml(client,uuid,query,auth)
else
 client=w.NfeClient(credentials,cfg);body=w.models['api1_fiscal.NfeCancelRequest'].new();body:set_uuid(uuid);body:set_motivo('Ordinary synthetic C6 cancellation context.');task=w.nfeCancelDocument(client,body)
end
if control=='cancel' then assert(io.read(1)=='C');task:cancel() end
local value,error=task:await()
if value then
 local bytes=value:bytes();io.write('{"ok":true,"kind":',w.Scalar.text(value:kind()):to_json(),',"bytes":',#bytes,'}');value:close()
else
 assert(error);local recovery=error:reveal_recovery();io.write('{"ok":false,"kind":',w.Scalar.text(error:kind()):to_json(),',"status":',error:status(),',"unknown":',tostring(error:outcome_unknown()),',"message":',w.Scalar.text(error:message()):to_json(),',"recovery":',recovery and recovery:to_json() or 'null','}');if recovery then recovery:close() end;error:close()
end
task:close();client:close();credentials:close();cfg:close();if body then body:close() end;if query then query:close() end;if auth then auth:close() end
collectgarbage('collect');local f,t,c=resource_counts();assert(f==fd and t==threads and c==children)
