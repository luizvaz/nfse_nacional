"""
Cliente HTTP para comunicação com a API de NFSe Nacional
A autenticação é feita via certificado digital A1 (.pfx)
"""

import base64
import gzip
from enum import Enum
from typing import Any, Dict, Optional

import requests

try:
    from requests_pkcs12 import Pkcs12Adapter

    HAS_PKCS12_ADAPTER = True
except ImportError:
    HAS_PKCS12_ADAPTER = False


class Ambiente(Enum):
    """Enum para ambiente da API"""

    PRODUCAO_RESTRITA = "producao_restrita"
    PRODUCAO_REAL = "producao_real"


class APIClient:
    """Cliente para comunicação com a API de NFSe Nacional"""

    # URLs base da API por ambiente
    BASE_URLS = {
        Ambiente.PRODUCAO_RESTRITA: "https://sefin.producaorestrita.nfse.gov.br/SefinNacional",
        Ambiente.PRODUCAO_REAL: "https://sefin.nfse.gov.br/SefinNacional",
    }

    def __init__(self, ambiente: Ambiente, pfx_path: str, pfx_password: str):
        """
        Inicializa o cliente da API

        Args:
            ambiente: Ambiente da API (PRODUCAO_RESTRITA ou PRODUCAO_REAL)
            pfx_path: Caminho para o arquivo .pfx do certificado A1
            pfx_password: Senha do certificado
        """
        self.ambiente = ambiente
        self.base_url = self.BASE_URLS.get(ambiente)
        if not self.base_url:
            raise ValueError(f"Ambiente inválido: {ambiente}")

        self.session = requests.Session()

        # Configura autenticação via certificado PKCS12
        if HAS_PKCS12_ADAPTER:
            self.session.mount(
                "https://",
                Pkcs12Adapter(
                    pkcs12_filename=pfx_path,
                    pkcs12_password=pfx_password,
                ),
            )
        else:
            raise ImportError(
                "Biblioteca requests-pkcs12 não encontrada. "
                "Instale com: pip install requests-pkcs12"
            )

        # Configura headers padrão
        self.session.headers.update(
            {
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
        )

    def enviar_dps(self, xml_dps_assinado: str) -> Dict[str, Any]:
        """
        Envia o DPS assinado para a API

        O XML é comprimido com gzip e codificado em base64 antes do envio.
        O payload é enviado como JSON: {"dpsXmlGZipB64": dps_b64}

        Args:
            xml_dps_assinado: XML do DPS já assinado

        Returns:
            Resposta da API com o resultado do envio
        """
        endpoint = f"{self.base_url}/nfse/"

        try:
            # Comprime o XML com gzip
            xml_bytes = xml_dps_assinado.encode("utf-8")
            xml_gzip = gzip.compress(xml_bytes)

            # Codifica em base64
            dps_b64 = base64.b64encode(xml_gzip).decode("utf-8")

            # Prepara o payload JSON
            payload = {"dpsXmlGZipB64": dps_b64}

            # Envia para a API
            response = self.session.post(endpoint, json=payload, timeout=30)

            self._check_response(response)

            # Retorna a resposta como JSON
            try:
                return response.json()
            except (ValueError, TypeError):
                # Se não conseguir fazer parse do JSON, retorna como dict
                return {
                    "status_code": response.status_code,
                    "content": response.text,
                    "headers": dict(response.headers),
                }

        except requests.exceptions.RequestException as e:
            raise Exception(f"Erro ao enviar DPS para a API: {str(e)}") from e

    def consultar_nota(
        self, numero_nota: str, codigo_verificacao: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Consulta uma nota fiscal já emitida

        Args:
            numero_nota: Número da nota fiscal
            codigo_verificacao: Código de verificação (opcional)

        Returns:
            Dados da nota fiscal
        """
        endpoint = f"{self.base_url}/nfse/{codigo_verificacao}"

        try:
            response = self.session.get(endpoint, timeout=30)
            self._check_response(response)

            try:
                return response.json()
            except (ValueError, TypeError):
                # Se não conseguir fazer parse do JSON, retorna como dict
                return {"status_code": response.status_code, "content": response.text}

        except requests.exceptions.RequestException as e:
            raise Exception(f"Erro ao consultar nota: {str(e)}") from e

    def cancelar_nota(self, numero_nota: str, motivo: str) -> Dict[str, Any]:
        """
        Cancela uma nota fiscal
        TODO: Implementar cancelamento de nota fiscal
        """

    def _check_response(self, response: requests.Response):
        """
        Verifica se a resposta da API está OK

        Args:
            response: Objeto Response do requests

        Raises:
            Exception: Se a resposta não estiver OK
        """
        if not response.ok:
            raise Exception(f"Erro {response.status_code}: {response.text}")
