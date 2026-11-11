local w=require('webmania')
local cfg=w.Config():set_worker_path(assert(arg[1])):set_timeout_ms(1000):set_base_url('http://127.0.0.1:9')
local c=w.NfeClient(w.CompanyCredentials('synthetic','synthetic','synthetic','synthetic'),cfg)
local tasks={}
for i=1,4 do tasks[i]=w.nfeGetSefazStatus(c) end
sleep_ms(30)
-- lua_close must run client/task finalizers in either order, cancel and join.
