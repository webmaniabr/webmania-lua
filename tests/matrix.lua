local w=require("webmania")
local cfg=w.Config():set_base_url(arg[2]):set_worker_path(arg[4])
local f=assert(io.open(arg[3],"rb"));cfg:set_ca_pem(f:read("a"));f:close();cfg:trust_file_origin(arg[2])
local credentials={w.CompanyCredentials("synthetic-company-key","synthetic-secret","synthetic-token","synthetic-secret2"),w.ResellerCredentials("synthetic-reseller-key","synthetic-secret","synthetic-token","synthetic-secret2"),w.IssuerToken("synthetic-issuer"),w.MonitorToken("synthetic-monitor")}
local clients={Nfe=w.NfeClient(credentials[1],cfg),Reseller=w.ResellerClient(credentials[2],cfg),Emitter=w.EmitterClient(credentials[3],cfg),Monitor=w.MonitorClient(credentials[4],cfg),NfeFiles=w.NfeFilesClient(credentials[1],cfg),EmitterFiles=w.EmitterFilesClient(credentials[3],cfg)}
local which=assert(math.tointeger(arg[1])); local task
if false then
elseif which==0 then
task=w.nfeGetCertificateValidity(clients.Nfe)
elseif which==1 then
task=w.nfeGetSefazStatus(clients.Nfe)
elseif which==2 then
local query,error=w.models["api1_fiscal.NfeGetDocumentQuery"].from_json("{\"uuid\":\"00000000-0000-4000-8000-000000000001\"}",cfg);assert(query,error and error:kind())
task=w.nfeGetDocument(clients.Nfe,query)
elseif which==3 then
local body,error=w.models["api1_fiscal.NfeLookupRequest"].from_json("{\"chave\":\"00000000000000000000000000000000000000000000\"}",cfg);assert(body,error and error:kind())
task=w.nfeQueryDocument(clients.Nfe,body)
elseif which==4 then
local body,error=w.models["api1_fiscal.NfeCorrectionRequest"].from_json("{\"chave\":\"00000000000000000000000000000000000000000000\",\"correcao\":\"00000000-0000-4000-8000-000000000001\"}",cfg);assert(body,error and error:kind())
task=w.nfeCreateCorrection(clients.Nfe,body)
elseif which==5 then
local body,error=w.models["api1_fiscal.NfeManifestationRequest"].from_json("{\"chave\":\"00000000000000000000000000000000000000000000\",\"ambiente\":2,\"evento\":\"210240\",\"justificativa\":\"The goods were never delivered.\"}",cfg);assert(body,error and error:kind())
task=w.nfeCreateManifestation(clients.Nfe,body)
elseif which==6 then
local body,error=w.models["api1_fiscal.NfeCancelRequest"].from_json("{\"chave\":\"00000000000000000000000000000000000000000000\",\"motivo\":\"00000000-0000-4000-8000-000000000001\"}",cfg);assert(body,error and error:kind())
task=w.nfeCancelDocument(clients.Nfe,body)
elseif which==7 then
local body,error=w.models["api1_fiscal.NfeVoidRequest"].from_json("{\"sequencia\":\"00000000\",\"motivo\":\"00000000-0000-4000-8000-000000000001\",\"ambiente\":1,\"serie\":\"0\",\"modelo\":\"1\"}",cfg);assert(body,error and error:kind())
task=w.nfeVoidNumbering(clients.Nfe,body)
elseif which==8 then
local body,error=w.models["api1_fiscal.NfePaymentEventRequest"].from_json("{\"uuid\":\"00000000-0000-4000-8000-000000000000\",\"pagamento\":{\"forma_pagamento\":\"01\",\"valor_pagamento\":\"0.00\",\"data_pagamento\":\"2026-10-25\"}}",cfg);assert(body,error and error:kind())
task=w.nfeCreatePaymentEvent(clients.Nfe,body)
elseif which==9 then
local body,error=w.models["api1_fiscal.NfePaymentEventCancelRequest"].from_json("{\"uuid\":\"00000000-0000-4000-8000-000000000001\"}",cfg);assert(body,error and error:kind())
task=w.nfeCancelPaymentEvent(clients.Nfe,body)
elseif which==10 then
local body,error=w.models["api1_fiscal.NfeIbsCbsEventCancelRequest"].from_json("{\"uuid\":\"00000000-0000-4000-8000-000000000001\"}",cfg);assert(body,error and error:kind())
task=w.nfeCancelIbsCbsEvent(clients.Nfe,body)
elseif which==11 then
task=w.nfeListTaxClasses(clients.Nfe)
elseif which==12 then
local body,error=w.models["api1_fiscal.TaxClassDeleteRequest"].from_json("{\"referencia\":\"synthetic\"}",cfg);assert(body,error and error:kind())
task=w.nfeDeleteTaxClasses(clients.Nfe,body)
elseif which==13 then
local body,error=w.models["api1_fiscal.FiscalTaxClassRequest"].from_json("{\"descricao\":\"synthetic\",\"icms\":[{\"tipo_tributacao\":\"synthetic\",\"cenario\":\"synthetic\",\"tipo_pessoa\":\"synthetic\",\"codigo_cfop\":\"synthetic\",\"situacao_tributaria\":\"syn\"}],\"ipi\":[{\"cenario\":\"synthetic\",\"tipo_pessoa\":\"synthetic\",\"situacao_tributaria\":\"sy\",\"codigo_enquadramento\":\"syn\",\"aliquota\":\"0\"}],\"pis\":[{\"cenario\":\"synthetic\",\"tipo_pessoa\":\"synthetic\",\"situacao_tributaria\":\"sy\",\"aliquota\":\"0\"}],\"cofins\":[{\"cenario\":\"synthetic\",\"tipo_pessoa\":\"synthetic\",\"situacao_tributaria\":\"sy\",\"aliquota\":\"0\"}]}",cfg);assert(body,error and error:kind())
task=w.nfeSaveTaxClasses(clients.Nfe,body)
elseif which==14 then
local body,error=w.models["api1_fiscal.NfeIssueRequest"].from_json("{\"ID\":\"controlled-001\",\"modelo\":\"1\",\"operacao\":1,\"natureza_operacao\":\"Synthetic sale\",\"finalidade\":1,\"ambiente\":2,\"cliente\":{\"cpf\":\"000.000.000-00\",\"nome_completo\":\"Synthetic person\",\"endereco\":\"Synthetic street\",\"numero\":\"1\",\"bairro\":\"Synthetic district\",\"cidade\":\"Synthetic city\",\"uf\":\"SP\",\"cep\":\"01001-000\"},\"produtos\":[{\"nome\":\"Synthetic item\",\"codigo\":\"0001\",\"ncm\":\"0000.00.00\",\"quantidade\":\"1.0000\",\"unidade\":\"UN\",\"subtotal\":\"0.10\",\"total\":\"0.10\",\"origem\":0,\"impostos\":{\"icms\":{\"codigo_cfop\":\"5102\",\"situacao_tributaria\":\"102\"}}}],\"pedido\":{\"presenca\":1,\"modalidade_frete\":9,\"pagamento\":0,\"forma_pagamento\":\"01\",\"valor_pagamento\":\"0.10\"}}",cfg);assert(body,error and error:kind())
task=w.nfeIssueDocument(clients.Nfe,body)
elseif which==15 then
local body,error=w.models["api1_fiscal.NfeReturnRequest"].from_json("{\"classe_imposto\":\"synthetic\",\"chave\":\"00000000000000000000000000000000000000000000\",\"ambiente\":1,\"natureza_operacao\":\"synthetic\"}",cfg);assert(body,error and error:kind())
task=w.nfeIssueReturn(clients.Nfe,body)
elseif which==16 then
local body,error=w.models["api1_fiscal.NfeAdjustmentRequest"].from_json("{\"operacao\":0,\"natureza_operacao\":\"synthetic\",\"codigo_cfop\":\"5102\",\"ambiente\":1,\"cliente\":{}}",cfg);assert(body,error and error:kind())
task=w.nfeIssueAdjustment(clients.Nfe,body)
elseif which==17 then
local body,error=w.models["api1_fiscal.NfeComplementRequest"].from_json("{\"uuid\":\"00000000-0000-4000-8000-000000000001\",\"operacao\":1,\"natureza_operacao\":\"Synthetic complement\",\"ambiente\":2,\"cliente\":{\"cpf\":\"000.000.000-00\",\"nome_completo\":\"Synthetic person\",\"endereco\":\"Synthetic street\",\"numero\":\"1\",\"bairro\":\"Synthetic district\",\"cidade\":\"Synthetic city\",\"uf\":\"SP\",\"cep\":\"01001-000\"},\"impostos\":{\"ibs_cbs\":{\"situacao_tributaria\":\"000\",\"classificacao_tributaria\":\"000001\",\"base_calculo\":0}}}",cfg);assert(body,error and error:kind())
task=w.nfeIssueComplement(clients.Nfe,body)
elseif which==18 then
local body,error=w.models["api1_fiscal.FiscalCompanyUpdateRequest"].from_json("{\"cnae\":null}",cfg);assert(body,error and error:kind())
task=w.fiscalUpdateCompany(clients.Nfe,body)
elseif which==19 then
local body,error=w.models["api1_fiscal.FiscalReportRequest"].from_json("{\"modelo\":\"nfe\",\"relatorio\":\"danfe\",\"numero_inicio\":\"1\",\"numero_final\":\"5\"}",cfg);assert(body,error and error:kind())
task=w.fiscalCreateOrPollReport(clients.Nfe,body)
elseif which==20 then
local body,error=w.models["api1_fiscal.NfeIbsCbsEventRequest"].from_json("{\"chave\":\"00000000000000000000000000000000000000000000\",\"ambiente\":2,\"cod_evento\":\"112110\"}",cfg);assert(body,error and error:kind())
task=w.nfeCreateIbsCbsEvent(clients.Nfe,body)
elseif which==21 then
local body,error=w.models["api1_b2b.ResellerCreateCompaniesRequest"].from_json("{\"quantidade\":1}",cfg);assert(body,error and error:kind())
task=w.b2bV1CreateCompanies(clients.Reseller,body)
elseif which==22 then
task=w.b2bV1ListCompanies(clients.Reseller)
elseif which==23 then
local query,error=w.models["api1_b2b.B2bV1GetProcessedRequestsQuery"].from_json("{}",cfg);assert(query,error and error:kind())
task=w.b2bV1GetProcessedRequests(clients.Reseller,query)
elseif which==24 then
local body,error=w.models["api2_cte_issuance.EmitterIssueCtePayload"].from_json("{\"ambiente\":2,\"modelo\":\"cte_os\",\"natureza_operacao\":\"Synthetic passenger transport\",\"modalidade\":1,\"finalidade\":\"0\",\"contribuicao_tomador\":9,\"indicador_tomador\":4,\"local_inicio_prestacao\":{\"cidade\":\"Synthetic origin\",\"uf\":\"SP\"},\"local_termino_prestacao\":{\"cidade\":\"Synthetic destination\",\"uf\":\"RJ\"},\"tomador\":{\"cnpj\":\"00000000000000\",\"nome_razao\":\"Synthetic company\",\"endereco\":\"Synthetic street\",\"numero\":\"001\",\"bairro\":\"Synthetic\",\"cidade\":\"Synthetic city\",\"uf\":\"SP\"},\"servico\":{\"tipo\":6,\"descricao\":\"Synthetic passenger transport\",\"valor_total\":\"100.00\",\"valor_recebido\":\"100.00\"},\"carga\":{\"produto_predominante\":\"Synthetic service\",\"valor_total\":\"100.00\",\"quantidades\":[{\"quantidade\":\"1.0000\"}]},\"impostos\":{\"cfop\":\"6353\",\"classificacao_tributaria\":\"SN\"},\"documentos_fiscais\":[{\"numero\":\"001\",\"data_emissao\":\"2026-01-01\",\"valor_documento\":\"100.00\"}],\"rodoviario\":{\"taf_cte_os\":\"000000000000\",\"tipo_fretamento\":\"2\"}}",cfg);assert(body,error and error:kind())
task=w.emitterIssueCte(clients.Emitter,body)
elseif which==25 then
local body,error=w.models["api2_cte_issuance.EmitterIssueSimplifiedCtePayload"].from_json("{\"ambiente\":\"1\",\"modelo\":\"cte\",\"nfe_xml\":\"synthetic\"}",cfg);assert(body,error and error:kind())
task=w.emitterIssueSimplifiedCte(clients.Emitter,body)
elseif which==26 then
local body,error=w.models["api2_cte_issuance.EmitterCancelCtePayload"].from_json("{\"uuid\":\"00000000-0000-4000-8000-000000000000\",\"justificativa\":\"Synthetic cancellation justification\"}",cfg);assert(body,error and error:kind())
task=w.emitterCancelCte(clients.Emitter,body)
elseif which==27 then
local body,error=w.models["api2_cte_issuance.EmitterCorrectCtePayload"].from_json("{\"alteracoes\":[{\"campo\":\"synthetic\",\"grupo\":\"synthetic\",\"valor\":\"synthetic\"}],\"uuid\":\"00000000-0000-4000-8000-000000000001\"}",cfg);assert(body,error and error:kind())
task=w.emitterCorrectCte(clients.Emitter,body)
elseif which==28 then
local body,error=w.models["api2_cte_issuance.EmitterConfirmCteDeliveryPayload"].from_json("{\"uuid\":\"00000000-0000-4000-8000-000000000001\",\"notas_fiscais\":[\"123456ab12cd34ef5600000000000000000000000000\"],\"comprovante\":\"SYNTHETIC_IMAGE_PLACEHOLDER\"}",cfg);assert(body,error and error:kind())
task=w.emitterConfirmCteDelivery(clients.Emitter,body)
elseif which==29 then
local body,error=w.models["api2_cte_issuance.EmitterCancelCteDeliveryPayload"].from_json("{\"uuid\":\"00000000-0000-4000-8000-000000000001\",\"protocolo\":\"synthetic\",\"sequencia\":\"synthetic\"}",cfg);assert(body,error and error:kind())
task=w.emitterCancelCteDelivery(clients.Emitter,body)
elseif which==30 then
local body,error=w.models["api2_cte_issuance.EmitterLinkCtePaymentPayload"].from_json("{\"pagamento\":{\"cnpj_base_psp\":\"00000000\",\"cnpj_recebedor\":\"00000000000000\",\"id_transacao\":\"synthetic\",\"n_pag\":1,\"tp_meio_pagamento\":\"synthetic\"},\"uuid\":\"00000000-0000-4000-8000-000000000001\"}",cfg);assert(body,error and error:kind())
task=w.emitterLinkCtePayment(clients.Emitter,body)
elseif which==31 then
local body,error=w.models["api2_cte_issuance.EmitterCancelCtePaymentLinkPayload"].from_json("{\"uuid\":\"00000000-0000-4000-8000-000000000001\",\"protocolo_vinculacao\":\"000000000000000\",\"sequencia_vinculacao\":1}",cfg);assert(body,error and error:kind())
task=w.emitterCancelCtePaymentLink(clients.Emitter,body)
elseif which==32 then
task=w.emitterGetCte(clients.Emitter,"synthetic")
elseif which==33 then
task=w.emitterGetCtePaymentEvents(clients.Emitter,"synthetic")
elseif which==34 then
local body,error=w.models["api2_dce_issuance.EmitterIssueDcePayload"].from_json("{\"ambiente\":\"1\",\"itens\":[{\"descricao\":\"synthetic\",\"ncm\":\"00000000\",\"quantidade\":0.0,\"valor_unitario\":0.0}],\"cliente\":{\"cnpj\":\"00000000000000\",\"cpf\":\"00000000000\",\"identificacao_alternativa\":\"synthetic\",\"nome_completo\":\"synthetic\",\"razao_social\":\"synthetic\"},\"emitente\":{\"cnpj\":\"00000000000000\",\"cpf\":\"00000000000\",\"identificacao_alternativa\":\"synthetic\",\"nome_completo\":\"synthetic\",\"razao_social\":\"synthetic\"}}",cfg);assert(body,error and error:kind())
task=w.emitterIssueDce(clients.Emitter,body)
elseif which==35 then
local body,error=w.models["api2_dce_issuance.EmitterCancelDcePayload"].from_json("{\"chave\":\"123456ab12cd34ef5600000000000000000000000000\",\"justificativa\":\"Synthetic schema example only\"}",cfg);assert(body,error and error:kind())
task=w.emitterCancelDce(clients.Emitter,body)
elseif which==36 then
task=w.emitterGetDce(clients.Emitter,"synthetic")
elseif which==37 then
local query,error=w.models["api2_emitter_reads.EmitterGetNfseProviderStatusQuery"].from_json("{}",cfg);assert(query,error and error:kind())
task=w.emitterGetNfseProviderStatus(clients.Emitter,query)
elseif which==38 then
task=w.emitterGetNfcomServiceStatus(clients.Emitter)
elseif which==39 then
task=w.emitterGetNfse(clients.Emitter,"synthetic")
elseif which==40 then
task=w.emitterGetNfcom(clients.Emitter,"00000000-0000-4000-8000-000000000001")
elseif which==41 then
task=w.emitterGetNfcomPaymentEvents(clients.Emitter,"00000000-0000-4000-8000-000000000001")
elseif which==42 then
local body,error=w.models["api2_emitter_reads.NfseManifestationRequest"].from_json("{\"ambiente\":2,\"chave\":\"00000000000000000000000000000000000000000000000000\",\"manifestador\":1,\"evento\":1}",cfg);assert(body,error and error:kind())
task=w.emitterManifestNfse(clients.Emitter,body)
elseif which==43 then
local body,error=w.models["api2_mdfe_issuance.EmitterIssueMdfePayload"].from_json("{\"ambiente\":\"1\",\"carregamento\":[{\"nome_municipio\":\"synthetic\"}],\"descarregamento\":[{\"documentos_fiscais\":[{\"chave\":\"00000000000000000000000000000000000000000000\"}],\"nome_municipio\":\"synthetic\"}],\"emitente\":\"1\",\"modalidade\":\"1\",\"peso_bruto\":\"synthetic\",\"uf_carregamento\":\"synthetic\",\"uf_descarregamento\":\"synthetic\",\"unidade\":\"01\",\"valor_carga\":\"synthetic\",\"rodoviario\":{}}",cfg);assert(body,error and error:kind())
task=w.emitterIssueMdfe(clients.Emitter,body)
elseif which==44 then
local body,error=w.models["api2_mdfe_issuance.EmitterCloseMdfePayload"].from_json("{\"uuid\":\"00000000-0000-4000-8000-000000000001\",\"codigo_municipio\":\"0000000\",\"municipio\":\"synthetic\",\"uf\":\"synthetic\"}",cfg);assert(body,error and error:kind())
task=w.emitterCloseMdfe(clients.Emitter,body)
elseif which==45 then
local body,error=w.models["api2_mdfe_issuance.EmitterCancelMdfePayload"].from_json("{\"chave\":\"123456ab12cd34ef5600000000000000000000000000\",\"justificativa\":\"Synthetic schema example only\"}",cfg);assert(body,error and error:kind())
task=w.emitterCancelMdfe(clients.Emitter,body)
elseif which==46 then
local body,error=w.models["api2_mdfe_issuance.EmitterAddMdfeConductorPayload"].from_json("{\"cpf\":\"synthetic\",\"nome\":\"synthetic\",\"uuid\":\"00000000-0000-4000-8000-000000000001\"}",cfg);assert(body,error and error:kind())
task=w.emitterAddMdfeConductor(clients.Emitter,body)
elseif which==47 then
task=w.emitterGetMdfe(clients.Emitter,"synthetic")
elseif which==48 then
local body,error=w.models["api2_nfcom_issuance.EmitterIssueNfcomPayload"].from_json("{\"ambiente\":2,\"natureza_operacao\":\"Synthetic communication\",\"tipo_operacao\":1,\"finalidade\":1,\"tipo_faturamento\":0,\"cliente\":{\"cnpj\":\"00000000000000\",\"razao_social\":\"Synthetic company\",\"indicador_ie\":9,\"endereco\":{\"logradouro\":\"Synthetic street\",\"numero\":\"001\",\"bairro\":\"Synthetic\",\"codigo_municipio\":\"3550308\",\"municipio\":\"Synthetic municipality\",\"uf\":\"SP\",\"cep\":\"00000000\"}},\"assinante\":{\"codigo\":\"SYNTHETIC\",\"tipo\":1,\"tipo_servico\":4,\"contrato\":{\"numero\":\"SYNTHETIC\",\"data_inicio\":\"2026-01-01\",\"data_fim\":\"2026-12-31\"}},\"itens\":[{\"descricao\":\"Synthetic communication service\",\"unidade\":\"MES\",\"quantidade\":\"1.0000\",\"valor_unitario\":\"99.90\",\"valor_total\":\"99.90\",\"indicador_total\":1,\"classe_imposto\":\"REF123456\"}]}",cfg);assert(body,error and error:kind())
task=w.emitterIssueNfcom(clients.Emitter,body)
elseif which==49 then
local body,error=w.models["api2_nfcom_issuance.EmitterCancelNfcomPayload"].from_json("{\"chave\":\"123456ab12cd34ef5600000000000000000000000000\",\"justificativa\":\"Synthetic schema example only\"}",cfg);assert(body,error and error:kind())
task=w.emitterCancelNfcom(clients.Emitter,body)
elseif which==50 then
local body,error=w.models["api2_nfse_issuance.EmitterIssueNfsePayload"].from_json("{\"ambiente\":2,\"rps\":[{\"servico\":{\"discriminacao\":\"Synthetic service\",\"valor_servicos\":\"100.00\",\"iss_retido\":2}}]}",cfg);assert(body,error and error:kind())
task=w.emitterIssueNfse(clients.Emitter,body)
elseif which==51 then
local body,error=w.models["api2_nfse_issuance.EmitterCancelNfsePayload"].from_json("{\"uuid\":\"00000000-0000-4000-8000-000000000001\"}",cfg);assert(body,error and error:kind())
task=w.emitterCancelNfse(clients.Emitter,body)
elseif which==52 then
local body,error=w.models["api2_nfse_issuance.EmitterReplaceNfsePayload"].from_json("{\"ambiente\":2,\"motivo\":1,\"chave\":\"00000000000000000000000000000000000000000000000000\",\"rps\":[{\"servico\":{\"classe_imposto\":\"SYNTHETIC\",\"discriminacao\":\"Synthetic service\",\"valor_servicos\":\"1.00\"}}]}",cfg);assert(body,error and error:kind())
task=w.emitterReplaceNfse(clients.Emitter,body)
elseif which==53 then
local body,error=w.models["api2_monitor_documents.MonitorSearchRequest"].from_json("{\"modelo\":\"nfe\",\"filtros\":{\"empresa_uuid\":[\"00000000-0000-0000-0000-000000000000\"],\"categoria\":[\"recebidas\"],\"status\":[\"aprovado\"]},\"filtros_modelo\":{\"operacao\":[\"0\",1]},\"paginacao\":\"cursor\"}",cfg);assert(body,error and error:kind())
local query,error=w.models["api2_monitor_documents.MonitorSearchDocumentsQuery"].from_json("{}",cfg);assert(query,error and error:kind())
task=w.monitorSearchDocuments(clients.Monitor,body,query)
elseif which==54 then
local query,error=w.models["api2_monitor_documents.MonitorGetDocumentQuery"].from_json("{}",cfg);assert(query,error and error:kind())
task=w.monitorGetDocument(clients.Monitor,"00000000-0000-4000-8000-000000000001",query)
elseif which==55 then
task=w.monitorListDocumentEvents(clients.Monitor,"00000000-0000-4000-8000-000000000001")
elseif which==56 then
local body,error=w.models["api2_monitor_documents.MonitorManifestationRequest"].from_json("{\"evento\":1,\"manifestacao\":3,\"justificativa\":\"Synthetic justified operation\"}",cfg);assert(body,error and error:kind())
task=w.monitorManifestDocument(clients.Monitor,"00000000-0000-4000-8000-000000000001",body)
elseif which==57 then
local query,error=w.models["api2_monitor_documents.MonitorListReportsQuery"].from_json("{}",cfg);assert(query,error and error:kind())
task=w.monitorListReports(clients.Monitor,query)
elseif which==58 then
task=w.monitorDownloadReport(clients.Monitor,"00000000-0000-4000-8000-000000000001")
elseif which==59 then
local body,error=w.models["api2_monitor_documents.MonitorImportRequest"].from_json("{\"empresa_uuid\":\"00000000-0000-4000-8000-000000000000\",\"chave\":\"00000000000000000000000000000000000000000000\"}",cfg);assert(body,error and error:kind())
task=w.monitorImportDocument(clients.Monitor,body)
elseif which==60 then
task=w.monitorGetImportStatus(clients.Monitor,"00000000-0000-4000-8000-000000000001")
elseif which==61 then
local body,error=w.models["api2_monitor_management.MonitorCreateCompanyRequest"].from_json("{\"cnpj\":\"00000000000000\",\"razao_social\":\"Synthetic company\",\"cep\":\"01001000\",\"certificado_base64\":\"PHRlc3QvPg==\",\"certificado_senha\":\"synthetic-placeholder\"}",cfg);assert(body,error and error:kind())
task=w.monitorCreateCompany(clients.Monitor,body)
elseif which==62 then
local body,error=w.models["api2_monitor_management.MonitorUpdateCompanyRequest"].from_json("{\"modelos_download\":[]}",cfg);assert(body,error and error:kind())
task=w.monitorUpdateCompany(clients.Monitor,"00000000-0000-4000-8000-000000000001",body)
elseif which==63 then
local body,error=w.models["api2_monitor_management.MonitorCreateMunicipalityRequest"].from_json("{\"codigo_ibge\":\"3550308\"}",cfg);assert(body,error and error:kind())
task=w.monitorCreateCompanyMunicipality(clients.Monitor,"00000000-0000-4000-8000-000000000001",body)
elseif which==64 then
local body,error=w.models["api2_monitor_management.MonitorUpdateMunicipalityRequest"].from_json("{}",cfg);assert(body,error and error:kind())
task=w.monitorUpdateCompanyMunicipality(clients.Monitor,"00000000-0000-4000-8000-000000000001","00000000-0000-4000-8000-000000000001",body)
elseif which==65 then
task=w.monitorDeleteCompanyMunicipality(clients.Monitor,"00000000-0000-4000-8000-000000000001","00000000-0000-4000-8000-000000000001")
elseif which==66 then
local query,error=w.models["api2_monitor_reads.MonitorListCompaniesQuery"].from_json("{}",cfg);assert(query,error and error:kind())
task=w.monitorListCompanies(clients.Monitor,query)
elseif which==67 then
task=w.monitorGetCompany(clients.Monitor,"00000000-0000-4000-8000-000000000001")
elseif which==68 then
local query,error=w.models["api2_monitor_reads.MonitorListCompanyMunicipalitiesQuery"].from_json("{}",cfg);assert(query,error and error:kind())
task=w.monitorListCompanyMunicipalities(clients.Monitor,"00000000-0000-4000-8000-000000000001",query)
elseif which==69 then
task=w.monitorGetCompanyMunicipality(clients.Monitor,"00000000-0000-4000-8000-000000000001","00000000-0000-4000-8000-000000000001")
elseif which==70 then
local query,error=w.models["api2_monitor_reads.MonitorListAvailableMunicipalitiesQuery"].from_json("{}",cfg);assert(query,error and error:kind())
task=w.monitorListAvailableMunicipalities(clients.Monitor,query)
elseif which==71 then
local query,error=w.models["api2_monitor_reads.MonitorGetDownloadStatisticsQuery"].from_json("{}",cfg);assert(query,error and error:kind())
task=w.monitorGetDownloadStatistics(clients.Monitor,query)
elseif which==72 then
task=w.nfeDownloadDanfe(clients.NfeFiles,"00000000-0000-4000-8000-000000000001",w.FileAuth.company())
elseif which==73 then
task=w.nfeDownloadSimpleDanfe(clients.NfeFiles,"00000000-0000-4000-8000-000000000001",w.FileAuth.company())
elseif which==74 then
task=w.nfeDownloadLabelDanfe(clients.NfeFiles,"00000000-0000-4000-8000-000000000001",w.FileAuth.company())
elseif which==75 then
task=w.nfeDownloadCorrectionPdf(clients.NfeFiles,"00000000-0000-4000-8000-000000000001",w.FileAuth.company())
elseif which==76 then
task=w.nfeDownloadCorrectionPdfSequence(clients.NfeFiles,"00000000-0000-4000-8000-000000000001",1,w.FileAuth.company())
elseif which==77 then
local query,error=w.models["api1_files.NfeDownloadXmlQuery"].from_json("{}",cfg);assert(query,error and error:kind())
task=w.nfeDownloadXml(clients.NfeFiles,"00000000-0000-4000-8000-000000000001",query,w.FileAuth.company())
elseif which==78 then
local query,error=w.models["api1_files.NfeDownloadCancellationXmlQuery"].from_json("{}",cfg);assert(query,error and error:kind())
task=w.nfeDownloadCancellationXml(clients.NfeFiles,"00000000-0000-4000-8000-000000000001",query,w.FileAuth.company())
elseif which==79 then
local query,error=w.models["api1_files.NfeDownloadCorrectionXmlQuery"].from_json("{}",cfg);assert(query,error and error:kind())
task=w.nfeDownloadCorrectionXml(clients.NfeFiles,"00000000-0000-4000-8000-000000000001",query,w.FileAuth.company())
elseif which==80 then
local query,error=w.models["api1_files.NfeDownloadCorrectionXmlSequenceQuery"].from_json("{}",cfg);assert(query,error and error:kind())
task=w.nfeDownloadCorrectionXmlSequence(clients.NfeFiles,"00000000-0000-4000-8000-000000000001",1,query,w.FileAuth.company())
elseif which==81 then
local query,error=w.models["api1_files.NfeDownloadManifestationXmlQuery"].from_json("{}",cfg);assert(query,error and error:kind())
task=w.nfeDownloadManifestationXml(clients.NfeFiles,"00000000-0000-4000-8000-000000000001",query,w.FileAuth.company())
elseif which==82 then
local query,error=w.models["api1_files.NfeDownloadPaymentEventXmlQuery"].from_json("{}",cfg);assert(query,error and error:kind())
task=w.nfeDownloadPaymentEventXml(clients.NfeFiles,"00000000-0000-4000-8000-000000000001",query,w.FileAuth.company())
elseif which==83 then
local query,error=w.models["api1_files.NfeDownloadPaymentEventXmlSequenceQuery"].from_json("{}",cfg);assert(query,error and error:kind())
task=w.nfeDownloadPaymentEventXmlSequence(clients.NfeFiles,"00000000-0000-4000-8000-000000000001",1,query,w.FileAuth.company())
elseif which==84 then
local query,error=w.models["api1_files.NfeDownloadIbsCbsEventXmlQuery"].from_json("{}",cfg);assert(query,error and error:kind())
local ok,err=pcall(w.nfeDownloadIbsCbsEventXml,clients.NfeFiles,"00000000-0000-4000-8000-000000000001",query,w.FileAuth.company());assert(not ok and type(err)=="string" and err:find("webmania capability: operation not available in this SDK release",1,true),tostring(err));io.write("blocked");os.exit(0)
elseif which==85 then
task=w.fiscalDownloadReport(clients.NfeFiles,"00000000-0000-4000-8000-000000000001",w.FileAuth.public_report())
elseif which==86 then
task=w.fileGetNfseXml(clients.EmitterFiles,"00000000-0000-4000-8000-000000000001",w.FileAuth.issuer())
elseif which==87 then
task=w.fileGetNfsePdf(clients.EmitterFiles,"00000000-0000-4000-8000-000000000001",w.FileAuth.issuer())
elseif which==88 then
task=w.fileGetNfseRpsPdf(clients.EmitterFiles,"00000000-0000-4000-8000-000000000001",w.FileAuth.issuer())
elseif which==89 then
task=w.fileGetCteXml(clients.EmitterFiles,"00000000-0000-4000-8000-000000000001",w.FileAuth.issuer())
elseif which==90 then
task=w.fileGetCteCancelXml(clients.EmitterFiles,"00000000-0000-4000-8000-000000000001",w.FileAuth.issuer())
elseif which==91 then
task=w.fileGetCtePdf(clients.EmitterFiles,"00000000-0000-4000-8000-000000000001",w.FileAuth.issuer())
elseif which==92 then
task=w.fileGetCteCorrectionXml(clients.EmitterFiles,"00000000-0000-4000-8000-000000000001",w.FileAuth.issuer())
elseif which==93 then
task=w.fileGetCteCorrectionPdf(clients.EmitterFiles,"00000000-0000-4000-8000-000000000001",w.FileAuth.issuer())
elseif which==94 then
task=w.fileGetMdfeXml(clients.EmitterFiles,"00000000-0000-4000-8000-000000000001",w.FileAuth.issuer())
elseif which==95 then
task=w.fileGetMdfePdf(clients.EmitterFiles,"00000000-0000-4000-8000-000000000001",w.FileAuth.issuer())
elseif which==96 then
task=w.fileGetNfcomXml(clients.EmitterFiles,"00000000-0000-4000-8000-000000000001",w.FileAuth.issuer())
elseif which==97 then
task=w.fileGetNfcomCancelXml(clients.EmitterFiles,"00000000-0000-4000-8000-000000000001",w.FileAuth.issuer())
elseif which==98 then
task=w.fileGetNfcomPdf(clients.EmitterFiles,"00000000-0000-4000-8000-000000000001",w.FileAuth.issuer())
elseif which==99 then
task=w.fileGetDceXml(clients.EmitterFiles,"00000000-0000-4000-8000-000000000001",w.FileAuth.issuer())
elseif which==100 then
task=w.fileGetDceCancelXml(clients.EmitterFiles,"00000000-0000-4000-8000-000000000001",w.FileAuth.issuer())
elseif which==101 then
task=w.fileGetDcePdf(clients.EmitterFiles,"00000000-0000-4000-8000-000000000001",w.FileAuth.issuer())
elseif which==102 then
task=w.fiscalDownloadReportV2(clients.EmitterFiles,"00000000-0000-4000-8000-000000000001",w.FileAuth.issuer())
else error("unknown case") end
local value,error=task:await();assert(value,error and error:kind());if value.bytes then local bytes=assert(value:bytes());io.write((bytes:gsub(".",function(c)return string.format("%02x",string.byte(c))end))) else io.write(value:to_json()) end
task:close();value:close();for _,c in pairs(clients) do c:close() end;for _,c in ipairs(credentials) do c:close() end;cfg:close()
