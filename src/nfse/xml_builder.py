"""
Construtor de XML para DPS (Declaração de Prestação de Serviço)
Baseado no schema XSD oficial da NFSe Nacional
"""

import os
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional

import xmlschema
from lxml import etree

from .models import DPS, IBSCBS, Endereco, IBSCBSDestinatario, Prestador, Servico, Tomador


class XMLBuilder:
    """Classe responsável por construir o XML do DPS conforme schema XSD oficial"""

    # Namespace oficial da NFSe Nacional
    NS_NFSE = "http://www.sped.fazenda.gov.br/nfse"
    NS_DS = "http://www.w3.org/2000/09/xmldsig#"

    def __init__(self, xsd_path: Optional[str] = None, versao: str = "1.01"):
        """
        Inicializa o construtor de XML

        Args:
            xsd_path: Caminho opcional para o arquivo XSD para validação
            versao: Versão do DPS (padrão: 1.01)
        """
        self.versao = versao
        self.xsd_path = xsd_path
        self._schema = None

        # Tenta carregar o schema se o caminho foi fornecido
        if xsd_path and os.path.exists(xsd_path):
            self._load_schema(xsd_path)

    def _load_schema(self, xsd_path: str):
        """Carrega o schema XSD para validação usando xmlschema"""
        try:
            # Converte para Path para facilitar manipulação
            xsd_file = Path(xsd_path)
            if not xsd_file.exists():
                print(f"Arquivo XSD não encontrado: {xsd_path}")
                self._schema = None
                return

            # Carrega o schema usando xmlschema
            self._schema = xmlschema.XMLSchema(str(xsd_file), build=True)

        except xmlschema.XMLSchemaException as e:
            print(f"Erro ao carregar o schema XSD: {e}")
            self._schema = None
        except Exception as e:
            print(f"Erro inesperado ao carregar o schema XSD: {e}")
            import traceback

            traceback.print_exc()
            self._schema = None

    def build_dps_xml(self, dps: DPS, validate: bool = False) -> str:
        """
        Constrói o XML completo do DPS conforme schema XSD

        Args:
            dps: Objeto DPS com todos os dados
            validate: Se True, valida o XML contra o XSD (requer xsd_path configurado)

        Returns:
            String XML do DPS

        Raises:
            ValueError: Se validate=True mas não há schema carregado
            etree.DocumentInvalid: Se o XML não passar na validação
        """
        # Elemento raiz DPS com namespace e versão
        root = etree.Element(
            f"{{{self.NS_NFSE}}}DPS", nsmap={None: self.NS_NFSE}, versao=self.versao
        )

        # Elemento infDPS com Id obrigatório (atributo do schema)
        # O Id é construído com a lógica: DPS{cod_municipio}{tipo_inscricao}{cpf_cnpj_emitente}{serie_dps}{numero_dps}
        # O Id é usado para referenciar o elemento na assinatura digital
        dps_id = dps.get_id()
        inf_dps = etree.SubElement(root, f"{{{self.NS_NFSE}}}infDPS", Id=dps_id)

        # Campos obrigatórios do infDPS
        self._add_inf_dps(inf_dps, dps)

        # Validação contra XSD se solicitada
        if validate:
            if self._schema is None:
                raise ValueError(
                    "Validação solicitada mas nenhum schema XSD foi carregado. "
                    "Configure xsd_path no construtor ou use validate=False."
                )
            try:
                # xmlschema precisa validar a string XML, não o elemento
                xml_string_temp = etree.tostring(root, encoding="utf-8").decode("utf-8")
                self._schema.validate(xml_string_temp)
            except xmlschema.XMLSchemaException as e:
                raise ValueError(f"XML não passou na validação XSD: {e}") from e

        # Converte para string XML
        xml_string = etree.tostring(
            root, encoding="utf-8", xml_declaration=True, pretty_print=True
        ).decode("utf-8")
        # print("xml_string", xml_string)
        return xml_string

    def _add_inf_dps(self, parent, dps: DPS):
        """Adiciona os campos do infDPS (TCInfDPS)"""
        # tpAmb - Tipo de ambiente (1-Produção, 2-Homologação)
        tp_amb = getattr(dps, "tp_amb", 2)  # Default: Homologação
        etree.SubElement(parent, f"{{{self.NS_NFSE}}}tpAmb").text = str(tp_amb)

        # dhEmi - Data e hora de emissão (formato UTC)
        dh_emi = dps.data_emissao if dps.data_emissao else datetime.now()
        etree.SubElement(parent, f"{{{self.NS_NFSE}}}dhEmi").text = dh_emi.strftime(
            "%Y-%m-%dT%H:%M:%S-03:00"
        )

        # verAplic - Versão do aplicativo
        ver_aplic = getattr(dps, "ver_aplic", "1.0")
        etree.SubElement(parent, f"{{{self.NS_NFSE}}}verAplic").text = str(ver_aplic)

        # serie - Série do DPS
        serie = dps.serie_rps or "NF"
        etree.SubElement(parent, f"{{{self.NS_NFSE}}}serie").text = str(serie)

        # nDPS - Número do DPS
        n_dps = dps.numero_rps.lstrip("0") or "1"
        etree.SubElement(parent, f"{{{self.NS_NFSE}}}nDPS").text = str(n_dps)

        # dCompet - Data de competência (AAAA-MM-DD)
        d_compet = dps.data_emissao if dps.data_emissao else datetime.now()
        etree.SubElement(parent, f"{{{self.NS_NFSE}}}dCompet").text = d_compet.strftime("%Y-%m-%d")

        # tpEmit - Tipo de emitente (1-Prestador, 2-Tomador, 3-Intermediário)
        tp_emit = getattr(dps, "tp_emit", 1)  # Default: Prestador
        etree.SubElement(parent, f"{{{self.NS_NFSE}}}tpEmit").text = str(tp_emit)

        # cLocEmi - Código do município emissor (IBGE)
        c_loc_emi = getattr(
            dps,
            "c_loc_emi",
            dps.prestador.endereco.codigo_municipio if dps.prestador.endereco else None,
        )
        if not c_loc_emi:
            raise ValueError("cLocEmi (código do município emissor) é obrigatório")
        etree.SubElement(parent, f"{{{self.NS_NFSE}}}cLocEmi").text = str(c_loc_emi)

        # Prestador (obrigatório)
        self._add_prestador(parent, dps.prestador)

        # Tomador (opcional)
        if dps.tomador:
            self._add_tomador(parent, dps.tomador)

        # Serviço (obrigatório)
        self._add_servico(parent, dps.servicos[0] if dps.servicos else None)

        # Valores (obrigatório)
        self._add_valores(parent, dps)

        # IBSCBS - Grupo de informações declaradas pelo emitente referentes
        # ao IBS e à CBS (Reforma Tributária). Elemento de mesmo nível que
        # <serv> e <valores>, adicionado por último conforme sequência do XSD.
        if getattr(dps, "ibscbs", None):
            self._add_ibscbs(parent, dps.ibscbs)

    def _add_ibscbs(self, parent, ibscbs: IBSCBS):
        """Adiciona o grupo IBSCBS declarado pelo emitente (TCRTCInfoIBSCBS)"""
        ibscbs_elem = etree.SubElement(parent, f"{{{self.NS_NFSE}}}IBSCBS")

        # finNFSe - Finalidade da emissão (obrigatório, único valor válido: "0")
        etree.SubElement(ibscbs_elem, f"{{{self.NS_NFSE}}}finNFSe").text = str(ibscbs.fin_nfse)

        # indFinal - Uso/consumo pessoal, art. 57 (opcional)
        if ibscbs.ind_final is not None:
            etree.SubElement(ibscbs_elem, f"{{{self.NS_NFSE}}}indFinal").text = str(
                ibscbs.ind_final
            )

        # cIndOp - Código indicador da operação de fornecimento (obrigatório)
        etree.SubElement(ibscbs_elem, f"{{{self.NS_NFSE}}}cIndOp").text = str(ibscbs.c_ind_op)

        # tpOper - Tipo de operação com entes governamentais / bens imóveis (opcional)
        if ibscbs.tp_oper is not None:
            etree.SubElement(ibscbs_elem, f"{{{self.NS_NFSE}}}tpOper").text = str(ibscbs.tp_oper)

        # tpEnteGov - Tipo de ente governamental (opcional)
        if ibscbs.tp_ente_gov is not None:
            etree.SubElement(ibscbs_elem, f"{{{self.NS_NFSE}}}tpEnteGov").text = str(
                ibscbs.tp_ente_gov
            )

        # indDest - A respeito do destinatário dos serviços (obrigatório)
        etree.SubElement(ibscbs_elem, f"{{{self.NS_NFSE}}}indDest").text = str(ibscbs.ind_dest)

        # dest - Destinatário (obrigatório quando indDest = "1")
        if ibscbs.destinatario:
            self._add_ibscbs_destinatario(ibscbs_elem, ibscbs.destinatario)

        # valores/trib/gIBSCBS - Situação e classificação tributária (obrigatório)
        valores_elem = etree.SubElement(ibscbs_elem, f"{{{self.NS_NFSE}}}valores")
        trib_elem = etree.SubElement(valores_elem, f"{{{self.NS_NFSE}}}trib")
        g_ibscbs = etree.SubElement(trib_elem, f"{{{self.NS_NFSE}}}gIBSCBS")

        tributacao = ibscbs.trib

        # CST - Código de Situação Tributária do IBS/CBS (obrigatório, 3 dígitos)
        etree.SubElement(g_ibscbs, f"{{{self.NS_NFSE}}}CST").text = str(tributacao.cst)

        # cClassTrib - Código de Classificação Tributária (obrigatório, 6 dígitos)
        etree.SubElement(g_ibscbs, f"{{{self.NS_NFSE}}}cClassTrib").text = str(
            tributacao.c_class_trib
        )

        # cCredPres - Código do Crédito Presumido (opcional, 2 dígitos)
        if tributacao.c_cred_pres:
            etree.SubElement(g_ibscbs, f"{{{self.NS_NFSE}}}cCredPres").text = str(
                tributacao.c_cred_pres
            )

        # gTribRegular - Tributação regular (opcional)
        if tributacao.cst_regular and tributacao.c_class_trib_regular:
            g_trib_regular = etree.SubElement(g_ibscbs, f"{{{self.NS_NFSE}}}gTribRegular")
            etree.SubElement(g_trib_regular, f"{{{self.NS_NFSE}}}CSTReg").text = str(
                tributacao.cst_regular
            )
            etree.SubElement(g_trib_regular, f"{{{self.NS_NFSE}}}cClassTribReg").text = str(
                tributacao.c_class_trib_regular
            )

        # gDif - Diferimento (opcional)
        if (
            tributacao.p_dif_uf is not None
            or tributacao.p_dif_mun is not None
            or tributacao.p_dif_cbs is not None
        ):
            g_dif = etree.SubElement(g_ibscbs, f"{{{self.NS_NFSE}}}gDif")
            etree.SubElement(g_dif, f"{{{self.NS_NFSE}}}pDifUF").text = self._format_decimal(
                tributacao.p_dif_uf
            )
            etree.SubElement(g_dif, f"{{{self.NS_NFSE}}}pDifMun").text = self._format_decimal(
                tributacao.p_dif_mun
            )
            etree.SubElement(g_dif, f"{{{self.NS_NFSE}}}pDifCBS").text = self._format_decimal(
                tributacao.p_dif_cbs
            )

    def _add_ibscbs_destinatario(self, parent, destinatario: IBSCBSDestinatario):
        """Adiciona o grupo dest (TCRTCInfoDest) do IBSCBS"""
        dest_elem = etree.SubElement(parent, f"{{{self.NS_NFSE}}}dest")

        # Choice: CNPJ ou CPF
        if len(destinatario.cpf_cnpj) == 11:
            etree.SubElement(dest_elem, f"{{{self.NS_NFSE}}}CPF").text = destinatario.cpf_cnpj
        elif len(destinatario.cpf_cnpj) == 14:
            etree.SubElement(dest_elem, f"{{{self.NS_NFSE}}}CNPJ").text = destinatario.cpf_cnpj
        else:
            raise ValueError("CPF/CNPJ do destinatário deve ter 11 ou 14 dígitos")

        # xNome - Nome/Razão social (obrigatório)
        etree.SubElement(dest_elem, f"{{{self.NS_NFSE}}}xNome").text = destinatario.razao_social

        # end - Endereço (opcional)
        if destinatario.endereco:
            self._add_endereco(dest_elem, destinatario.endereco)

        # fone - Telefone (opcional)
        if destinatario.telefone:
            etree.SubElement(dest_elem, f"{{{self.NS_NFSE}}}fone").text = destinatario.telefone

        # email - E-mail (opcional)
        if destinatario.email:
            etree.SubElement(dest_elem, f"{{{self.NS_NFSE}}}email").text = destinatario.email

    def _add_prestador(self, parent, prestador: Prestador):
        """Adiciona dados do prestador (TCInfoPrestador)"""
        prest_elem = etree.SubElement(parent, f"{{{self.NS_NFSE}}}prest")

        # Choice: CNPJ, CPF, NIF ou cNaoNIF
        if len(prestador.cpf_cnpj) == 11:
            etree.SubElement(prest_elem, f"{{{self.NS_NFSE}}}CPF").text = prestador.cpf_cnpj
        elif len(prestador.cpf_cnpj) == 14:
            etree.SubElement(prest_elem, f"{{{self.NS_NFSE}}}CNPJ").text = prestador.cpf_cnpj
        else:
            raise ValueError("CPF/CNPJ do prestador deve ter 11 ou 14 dígitos")

        # IM - Inscrição Municipal (opcional)
        if prestador.inscricao_municipal:
            etree.SubElement(
                prest_elem, f"{{{self.NS_NFSE}}}IM"
            ).text = prestador.inscricao_municipal

        # xNome - Nome/Razão Social (opcional)
        if prestador.razao_social:
            etree.SubElement(prest_elem, f"{{{self.NS_NFSE}}}xNome").text = prestador.razao_social

        # end - Endereço (opcional)
        if prestador.endereco:
            self._add_endereco(prest_elem, prestador.endereco)

        # fone - Telefone (opcional)
        if prestador.telefone:
            etree.SubElement(prest_elem, f"{{{self.NS_NFSE}}}fone").text = prestador.telefone

        # email - E-mail (opcional)
        if prestador.email:
            etree.SubElement(prest_elem, f"{{{self.NS_NFSE}}}email").text = prestador.email

        # regTrib - Regime de tributação (obrigatório)
        reg_trib = etree.SubElement(prest_elem, f"{{{self.NS_NFSE}}}regTrib")

        # opSimpNac - Situação perante Simples Nacional (obrigatório)
        # 1 - Não Optante, 2 - MEI, 3 - ME/EPP
        op_simp_nac = (
            prestador.op_simp_nac if prestador.optante_simples_nacional else 1
        )  # 1 = Não Optante
        etree.SubElement(reg_trib, f"{{{self.NS_NFSE}}}opSimpNac").text = str(op_simp_nac)

        # regApTribSN - Regime de apuração no Simples Nacional (opcional, apenas para ME/EPP)
        if prestador.optante_simples_nacional and prestador.reg_apuracao_sn is not None:
            etree.SubElement(reg_trib, f"{{{self.NS_NFSE}}}regApTribSN").text = str(
                prestador.reg_apuracao_sn
            )
        # regEspTrib - Regime especial de tributação (0-Nenhum, 1-Ato Cooperado, etc)
        reg_esp_trib = getattr(prestador, "reg_esp_trib", 0)
        etree.SubElement(reg_trib, f"{{{self.NS_NFSE}}}regEspTrib").text = str(reg_esp_trib)

    def _add_tomador(self, parent, tomador: Tomador):
        """Adiciona dados do tomador (TCInfoPessoa)"""
        toma_elem = etree.SubElement(parent, f"{{{self.NS_NFSE}}}toma")

        # Choice: CNPJ, CPF, NIF ou cNaoNIF
        if len(tomador.cpf_cnpj) == 11:
            etree.SubElement(toma_elem, f"{{{self.NS_NFSE}}}CPF").text = tomador.cpf_cnpj
        elif len(tomador.cpf_cnpj) == 14:
            etree.SubElement(toma_elem, f"{{{self.NS_NFSE}}}CNPJ").text = tomador.cpf_cnpj
        else:
            raise ValueError("CPF/CNPJ do tomador deve ter 11 ou 14 dígitos")

        # IM - Inscrição Municipal (opcional)
        if tomador.inscricao_municipal:
            etree.SubElement(toma_elem, f"{{{self.NS_NFSE}}}IM").text = tomador.inscricao_municipal.trim()

        # xNome - Nome/Razão Social (obrigatório)
        if tomador.razao_social:
            etree.SubElement(toma_elem, f"{{{self.NS_NFSE}}}xNome").text = tomador.razao_social

        # end - Endereço (opcional)
        if tomador.endereco:
            self._add_endereco(toma_elem, tomador.endereco)

        # fone - Telefone (opcional)
        if tomador.telefone:
            etree.SubElement(toma_elem, f"{{{self.NS_NFSE}}}fone").text = tomador.telefone

        # email - E-mail (opcional)
        if tomador.email:
            etree.SubElement(toma_elem, f"{{{self.NS_NFSE}}}email").text = tomador.email

    def _add_endereco(self, parent, endereco: Endereco):
        """Adiciona dados de endereço (TCEndereco)"""
        end_elem = etree.SubElement(parent, f"{{{self.NS_NFSE}}}end")

        # endNac - Endereço nacional (opcional, mas comum)
        if endereco.codigo_pais == "1058":  # Brasil
            end_nac = etree.SubElement(end_elem, f"{{{self.NS_NFSE}}}endNac")
            etree.SubElement(end_nac, f"{{{self.NS_NFSE}}}cMun").text = endereco.codigo_municipio
            etree.SubElement(end_nac, f"{{{self.NS_NFSE}}}CEP").text = endereco.cep.replace("-", "")

        # xLgr - Logradouro (obrigatório)
        etree.SubElement(end_elem, f"{{{self.NS_NFSE}}}xLgr").text = endereco.logradouro

        # nro - Número (obrigatório)
        etree.SubElement(end_elem, f"{{{self.NS_NFSE}}}nro").text = endereco.numero

        # xCpl - Complemento (opcional)
        if endereco.complemento:
            etree.SubElement(end_elem, f"{{{self.NS_NFSE}}}xCpl").text = endereco.complemento

        # xBairro - Bairro (obrigatório)
        etree.SubElement(end_elem, f"{{{self.NS_NFSE}}}xBairro").text = endereco.bairro

    def _add_servico(self, parent, servico: Optional[Servico]):
        """Adiciona dados do serviço (TCServ)"""
        if not servico:
            raise ValueError("Pelo menos um serviço é obrigatório")

        serv_elem = etree.SubElement(parent, f"{{{self.NS_NFSE}}}serv")

        # locPrest - Local da prestação
        loc_prest = etree.SubElement(serv_elem, f"{{{self.NS_NFSE}}}locPrest")
        if servico.codigo_municipio:
            etree.SubElement(
                loc_prest, f"{{{self.NS_NFSE}}}cLocPrestacao"
            ).text = servico.codigo_municipio
        else:
            etree.SubElement(
                loc_prest, f"{{{self.NS_NFSE}}}cPaisPrestacao"
            ).text = servico.codigo_pais

        # cServ - Código do serviço
        c_serv = etree.SubElement(serv_elem, f"{{{self.NS_NFSE}}}cServ")

        # cTribNac - Código de tributação nacional (6 dígitos)
        c_trib_nac = servico.codigo_servico
        etree.SubElement(c_serv, f"{{{self.NS_NFSE}}}cTribNac").text = c_trib_nac

        # cTribMun - Código de tributação municipal (opcional)
        if hasattr(servico, "codigo_tributacao_municipal") and servico.codigo_tributacao_municipal:
            etree.SubElement(
                c_serv, f"{{{self.NS_NFSE}}}cTribMun"
            ).text = servico.codigo_tributacao_municipal

        # xDescServ - Descrição do serviço (obrigatório)
        etree.SubElement(c_serv, f"{{{self.NS_NFSE}}}xDescServ").text = servico.descricao

        # cNBS - Código NBS (opcional)
        if hasattr(servico, "codigo_nbs") and servico.codigo_nbs:
            etree.SubElement(c_serv, f"{{{self.NS_NFSE}}}cNBS").text = servico.codigo_nbs

    def _add_valores(self, parent, dps: DPS):
        """Adiciona valores (TCInfoValores)"""
        valores_elem = etree.SubElement(parent, f"{{{self.NS_NFSE}}}valores")

        # vServPrest - Valores do serviço prestado
        v_serv_prest = etree.SubElement(valores_elem, f"{{{self.NS_NFSE}}}vServPrest")
        if dps.valor_total_servicos is not None:
            valor_total = dps.valor_total_servicos
        elif dps.servicos:
            valor_total = sum(s.valor_servico for s in dps.servicos)
        else:
            valor_total = Decimal("0.00")
        etree.SubElement(v_serv_prest, f"{{{self.NS_NFSE}}}vServ").text = self._format_decimal(
            valor_total
        )

        # vDescCondIncond - Descontos (opcional)
        if dps.valor_total_desconto and dps.valor_total_desconto > 0:
            v_desc = etree.SubElement(valores_elem, f"{{{self.NS_NFSE}}}vDescCondIncond")
            etree.SubElement(v_desc, f"{{{self.NS_NFSE}}}vDescIncond").text = self._format_decimal(
                dps.valor_total_desconto
            )

        # vDedRed - Dedução/Redução (opcional)
        if dps.valor_total_deducoes and dps.valor_total_deducoes > 0:
            v_ded_red = etree.SubElement(valores_elem, f"{{{self.NS_NFSE}}}vDedRed")
            etree.SubElement(v_ded_red, f"{{{self.NS_NFSE}}}vDR").text = self._format_decimal(
                dps.valor_total_deducoes
            )

        # trib - Tributação (obrigatório)
        trib = etree.SubElement(valores_elem, f"{{{self.NS_NFSE}}}trib")

        # tribMun - Tributação municipal (ISSQN)
        trib_mun = etree.SubElement(trib, f"{{{self.NS_NFSE}}}tribMun")

        # tribISSQN - Tipo de tributação do ISSQN (obrigatório)
        # 1 - Operação tributável, 2 - Imunidade, 3 - Exportação, 4 - Não Incidência
        trib_issqn = getattr(dps, "trib_issqn", 1)  # Default: Operação tributável
        etree.SubElement(trib_mun, f"{{{self.NS_NFSE}}}tribISSQN").text = str(trib_issqn)

        # Para cada serviço, adiciona informações de tributação
        if dps.servicos and len(dps.servicos) > 0:
            servico = dps.servicos[0]

            # cPaisResult - Código do país (opcional, apenas para exportação)
            if trib_issqn == 3 and hasattr(servico, "codigo_pais") and servico.codigo_pais:
                etree.SubElement(
                    trib_mun, f"{{{self.NS_NFSE}}}cPaisResult"
                ).text = servico.codigo_pais

            # tpImunidade - Tipo de imunidade (opcional, apenas para imunidade)
            if trib_issqn == 2 and hasattr(servico, "tp_imunidade"):
                etree.SubElement(trib_mun, f"{{{self.NS_NFSE}}}tpImunidade").text = str(
                    servico.tp_imunidade
                )

            # tpRetISSQN - Tipo de retenção do ISSQN (obrigatório)
            # 1 - Não Retido, 2 - Retido pelo Tomador, 3 - Retido pelo Intermediário
            if servico.iss_retido:
                tp_ret_issqn = 2  # Retido pelo Tomador (padrão)
                if hasattr(servico, "tp_ret_issqn"):
                    tp_ret_issqn = servico.tp_ret_issqn
            else:
                tp_ret_issqn = 1  # Não Retido
            etree.SubElement(trib_mun, f"{{{self.NS_NFSE}}}tpRetISSQN").text = str(tp_ret_issqn)

            # pAliq - Alíquota (opcional)
            if servico.tributos and len(servico.tributos) > 0:
                tributo = servico.tributos[0]
                if tributo.aliquota is not None and tributo.aliquota > 0:
                    etree.SubElement(
                        trib_mun, f"{{{self.NS_NFSE}}}pAliq"
                    ).text = self._format_decimal(tributo.aliquota)

        # tribFed - Tributação federal (opcional)
        # Pode conter PIS/COFINS, CP, IRRF, CSLL
        # Por enquanto, deixamos vazio (opcional)

        # totTrib - Totais de tributos (obrigatório conforme validação)
        tot_trib = etree.SubElement(trib, f"{{{self.NS_NFSE}}}totTrib")
        if dps.prestador.optante_simples_nacional:
            if dps.prestador.p_tot_trib_sn is not None:
                etree.SubElement(tot_trib, f"{{{self.NS_NFSE}}}pTotTribSN").text = self._format_decimal(
                    dps.prestador.p_tot_trib_sn
                )
        else:
            # Se não for optante do SN
            vTotTrib = etree.SubElement(tot_trib, f"{{{self.NS_NFSE}}}vTotTrib")
            etree.SubElement(vTotTrib, f"{{{self.NS_NFSE}}}vTotTribFed").text = "0.00"
            etree.SubElement(vTotTrib, f"{{{self.NS_NFSE}}}vTotTribEst").text = "0.00"
            etree.SubElement(vTotTrib, f"{{{self.NS_NFSE}}}vTotTribMun").text = "0.00"

            # Se não for optante do SN ou não tiver p_tot_trib_sn, usa indTotTrib=0
            #etree.SubElement(tot_trib, f"{{{self.NS_NFSE}}}indTotTrib").text = "0"

    def validate_xml(self, xml_string: str) -> bool:
        """
        Valida um XML contra o schema XSD

        Args:
            xml_string: String XML a ser validada

        Returns:
            True se válido, False caso contrário

        Raises:
            ValueError: Se não há schema carregado
        """
        if self._schema is None:
            raise ValueError("Nenhum schema XSD foi carregado. Configure xsd_path no construtor.")

        try:
            self._schema.validate(xml_string)
            return True
        except xmlschema.XMLSchemaException:
            return False

    def _format_decimal(self, value: Optional[Decimal]) -> str:
        """Formata Decimal para string com 2 casas decimais"""
        if value is None:
            return "0.00"
        return f"{value:.2f}"
