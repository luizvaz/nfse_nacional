import re
import os
import sys
import json
import shutil
import traceback
from pathlib import Path
import urllib3

# Desabilita warnings de SSL não verificado
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Adiciona o diretório raiz do projeto ao PYTHONPATH
# Isso permite importar os módulos mesmo executando o script diretamente
root_ = Path(__file__).parent
sys.path.insert(0, str(root_))

# Corrigido: adiciona o diretório PAI de nfse
nfse_ = Path("/opt/nfse_nacional/")
sys.path.insert(0, str(nfse_))

import xml.etree.ElementTree as ET

from datetime import datetime
from decimal import Decimal
from datetime import datetime

from src.nfse.api_client import Ambiente
from src.nfse.emissor import NFSeEmissor
from src.nfse.models import (
    DPS,
    Endereco,
    IBSCBS,
    IBSCBSTributacao,
    Prestador,
    Servico,
    Tomador,
    Tributo,
)

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass  # dotenv é opcional


# ============================================================================
# CLASSIFICAÇÃO TRIBUTÁRIA DO IBS/CBS (Reforma Tributária)
# ============================================================================
# ATENÇÃO: os valores abaixo são o "caso regular" (tributação integral, sem
# isenção/imunidade/redução) — CST 000 + cClassTrib 000001. Isso cobre a
# maioria das operações comerciais comuns, mas serviços de EDUCAÇÃO podem se
# enquadrar em algum benefício específico da LC 214/2025 (isenção, redução
# de alíquota etc.), o que mudaria o CST/cClassTrib.
#
# O mesmo vale para o cIndOp: ele depende da correlação oficial entre o
# Item de Serviço prestado, o NBS e o cClassTrib (Anexo VIII da NFS-e
# Nacional). "100301" é o código genérico de "serviços gerais em operação
# onerosa" e serve como ponto de partida, mas PRECISA ser conferido contra
# o Anexo VIII para o seu NBS (1.2205.20.00) antes de rodar em produção real.
#
# CONFIRME ESSES 3 VALORES COM SEU CONTADOR ANTES DE EMITIR EM PRODUÇÃO REAL.
CST_IBS_CBS_PADRAO = "000"  # Tributação integral
C_CLASS_TRIB_PADRAO = "000001"  # Situações tributadas integralmente pelo IBS e CBS
C_IND_OP_PADRAO = "100301"  # Serviços gerais em operação onerosa (CONFERIR no Anexo VIII)


def main():

    arquivos = sorted(f for f in os.listdir("./rps/") if f.lower().endswith(".json"))
    if arquivos:
        for arq in arquivos:
            try:
                full = os.path.join("./rps/", arq)
                with open(full, "r", encoding="utf-8") as f:
                    dados = json.load(f)
                resultado = emite_nf(f"{full}", dados)
                if resultado:
                    os.makedirs("./rps/processados", exist_ok=True)
                    shutil.move(full, os.path.join("./rps/processados", arq))

                    nfse_file = os.path.join(
                        "./rps/processados", os.path.splitext(arq)[0] + ".nfse"
                    )
                    with open(nfse_file, "w", encoding="utf-8") as f:
                        f.write(json.dumps(resultado, ensure_ascii=False, indent=4))

                    print(f"Movido: {arq}")
                    print()
                else:
                    print()
                    continue

            except Exception as e:
                print(f"Erro ao processar: {arq}")
                print(f" {e}")
                traceback.print_exc()
                continue


