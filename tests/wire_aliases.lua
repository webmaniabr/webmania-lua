local w=require('webmania')
local n=0
local function check(v) assert(v,'wire line '..debug.getinfo(2,'l').currentline);n=n+1 end
local function reject(f)check(not pcall(f))end
local cfg=w.Config():set_worker_path(assert(arg[1]))
local ctor=w.models['api2_nfcom_issuance.NfcomDocumentedGroup2114']
local group=ctor.new();check(group:type()=='api2_nfcom_issuance.NfcomDocumentedGroup2114')
local fields={'substituicao_chave_nfcom_substituida','substituicao_motivo','substituicao_nf_referenciada'}
local wire={'substituicao.chave_nfcom_substituida','substituicao.motivo','substituicao.nf_referenciada.*'}
for i,key in ipairs(fields)do check(group:presence(key)=='missing');reject(function()group:set_extension(wire[i],w.Json('null'))end)end
local key='key\0á';local map=w.Map();map:set_extension('modelo',w.Json('21'));map:set_extension('k\0*',w.Json('"v\\u0000*"'))
group:set_substituicao_chave_nfcom_substituida(key);group:set_substituicao_motivo('01');group:set_substituicao_nf_referenciada(map);map:close()
for _,field in ipairs(fields)do check(group:presence(field)=='present');group:set_extension(field,w.Json('false'))end
local encoded=group:to_json()
for _,name in ipairs(wire)do check(encoded:find('"'..name..'"',1,true)~=nil)end
local clone,error=ctor.from_json(encoded,cfg);check(clone~=nil and error==nil);group:close()
check(clone:get_substituicao_chave_nfcom_substituida()==key);check(clone:get_substituicao_motivo()=='01')
local copy=clone:get_substituicao_nf_referenciada();check(copy:type()=='Map');check(copy:get_extension('modelo'):to_json()=='21');check(copy:get_extension('k\0*'):to_json()=='"v\\u0000*"');copy:close()
for _,field in ipairs(fields)do check(clone:get_extension(field):to_json()=='false')end
local other=w.models['api1_fiscal.TaxClassListItem'].new();local stolen=clone.set_substituicao_motivo;reject(function()stolen(other,'01')end);other:close()
clone:unset_substituicao_chave_nfcom_substituida();clone:unset_substituicao_motivo();clone:unset_substituicao_nf_referenciada()
for i,field in ipairs(fields)do check(clone:presence(field)=='missing');reject(function()clone:set_extension(wire[i],w.Json('null'))end)end
local invalid,e=ctor.from_json('{"substituicao.motivo":false}',cfg);check(invalid==nil and e~=nil);e:close()
check(w.version=='0.1.0-alpha.5');clone:close();cfg:close();collectgarbage('collect')
print('Lua C5 aliases '..n..' nominal/wire/presence/unset/collision/NUL/star-map checks PASS HTTP=0')
