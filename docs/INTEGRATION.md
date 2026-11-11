# Detalhes técnicos de integração

Este documento reúne os detalhes técnicos do SDK para Lua que complementam o [README](../README.md): autenticação, URL base, limites de transporte, arquivos, relatórios e o tratamento do resultado fiscal. O texto é o mesmo que estava no README até esta versão.

## Escopo e disponibilidade

Integração de **Emissor Fiscal e Monitor Fiscal** em aplicações de servidor. O Emissor abrange NF-e/NFC-e na API1 e NFS-e, CT-e/CT-e OS, MDF-e, NFCom e DC-e na API2, com arquivos, eventos e as três operações gerenciais B2B públicas da API1. O Monitor mantém apenas as famílias de documentos e capacidades do seu contrato documentado.

Disponível no repositório público [github.com/webmaniabr/webmania-lua](https://github.com/webmaniabr/webmania-lua), com instalação a partir do clone (veja a seção Instalação). Ainda não há publicação em registro de pacotes; os nomes e versões abaixo identificam os pacotes gerados a partir desta fonte. Regras do provedor, aceitação fiscal real e plataformas adicionais permanecem com limitações explícitas.

## Visão geral para desenvolvedores

| Item | Detalhe |
|---|---|
| Status | Disponível no GitHub: versão `0.1.0-alpha.5` (rock `webmania` `0.1.0alpha5-1`, [rockspec](../webmania-0.1.0alpha5-1.rockspec) no repositório), instalada a partir do clone do repositório; ainda sem publicação no LuaRocks ou em outro registro de pacotes |
| Runtime | Lua 5.4 com inteiros de 64 bits; perfil medido Linux arm64/glibc 2.36; módulo nativo sobre o SDK C fixado em [dependency-lock.json](../dependency-lock.json) |
| Clientes (`require('webmania')`) | `NfeClient` (NF-e/NFC-e API 1.0), `NfeFilesClient`, `ResellerClient` (gerencial B2B API 1.0), `EmitterClient` (emissor API 2.0), `EmitterFilesClient`, `MonitorClient` (Monitor Fiscal) |
| Erros | Cada tarefa retorna `value, err` em `task:await()`; `err` expõe `kind()`, `status()` e `outcome_unknown()` |
| Contrato | Herdado do SDK C (contrato fixado por conteúdo, `contract_digest` `371a499f74012bb6b41f23642869dee4954e8394dcba7642edc701aedb3dd59e`, 14 módulos) e de [metadata/api-metadata.json](../metadata/api-metadata.json) |

### Autenticação

- **NF-e/NFC-e (API 1.0)** — `w.CompanyCredentials(consumer_key, consumer_secret, access_token, access_token_secret)` é enviada pelo SDK C nos cabeçalhos `X-Consumer-Key`, `X-Consumer-Secret`, `X-Access-Token` e `X-Access-Token-Secret`. `ResellerClient` usa `ResellerCredentials`.
- **API 2.0** — `EmitterClient` recebe um `IssuerToken` e `MonitorClient` um `MonitorToken`; ambos são enviados como `Authorization: Bearer <token>` e são credenciais distintas.

O exemplo abaixo lê as credenciais com `os.getenv` (`WEBMANIA_CONSUMER_KEY`, `WEBMANIA_CONSUMER_SECRET`, `WEBMANIA_ACCESS_TOKEN`, `WEBMANIA_ACCESS_TOKEN_SECRET`) e o worker de `WEBMANIA_WORKER_PATH`.

## Requisitos

Pacote Lua **0.1.0-alpha.5** (`0.1.0alpha5-1` no formato do LuaRocks), para Lua 5.4.9 com inteiros de 64 bits e Linux arm64/glibc 2.36. A facade usa o C SDK **0.1.0-alpha.7**, com os digests de fonte, binário, metadados e worker em [dependency-lock.json](../dependency-lock.json). Instale também seu worker e avisos de terceiros. Não há suporte verificado para macOS/Windows.

## Instalação

Instale primeiro o SDK C `0.1.0-alpha.7` a partir do clone de [webmania-c](https://github.com/webmaniabr/webmania-c), incluindo worker e licenças. O build do módulo por fonte requer a biblioteca C com PIC; o CMake da fonte C fixada já habilita PIC. `/caminho/c` aponta esse prefixo e `/caminho/lua` aponta a instalação Lua5.4 com seus headers. Com LuaRocks, CMake e compilador C11, a partir do clone deste repositório:

```sh
git clone https://github.com/webmaniabr/webmania-lua.git
cd webmania-lua
luarocks --lua-version=5.4 --lua-dir=/caminho/lua --tree=./rocks make webmania-0.1.0alpha5-1.rockspec WEBMANIA_DIR=/caminho/c --deps-mode=none
```

Com Lua5.4 da mesma instalação no PATH, configure os paths para a árvore escolhida e execute o exemplo salvo como `app.lua`:

```sh
eval "$(luarocks --lua-version=5.4 --lua-dir=/caminho/lua --tree=./rocks path)"
lua app.lua
```

Os comandos usam Lua e o pacote C já instalados, sem buscar dependências de registro. O rockspec compila a fonte do clone e não faz download. O consumidor não compila Rust nem executa o gerador.

## Primeira consulta

Configure somente a credencial do serviço escolhido, por instância, a partir de ambiente privado ou cofre de segredos. O exemplo não emite nem cancela documentos. Execute consultas apenas com conta e ambiente autorizados; uma origem de fixture controlada deve ser configurada explicitamente pela API do cliente.

```lua
local w = require('webmania')
local function required(name)
  return assert(os.getenv(name), 'Configure ' .. name .. '.')
end
local exit_code = 0
do
  local cfg <close> = w.Config():set_worker_path(required('WEBMANIA_WORKER_PATH'))
  local base = os.getenv('WEBMANIA_BASE_URL')
  if base then cfg:set_base_url(base) end
  local credentials <close> = w.CompanyCredentials(
    required('WEBMANIA_CONSUMER_KEY'), required('WEBMANIA_CONSUMER_SECRET'),
    required('WEBMANIA_ACCESS_TOKEN'), required('WEBMANIA_ACCESS_TOKEN_SECRET'))
  local client <close> = w.NfeClient(credentials, cfg)
  local task <close> = w.nfeGetSefazStatus(client)
  local value, err = task:await()
  if err then
    io.stderr:write(err:kind(), ' (', tostring(err:status()), ')\n')
    exit_code = err:outcome_unknown() and 3 or 2
    err:close()
  elseif value then
    local status = value:get_status()
    if status then io.write(status, '\n') end
    value:close()
  end
end
os.exit(exit_code, true)
```

`WEBMANIA_WORKER_PATH` aponta para `libexec/webmania-native-worker` do prefixo C instalado. `WEBMANIA_BASE_URL` é opcional para uma origem documentada ou fixture controlada; não troque a origem com credenciais reais sem autorização. As quatro variáveis de credencial pertencem à empresa API1.

A construção do cliente não comprova habilitação da conta. Respostas de sucesso e conversões explícitas para JSON podem conter dados fiscais, credenciais novas ou URLs privadas. Exponha apenas os campos necessários à aplicação.

## Ambiente e URL base

Sem configuração, cada cliente usa a origem pública do seu serviço: `w.NfeClient` em `https://webmania.com.br/api`, `w.ResellerClient` em `https://webmania.com.br`, `w.NfeFilesClient` em `https://nfe.webmania.com.br` e os clientes do emissor, de arquivos do emissor e do Monitor em `https://api.webmania.com.br`. Para outro ambiente autorizado, use um `w.Config()` por serviço com `:set_base_url(...)` (origem HTTPS explícita e prefixo opcional); clientes de arquivo também exigem `:trust_file_origin(...)` com a mesma origem. Cada cliente envia requisições somente para a origem e o prefixo configurados, e uma origem inválida falha com erro de configuração antes de DNS ou conexão. O exemplo de homologação lê `WEBMANIA_API1_BASE_URL`, `WEBMANIA_FILES_BASE_URL` e `WEBMANIA_API2_BASE_URL`.

## Integração e limites

Cada operação recebe seu cliente e exatamente os parâmetros de metadata/api-metadata.json e das anotações Lua. Modelos têm new, from_json validado, construtores from_Variant e métodos set/get/presence/unset. Getters retornam cópias próprias que precisam de close. Índices de array começam em um. Algumas projeções de união usam o validador local do worker.

Number recebe texto JSON exato; Scalar.text/number/boolean/null escolhe a alternativa explicitamente. Não passe valores financeiros por lua_Number. Campos inteiros aceitam apenas o subtipo inteiro Lua, inclusive zero; 1.0 float é recusado. Extensões e mapas usam handles Json, sem conversão implícita de tabelas ou tostring.

Cada chamada devolve uma Task. poll não bloqueia; await espera e consome o resultado uma vez. Task.cancel funciona durante a rede. Task.close, client.close, GC e <close> cancelam e juntam o trabalho antes de liberar recursos. Uma Task retida mantém o proprietário C vivo; os threads não chamam a API Lua. Operações de preparação antes do retorno da Task são síncronas.

Erros preservam Unknown. reveal_recovery e reveal_location são acesso privado deliberado; tostring é redigido. Uma falha local de alocação sem metadado nativo é conservadoramente Unknown. fileGetNfsePdf pode retornar arquivo, redirect ou NfsePdfPending nominal. Pendência tem status/media_type/value e não tem bytes ou Location; HTML tem kind Html e bytes opacos.

`require('webmania_helpers')` oferece pages e poll finitos, com detecção de ciclos. Poll exige intervalo mínimo de cinco segundos e funções de relógio/sleep fornecidas pelo chamador que respeitem esse intervalo. Erro de fetch interrompe o helper, sem retry.

O vínculo fiscal contextual de alguns nomes JSON NFCom ainda depende de confirmação; o mapeamento de wire não encerra essa condição do contrato.

## Credenciais e resultado fiscal

Credenciais da empresa API1, revenda API1, Bearer do emissor API2 e Bearer Monitor pertencem a escopos diferentes. Arquivos exigem a modalidade de acesso documentada. Uma falha não autoriza trocar automaticamente o modo ou a credencial. Mantenha segredos no servidor.

O catálogo contém 103 operações nomeadas, 102 habilitadas. `nfeDownloadIbsCbsEventXml` não está disponível nesta versão do SDK: a função existe, mas falha com erro `capability` sem enviar requisição. Condições fiscais, municipais, de cadastro, provedor e implantação ainda pendentes continuam sujeitas ao contrato e ao serviço. Validação local, cálculo ou prévia não comprovam autorização fiscal.

Relatórios atuais são baixados com `w.fiscalDownloadReportV2(cliente_de_arquivos_do_emissor, uuid, auth)` (`/relatorios/{uuid}` na API2), usando a `url` devolvida pela criação/consulta do relatório: aceite somente uma URL da origem e do prefixo configurados seguida de `/relatorios/<uuid>`, com `w.FileAuth.anonymous()` (a URL é a capability) ou `w.FileAuth.issuer()`. Redirecionamentos não são seguidos. Relatórios legados continuam em `w.fiscalDownloadReport` com `w.FileAuth.public_report()`: CSV e XLSX chegam rotulados `text/xml` e o formato é identificado pelos bytes (assinatura ZIP = XLSX, caso contrário CSV completo preservado byte a byte); XML, HTML e JSON nunca são aceitos como relatório.

O download público do relatório API1 pode consumir quota mesmo por GET. Uma falha ambígua após possível envio preserva Unknown; uma rejeição completa conhecida e falhas anteriores ao envio mantêm sua classificação. A capability do relatório não é uma referência de recuperação e não autoriza repetição automática.

Não há retry automático de operação nem seguimento automático de redirects. Depois de possível envio de uma operação com efeito, uma falha pode indicar resultado desconhecido. Preserve o seletor original com segurança, consulte a tentativa anterior e decida explicitamente como prosseguir. Uma referência protegida exige acesso deliberado e pode estar ausente; não é uma chave de idempotência.

## Arquivos e processamento

Verifique tipo de resultado, status e representação antes de consumir bytes. JSON pendente, HTML e redirect não comprovam PDF pronto. Proteção de PDF/ZIP é distinta da autorização de download; não há descriptografia automática nem confirmação de autenticidade fiscal. O reconhecimento de formatos cobre somente o perfil documentado desta implementação. Uma Location revelada continua privada e exige decisão explícita de origem e autenticação para outra transferência.

Paginação e espera são optativas e limitadas quando disponíveis. Um estado futuro ou desconhecido não significa conclusão. Não repita emissão, cancelamento ou importação inicial como se fossem consultas de processamento.

Para migrar uma integração anterior, remapeie métodos, modelos e escopos de credencial pela referência desta versão. Não há promessa de substituição automática de outro SDK; compare também o changelog quando disponível.

## Documentação para assistentes e contratos

Índices em Markdown para assistentes: [documentação Webmania](https://webmania.com.br/docs/llms.txt) e [API 2.0](https://api.webmania.com.br/llms.txt). Contratos OpenAPI: [API 2.0](https://api.webmania.com.br/docs/openapi) e [NF-e](https://webmania.com.br/docs/rest-api-nfe/?format=openapi).

No catálogo de SDKs, `lua` aparece como disponível no repositório público, com instalação pelo clone; plataformas Lua 5.4 e Linux arm64. Estar listado nesses índices não amplia a cobertura documentada deste SDK.
