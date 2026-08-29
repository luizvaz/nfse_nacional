"""
Testes para o cliente da API de NFSe
"""

import json
import unittest
from unittest.mock import Mock, patch

from src.nfse.api_client import Ambiente, APIClient
from src.nfse.exceptions import NFSeAPIError, NFSeError, NFSeNotFoundError


class TestAPIClient(unittest.TestCase):
    """Testes para a classe APIClient"""

    def setUp(self):
        """Configuração inicial dos testes"""
        # Usa um certificado mock para os testes
        # Em testes reais, você precisaria de um certificado válido
        self.pfx_path = "test_certificate.pfx"
        self.pfx_password = "test_password"
        self.ambiente = Ambiente.PRODUCAO_RESTRITA

    @patch("src.nfse.api_client.Pkcs12Adapter")
    @patch("src.nfse.api_client.HAS_PKCS12_ADAPTER", True)
    def test_client_initialization(self, mock_adapter):
        """Testa a inicialização do cliente"""
        client = APIClient(
            ambiente=self.ambiente, pfx_path=self.pfx_path, pfx_password=self.pfx_password
        )

        self.assertIsNotNone(client)
        self.assertEqual(client.ambiente, self.ambiente)
        self.assertIsNotNone(client.base_url)
        self.assertIn("nfse.gov.br", client.base_url)
        # Verifica se o adapter foi configurado
        mock_adapter.assert_called_once()

    @patch("src.nfse.api_client.HAS_PKCS12_ADAPTER", False)
    def test_client_initialization_without_pkcs12(self):
        """Testa que o cliente falha se requests-pkcs12 não estiver instalado"""
        with self.assertRaises(ImportError):
            APIClient(
                ambiente=self.ambiente, pfx_path=self.pfx_path, pfx_password=self.pfx_password
            )

    def test_invalid_ambiente(self):
        """Testa que ambiente inválido gera erro"""
        with patch("src.nfse.api_client.HAS_PKCS12_ADAPTER", True):
            with patch("src.nfse.api_client.Pkcs12Adapter"):
                # Cria um ambiente inválido
                invalid_ambiente = Mock()
                invalid_ambiente.value = "invalid"

                with self.assertRaises(ValueError):
                    APIClient(
                        ambiente=invalid_ambiente,
                        pfx_path=self.pfx_path,
                        pfx_password=self.pfx_password,
                    )


class TestCheckResponse(unittest.TestCase):
    """Testes para o tratamento de erros retornados pela API"""

    def setUp(self):
        with patch("src.nfse.api_client.HAS_PKCS12_ADAPTER", True):
            with patch("src.nfse.api_client.Pkcs12Adapter"):
                self.client = APIClient(
                    ambiente=Ambiente.PRODUCAO_RESTRITA,
                    pfx_path="test_certificate.pfx",
                    pfx_password="test_password",
                )

    @staticmethod
    def _resposta(status_code, corpo, json_valido=True):
        """Cria um Mock de requests.Response"""
        resposta = Mock()
        resposta.ok = 200 <= status_code < 300
        resposta.status_code = status_code
        resposta.text = corpo

        if json_valido:
            resposta.json = lambda: json.loads(corpo)
        else:
            def _raise():
                raise ValueError("resposta não é JSON")

            resposta.json = _raise

        return resposta

    def test_resposta_ok_nao_levanta_excecao(self):
        """Uma resposta bem-sucedida não deve levantar exceção"""
        self.client._check_response(self._resposta(200, '{"chaveAcesso": "123"}'))

    def test_dps_sem_nfse_levanta_not_found(self):
        """HTTP 404 com código E2404 deve virar NFSeNotFoundError"""
        corpo = json.dumps(
            {
                "tipoAmbiente": 1,
                "erro": {
                    "codigo": "E2404",
                    "descricao": (
                        "Não foi gerada uma NFS-e com o identificador de DPS informado"
                    ),
                },
            }
        )

        with self.assertRaises(NFSeNotFoundError) as ctx:
            self.client._check_response(self._resposta(404, corpo))

        erro = ctx.exception
        self.assertEqual(erro.status_code, 404)
        self.assertEqual(erro.codigo, "E2404")
        self.assertIn("identificador de DPS", erro.descricao)
        # A mensagem deve conter código e descrição, não o JSON bruto
        self.assertIn("E2404", str(erro))

    def test_erro_generico_levanta_api_error(self):
        """Erros que não são 404 devem virar NFSeAPIError"""
        corpo = json.dumps(
            {"erro": {"codigo": "E0001", "descricao": "Requisição inválida"}}
        )

        with self.assertRaises(NFSeAPIError) as ctx:
            self.client._check_response(self._resposta(400, corpo))

        erro = ctx.exception
        self.assertNotIsInstance(erro, NFSeNotFoundError)
        self.assertEqual(erro.status_code, 400)
        self.assertEqual(erro.codigo, "E0001")

    def test_erro_sem_json_valido(self):
        """Resposta de erro que não é JSON não deve quebrar o parsing"""
        with self.assertRaises(NFSeAPIError) as ctx:
            self.client._check_response(
                self._resposta(500, "<html>Internal Server Error</html>", json_valido=False)
            )

        erro = ctx.exception
        self.assertEqual(erro.status_code, 500)
        self.assertIsNone(erro.codigo)
        self.assertIn("Internal Server Error", str(erro))

    def test_excecoes_sao_capturaveis_como_exception(self):
        """As exceções devem manter compatibilidade com 'except Exception'"""
        self.assertTrue(issubclass(NFSeNotFoundError, NFSeAPIError))
        self.assertTrue(issubclass(NFSeAPIError, NFSeError))
        self.assertTrue(issubclass(NFSeError, Exception))
