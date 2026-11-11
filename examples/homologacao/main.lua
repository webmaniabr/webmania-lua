-- Optional homologation run (ambiente 2) of the installed Lua SDK: read-only
-- checks, then NF-e and NFS-e issue -> consult -> files -> cancel -> consult.
--
-- Configuration comes only from environment variables (README, "Teste em
-- homologação"). Without WEBMANIA_LIVE=1 it prints {"result":"blocked"} and
-- exits 77 before any network work. Output is one JSON line per step with a
-- short reference (sha256 prefix) instead of identifiers; files appear as size,
-- sha256 and detected format. Credentials, payloads and bytes are never
-- printed. A mutation is never resent: an unknown outcome stops the run with
-- exit code 1 and stays in the ledger for reconciliation by consult. Consults
-- are repeated with backoff while a document is processing (after an NFS-e
-- cancellation also while processando_cancelamento); only cancelado confirms a
-- cancellation, and one still pending when the consults run out is ledgered as
-- unknown. The NF-e cancellation XML is downloaded only once cancelado is seen.
-- Exit codes: 0 all steps succeeded, 1 a step failed or is unknown, 77 not
-- enabled or not configured.
local function env(name)
  local v = os.getenv(name)
  if v == nil or v == '' then return nil end
  return v
end

local function quoted(text)
  return '"' .. tostring(text):gsub('[%c"\\]', function(c)
    if c == '"' or c == '\\' then return '\\' .. c end
    return string.format('\\u%04x', string.byte(c))
  end) .. '"'
end

local function blocked(reason)
  io.write('{"result":"blocked","reason":', quoted(reason), '}\n')
  os.exit(77)
end

if os.getenv('WEBMANIA_LIVE') ~= '1' then blocked('WEBMANIA_LIVE is not 1') end

-- SHA-256 (FIPS 180-4) on Lua 5.4 64-bit integers.
local K = {
  0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5, 0xd807aa98, 0x12835b01, 0x243185be,
  0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa,
  0x5cb0a9dc, 0x76f988da, 0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967, 0x27b70a85,
  0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3,
  0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070, 0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f,
  0x682e6ff3, 0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2}
local M32 = 0xffffffff
local function ror(x, n) return ((x >> n) | (x << (32 - n))) & M32 end
local function sha256(data)
  local h = {0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19}
  local bits = #data * 8
  data = data .. '\128' .. string.rep('\0', (55 - #data) % 64) .. string.pack('>I8', bits)
  for off = 1, #data, 64 do
    local w = {}
    for i = 0, 15 do w[i] = string.unpack('>I4', data, off + 4 * i) end
    for i = 16, 63 do
      local s0 = ror(w[i - 15], 7) ~ ror(w[i - 15], 18) ~ (w[i - 15] >> 3)
      local s1 = ror(w[i - 2], 17) ~ ror(w[i - 2], 19) ~ (w[i - 2] >> 10)
      w[i] = (w[i - 16] + s0 + w[i - 7] + s1) & M32
    end
    local a, b, c, d, e, f, g, hh = table.unpack(h)
    for i = 0, 63 do
      local t1 = (hh + (ror(e, 6) ~ ror(e, 11) ~ ror(e, 25)) + ((e & f) ~ (~e & g)) + K[i + 1] + w[i]) & M32
      local t2 = ((ror(a, 2) ~ ror(a, 13) ~ ror(a, 22)) + ((a & b) ~ (a & c) ~ (b & c))) & M32
      hh, g, f, e, d, c, b, a = g, f, e, (d + t1) & M32, c, b, a, (t1 + t2) & M32
    end
    for i, v in ipairs({a, b, c, d, e, f, g, hh}) do h[i] = (h[i] + v) & M32 end
  end
  return string.format(string.rep('%08x', 8), table.unpack(h))
end
local function ref(identifier) return sha256(identifier):sub(1, 12) end

local failed = false
local ledger = nil

local function line(step, op, ok, http, outcome, kind, identifier, extra)
  io.write('{"step":', quoted(step), ',"operation":', quoted(op), ',"ok":', ok and 'true' or 'false',
    ',"http_status":', (http and http > 0) and tostring(http) or 'null', ',"outcome":', quoted(outcome),
    ',"kind":', kind and quoted(kind) or 'null', ',"ref":', (identifier and identifier ~= '') and quoted(ref(identifier)) or 'null',
    extra or '', '}\n')
  io.flush()
  if not ok then failed = true end
end
local function note(step, op, ok, outcome, identifier) line(step, op, ok, nil, outcome, nil, identifier) end
-- Records an SDK failure; returns true when the outcome is unknown (stop).
local function fail(step, op, err, identifier)
  local unknown = err ~= nil and err:outcome_unknown()
  line(step, op, false, err and err:status() or nil, unknown and 'unknown' or 'failed', err and err:kind() or 'local', identifier)
  if err then err:close() end
  return unknown
end
local function file_line(step, op, file, identifier)
  local bytes = file:bytes() or ''
  line(step, op, true, file:status(), 'success', file:kind(), identifier, ',"size":' .. #bytes .. ',"sha256":' .. quoted(sha256(bytes)))
end
local function record(model, identifier, status, op)
  if not ledger then return end
  ledger:write('{"model":', quoted(model), ',"identifier":', quoted(identifier), ',"status":', quoted(status or ''), ',"operation":', quoted(op), '}\n')
  if not ledger:flush() then failed = true end
end

local w = require('webmania')
local scope = env('WEBMANIA_LIVE_SCOPE') or 'readonly'
local do_nfe, do_nfse = scope == 'nfe' or scope == 'all', scope == 'nfse' or scope == 'all'
if not do_nfe and not do_nfse and scope ~= 'readonly' then blocked('unsupported WEBMANIA_LIVE_SCOPE') end
-- Most consults of one poll; the optional WEBMANIA_LIVE_POLL_ATTEMPTS can only lower it.
local MAX_ATTEMPTS = 20
local attempts = MAX_ATTEMPTS
local attempts_text = env('WEBMANIA_LIVE_POLL_ATTEMPTS')
if attempts_text then
  attempts = attempts_text:match('^%d%d?$') and tonumber(attempts_text) or 0
  if attempts < 1 or attempts > MAX_ATTEMPTS then blocked('WEBMANIA_LIVE_POLL_ATTEMPTS must be 1 to ' .. MAX_ATTEMPTS) end
end
local api1 = env('WEBMANIA_API1_BASE_URL') or 'https://webmania.com.br/api'
local files_base = env('WEBMANIA_FILES_BASE_URL') or 'https://nfe.webmania.com.br'
local api2 = env('WEBMANIA_API2_BASE_URL') or 'https://api.webmania.com.br'
local function host_of(origin) return (origin:gsub('^%a[%w+.-]*://', ''):match('^[^/:?#]*') or ''):lower() end
-- The allow-list is mandatory: without it no origin is trusted (fail closed).
local allowed = env('WEBMANIA_LIVE_ALLOWED_HOSTS') or blocked('WEBMANIA_LIVE_ALLOWED_HOSTS not configured')
local hosts = {}
for h in allowed:gmatch('[^,]+') do
  local host = h:match('^%s*(.-)%s*$'):lower()
  if host ~= '' then hosts[host] = true end
end
for _, origin in ipairs({api1, files_base, api2}) do
  if not hosts[host_of(origin)] then blocked('configured origin outside WEBMANIA_LIVE_ALLOWED_HOSTS') end
end
local worker = env('WEBMANIA_WORKER_PATH') or blocked('worker path not configured')
local function origin_only(base) return base:match('^(%a[%w+.-]*://[^/]*)') or base end
local function config(base, files)
  local ok, c = pcall(function()
    local c = w.Config():set_worker_path(worker):set_base_url(base):set_timeout_ms(60000)
    if files then c:trust_file_origin(origin_only(base)) end
    return c
  end)
  if not ok then blocked('invalid base URL or worker configuration') end
  return c
end
local c1, cf, c2, c2f = config(api1, false), config(files_base, true), config(api2, false), config(api2, true)
-- Decodes the payload into the request model that is sent and requires its
-- top-level "ambiente" to be the integer 2 (homologation), before any network.
local function payload(variable, model, cfg)
  local path = env(variable) or blocked('payload not configured')
  local f = io.open(path, 'rb') or blocked('payload unreadable')
  local text = f:read('a')
  f:close()
  local ok, body = pcall(w.models[model].from_json, text, cfg)
  if not ok or not body then blocked('payload is not a valid request') end
  local value = body:get_ambiente()
  local exact = value ~= nil and value ~= w.null
  local homologation = exact and value:to_json() == '2'
  if exact then value:close() end
  if not homologation then body:close(); blocked('payload ambiente must be 2') end
  return body
end
local nfe_body = do_nfe and payload('WEBMANIA_LIVE_NFE_PAYLOAD', 'api1_fiscal.NfeIssueRequest', c1) or nil
local nfse_body = do_nfse and payload('WEBMANIA_LIVE_NFSE_PAYLOAD', 'api2_nfse_issuance.EmitterIssueNfsePayload', c2) or nil
-- An unknown outcome is recorded only in the ledger: it must be writable before any mutation.
local ledger_path = env('WEBMANIA_LIVE_LEDGER')
if (do_nfe or do_nfse) and not ledger_path then blocked('WEBMANIA_LIVE_LEDGER not configured') end
if ledger_path then
  ledger = io.open(ledger_path, 'a') or blocked('ledger unwritable')
end
local key, secret = env('WEBMANIA_CONSUMER_KEY'), env('WEBMANIA_CONSUMER_SECRET')
local token, token_secret = env('WEBMANIA_ACCESS_TOKEN'), env('WEBMANIA_ACCESS_TOKEN_SECRET')
if not (key and secret and token and token_secret) then blocked('company credentials not configured') end
local issuer_value = env('WEBMANIA_ISSUER_TOKEN') or blocked('issuer token not configured')
local company = w.CompanyCredentials(key, secret, token, token_secret)
local issuer = w.IssuerToken(issuer_value)
local nfe, nfe_files = w.NfeClient(company, c1), w.NfeFilesClient(company, cf)
local emitter, emitter_files = w.EmitterClient(issuer, c2), w.EmitterFilesClient(issuer, c2f)
local function call(task)
  local value, err = task:await()
  task:close()
  return value, err
end
-- Statuses of a document that is still being processed; after an NFS-e cancellation the
-- document can also stay in processando_cancelamento until a later consult completes it.
local PROCESSING = {processando = true, processamento = true, pendente = true}
local CANCELLING = {processando = true, processamento = true, pendente = true, processando_cancelamento = true}
local function pending(status, set) return status == nil or status == '' or set[status] == true end
local function sleep(seconds) os.execute('sleep ' .. math.tointeger(seconds)) end
-- Consults while the status is empty or pending, at most `attempts` times, waiting 1, 2, 4,
-- 8 and then 10 seconds between consults. Only consults are repeated, never a mutation.
-- Returns the last status and the error that ended the poll, if any.
local function poll(set, consult)
  local status
  for attempt = 1, attempts do
    local s, err = consult()
    if s == nil and err then return status, err end
    status = s
    if not pending(status, set) or attempt == attempts then break end
    sleep(math.min(10, 2 ^ (attempt - 1)))
  end
  return status
end
-- The consult after a cancellation: only cancelado is success. A document still pending when
-- the consults run out, or a consult that failed, leaves the cancellation unknown: it is
-- ledgered as unknown for reconciliation by consult, and the cancel is never resent.
-- Returns true only when the consult showed cancelado.
local function cancel_settled(model, op, cancel_op, set, uuid, status, err)
  local step = model .. '.consult_cancelled'
  if err then
    fail(step, op, err, uuid)
    record(model, uuid, 'unknown', cancel_op)
  elseif status == 'cancelado' then
    record(model, uuid, status, op)
    note(step, op, true, 'success', uuid)
    return true
  elseif pending(status, set) then
    if status and status ~= '' then record(model, uuid, status, op) end
    record(model, uuid, 'unknown', cancel_op)
    note(step, op, false, 'unknown', uuid)
  else
    record(model, uuid, status, op)
    note(step, op, false, 'not_cancelled', uuid)
  end
  return false
end

for _, step in ipairs({
  {'readonly.sefaz_status', 'nfeGetSefazStatus', function() return w.nfeGetSefazStatus(nfe) end},
  {'readonly.certificate', 'nfeGetCertificateValidity', function() return w.nfeGetCertificateValidity(nfe) end},
  {'readonly.tax_classes', 'nfeListTaxClasses', function() return w.nfeListTaxClasses(nfe) end},
  {'readonly.nfse_provider', 'emitterGetNfseProviderStatus', function()
    return w.emitterGetNfseProviderStatus(emitter, assert(w.models['api2_emitter_reads.EmitterGetNfseProviderStatusQuery'].from_json('{}', c2)))
  end},
}) do
  local value, err = call(step[3]())
  if value then note(step[1], step[2], true, 'success'); value:close() else fail(step[1], step[2], err) end
end

local function nfe_status(uuid)
  local query = assert(w.models['api1_fiscal.NfeGetDocumentQuery'].from_json('{"uuid":' .. quoted(uuid) .. '}', c1))
  local value, err = call(w.nfeGetDocument(nfe, query))
  query:close()
  if not value then return nil, err end
  local ok, doc = pcall(value.get_NfeDocument, value, c1)
  local status = ok and doc and doc:get_status() or nil
  if not ok then
    local list = value:get_List(c1)
    local first = list and list:count() > 0 and list:at(1) or nil
    status = first and first:get_status() or nil
  end
  value:close()
  return status
end

-- Returns false when an unknown outcome stopped the run.
local function nfe_cycle(body)
  local issued, err = call(w.nfeIssueDocument(nfe, body))
  body:close()
  if not issued then
    if fail('nfe.issue', 'nfeIssueDocument', err) then record('nfe', '', 'unknown', 'nfeIssueDocument'); return false end
    return true
  end
  local ok, doc = pcall(issued.get_NfeDocument, issued, c1)
  local uuid = ok and doc and doc:get_uuid() or nil
  if uuid then record('nfe', uuid, doc:get_status(), 'nfeIssueDocument') end
  issued:close()
  if not uuid then note('nfe.issue', 'nfeIssueDocument', false, 'not_a_document'); return true end
  note('nfe.issue', 'nfeIssueDocument', true, 'success', uuid)
  local status, perr = poll(PROCESSING, function() return nfe_status(uuid) end)
  if perr and fail('nfe.consult', 'nfeGetDocument', perr, uuid) then return false end
  record('nfe', uuid, status, 'nfeGetDocument')
  if status ~= 'aprovado' then
    -- Still processing: reconciliation consults it later, never a blind cancel or
    -- resend. Rejected or denied documents need no cancellation.
    note('nfe.consult', 'nfeGetDocument', false, 'not_approved', uuid)
    return true
  end
  note('nfe.consult', 'nfeGetDocument', true, 'success', uuid)
  local lookup = assert(w.models['api1_fiscal.NfeLookupRequest'].from_json('{"uuid":' .. quoted(uuid) .. '}', c1))
  local q, qerr = call(w.nfeQueryDocument(nfe, lookup))
  lookup:close()
  if q then note('nfe.query', 'nfeQueryDocument', true, 'success', uuid); q:close() else fail('nfe.query', 'nfeQueryDocument', qerr, uuid) end
  local auth = w.FileAuth.company()
  local function download(step, op, task)
    local f, ferr = call(task)
    if f then file_line(step, op, f, uuid); f:close() else fail(step, op, ferr, uuid) end
  end
  download('nfe.danfe', 'nfeDownloadDanfe', w.nfeDownloadDanfe(nfe_files, uuid, auth))
  download('nfe.danfe_simple', 'nfeDownloadSimpleDanfe', w.nfeDownloadSimpleDanfe(nfe_files, uuid, auth))
  download('nfe.xml', 'nfeDownloadXml', w.nfeDownloadXml(nfe_files, uuid, assert(w.models['api1_files.NfeDownloadXmlQuery'].from_json('{}', cf)), auth))
  -- Cancellation is attempted for every approved document, even after a failed read.
  local cancel = assert(w.models['api1_fiscal.NfeCancelRequest'].from_json('{"uuid":' .. quoted(uuid) .. ',"motivo":"Cancelamento de teste em homologacao"}', c1))
  local cancelled, cerr = call(w.nfeCancelDocument(nfe, cancel))
  cancel:close()
  if not cancelled then
    if fail('nfe.cancel', 'nfeCancelDocument', cerr, uuid) then record('nfe', uuid, 'unknown', 'nfeCancelDocument'); return false end
    return true
  end
  record('nfe', uuid, cancelled:get_status(), 'nfeCancelDocument')
  cancelled:close()
  note('nfe.cancel', 'nfeCancelDocument', true, 'success', uuid)
  -- The cancellation XML exists only for a document whose cancellation was confirmed.
  if cancel_settled('nfe', 'nfeGetDocument', 'nfeCancelDocument', PROCESSING, uuid, poll(PROCESSING, function() return nfe_status(uuid) end)) then
    download('nfe.cancellation_xml', 'nfeDownloadCancellationXml',
      w.nfeDownloadCancellationXml(nfe_files, uuid, assert(w.models['api1_files.NfeDownloadCancellationXmlQuery'].from_json('{}', cf)), auth))
  end
  return true
end

-- Returns false when an unknown outcome stopped the run.
local function nfse_cycle(body)
  local issued, err = call(w.emitterIssueNfse(emitter, body))
  body:close()
  if not issued then
    if fail('nfse.issue', 'emitterIssueNfse', err) then record('nfse', '', 'unknown', 'emitterIssueNfse'); return false end
    return true
  end
  local uuid = issued:get_uuid()
  if uuid then record('nfse', uuid, issued:get_status(), 'emitterIssueNfse') end
  issued:close()
  if not uuid then note('nfse.issue', 'emitterIssueNfse', false, 'not_a_document'); return true end
  note('nfse.issue', 'emitterIssueNfse', true, 'success', uuid)
  local function nfse_status()
    local r, rerr = call(w.emitterGetNfse(emitter, uuid))
    if not r then return nil, rerr end
    local s = r:get_status()
    r:close()
    return s
  end
  local status, perr = poll(PROCESSING, nfse_status)
  if perr and fail('nfse.consult', 'emitterGetNfse', perr, uuid) then return false end
  record('nfse', uuid, status, 'emitterGetNfse')
  if status ~= 'aprovado' then note('nfse.consult', 'emitterGetNfse', false, 'not_approved', uuid); return true end
  note('nfse.consult', 'emitterGetNfse', true, 'success', uuid)
  local auth = w.FileAuth.issuer()
  local xml, xerr = call(w.fileGetNfseXml(emitter_files, uuid, auth))
  if xml then file_line('nfse.xml', 'fileGetNfseXml', xml, uuid); xml:close() else fail('nfse.xml', 'fileGetNfseXml', xerr, uuid) end
  local pdf, perr = call(w.fileGetNfsePdf(emitter_files, uuid, auth))
  if pdf then
    if pdf:kind() == 'NfsePdfPending' or pdf:is_redirect() then note('nfse.pdf', 'fileGetNfsePdf', true, 'pending_or_redirect', uuid)
    else file_line('nfse.pdf', 'fileGetNfsePdf', pdf, uuid) end
    pdf:close()
  else
    fail('nfse.pdf', 'fileGetNfsePdf', perr, uuid)
  end
  local rps, rerr = call(w.fileGetNfseRpsPdf(emitter_files, uuid, auth))
  if rps then file_line('nfse.rps_pdf', 'fileGetNfseRpsPdf', rps, uuid); rps:close() else fail('nfse.rps_pdf', 'fileGetNfseRpsPdf', rerr, uuid) end
  local cancel = assert(w.models['api2_nfse_issuance.EmitterCancelNfsePayload'].from_json('{"uuid":' .. quoted(uuid) .. ',"motivo":1,"justificativa":"Cancelamento de teste em homologacao"}', c2))
  local cancelled, cerr = call(w.emitterCancelNfse(emitter, cancel))
  cancel:close()
  if not cancelled then
    if fail('nfse.cancel', 'emitterCancelNfse', cerr, uuid) then record('nfse', uuid, 'unknown', 'emitterCancelNfse'); return false end
    return true
  end
  record('nfse', uuid, cancelled:get_status(), 'emitterCancelNfse')
  cancelled:close()
  note('nfse.cancel', 'emitterCancelNfse', true, 'success', uuid)
  -- Consulted again while processando_cancelamento; the cancel itself is never resent.
  cancel_settled('nfse', 'emitterGetNfse', 'emitterCancelNfse', CANCELLING, uuid, poll(CANCELLING, nfse_status))
  return true
end

local stop = false
if nfe_body and not nfe_cycle(nfe_body) then stop = true end
if nfse_body then
  if stop then nfse_body:close() elseif not nfse_cycle(nfse_body) then stop = true end
end
if ledger then ledger:close() end
os.exit((stop or failed) and 1 or 0)
