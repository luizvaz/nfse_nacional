"""
Testes para validação do XML gerado contra o schema XSD
"""

import sys
from datetime import datetime
from pathlib import Path

import pytest
from lxml import etree

from src.nfse.models import DPS, Endereco, Prestador
from src.nfse.xml_builder import XMLBuilder

# Adiciona o diretório raiz ao PYTHONPATH
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def xsd_path():
    """Retorna o caminho para o arquivo XSD"""
    xsd_file = Path(__file__).parent.parent / "schemas" / "DPS_v1.00.xsd"
    if not xsd_file.exists():
        pytest.skip("Arquivo XSD não encontrado em schemas/DPS_v1.00.xsd")

    # Verifica se os arquivos XSD relacionados existem
    schemas_dir = xsd_file.parent
    required_files = [
        "tiposComplexos_v1.00.xsd",
        "tiposSimples_v1.00.xsd",
        "xmldsig-core-schema.xsd",
    ]

    missing_files = [f for f in required_files if not (schemas_dir / f).exists()]
    if missing_files:
        pytest.skip(f"Arquivos XSD relacionados não encontrados: {', '.join(missing_files)}")

    return str(xsd_file)


@pytest.fixture
def xml_builder(xsd_path):
    """Cria uma instância do XMLBuilder com validação XSD"""
    return XMLBuilder(xsd_path=xsd_path, versao="1.00")


# As fixtures prestador_exemplo, tomador_exemplo, servico_exemplo e dps_exemplo
# estão definidas em conftest.py para serem compartilhadas entre todos os testes


