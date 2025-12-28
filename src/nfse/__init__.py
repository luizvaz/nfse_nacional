"""
Módulo principal para integração com a API de NFSe Nacional
"""

from .api_client import Ambiente, APIClient
from .config import NaturezaOperacao, RegimeEspecialTributacao
from .emissor import NFSeEmissor
from .models import DPS, Endereco, NotaFiscal, Prestador, Servico, Tomador, Tributo
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
    "NotaFiscal",
    "XMLBuilder",
    "XMLSigner",
    "NaturezaOperacao",
    "RegimeEspecialTributacao",
]
