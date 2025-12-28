"""
Assinatura digital de XML com certificado A1 (.pfx)
"""

import os
from typing import Optional

import signxml
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import pkcs12
from lxml import etree
from signxml import XMLSigner as SignXMLSigner
from signxml import namespaces


class XMLSigner:
    """Classe responsável por assinar XML com certificado digital A1"""

    def __init__(self, pfx_path: str, pfx_password: str):
        """
        Inicializa o assinador XML

        Args:
            pfx_path: Caminho para o arquivo .pfx do certificado
            pfx_password: Senha do certificado
        """
        if not os.path.exists(pfx_path):
            raise FileNotFoundError(f"Certificado não encontrado: {pfx_path}")

        self.pfx_path = pfx_path
        self.pfx_password = pfx_password
        self._load_certificate()

    def _load_certificate(self):
        """Carrega o certificado do arquivo .pfx"""
        with open(self.pfx_path, "rb") as f:
            pfx_data = f.read()

        try:
            # Carrega o certificado e a chave privada
            private_key, certificate, additional_certificates = pkcs12.load_key_and_certificates(
                pfx_data,
                self.pfx_password.encode()
                if isinstance(self.pfx_password, str)
                else self.pfx_password,
                backend=default_backend(),
            )

            if private_key is None or certificate is None:
                raise ValueError(
                    "Não foi possível extrair a chave privada ou o certificado do arquivo .pfx"
                )

            self.private_key = private_key
            self.certificate = certificate
            self.additional_certificates = additional_certificates or []

        except Exception as e:
            raise ValueError(f"Erro ao carregar certificado: {str(e)}") from e

    def sign_xml(self, xml_string: str, reference_uri: Optional[str] = None) -> str:
        """
        Assina o XML fornecido

        Args:
            xml_string: String XML a ser assinada
            reference_uri: URI de referência para assinatura. Se None, detecta automaticamente
                          o atributo Id do elemento infDPS

        Returns:
            String XML assinada
        """
        # Parse do XML
        root = etree.fromstring(xml_string.encode("utf-8"))

        # Se reference_uri não foi fornecido, tenta detectar do atributo Id do infDPS
        if reference_uri is None:
            # Busca o elemento infDPS e seu atributo Id
            ns_nfse = "http://www.sped.fazenda.gov.br/nfse"
            inf_dps = root.find(f".//{{{ns_nfse}}}infDPS")
            if inf_dps is not None and "Id" in inf_dps.attrib:
                reference_uri = f"#{inf_dps.attrib['Id']}"
            else:
                reference_uri = "#DPS1"  # Fallback padrão

        # Cria o assinador
        signer = SignXMLSigner(
            method=signxml.methods.enveloped,
            signature_algorithm="rsa-sha256",
            digest_algorithm="sha256",
            c14n_algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315",
        )
        signer.excise_empty_xmlns_declarations = True
        signer.namespaces = {None: namespaces.ds}

        # Assina o XML
        signed_root = signer.sign(
            root, key=self.private_key, cert=[self.certificate], reference_uri=reference_uri
        )

        # Converte para string
        signed_xml = etree.tostring(
            signed_root, encoding="utf-8", xml_declaration=True, pretty_print=True
        ).decode("utf-8")

        return signed_xml

    def get_certificate_info(self) -> dict:
        """
        Retorna informações do certificado

        Returns:
            Dicionário com informações do certificado
        """
        subject = self.certificate.subject
        issuer = self.certificate.issuer

        return {
            "subject": dict(subject),
            "issuer": dict(issuer),
            "serial_number": str(self.certificate.serial_number),
            "not_valid_before": self.certificate.not_valid_before,
            "not_valid_after": self.certificate.not_valid_after,
        }