def emite_nf(arquivo, dados):
    print(f"Processando: {arquivo}")

    pfx_path = os.getenv("PFX_PATH", "./cert.pfx")
    pfx_password = os.getenv("PFX_PASSWORD", "senha_do_certificado")
    # ambiente = Ambiente.PRODUCAO_RESTRITA
    ambiente = Ambiente.PRODUCAO_REAL

    emissor = NFSeEmissor(pfx_path=pfx_path, pfx_password=pfx_password, ambiente=ambiente)

    # ========================================================================
    # 2. DADOS DO PRESTADOR (EMISSOR DA NOTA)
    # ========================================================================
    prestador = Prestador(
        # Obrigatório
        cpf_cnpj="20637193000101",  # CNPJ sem formatação
        inscricao_municipal="23086401",
        # razao_social="COLEGIO VETOR LTDA",
        optante_simples_nacional=False,
        op_simp_nac=1,  # 1-Não Optante, 2-MEI, 3-ME/EPP
    )

    # ========================================================================
    # 3. DADOS DO TOMADOR (CLIENTE)
    # ========================================================================
    # Campos obrigatórios: cpf_cnpj
    # Campos opcionais: razao_social, endereco, telefone, email, inscricao_municipal
    endereco_tomador = Endereco(
        logradouro=dados["endereco"]["logradouro"],
        numero=dados["endereco"]["numero"] or "0",
        bairro=dados["endereco"]["bairro"],
        codigo_municipio=dados["endereco"]["cidade"],
        uf=dados["endereco"]["uf"],
        cep=dados["endereco"]["cep"],
        # Corrigido: o complemento do endereço (ex: "CJ CELETRA") estava sendo
        # lido do JSON mas nunca passado para o modelo — se perdia no XML.
        complemento=dados["endereco"].get("complemento") or None,
    )

    tomador = Tomador(
        # Obrigatório
        cpf_cnpj=dados["cpf"],  # CNPJ sem formatação
        # Opcionais
        razao_social=dados["nome"],
        endereco=endereco_tomador,
        email=dados["email"],
    )

    # ========================================================================
    # 4. DADOS DO SERVIÇO PRESTADO
    # ========================================================================
    # Campos obrigatórios: codigo_servico, descricao, valor_servico
    # Campos opcionais: valor_deducoes, valor_desconto, valor_liquido,
    #                   iss_retido, codigo_municipio, tributos, codigo_nbs

    servico_json = dados["servicos"][0]

    # Corrigido: Decimal(float) herda o erro de precisão binária do float
    # (ex: Decimal(980.1) vira 980.099999999999909...). Usar Decimal(str(x))
    # evita esse problema na origem, em vez de confiar no arredondamento do
    # ".2f" na hora de formatar.
    valor_servico = Decimal(str(servico_json["valor"]))

    # Corrigido: o tributo ISS estava sendo montado com o VALOR DO SERVIÇO
    # inteiro (980.10) como se fosse o valor do imposto, e com alíquota
    # travada em 0 — ou seja, os campos reais do JSON (aliq_iss, valor_iss,
    # base_iss) eram ignorados e a alíquota do ISS nunca aparecia no XML
    # (o builder só emite <pAliq> quando aliquota > 0).
    tributo_iss = Tributo(
        aliquota=Decimal(str(servico_json.get("aliq_iss", 0))),
        valor=Decimal(str(servico_json.get("valor_iss", 0))),
        base_calculo=Decimal(str(servico_json.get("base_iss", 0))),
        codigo_tributacao=dados["cTribMun"],
        descricao="ISS",
    )

    servico = Servico(
        # Obrigatórios
        codigo_servico=re.sub(
            r"\D", "", dados["cTribNac"]
        ),  # Ver lista em https://www.gov.br/nfse/pt-br/mei-e-demais-empresas/codigos-de-tributacao-nacional-nbs
        descricao=servico_json["descricao"],
        valor_servico=valor_servico,  # Valor do serviço
        codigo_tributacao_municipal=dados["cTribMun"],
        # Opcionais - Valores
        # valor_deducoes=Decimal("0.00"),  # Valor das deduções
        # valor_desconto=Decimal("0.00"),  # Valor do desconto
        # valor_liquido=Decimal("100.00"),  # Valor líquido
        # Opcionais - Tributação
        iss_retido=False,  # True se o ISSQN for retido na fonte
        codigo_municipio="1302603",  # Código IBGE do município de prestação (Ver lista em https://www.ibge.gov.br/explica/codigos-dos-municipios.php)
        codigo_nbs=re.sub(
            r"\D", "", dados["cNBS"]
        ),  # https://www.gov.br/mdic/pt-br/images/REPOSITORIO/scs/decos/NBS/Anexoa_Ia_NBSa_2.0a_coma_alteraa_esa_6.12.18.pdf
        tributos=[tributo_iss],
    )

    # ========================================================================
    # 4b. GRUPO IBS/CBS (Reforma Tributária) — obrigatório desde 03/08/2026
    # para emissores integrados via Web Service.
    # ========================================================================
    # IMPORTANTE: o layout da DPS NÃO tem campo para enviar a alíquota do
    # IBS/CBS (pIBS/vIBS/pCBS/vCBS) — esses valores são calculados pelo
    # sistema nacional a partir do CST + cClassTrib e devolvidos no XML da
    # NFS-e de retorno, não são enviados por você. As alíquotas de teste de
    # 2026 (0,1% IBS + 0,9% CBS) do seu JSON são, portanto, apenas
    # informativas aqui — mantidas no arquivo de origem, mas não têm campo
    # de destino na DPS.
    tributacao_ibscbs = IBSCBSTributacao(
        cst=dados.get("cst_ibs_cbs", CST_IBS_CBS_PADRAO),  # ver aviso no topo do arquivo
        c_class_trib=dados.get("c_class_trib", C_CLASS_TRIB_PADRAO),  # ver aviso no topo do arquivo
    )
    ibscbs = IBSCBS(
        c_ind_op=dados.get("c_ind_op", C_IND_OP_PADRAO),  # ver aviso no topo do arquivo
        ind_dest="0",  # destinatário = tomador (não há destinatário distinto nos dados)
        trib=tributacao_ibscbs,
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
        tp_amb=1 if ambiente == Ambiente.PRODUCAO_REAL else 2,  # 1-Produção, 2-Homologação
        numero_rps=dados["num_nf"].lstrip("0")
        or "0",  # Número do RPS (Recibo de Prestação de Serviço)
        serie_rps="00002",  # Série do RPS
        data_emissao=datetime.strptime(dados["data_emissao"], "%d/%m/%Y"),
        c_loc_emi="1302603",  # Código IBGE do município emissor (obrigatório para gerar o ID)
        # Opcionais - Configurações
        natureza_operacao=1,  # 1-Tributação no município, 2-Tributação fora do município
        optante_simples_nacional=False,
        incentivador_cultural=False,
        # Opcional - Tomador
        tomador=tomador,
        # Grupo IBS/CBS (Reforma Tributária)
        ibscbs=ibscbs,
    )

    # Visualizar o ID gerado automaticamente
    print(f"ID do DPS gerado: {dps.get_id()}")

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
        return resultado

    except Exception as e:
        print(f"✗ Erro ao emitir nota fiscal: {str(e)}")
        return False


if __name__ == "__main__":
    main()
