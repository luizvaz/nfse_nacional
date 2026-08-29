"""
Configuração global de testes pytest
"""

import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pytest

from src.nfse.models import DPS, Endereco, Prestador, Servico, Tomador, Tributo

# Adiciona o diretório raiz ao PYTHONPATH para todos os testes
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))




@pytest.fixture
def prestador_exemplo():
    """Cria um prestador de exemplo"""
    endereco = Endereco(
        logradouro="Rua Exemplo",
        numero="123",
        bairro="Centro",
        codigo_municipio="3550308",  # São Paulo
        uf="SP",
        cep="01000-000",
    )
    return Prestador(
        cpf_cnpj="12345678000190",
        inscricao_municipal="123456",
        razao_social="Empresa Exemplo Ltda",
        endereco=endereco,
        telefone="11999999999",
        email="contato@exemplo.com.br",
        optante_simples_nacional=True,
        op_simp_nac=3,  # ME/EPP
        reg_apuracao_sn=1,  # Regime de apuração no Simples Nacional
        p_tot_trib_sn=Decimal("15.00"),  # Percentual total de tributos no SN
        reg_esp_trib=0,
    )


@pytest.fixture
def tomador_exemplo():
    """Cria um tomador de exemplo"""
    endereco = Endereco(
        logradouro="Avenida Cliente",
        numero="456",
        bairro="Jardim",
        codigo_municipio="3550308",
        uf="SP",
        cep="02000-000",
    )
    return Tomador(
        cpf_cnpj="98765432000100",
        razao_social="Cliente Exemplo Ltda",
        endereco=endereco,
        telefone="11888888888",
        email="cliente@exemplo.com.br",
    )


@pytest.fixture
def servico_exemplo():
    """Cria um serviço de exemplo"""
    tributo = Tributo(
        aliquota=Decimal("5.00"), valor=Decimal("50.00"), base_calculo=Decimal("1000.00")
    )
    return Servico(
        codigo_servico="140101",  # cTribNac exige 6 dígitos (código de tributação nacional)
        descricao="Desenvolvimento de software",
        valor_servico=Decimal("1000.00"),
        codigo_municipio="3550308",
        iss_retido=False,
        tributos=[tributo],
    )


@pytest.fixture
def dps_exemplo(prestador_exemplo, tomador_exemplo, servico_exemplo):
    """Cria um DPS de exemplo completo"""
    return DPS(
        prestador=prestador_exemplo,
        tomador=tomador_exemplo,
        servicos=[servico_exemplo],
        numero_rps="100000000000001",
        serie_rps="00001",
        data_emissao=datetime.now(),
        tp_amb=2,  # Homologação
        ver_aplic="1.0",
        tp_emit=1,  # Prestador
        c_loc_emi="3550308",
        trib_issqn=1,  # Operação tributável
    )
