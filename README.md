<p align="center"><img src=".github/assets/webmania-logo.png" alt="Webmania" width="320"></p>

# Webmania SDK para Lua

Através do emissor fiscal da Webmania®, você conta com a emissão e o arquivamento dos seus documentos fiscais, cálculo automático de impostos, geração do DANFE para impressão e envio automático de e-mails para os clientes. Com este SDK, o seu sistema em Lua se integra à nossa REST API para emitir, consultar e cancelar NF-e, NFC-e, NFS-e, CT-e, MDF-e, NFCom e DC-e, baixar XML e PDF dos documentos e usar o Monitor Fiscal.

- Emissor de Nota Fiscal Webmania®: [Saiba mais](https://webmania.com.br/nota-fiscal-eletronica/)
- Documentação da REST API: [Visualizar](https://webmania.com.br/docs/)
- Índice da documentação para assistentes de IA: [llms.txt](https://webmania.com.br/docs/llms.txt)

## Requisitos

- Contrate um dos planos de Nota Fiscal Eletrônica da Webmania®: [Assine agora mesmo](https://webmania.com.br/nota-fiscal-eletronica/#plans-section).
- Lua 5.4 (inteiros de 64 bits) e LuaRocks.
- Linux arm64 com glibc 2.36 ou superior.
- O SDK para C instalado a partir do clone de [webmania-c](https://github.com/webmaniabr/webmania-c) (seção Instalação do README dele), com o worker e as licenças; os digests esperados estão em [dependency-lock.json](dependency-lock.json).
- Credenciais de acesso da sua empresa, disponíveis no [Painel de Controle](https://webmania.com.br/painel/).

## Instalação

O SDK é distribuído pelo repositório [github.com/webmaniabr/webmania-lua](https://github.com/webmaniabr/webmania-lua) e ainda não está publicado no LuaRocks. Com o SDK para C instalado em `/caminho/c`, clone o repositório e compile o módulo:

```sh
git clone https://github.com/webmaniabr/webmania-lua.git
cd webmania-lua
luarocks --lua-version=5.4 --lua-dir=/caminho/lua --tree=./rocks make webmania-0.1.0alpha5-1.rockspec WEBMANIA_DIR=/caminho/c --deps-mode=none
```

Com o Lua 5.4 da mesma instalação no PATH, configure os caminhos da árvore e execute a sua aplicação:

```sh
eval "$(luarocks --lua-version=5.4 --lua-dir=/caminho/lua --tree=./rocks path)"
lua app.lua
```

## Credenciais

Cada serviço usa a sua própria credencial. Guarde-as em variáveis de ambiente (ou em um cofre de segredos) no servidor e nunca as escreva no código-fonte:

| Variável de ambiente | Uso |
|---|---|
| `WEBMANIA_CONSUMER_KEY`, `WEBMANIA_CONSUMER_SECRET`, `WEBMANIA_ACCESS_TOKEN`, `WEBMANIA_ACCESS_TOKEN_SECRET` | NF-e e NFC-e (`w.NfeClient`) e arquivos da NF-e (`w.NfeFilesClient`) |
| `WEBMANIA_ISSUER_TOKEN` | NFS-e, CT-e, MDF-e, NFCom e DC-e (`w.EmitterClient`) e seus arquivos (`w.EmitterFilesClient`) |
| `WEBMANIA_MONITOR_TOKEN` | Monitor Fiscal (`w.MonitorClient`) |

```lua
local w = require('webmania')

-- caminho absoluto de libexec/webmania-native-worker no prefixo C instalado
local config = w.Config():set_worker_path(os.getenv('WEBMANIA_WORKER_PATH'))
local credenciais = w.CompanyCredentials(
  os.getenv('WEBMANIA_CONSUMER_KEY'), os.getenv('WEBMANIA_CONSUMER_SECRET'),
  os.getenv('WEBMANIA_ACCESS_TOKEN'), os.getenv('WEBMANIA_ACCESS_TOKEN_SECRET'))
local token_emissor = w.IssuerToken(os.getenv('WEBMANIA_ISSUER_TOKEN'))

local nfe = w.NfeClient(credenciais, config)           -- NF-e e NFC-e
local emissor = w.EmitterClient(token_emissor, config)  -- NFS-e, CT-e, MDF-e, NFCom e DC-e
```

Cada operação devolve uma tarefa; `tarefa:await()` espera e devolve `valor, erro`. Feche clientes, tarefas e valores com `close()` (ou declare-os com `<close>`) quando não precisar mais deles.

## Utilização

Os exemplos abaixo usam o ambiente de **homologação** (`ambiente` 2), em que os documentos não têm validade fiscal. Para emitir em produção, envie `ambiente` 1. Os pedidos são montados a partir de JSON; informe valores decimais como texto (`"44.90"`) para manter a precisão.

### Status do SEFAZ e certificado A1

```lua
local sefaz = w.nfeGetSefazStatus(nfe):await()
if sefaz then print(sefaz:get_status()) end  -- online ou offline

local certificado = w.nfeGetCertificateValidity(nfe):await()
if certificado then print(certificado:get_expiration()) end  -- dias até o vencimento do certificado A1
```

### Emitir NF-e

Para emitir uma NF-e, monte o pedido a partir do JSON da nota e use `w.nfeIssueDocument`. A mesma função emite NFC-e com `"modelo": 2`.

```lua
local pedido = w.models['api1_fiscal.NfeIssueRequest'].from_json([[{
  "operacao": 1,
  "natureza_operacao": "Venda de produção do estabelecimento",
  "modelo": 1,
  "finalidade": 1,
  "ambiente": 2,
  "cliente": {
    "cpf": "000.000.000-00", "nome_completo": "Nome do Cliente",
    "endereco": "Av. Brg. Faria Lima", "numero": "1000", "bairro": "Itaim Bibi",
    "cidade": "São Paulo", "uf": "SP", "cep": "00000-000", "email": "nome@email.com"
  },
  "produtos": [{
    "nome": "Nome do produto", "codigo": "nome-do-produto", "ncm": "6109.10.00",
    "quantidade": "1", "unidade": "UN", "origem": 0,
    "subtotal": "44.90", "total": "44.90", "classe_imposto": "REF1000"
  }],
  "pedido": {"presenca": 2, "modalidade_frete": 9, "pagamento": 0, "forma_pagamento": "01", "total": "44.90"}
}]], config)

local resultado, erro = w.nfeIssueDocument(nfe, pedido):await()
local uuid
if resultado then
  local nota = resultado:get_NfeDocument(config)
  uuid = nota:get_uuid()    -- identificador único da nota fiscal
  print(nota:get_status())  -- aprovado, reprovado, processamento...
  print(nota:get_chave())   -- chave de acesso
  print(nota:get_xml())     -- URL do XML
  print(nota:get_danfe())   -- URL do DANFE (PDF)
  print(nota:get_motivo())  -- retorno do SEFAZ
end
```

Somente o status `aprovado` indica uma nota autorizada. Quando o retorno for `processamento`, consulte a nota alguns segundos depois.

### Consultar NF-e

```lua
local consulta = w.models['api1_fiscal.NfeGetDocumentQuery'].from_json('{"uuid": "' .. uuid .. '"}', config)
local resposta = w.nfeGetDocument(nfe, consulta):await()
if resposta then print(resposta:get_NfeDocument(config):get_status()) end
```

A consulta também aceita a chave de acesso (`{"chave": "..."}`).

### Cancelar NF-e

```lua
local cancelamento = w.models['api1_fiscal.NfeCancelRequest'].from_json(
  '{"uuid": "' .. uuid .. '", "motivo": "Cancelamento por erro no pedido."}', config)  -- motivo: mínimo de 15 caracteres
local cancelada = w.nfeCancelDocument(nfe, cancelamento):await()
if cancelada then print(cancelada:get_status()) end
```

### Baixar o DANFE e o XML

O cliente de arquivos usa uma configuração própria, que confia na origem pública dos arquivos da NF-e:

```lua
local config_arquivos = w.Config():set_worker_path(os.getenv('WEBMANIA_WORKER_PATH'))
config_arquivos:trust_file_origin('https://nfe.webmania.com.br')
local arquivos = w.NfeFilesClient(credenciais, config_arquivos)
local acesso = w.FileAuth.company()

local danfe = w.nfeDownloadDanfe(arquivos, uuid, acesso):await()
if danfe then
  local pdf = assert(io.open('danfe.pdf', 'wb')); pdf:write(danfe:bytes()); pdf:close()
end

local consulta_xml = w.models['api1_files.NfeDownloadXmlQuery'].from_json('{}', config_arquivos)
local xml = w.nfeDownloadXml(arquivos, uuid, consulta_xml, acesso):await()
if xml then
  local arquivo = assert(io.open('nfe.xml', 'wb')); arquivo:write(xml:bytes()); arquivo:close()
end
```

### Emitir, consultar e cancelar NFS-e

A NFS-e é emitida a partir de um ou mais RPS com `w.emitterIssueNfse`:

```lua
local rps = w.models['api2_nfse_issuance.EmitterIssueNfsePayload'].from_json([[{
  "ambiente": 2,
  "rps": [{
    "servico": {
      "valor_servicos": "15.00",
      "discriminacao": "Prestação de serviço referente ao mês 10/2026",
      "classe_imposto": "REF000000"
    },
    "tomador": {"cpf": "000.000.000-00", "nome_completo": "Nome do tomador"}
  }]
}]], config)
local nfse = assert(w.emitterIssueNfse(emissor, rps):await())
local uuid_nfse = nfse:get_uuid()
print(nfse:get_status())

local consulta_nfse = assert(w.emitterGetNfse(emissor, uuid_nfse):await())
print(consulta_nfse:get_status(), consulta_nfse:get_numero())

local cancela = w.models['api2_nfse_issuance.EmitterCancelNfsePayload'].from_json(
  '{"uuid": "' .. uuid_nfse .. '", "motivo": "1", "justificativa": "Serviço cancelado a pedido do tomador."}', config)
-- motivo: código do motivo (veja a documentação da NFS-e); justificativa: mínimo de 15 caracteres
local cancelada_nfse = assert(w.emitterCancelNfse(emissor, cancela):await())
print(cancelada_nfse:get_status())
```

### Tratamento de erros

Quando a operação falha, `await()` devolve `nil` e o erro:

```lua
local emitida, erro = w.nfeIssueDocument(nfe, pedido):await()
if erro then
  print(erro:kind())     -- validation (dados recusados antes do envio), business (recusa da API ou do SEFAZ), http, timeout...
  print(erro:status())   -- status HTTP, quando houver
  print(erro:message())  -- mensagem, com dados sensíveis mascarados
  if erro:outcome_unknown() then
    -- A requisição pode ter sido processada: consulte a nota antes de emitir de novo.
  end
  erro:close()
end
```

O SDK não repete requisições automaticamente. Se uma emissão ou um cancelamento terminar com `outcome_unknown()` verdadeiro, consulte o documento antes de tentar novamente, para não emitir em duplicidade.

## Métodos disponíveis

**NF-e e NFC-e** — `w.NfeClient`

- **w.nfeIssueDocument**: Emissão de NF-e ou NFC-e junto ao SEFAZ.
- **w.nfeGetDocument**: Consulta da nota fiscal pelo UUID, pela chave de acesso ou pelo ID do pedido.
- **w.nfeCancelDocument**: Cancelamento de NF-e ou NFC-e.
- **w.nfeCreateCorrection**: Carta de correção.
- **w.nfeVoidNumbering**: Inutilização de sequência de numeração.
- **w.nfeIssueReturn**: Emissão de NF-e de devolução.
- **w.nfeIssueComplement**: Emissão de NF-e complementar.
- **w.nfeIssueAdjustment**: Emissão de NF-e de ajuste.
- **w.nfeCreateManifestation**: Manifestação do destinatário.
- **w.nfeCreatePaymentEvent** / **w.nfeCancelPaymentEvent**: Evento de conciliação financeira (ECONF) e o seu cancelamento.
- **w.nfeCreateIbsCbsEvent** / **w.nfeCancelIbsCbsEvent**: Eventos de IBS/CBS e o seu cancelamento.
- **w.nfeListTaxClasses** / **w.nfeSaveTaxClasses** / **w.nfeDeleteTaxClasses**: Classes de imposto.
- **w.fiscalCreateOrPollReport**: Relatórios fiscais.
- **w.fiscalUpdateCompany**: Atualização dos dados da empresa emissora.
- **w.nfeGetSefazStatus**: Verifica se o SEFAZ está online ou offline.
- **w.nfeGetCertificateValidity**: Verifica quantos dias faltam para o certificado A1 expirar.

**NFS-e** — `w.EmitterClient`

- **w.emitterIssueNfse**: Emissão de NFS-e a partir de RPS.
- **w.emitterGetNfse**: Consulta da NFS-e.
- **w.emitterCancelNfse**: Cancelamento da NFS-e.
- **w.emitterReplaceNfse**: Substituição de NFS-e.
- **w.emitterManifestNfse**: Manifestação sobre NFS-e nacional.
- **w.emitterGetNfseProviderStatus**: Recursos do provedor de NFS-e do município da empresa.

**CT-e e CT-e OS** — `w.EmitterClient`

- **w.emitterIssueCte** / **w.emitterIssueSimplifiedCte**: Emissão de CT-e, CT-e OS e CT-e simplificado.
- **w.emitterGetCte**: Consulta do CT-e.
- **w.emitterCancelCte**: Cancelamento do CT-e.
- **w.emitterCorrectCte**: Carta de correção do CT-e.
- **w.emitterConfirmCteDelivery** / **w.emitterCancelCteDelivery**: Comprovante de entrega e o seu cancelamento.
- **w.emitterLinkCtePayment** / **w.emitterCancelCtePaymentLink** / **w.emitterGetCtePaymentEvents**: Eventos de pagamento do CT-e.

**MDF-e** — `w.EmitterClient`

- **w.emitterIssueMdfe**: Emissão do MDF-e.
- **w.emitterGetMdfe**: Consulta do MDF-e pela chave de acesso.
- **w.emitterCloseMdfe**: Encerramento do MDF-e.
- **w.emitterCancelMdfe**: Cancelamento do MDF-e.
- **w.emitterAddMdfeConductor**: Inclusão de condutor.

**NFCom e DC-e** — `w.EmitterClient`

- **w.emitterIssueNfcom** / **w.emitterGetNfcom** / **w.emitterCancelNfcom**: Emissão, consulta e cancelamento da NFCom.
- **w.emitterGetNfcomPaymentEvents**: Eventos de pagamento da NFCom.
- **w.emitterGetNfcomServiceStatus**: Disponibilidade do serviço da NFCom no SEFAZ.
- **w.emitterIssueDce** / **w.emitterGetDce** / **w.emitterCancelDce**: Emissão, consulta e cancelamento da DC-e.

**Arquivos (XML e PDF)** — `w.NfeFilesClient` e `w.EmitterFilesClient`

- **w.nfeDownloadDanfe** / **w.nfeDownloadSimpleDanfe** / **w.nfeDownloadLabelDanfe**: DANFE completo, simplificado e etiqueta.
- **w.nfeDownloadXml** / **w.nfeDownloadCancellationXml**: XML da NF-e e do cancelamento.
- **w.nfeDownloadCorrectionPdf** / **w.nfeDownloadCorrectionXml**: PDF e XML da carta de correção.
- **w.fileGetNfseXml** / **w.fileGetNfsePdf** / **w.fileGetNfseRpsPdf**: XML e PDF da NFS-e e PDF do RPS.
- **w.fileGetCteXml** / **w.fileGetCtePdf** / **w.fileGetMdfeXml** / **w.fileGetMdfePdf** / **w.fileGetNfcomXml** / **w.fileGetNfcomPdf** / **w.fileGetDceXml** / **w.fileGetDcePdf**: XML e PDF de CT-e, MDF-e, NFCom e DC-e.

**Monitor Fiscal** — `w.MonitorClient`

- **w.monitorSearchDocuments** / **w.monitorGetDocument** / **w.monitorListDocumentEvents**: Busca e consulta de documentos recebidos e do histórico de eventos.
- **w.monitorManifestDocument**: Manifestação do destinatário.
- **w.monitorImportDocument** / **w.monitorGetImportStatus**: Importação por chave de acesso, XML ou ZIP.
- **w.monitorListCompanies** / **w.monitorCreateCompany** / **w.monitorUpdateCompany**: Empresas monitoradas.

**Gerencial B2B** — `w.ResellerClient`

- **w.b2bV1CreateCompanies** / **w.b2bV1ListCompanies** / **w.b2bV1GetProcessedRequests**: Cadastro de empresas, listagem e contagem de notas processadas por empresa.

A lista completa, com todas as funções do Monitor Fiscal e dos arquivos, está em [docs/OPERATIONS.md](docs/OPERATIONS.md); os parâmetros de cada uma estão em `lua/webmania_annotations.lua`.

## Exemplo completo em homologação

A pasta [examples/homologacao](examples/homologacao) traz um programa que emite, consulta, baixa os arquivos e cancela uma NF-e e uma NFS-e em homologação, usando as credenciais das variáveis de ambiente. Por segurança, ele só envia requisições quando `WEBMANIA_LIVE=1` está definido e `WEBMANIA_LIVE_ALLOWED_HOSTS` lista os hosts da API. Para rodar só as consultas (status do SEFAZ, certificado e provedor de NFS-e):

```sh
WEBMANIA_LIVE=1 WEBMANIA_LIVE_SCOPE=readonly WEBMANIA_LIVE_ALLOWED_HOSTS=webmania.com.br,nfe.webmania.com.br,api.webmania.com.br sh examples/homologacao/run.sh
```

As variáveis aceitas e o formato da saída estão em [examples/homologacao/README.md](examples/homologacao/README.md).

## Documentação

- Documentação da REST API: [NF-e / NFC-e](https://webmania.com.br/docs/rest-api-nfe/) · [NFS-e](https://webmania.com.br/docs/rest-api-nfse/) · [CT-e](https://webmania.com.br/docs/rest-api-cte/) · [MDF-e](https://webmania.com.br/docs/rest-api-mdfe/) · [NFCom](https://webmania.com.br/docs/rest-api-nfcom/) · [DC-e](https://webmania.com.br/docs/rest-api-dce/) · [Monitor Fiscal](https://webmania.com.br/docs/rest-api-monitor-fiscal/) · [Gerencial B2B](https://webmania.com.br/docs/rest-api-gerencial-b2b/)
- Contratos OpenAPI: [API 2.0](https://api.webmania.com.br/docs/openapi) e [NF-e](https://webmania.com.br/docs/rest-api-nfe/?format=openapi)
- Detalhes técnicos do SDK (URL base, arquivos, relatórios, limites): [docs/INTEGRATION.md](docs/INTEGRATION.md)
- Lista completa de funções: [docs/OPERATIONS.md](docs/OPERATIONS.md)
- Desenvolvimento e testes do SDK: [docs/TESTING.md](docs/TESTING.md)
- Histórico de versões: [CHANGELOG.md](CHANGELOG.md)

## Suporte

Qualquer dúvida entre em contato na nossa [Central de Ajuda](https://ajuda.webmania.com.br) ou acesse o [Painel de Controle](https://webmania.com.br/painel/) para conversar em tempo real no Chat ou Abrir um chamado.

## Licença

Licença proprietária Webmania®: veja [LICENSE](LICENSE) e os [Termos de Uso](https://webmania.com.br/termos-de-uso/). As dependências de terceiros mantêm as suas próprias licenças.
