local w=require('webmania')
local base,worker,ca,want,kind,path=table.unpack(arg)
local cfg=w.Config():set_worker_path(worker):set_base_url(base):trust_file_origin(base):set_timeout_ms(10000)
local f=assert(io.open(ca,'rb'));cfg:set_ca_pem(f:read('a'));f:close()
local client=w.NfeFilesClient(nil,cfg);local task=w.fiscalDownloadReport(client,'00000000-0000-4000-8000-000000000001',w.FileAuth.public_report())
local value,error=task:await();task:close();client:close();cfg:close()
if want=='file'then
 assert(value and not error,error and error:kind());assert(value:kind()==kind and value:status()==200)
 f=assert(io.open(path,'rb'));local exact=f:read('a');f:close();local bytes=value:bytes();local independent=value:bytes();assert(bytes==exact and independent==exact);value:close();collectgarbage('collect');assert(bytes==exact and independent==exact)
else assert(not value and error and error:kind()==want);error:close()end
collectgarbage('collect');print('Lua file gate '..want..' owned copied bytes PASS')
