"""
Exemplo básico de uso da API de NFSe
"""

import os
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from src.nfse.api_client import Ambiente
from src.nfse.emissor import NFSeEmissor
from src.nfse.models import DPS, Endereco, Prestador, Servico, Tomador, Tributo

# Adiciona o diretório raiz do projeto ao PYTHONPATH
# Isso permite importar os módulos mesmo executando o script diretamente
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass  # dotenv é opcional




def main():
    """
    Exemplo básico de emissão de nota fiscal de serviço (NFSe)

    Este exemplo demonstra o fluxo completo:
    1. Configuração do emissor com certificado digital
    2. Criação dos dados do prestador, tomador e serviço
    3. Construção do DPS (Declaração de Prestação de Serviço)
    4. Assinatura digital do XML
    5. Envio para a API da NFSe Nacional
    """

    # ========================================================================
    # 1. CONFIGURAÇÃO DO EMISSOR
    # ========================================================================
    # A autenticação é feita automaticamente via certificado digital A1 (.pfx)
    # Salve as variáveis de ambiente PFX_PATH e PFX_PASSWORD no arquivo .env
    pfx_path = os.getenv("PFX_PATH", "caminho/para/seu/certificado.pfx")
    pfx_password = os.getenv("PFX_PASSWORD", "senha_do_certificado")
    ambiente = Ambiente.PRODUCAO_RESTRITA  # ou Ambiente.PRODUCAO_REAL

    emissor = NFSeEmissor(pfx_path=pfx_path, pfx_password=pfx_password, ambiente=ambiente)

    # ========================================================================
    # 2. DADOS DO PRESTADOR (EMISSOR DA NOTA)
    # ========================================================================
    # Campos obrigatórios: cpf_cnpj
    # Campos opcionais: inscricao_municipal, razao_social, endereco, telefone, email
    prestador = Prestador(
        # Obrigatório
        cpf_cnpj="00000000000000",  # CNPJ sem formatação
        # Opcionais
        inscricao_municipal="00000",
        razao_social="Empresa Exemplo Ltda",  # Razão social do prestador
        telefone="11999999999",
        email="contato@exemplo.com.br",
        # Configuração para Simples Nacional
        optante_simples_nacional=True,
        op_simp_nac=3,  # 1-Não Optante, 2-MEI, 3-ME/EPP
        reg_apuracao_sn=1,  # Regime de apuração no Simples Nacional
        p_tot_trib_sn=Decimal("15.00"),  # Percentual total de tributos no SN
    )

    # Endereço do prestador (opcional)
    # Se a nota for emitida pelo próprio prestador, não é necessário informar o endereço
    # endereco_prestador = Endereco(
    #     logradouro="Rua Exemplo",
    #     numero="123",
    #     bairro="Centro",
    #     codigo_municipio="3550308",  # Código IBGE (São Paulo)
    #     uf="SP",
    #     cep="01000-000"
    # )
    # prestador.endereco = endereco_prestador

    # ========================================================================
    # 3. DADOS DO TOMADOR (CLIENTE)
    # ========================================================================
    # Campos obrigatórios: cpf_cnpj
    # Campos opcionais: razao_social, endereco, telefone, email, inscricao_municipal
    endereco_tomador = Endereco(
        logradouro="Av. República do Chile",
        numero="65",
        bairro="Centro",
        codigo_municipio="3304557",  # Código IBGE do município do Tomador (Ver lista em https://www.ibge.gov.br/explica/codigos-dos-municipios.php)
        uf="RJ",
        cep="20031-170",
    )

    tomador = Tomador(
        # Obrigatório
        cpf_cnpj="33000167000101",  # CNPJ sem formatação
        # Opcionais
        razao_social="Cliente Exemplo Ltda",
        endereco=endereco_tomador,
        telefone="11888888888",
        email="cliente@exemplo.com.br",
    )

    # ========================================================================
    # 4. DADOS DO SERVIÇO PRESTADO
    # ========================================================================
    # Campos obrigatórios: codigo_servico, descricao, valor_servico
    # Campos opcionais: valor_deducoes, valor_desconto, valor_liquido,
    #                   iss_retido, codigo_municipio, tributos, codigo_nbs

    # Tributo ISSQN (opcional, mas recomendado)
    tributo_iss = Tributo(
        aliquota=Decimal("0.00"),  # Alíquota do ISSQN (%)
        valor=Decimal("0.00"),  # Valor do imposto
        base_calculo=Decimal("0.00"),  # Base de cálculo
        codigo_tributacao="1401",  # Código de tributação municipal
        descricao="ISS",
    )

    servico = Servico(
        # Obrigatórios
        codigo_servico="010501",  # Ver lista em https://www.gov.br/nfse/pt-br/mei-e-demais-empresas/codigos-de-tributacao-nacional-nbs
        descricao="Desenvolvimento de software",
        valor_servico=Decimal("100.00"),  # Valor do serviço
        # Opcionais - Valores
        valor_deducoes=Decimal("0.00"),  # Valor das deduções
        valor_desconto=Decimal("0.00"),  # Valor do desconto
        valor_liquido=Decimal("100.00"),  # Valor líquido
        # Opcionais - Tributação
        iss_retido=False,  # True se o ISSQN for retido na fonte
        codigo_municipio="3550308",  # Código IBGE do município de prestação (Ver lista em https://www.ibge.gov.br/explica/codigos-dos-municipios.php)
        tributos=[tributo_iss],
        codigo_nbs="111032100",  # https://www.gov.br/mdic/pt-br/images/REPOSITORIO/scs/decos/NBS/Anexoa_Ia_NBSa_2.0a_coma_alteraa_esa_6.12.18.pdf
    )

    # ========================================================================
    # 5. CRIAÇÃO DO DPS (DECLARAÇÃO DE PRESTAÇÃO DE SERVIÇO)
    # ========================================================================
    # O ID do DPS é construído automaticamente com a lógica:
    # DPS{cod_municipio}{tipo_inscricao}{cpf_cnpj_emitente}{serie_dps}{numero_dps}
    #
    # Campos obrigatórios: prestador, servicos
    # Campos opcionais: tomador, numero_rps, serie_rps, data_emissao, etc.
    dps = DPS(
        # Obrigatórios
        prestador=prestador,
        servicos=[servico],
        # Opcionais - Identificação
        numero_rps="100000000000010",  # Número do RPS (Recibo de Prestação de Serviço)
        serie_rps="00001",  # Série do RPS
        data_emissao=datetime.now(),
        c_loc_emi="3143302",  # Código IBGE do município emissor (obrigatório para gerar o ID)
        # Opcionais - Configurações
        natureza_operacao=1,  # 1-Tributação no município, 2-Tributação fora do município
        optante_simples_nacional=True,
        incentivador_cultural=False,
        # Opcional - Tomador
        tomador=tomador,
    )

    # Visualizar o ID gerado automaticamente
    print(f"ID do DPS gerado: {dps.get_id()}")
    print()

    # ========================================================================
    # 6. EMISSÃO DA NOTA FISCAL
    # ========================================================================
    # O método emitir_nota() realiza automaticamente:
    # - Construção do XML do DPS
    # - Assinatura digital com o certificado A1
    # - Compressão (gzip) e codificação (base64)
    # - Envio para a API da NFSe Nacional
    try:
        resultado = emissor.emitir_nota(dps, validate_xml=False)
        print("✓ Nota fiscal emitida com sucesso!")
        print(f"Resultado: {resultado}")
    except Exception as e:
        print(f"✗ Erro ao emitir nota fiscal: {str(e)}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
