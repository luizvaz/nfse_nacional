"""
Modelos de dados para NFSe
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import List, Optional


@dataclass
class Endereco:
    """Modelo de endereço"""

    logradouro: str
    numero: str
    bairro: str
    codigo_municipio: str
    uf: str
    cep: str
    complemento: Optional[str] = None
    codigo_pais: str = "1058"  # Brasil


@dataclass
class Prestador:
    """Modelo de dados do prestador de serviços (emissor)"""

    cpf_cnpj: str
    inscricao_municipal: Optional[str] = None
    razao_social: Optional[str] = None
    endereco: Optional[Endereco] = None
    telefone: Optional[str] = None
    email: Optional[str] = None
    optante_simples_nacional: bool = False
    op_simp_nac: int = 1  # 1-Não Optante, 2-MEI, 3-ME/EPP
    reg_apuracao_sn: Optional[int] = (
        None  # 1-Regime de apuração dos tributos federais e municipal pelo SN, 2-Regime de apuração dos tributos federais pelo SN e ISSQN  por fora do SN conforme respectiva legislação municipal do tributo, 3-Regime de apuração dos tributos federais e municipal por fora do SN conforme respectivas legilações federal e municipal de cada tributo
    )
    reg_esp_trib: int = 0  # 0-Nenhum, 1-Ato Cooperado, 2-Estimativa, etc
    p_tot_trib_sn: Optional[Decimal] = None


@dataclass
class Tomador:
    """Modelo de dados do tomador de serviços"""

    cpf_cnpj: str
    razao_social: Optional[str] = None
    nome_fantasia: Optional[str] = None
    endereco: Optional[Endereco] = None
    telefone: Optional[str] = None
    email: Optional[str] = None
    inscricao_municipal: Optional[str] = None


@dataclass
class Tributo:
    """Modelo de dados de tributos"""

    aliquota: Decimal
    valor: Decimal
    base_calculo: Decimal
    codigo_tributacao: Optional[str] = None
    descricao: Optional[str] = None


@dataclass
class Servico:
    """Modelo de dados do serviço prestado"""

    codigo_servico: str
    descricao: str
    valor_servico: Decimal
    valor_deducoes: Decimal = Decimal("0.00")
    valor_desconto: Decimal = Decimal("0.00")
    valor_liquido: Decimal = Decimal("0.00")
    iss_retido: bool = False
    codigo_municipio: Optional[str] = None
    codigo_pais: str = "1058"  # Brasil
    tributos: List[Tributo] = field(default_factory=list)
    codigo_tributacao_municipal: Optional[str] = None
    codigo_nbs: Optional[str] = None
    tp_imunidade: Optional[int] = None  # Tipo de imunidade (0-5, apenas para imunidade)
    tp_ret_issqn: int = (
        2  # Tipo de retenção: 1-Não Retido, 2-Retido pelo Tomador, 3-Retido pelo Intermediário
    )


@dataclass
class DPS:
    """
    Modelo de dados da Declaração de Prestação de Serviço (DPS)

    O atributo 'Id' do elemento 'infDPS' no XML é construído automaticamente
    com a lógica: DPS{cod_municipio}{tipo_inscricao}{cpf_cnpj_emitente}{serie_dps}{numero_dps}
    """

    prestador: Prestador
    tomador: Optional[Tomador] = None  # Opcional no schema
    servicos: List[Servico] = field(default_factory=list)
    numero_rps: Optional[str] = None
    serie_rps: Optional[str] = None
    data_emissao: Optional[datetime] = None
    tp_amb: int = 2  # 1-Produção, 2-Homologação
    ver_aplic: str = "1.0"  # Versão do aplicativo
    tp_emit: int = 1  # 1-Prestador, 2-Tomador, 3-Intermediário
    c_loc_emi: Optional[str] = None  # Código do município emissor (IBGE)
    natureza_operacao: int = 1  # 1-Tributação no município, 2-Tributação fora do município, etc
    optante_simples_nacional: bool = False
    incentivador_cultural: bool = False
    valor_total_servicos: Optional[Decimal] = None
    valor_total_deducoes: Optional[Decimal] = None
    valor_total_desconto: Optional[Decimal] = None
    valor_total_liquido: Optional[Decimal] = None
    observacoes: Optional[str] = None
    trib_issqn: int = 1  # 1-Operação tributável, 2-Imunidade, 3-Exportação, 4-Não Incidência

    def get_id(self) -> str:
        """
        Constrói o ID do elemento infDPS conforme a regra:
        DPS{cod_municipio}{tipo_inscricao}{cpf_cnpj_emitente}{serie_dps}{numero_dps}

        Returns:
            ID formatado do DPS
        """
        # Código do município
        cod_municipio = self.c_loc_emi
        if not cod_municipio and self.prestador.endereco:
            cod_municipio = self.prestador.endereco.codigo_municipio
        if not cod_municipio:
            raise ValueError(
                "c_loc_emi (código do município) é obrigatório para construir o ID do DPS"
            )

        # Tipo de inscrição: 1-CPF, 2-CNPJ, 3-NIF
        cpf_cnpj = self.prestador.cpf_cnpj.replace(".", "").replace("/", "").replace("-", "")
        if len(cpf_cnpj) == 11:
            tipo_inscricao = "1"  # CPF
        elif len(cpf_cnpj) == 14:
            tipo_inscricao = "2"  # CNPJ
        else:
            tipo_inscricao = "3"  # NIF ou outro

        # CPF/CNPJ do emitente (sem formatação)
        cpf_cnpj_emitente = cpf_cnpj if len(cpf_cnpj) == 14 else cpf_cnpj.zfill(14)

        # Série do DPS
        serie_dps = self.serie_rps or "NF"

        # Número do DPS
        numero_dps = self.numero_rps or "1"

        # Constrói o ID
        return f"DPS{cod_municipio}{tipo_inscricao}{cpf_cnpj_emitente}{serie_dps}{numero_dps}"


@dataclass
class NotaFiscal:
    """Modelo de dados para uma nota fiscal emitida"""

    numero: Optional[str] = None
    codigo_verificacao: Optional[str] = None
    data_emissao: Optional[datetime] = None
    prestador: Optional[Prestador] = None
    tomador: Optional[Tomador] = None
    servicos: Optional[List[Servico]] = None
