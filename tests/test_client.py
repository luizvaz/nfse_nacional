"""
Testes para o cliente da API de NFSe
"""

import unittest
from unittest.mock import Mock, patch

from src.nfse.api_client import Ambiente, APIClient


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
