"""
Módulo principal para integração com a API de NFSe Nacional
"""

from .api_client import Ambiente, APIClient
from .config import NaturezaOperacao, RegimeEspecialTributacao
from .emissor import NFSeEmissor
from .exceptions import (
    NFSeAPIError,
    NFSeConnectionError,
    NFSeError,
    NFSeNotFoundError,
)
from .models import (
    DPS,
    IBSCBS,
    Endereco,
    IBSCBSDestinatario,
    IBSCBSTributacao,
    NotaFiscal,
    Prestador,
    Servico,
    Tomador,
    Tributo,
)
from .signer import XMLSigner
from .xml_builder import XMLBuilder

__all__ = [
    "NFSeEmissor",
    "APIClient",
    "Ambiente",
    "DPS",
    "Prestador",
    "Tomador",
    "Servico",
    "Tributo",
    "Endereco",
    "IBSCBS",
    "IBSCBSTributacao",
    "IBSCBSDestinatario",
    "NotaFiscal",
    "XMLBuilder",
    "XMLSigner",
    "NaturezaOperacao",
    "RegimeEspecialTributacao",
    "NFSeError",
    "NFSeAPIError",
    "NFSeNotFoundError",
    "NFSeConnectionError",
]