class TestXMLBuilder:
    """Testes para o XMLBuilder"""

    def test_xml_builder_initialization(self, xsd_path):
        """Testa a inicialização do XMLBuilder"""
        builder = XMLBuilder(xsd_path=xsd_path)
        assert builder is not None

        # Se o schema não foi carregado, mostra o motivo
        if builder._schema is None:
            # Tenta carregar novamente para ver o erro
            import sys
            from io import StringIO

            old_stderr = sys.stderr
            sys.stderr = StringIO()
            try:
                builder._load_schema(xsd_path)
                error_msg = sys.stderr.getvalue()
            finally:
                sys.stderr = old_stderr

            pytest.fail(
                f"Schema XSD não foi carregado.\n"
                f"Verifique se todos os arquivos XSD estão presentes em schemas/.\n"
                f"Erro: {error_msg}"
            )

    def test_build_dps_xml_basic(self, xml_builder, dps_exemplo):
        """Testa a construção básica do XML do DPS"""
        xml = xml_builder.build_dps_xml(dps_exemplo, validate=False)

        assert xml is not None
        assert isinstance(xml, str)
        assert "<?xml" in xml
        assert "<DPS" in xml or "DPS" in xml

    def test_xml_validation_against_xsd(self, xml_builder, dps_exemplo):
        """Testa se o XML gerado passa na validação XSD"""
        # Verifica se o schema foi carregado
        if xml_builder._schema is None:
            pytest.skip(
                "Schema XSD não foi carregado. Verifique se todos os arquivos XSD estão presentes."
            )

        xml = xml_builder.build_dps_xml(dps_exemplo, validate=True)

        # Se chegou aqui sem exceção, passou na validação
        assert xml is not None

    def test_xml_validation_manual(self, xml_builder, dps_exemplo):
        """Testa a validação manual do XML"""
        # Verifica se o schema foi carregado
        if xml_builder._schema is None:
            pytest.skip(
                "Schema XSD não foi carregado. Verifique se todos os arquivos XSD estão presentes."
            )

        xml = xml_builder.build_dps_xml(dps_exemplo, validate=False)

        # Valida manualmente
        is_valid = xml_builder.validate_xml(xml)
        assert is_valid is True

    def test_dps_id_generation(self, dps_exemplo):
        """Testa a geração do ID do DPS"""
        dps_id = dps_exemplo.get_id()

        assert dps_id is not None
        assert dps_id.startswith("DPS")
        assert "3550308" in dps_id  # Código do município
        assert "2" in dps_id  # Tipo de inscrição (CNPJ)
        assert "12345678000190" in dps_id  # CNPJ
        assert "00001" in dps_id  # Série
        assert "100000000000001" in dps_id  # Número

    def test_xml_contains_required_elements(self, xml_builder, dps_exemplo):
        """Testa se o XML contém os elementos obrigatórios"""
        xml = xml_builder.build_dps_xml(dps_exemplo, validate=False)
        root = etree.fromstring(xml.encode("utf-8"))

        # Verifica elementos obrigatórios
        ns = {"nfse": XMLBuilder.NS_NFSE}

        # Verifica infDPS
        inf_dps = root.find(".//nfse:infDPS", ns)
        assert inf_dps is not None

        # Verifica campos obrigatórios do infDPS
        assert inf_dps.find("nfse:tpAmb", ns) is not None
        assert inf_dps.find("nfse:dhEmi", ns) is not None
        assert inf_dps.find("nfse:verAplic", ns) is not None
        assert inf_dps.find("nfse:serie", ns) is not None
        assert inf_dps.find("nfse:nDPS", ns) is not None
        assert inf_dps.find("nfse:dCompet", ns) is not None
        assert inf_dps.find("nfse:tpEmit", ns) is not None
        assert inf_dps.find("nfse:cLocEmi", ns) is not None
        assert inf_dps.find("nfse:prest", ns) is not None
        assert inf_dps.find("nfse:serv", ns) is not None
        assert inf_dps.find("nfse:valores", ns) is not None

    def test_xml_tribmun_structure(self, xml_builder, dps_exemplo):
        """Testa se a estrutura do tribMun está correta"""
        xml = xml_builder.build_dps_xml(dps_exemplo, validate=False)
        root = etree.fromstring(xml.encode("utf-8"))

        ns = {"nfse": XMLBuilder.NS_NFSE}

        # Verifica tribMun
        trib_mun = root.find(".//nfse:tribMun", ns)
        assert trib_mun is not None

        # Verifica elementos obrigatórios do tribMun
        assert trib_mun.find("nfse:tribISSQN", ns) is not None
        assert trib_mun.find("nfse:tpRetISSQN", ns) is not None

        # Verifica que totTrib existe
        tot_trib = root.find(".//nfse:totTrib", ns)
        assert tot_trib is not None

    def test_xml_without_tomador(self, xml_builder, prestador_exemplo, servico_exemplo):
        """Testa a geração de XML sem tomador (opcional)"""
        # Verifica se o schema foi carregado
        if xml_builder._schema is None:
            pytest.skip(
                "Schema XSD não foi carregado. Verifique se todos os arquivos XSD estão presentes."
            )

        dps = DPS(
            prestador=prestador_exemplo,
            tomador=None,  # Tomador opcional
            servicos=[servico_exemplo],
            numero_rps="100000000000001",
            serie_rps="00001",
            data_emissao=datetime.now(),
            c_loc_emi="3550308",
        )

        xml = xml_builder.build_dps_xml(dps, validate=True)
        assert xml is not None

    def test_xml_with_cpf_prestador(self, xml_builder, tomador_exemplo, servico_exemplo):
        """Testa a geração de XML com prestador CPF"""
        # Verifica se o schema foi carregado
        if xml_builder._schema is None:
            pytest.skip(
                "Schema XSD não foi carregado. Verifique se todos os arquivos XSD estão presentes."
            )

        endereco = Endereco(
            logradouro="Rua Exemplo",
            numero="123",
            bairro="Centro",
            codigo_municipio="3550308",
            uf="SP",
            cep="01000-000",
        )
        prestador = Prestador(
            cpf_cnpj="12345678901",  # CPF
            inscricao_municipal="123456",
            razao_social="Prestador CPF",
            endereco=endereco,
            optante_simples_nacional=False,
            op_simp_nac=1,
            reg_esp_trib=0,
        )

        dps = DPS(
            prestador=prestador,
            tomador=tomador_exemplo,
            servicos=[servico_exemplo],
            numero_rps="100000000000001",
            serie_rps="00001",
            data_emissao=datetime.now(),
            c_loc_emi="3550308",
        )

        xml = xml_builder.build_dps_xml(dps, validate=True)
        assert xml is not None

        # Verifica se o ID foi gerado corretamente com tipo_inscricao=1 (CPF)
        dps_id = dps.get_id()
        assert "1" in dps_id  # Tipo de inscrição para CPF


