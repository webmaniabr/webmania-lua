local w=require('webmania')
local n=0
local function check(v) assert(v,'core at line '..debug.getinfo(2,'l').currentline);n=n+1 end
local function reject(f) check(not pcall(f)) end
local cfg=w.Config():set_worker_path(assert(arg[1]))
-- Rust model.rs Scalar admits all four exact alternatives, independently of
-- a particular property's contract. Builders project; from_json validates.
local order=w.models['api1_fiscal.NfeOrder'].new()
check(order:presence_frete()=='missing' and order:get_frete()==nil)
local lex='-9007199254740993.000000000000000001e+12'
local alternatives={{w.Scalar.boolean(false),'false'},{w.Scalar.boolean(true),'true'},{w.Scalar.null(),'null'},{w.Scalar.text('x\0á😀'),'"x\\u0000á😀"'},{w.Scalar.number(w.Number(lex)),lex}}
for _,case in ipairs(alternatives) do
 local scalar,json=case[1],case[2];check(scalar:to_json()==json);order:set_frete(scalar);scalar:close();check(order:presence_frete()==(json=='null' and 'null' or 'present'));local copy=order:get_frete();check(copy:type()=='Scalar' and copy:to_json()==json);copy:close()
end
order:unset_frete();check(order:presence_frete()=='missing' and order:get_frete()==nil)
reject(function()w.Scalar.boolean(0)end);reject(function()w.Scalar.number(1)end);reject(function()w.Scalar.text(false)end);reject(function()order:set_frete(w.null)end)
-- Presence and Nullable are distinct from common Scalar::Null.
local company=w.models['api1_b2b.ResellerCreatedCompany'].new()
check(company:presence_bearer_access_token_recovery_queued()=='missing')
company:set_bearer_access_token_recovery_queued(false);check(company:get_bearer_access_token_recovery_queued()==false and company:presence_bearer_access_token_recovery_queued()=='present')
company:set_bearer_access_token_recovery_queued(w.null);check(company:get_bearer_access_token_recovery_queued()==w.null and company:presence_bearer_access_token_recovery_queued()=='null')
company:unset_bearer_access_token_recovery_queued();check(company:get_bearer_access_token_recovery_queued()==nil)
local item=w.models['api1_fiscal.TaxClassListItem'].new()
check(item:presence_type()=='missing' and item:get_type()==nil)
-- A declared-name extension collision fails even while the property is absent.
local extra=w.Json('false');reject(function()item:set_extension('type',extra)end);check(item:presence_type()=='missing')
item:set_extension('TYPE',extra);extra:close();check(item:get_extension('TYPE'):to_json()=='false')
item:set_type('typed\0á😀');check(item:get_type()=='typed\0á😀' and item:presence_type()=='present');check(item:to_json():find('typed\\u0000',1,true)~=nil)
local stolen=item.get_type;reject(function()stolen(order)end)
-- type is a required member: it can be replaced but not unset.
reject(function()item:unset_type()end);check(item:presence_type()=='present');reject(function()item:set_extension('type',w.Json('null'))end)
local map=w.Map();local source=w.Json('{"false":false,"zero":0,"null":null,"text":"a\\u0000b"}')
map:set_extension('key\0á',source);source:close();local copy=map:get_extension('key\0á');map:close();check(copy:to_json()=='{"false":false,"zero":0,"null":null,"text":"a\\u0000b"}');copy:close()
-- Exact core parsing rejects aggregate Scalar input and illegal nullable values
-- through typed constructors, without string/table coercion.
reject(function()order:set_frete(w.Json('{}'))end);reject(function()company:set_bearer_access_token_recovery_queued(0)end)
order:close();company:close();item:close();cfg:close();collectgarbage('collect')
print(n..' manual Scalar BOOL/NULL/TEXT/NUMBER, Nullable/presence/maps/type collision/NUL/case checks PASS')
