local w=require('webmania')
local cfg=w.Config():set_worker_path(assert(arg[1])):set_base_url(assert(arg[2])):set_timeout_ms(2000)
local c=w.NfeClient(w.CompanyCredentials('synthetic','synthetic','synthetic','synthetic'),cfg)
local body=w.models['api1_fiscal.NfeCancelRequest'].new()
local returned=false
local ok,err=pcall(function()local task=w.nfeCancelDocument(c,body);returned=true;task:close()end)
assert(not ok and not returned,'invalid snapshot must fail synchronously before Task return')
-- The cause must be the snapshot rejection itself, not an allocation failure.
assert(type(err)=='string' and err:find('webmania: invalid typed snapshot or local validation failure',1,true),tostring(err))
body:close();c:close();cfg:close();for _=1,4 do collectgarbage('collect') end
