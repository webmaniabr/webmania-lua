local w=require('webmania')
local mode,base,worker,ca,expected=arg[1],arg[2],arg[3],arg[4],arg[5]
local cfg=w.Config():set_worker_path(worker):set_base_url(base):trust_file_origin(base):set_timeout_ms(15000)
local f=assert(io.open(ca,'rb'));cfg:set_ca_pem(f:read('a'));f:close()
local client=w.EmitterFilesClient(w.IssuerToken('synthetic-issuer'),cfg)
local op=mode:match('^html:([^:]+)') or 'fileGetNfsePdf'
local task=w[op](client,'00000000-0000-4000-8000-000000000001',w.FileAuth.issuer())
local value,err=task:await()
if expected~='success' then assert(value==nil and err:kind()==expected,err and err:kind());err:close();task:close();client:close();cfg:close();return end
assert(value,err and err:kind());task:close();client:close();cfg:close()
if mode:sub(1,4)=='html' then
 local f=assert(io.open(arg[6],'rb'));local exact=f:read('a');f:close()
 assert(value:kind()=='Html' and value:status()==200);assert(value:media_type()=='text/html');assert(value:bytes()==exact)
 assert(not tostring(value):find('fetch'));value:close()
else
 assert(type(value)=='userdata' and value:is_pending() and value:kind()=='NfsePdfPending');assert(value:status()==200 and value:media_type()=='application/json')
 assert(value.bytes==nil and value.reveal_location==nil and value.is_redirect==nil);assert(not tostring(value):find('queued'))
 local a=value:value();local b=value:payload();assert(a:type()=='api2_emitter_files.NfsePdfPending' and b:type()==a:type());assert(a:get_msg()=='queued\0á😀')
 assert(not pcall(value.status,a) and not pcall(value.payload,b))
 a:set_msg('mutated');a:set_extension('Case',w.Json('0'));a:close();assert(b:get_msg()=='queued\0á😀')
 local before=b:to_json();value:close();value:close();assert(b:to_json()==before)
 if mode=='pending16' then assert(#before==16*1024*1024) else
  assert(b:get_extension('big'):to_json()=='9007199254740995');assert(b:get_extension('tiny'):to_json()=='1.2300e-200');assert(b:get_extension('Case'):to_json()=='null');assert(b:get_extension('case'):to_json()=='[true,{"x":"extension"}]')
 end
 assert(not pcall(function()value:status()end));b:close()
end
collectgarbage('collect')
