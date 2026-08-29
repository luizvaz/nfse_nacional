"""
Cliente HTTP para comunicação com a API de NFSe Nacional
A autenticação é feita via certificado digital A1 (.pfx)
"""

import base64
import gzip
from enum import Enum
from typing import Any, Dict

import requests

from .exceptions import NFSeAPIError, NFSeConnectionError, NFSeNotFoundError

try:
    from requests_pkcs12 import Pkcs12Adapter

    HAS_PKCS12_ADAPTER = True
except ImportError:
    # Mantém o nome definido (como None) mesmo sem a dependência opcional
    # instalada, para que o módulo continue "patchable"/testável (ex.: em
    # testes com unittest.mock.patch) sem exigir requests-pkcs12 instalado.
    Pkcs12Adapter = None
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
        Envia o DPS assinado para a API (POST /nfse)

        O XML é comprimido com gzip e codificado em base64 antes do envio.
        O payload é enviado como JSON: {"dpsXmlGZipB64": dps_b64}

        Args:
            xml_dps_assinado: XML do DPS já assinado digitalmente

        Returns:
            Resposta da API com os dados da NFS-e gerada, incluindo a
            chave de acesso (campo "chaveAcesso")

        Raises:
            NFSeAPIError: Se a API rejeitar o DPS
            NFSeConnectionError: Se houver falha de comunicação
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
            raise NFSeConnectionError(f"Erro ao enviar DPS para a API: {e}") from e

    def consultar_dps(self, id_dps: str) -> Dict[str, Any]:
        """
        Consulta a NFS-e gerada a partir de uma DPS (GET /dps/{id})

        O identificador da DPS pode ser obtido com `DPS.get_id()` e segue a
        regra de formação: código IBGE do município (7) + tipo de inscrição
        (1) + inscrição federal (14) + série (5) + número (15).

        Args:
            id_dps: Identificador da DPS (com ou sem o prefixo "DPS")

        Returns:
            Dados da NFS-e correspondente

        Raises:
            NFSeNotFoundError: Se a DPS ainda não gerou NFS-e (código E2404)
            NFSeAPIError: Demais erros retornados pela API
            NFSeConnectionError: Se houver falha de comunicação
        """
        endpoint = f"{self.base_url}/dps/{id_dps}"

        try:
            response = self.session.get(endpoint, timeout=30)
            self._check_response(response)

            try:
                return response.json()
            except (ValueError, TypeError):
                # Se não conseguir fazer parse do JSON, retorna como dict
                return {"status_code": response.status_code, "content": response.text}

        except requests.exceptions.RequestException as e:
            raise NFSeConnectionError(f"Erro ao consultar nota: {e}") from e

    def consultar_nota(self, chave_acesso: str) -> Dict[str, Any]:
        """
        Consulta uma NFS-e pela chave de acesso (GET /nfse/{chaveAcesso})

        A chave de acesso é retornada no campo "chaveAcesso" da resposta de
        `enviar_dps()` e de `consultar_dps()`.

        Args:
            chave_acesso: Chave de acesso da NFS-e (50 caracteres)

        Returns:
            Dados da NFS-e

        Raises:
            NFSeNotFoundError: Se a NFS-e não for encontrada
            NFSeAPIError: Demais erros retornados pela API
            NFSeConnectionError: Se houver falha de comunicação
        """
        endpoint = f"{self.base_url}/nfse/{chave_acesso}"

        try:
            response = self.session.get(endpoint, timeout=30)
            self._check_response(response)

            try:
                return response.json()
            except (ValueError, TypeError):
                # Se não conseguir fazer parse do JSON, retorna como dict
                return {"status_code": response.status_code, "content": response.text}

        except requests.exceptions.RequestException as e:
            raise NFSeConnectionError(f"Erro ao consultar nota: {e}") from e

    def cancelar_nota(self, numero_nota: str, motivo: str) -> Dict[str, Any]:
        """
        Cancela uma nota fiscal
        TODO: Implementar cancelamento de nota fiscal
        """

    def _check_response(self, response: requests.Response):
        """
        Verifica se a resposta da API está OK

        Extrai o código e a descrição do erro retornados pela API, quando
        presentes, para que o chamador possa tratar cada situação de forma
        específica (ver src/nfse/exceptions.py).

        Args:
            response: Objeto Response do requests

        Raises:
            NFSeNotFoundError: Recurso não encontrado (HTTP 404). Ex: uma DPS
                que ainda não gerou NFS-e (código "E2404")
            NFSeAPIError: Demais erros retornados pela API
        """
        if response.ok:
            return

        # A API retorna os detalhes do erro em JSON, no campo "erro"
        codigo = None
        descricao = None
        payload = None

        try:
            payload = response.json()
        except (ValueError, TypeError):
            payload = None

        if isinstance(payload, dict):
            erro = payload.get("erro")
            if isinstance(erro, dict):
                codigo = erro.get("codigo")
                descricao = erro.get("descricao")

        classe_erro = NFSeNotFoundError if response.status_code == 404 else NFSeAPIError

        raise classe_erro(
            status_code=response.status_code,
            texto=response.text,
            codigo=codigo,
            descricao=descricao,
            payload=payload,
        )
