local w=require('webmania')
local n=0
local function check(v) assert(v,'control at line '..debug.getinfo(2,'l').currentline);n=n+1 end
local function rejects(f) local ok,e=pcall(f);check(not ok);check(not tostring(e):find('private%-marker')) end
local function gc() for _=1,4 do collectgarbage('collect') end end
local function baseline(expected) gc();local fd,threads,children=resource_counts();check(fd==expected[1]);check(threads==expected[2]);check(children==expected[3]) end
local worker=assert(arg[1]);local fake=assert(arg[2]);local slow=assert(arg[3])
local base={resource_counts()}
local cfg=w.Config():set_worker_path(worker):set_base_url('http://127.0.0.1:9'):set_timeout_ms(500)
local function client(config) local c=w.CompanyCredentials('secret-marker','private-marker','private-marker','private-marker');local x=w.NfeClient(c,config);c:close();return x end
local value=w.Number('9007199254740993.000000000000000001');check(value:reveal()=='9007199254740993.000000000000000001');check(not tostring(value):find('9007'))
rejects(function()w.Number(1.5)end);rejects(function()w.Number('1\0.2')end);rejects(function()w.Number('01')end)
local x=w.models['api1_fiscal.NfeLookupRequest'].new();check(x:presence_uuid()=='missing');check(x:get_uuid()==nil);x:set_uuid('private-marker\0á😀');check(x:get_uuid()=='private-marker\0á😀');check(x:presence_uuid()=='present');x:unset_uuid();check(x:presence_uuid()=='missing')
x:set_ID('upper');x:set_id('lower');check(x:get_ID()=='upper' and x:get_id()=='lower');x:set_extension('future\0á',w.Json('false'));check(x:get_extension('future\0á'):to_json()=='false');rejects(function()x:set_extension('uuid',w.Json('0'))end);check(not tostring(x):find('upper'))
local order=w.models['api1_fiscal.NfeOrder'].new();order:set_presenca(0);check(order:get_presenca()==0);rejects(function()order:set_presenca(1.0)end);rejects(function()order:set_presenca(1.5)end);rejects(function()order:set_pagamento(x)end)
local stolen=order.get_presenca;rejects(function()stolen(x)end);rejects(function()w.models['api1_fiscal.NfeOrder'].new(1.0)end)
order:set_presenca(math.maxinteger);check(order:get_presenca()==math.maxinteger);order:set_presenca(math.mininteger);check(order:get_presenca()==math.mininteger);order:set_presenca(0)
local company=w.models['api1_b2b.ResellerCompanyCredentials'].new();company:set_bearer_access_token_pending(false);check(company:get_bearer_access_token_pending()==false and company:presence_bearer_access_token_pending()=='present');company:close()
local called=false;local hostile=setmetatable({}, {__tostring=function()called=true;return 'private-marker'end});rejects(function()x:set_uuid(hostile)end);check(not called)
local map=w.Map();map:set_extension('a\0b',w.Json('null'));map:set_extension('zero',w.Json('0'));map:set_extension('false',w.Json('false'));check(map:key_at(1)=='a\0b');check(map:get_extension('a\0b'):to_json()=='null');check(map:get_extension('zero'):to_json()=='0');check(map:get_extension('false'):to_json()=='false')
local scalar=w.Scalar.number(value);check(scalar:to_json()==value:reveal());check(w.Scalar.boolean(false):to_json()=='false');check(w.Scalar.text('a\0b'):to_json()=='"a\\u0000b"')
order:set_frete(scalar);local money=order:get_frete();check(money:to_json()==value:reveal());money:close()
local depth=string.rep('[',64)..'0'..string.rep(']',64);check(w.Json(depth):to_json()==depth);rejects(function()w.Json('['..depth..']')end);rejects(function()w.Json('{"a":0,"a":1}')end);rejects(function()w.Json('"\255"')end);rejects(function()w.Json('"\\ud800"')end)
local huge=string.rep('9',4096);check(w.Number(huge):reveal()==huge);rejects(function()w.Number(huge..'9')end);check(w.Json('"á😀\\u0000"'):to_json():find('á😀')~=nil)
local h=require('webmania_helpers');local ids={};local pages=h.pages(function(id)ids[#ids+1]=id or 'first';return {next=id==nil and '000opaque' or nil}end,nil,2,function(v)return v.next end);check(pages()~=nil);check(pages()~=nil);check(pages()==nil);check(ids[2]=='000opaque')
local clock=0;local polls=0;local result=h.poll(function()polls=polls+1;return polls end,function(v)return v==3 end,3,function()return clock end,function(seconds)clock=clock+seconds end);check(result==3 and clock>=10)
local config=w.Config():set_worker_path(fake):set_base_url('http://127.0.0.1:9'):set_timeout_ms(500)
local c=client(config);config:set_base_url('http://127.0.0.1:8'):set_worker_path('/unavailable');config:close()
local task=w.nfeGetSefazStatus(c);local reply,error=task:await();check(reply~=nil and error==nil);check(reply:get_status()=='online');check(not tostring(c):find('secret'));reply:close();task:close()
local retained=w.nfeGetSefazStatus(client(w.Config():set_worker_path(fake):set_base_url('http://127.0.0.1:9'):set_timeout_ms(500)))
gc();local started=monotonic();while true do local ready,result,err=retained:poll();if ready then check(result~=nil and err==nil);check(result:get_status()=='online');result:close();break end;assert(monotonic()-started<1);sleep_ms(2) end;retained:close()
local query=w.models['api1_fiscal.NfeGetDocumentQuery'].new();query:set_uuid('00000000-0000-4000-8000-000000000001');task=w.nfeGetDocument(c,query);query:set_uuid('00000000-0000-4000-8000-000000000002');query:close();reply,error=task:await();check(reply~=nil);reply:close();task:close();c:close()
local slowcfg=w.Config():set_worker_path(slow):set_base_url('http://127.0.0.1:9'):set_timeout_ms(1000)
c=client(slowcfg);local start=monotonic();task=w.nfeGetSefazStatus(c);check(task:poll()==false);check(monotonic()-start<.2);sleep_ms(40);task:cancel();reply,error=task:await();check(reply==nil and error~=nil);check(not error:outcome_unknown());check(not tostring(error):find('private'));error:close();task:close();check(monotonic()-start<1)
local tasks={};for i=1,4 do tasks[i]=w.nfeGetSefazStatus(c)end;sleep_ms(40);start=monotonic();c:close();check(monotonic()-start<1);for _,t in ipairs(tasks) do t:close() end;tasks=nil;task=nil;baseline(base)
local deadline=client(w.Config():set_worker_path(slow):set_base_url('http://127.0.0.1:9'):set_timeout_ms(80));start=monotonic();task=w.nfeGetSefazStatus(deadline);reply,error=task:await();check(reply==nil and error~=nil);assert(error:kind()=='timeout','deadline classification '..error:kind());check(monotonic()-start<1);error:close();task:close();deadline:close()
c=client(slowcfg);local weak=setmetatable({}, {__mode='v'});do local abandoned=w.nfeGetSefazStatus(c);weak[1]=abandoned end;gc();check(weak[1]==nil);c:close();baseline(base)
for _=1,10 do local cc=client(slowcfg);local tt=w.nfeGetSefazStatus(cc);tt:close();cc:close();tt:close();cc:close() end;baseline(base)
-- Gate runs before credential/model/configuration access; no hostile metamethod.
rejects(function()w.nfeDownloadIbsCbsEventXml(hostile,hostile,hostile)end);check(not called)
rejects(function()w.nfeGetSefazStatus(w.MonitorClient(w.MonitorToken('private-marker'),cfg))end);rejects(function()w.nfeGetSefazStatus(c)end)
x:close();x:close();rejects(function()x:to_json()end);cfg:close();slowcfg:close();baseline(base)
print(n..' public Lua ownership/privacy/numeric/presence/depth/misuse/helper controls PASS')
