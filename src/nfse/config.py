"""
Configurações e constantes do módulo NFSe
"""

from enum import Enum


class NaturezaOperacao(Enum):
    """Natureza da operação"""

    TRIBUTACAO_MUNICIPIO = 1
    TRIBUTACAO_FORA_MUNICIPIO = 2
    ISENCAO = 3
    IMUNE = 4
    EXIGIBILIDADE_SUSPENSA = 5
    NAO_INCIDENCIA = 6
    EXPORTACAO = 7


class RegimeEspecialTributacao(Enum):
    """Regime especial de tributação"""

    MICROEMPRESA_MUNICIPAL = 1
    ESTIMATIVA = 2
    SOCIEDADE_PROFISSIONAIS = 3
    COOPERATIVA = 4
    MEI = 5
    ME_EPP = 6
