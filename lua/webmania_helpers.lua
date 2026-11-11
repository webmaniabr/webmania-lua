-- Finite helpers: caller owns the clock/sleep integration and credentials.
local H = {}
function H.pages(fetch, first, limit, next_id)
  assert(math.type(limit) == 'integer' and limit > 0, 'finite positive page limit required')
  local id, n, seen, done = first, 0, {}, false
  return function()
    if done or n == limit then return nil end
    if id ~= nil then assert(type(id) == 'string', 'opaque page id required'); assert(not seen[id], 'page cycle'); seen[id] = true end
    n = n + 1
    local value, err = fetch(id)
    if err then done = true; return nil, err end
    if value == nil then done = true; return nil end
    local next_value = next_id(value)
    assert(next_value == nil or type(next_value) == 'string', 'opaque page id required')
    if next_value == nil then done = true end
    id = next_value
    return value
  end
end
function H.poll(fetch, finished, attempts, now, sleep)
  assert(math.type(attempts) == 'integer' and attempts > 0, 'finite positive poll limit required')
  local last
  for i = 1, attempts do
    if last then
      local current = now()
      assert(current >= last, 'monotonic clock required')
      if current - last < 5 then
        sleep(5 - (current - last))
        assert(now() - last >= 5, 'sleep must wait the requested duration')
      end
    end
    last = now()
    local value, err = fetch()
    if err or finished(value) then return value, err end
  end
  return nil, 'poll limit reached'
end
return H
