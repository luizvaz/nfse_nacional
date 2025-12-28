"""
Classe principal que orquestra o fluxo completo de emissão de NFSe
"""

from typing import Optional

from .api_client import Ambiente, APIClient
from .models import DPS
from .signer import XMLSigner
from .xml_builder import XMLBuilder


class NFSeEmissor:
    """Classe principal para emissão de NFSe"""

    def __init__(
        self, pfx_path: str, pfx_password: str, ambiente: Ambiente, xsd_path: Optional[str] = None
    ):
        """
        Inicializa o emissor de NFSe

        Args:
            pfx_path: Caminho para o arquivo .pfx do certificado A1
            pfx_password: Senha do certificado
            ambiente: Ambiente da API (PRODUCAO_RESTRITA ou PRODUCAO_REAL)
            xsd_path: Caminho para o arquivo XSD para validação (opcional)
        """
        self.xml_builder = XMLBuilder(xsd_path=xsd_path)
        self.signer = XMLSigner(pfx_path, pfx_password)
        self.api_client = APIClient(ambiente, pfx_path, pfx_password)

    def emitir_nota(self, dps: DPS, validate_xml: bool = False) -> dict:
        """
        Emite uma nota fiscal seguindo o fluxo completo:
        1. Constrói o XML do DPS
        2. Assina o XML com certificado digital
        3. Envia para a API

        Args:
            dps: Objeto DPS com todos os dados da nota
            validate_xml: Se True, valida o XML contra o XSD antes de assinar

        Returns:
            Resposta da API com os dados da nota emitida
        """
        # Passo 1: Construir XML do DPS
        print("Construindo XML do DPS...")
        xml_dps = self.xml_builder.build_dps_xml(dps, validate=validate_xml)

        # Passo 2: Assinar XML
        print("Assinando XML com certificado digital...")
        xml_assinado = self.signer.sign_xml(xml_dps)

        # Passo 3: Enviar para API
        print("Enviando DPS para a API...")
        resposta = self.api_client.enviar_dps(xml_assinado)

        print("Nota fiscal emitida com sucesso!")
        return resposta

    def consultar_nota(self, numero_nota: str, codigo_verificacao: Optional[str] = None) -> dict:
        """
        Consulta uma nota fiscal já emitida

        Args:
            numero_nota: Número da nota fiscal
            codigo_verificacao: Código de verificação (opcional)

        Returns:
            Dados da nota fiscal
        """
        return self.api_client.consultar_nota(numero_nota, codigo_verificacao)

    def cancelar_nota(self, numero_nota: str, motivo: str) -> dict:
        """
        Cancela uma nota fiscal

        Args:
            numero_nota: Número da nota fiscal
            motivo: Motivo do cancelamento

        Returns:
            Resultado do cancelamento
        """
        return self.api_client.cancelar_nota(numero_nota, motivo)

    def get_certificate_info(self) -> dict:
        """
        Retorna informações do certificado digital configurado

        Returns:
            Dicionário com informações do certificado
        """
        return self.signer.get_certificate_info()