class TestIBSCBS:
    """Testes para o grupo IBSCBS (Reforma Tributária, leiaute v1.01)"""

    def test_ibscbs_element_is_sibling_of_serv_and_valores(
        self, prestador_exemplo, tomador_exemplo, servico_exemplo
    ):
        """
        O elemento <IBSCBS> declarado pelo emitente é IRMÃO de <serv> e
        <valores> dentro de <infDPS> - não deve ficar aninhado em <serv>.
        """
        from src.nfse.models import IBSCBS, IBSCBSTributacao

        tributacao = IBSCBSTributacao(cst="000", c_class_trib="101001")
        ibscbs = IBSCBS(c_ind_op="000001", ind_dest="0", trib=tributacao)

        dps = DPS(
            prestador=prestador_exemplo,
            tomador=tomador_exemplo,
            servicos=[servico_exemplo],
            numero_rps="100000000000001",
            serie_rps="00001",
            c_loc_emi="3550308",
            ibscbs=ibscbs,
        )

        builder = XMLBuilder(versao="1.01")
        xml = builder.build_dps_xml(dps, validate=False)
        root = etree.fromstring(xml.encode("utf-8"))
        ns = {"n": "http://www.sped.fazenda.gov.br/nfse"}

        inf_dps = root.find("n:infDPS", ns)
        children = [etree.QName(c).localname for c in inf_dps]

        assert "IBSCBS" in children
        # IBSCBS deve vir depois de serv e valores, no mesmo nível
        assert children.index("IBSCBS") > children.index("serv")
        assert children.index("IBSCBS") > children.index("valores")

        # serv não deve conter IBSCBS
        serv_elem = inf_dps.find("n:serv", ns)
        assert serv_elem.find("n:IBSCBS", ns) is None

        # Confere os valores do grupo gIBSCBS
        g_ibscbs = inf_dps.find("n:IBSCBS/n:valores/n:trib/n:gIBSCBS", ns)
        assert g_ibscbs.find("n:CST", ns).text == "000"
        assert g_ibscbs.find("n:cClassTrib", ns).text == "101001"

    def test_ibscbs_valid_against_xsd_v101(
        self, prestador_exemplo, tomador_exemplo, servico_exemplo
    ):
        """O grupo IBSCBS gerado deve validar contra o schema oficial v1.01"""
        import xmlschema
        from xmlschema.validators.exceptions import XMLSchemaValidationError

        from src.nfse.models import IBSCBS, IBSCBSTributacao

        xsd_path = Path(__file__).parent.parent / "schemas" / "DPS_v1.01.xsd"
        if not xsd_path.exists():
            pytest.skip("Schema DPS_v1.01.xsd não encontrado em schemas/")

        tributacao = IBSCBSTributacao(cst="000", c_class_trib="101001")
        ibscbs = IBSCBS(c_ind_op="000001", ind_dest="0", trib=tributacao)

        dps = DPS(
            prestador=prestador_exemplo,
            tomador=tomador_exemplo,
            servicos=[servico_exemplo],
            numero_rps="100000000000001",
            serie_rps="00001",
            c_loc_emi="3550308",
            ibscbs=ibscbs,
        )

        builder = XMLBuilder(versao="1.01")
        xml = builder.build_dps_xml(dps, validate=False)
        root = etree.fromstring(xml.encode("utf-8"))
        ns = {"n": "http://www.sped.fazenda.gov.br/nfse"}
        ibscbs_elem = root.find("n:infDPS/n:IBSCBS", ns)

        schema = xmlschema.XMLSchema(str(xsd_path))
        ibscbs_type = schema.types["TCRTCInfoIBSCBS"]
        errors = [
            e
            for e in ibscbs_type.iter_decode(ibscbs_elem)
            if isinstance(e, XMLSchemaValidationError)
        ]
        assert not errors, f"Grupo IBSCBS inválido contra o XSD 1.01: {errors}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
