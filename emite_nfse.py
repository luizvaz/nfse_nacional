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
nfse_ = Path('/opt/nfse_nacional/')
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
    IBSCBSDestinatario,
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
CST_IBS_CBS_PADRAO = "000"          # Tributação integral
C_CLASS_TRIB_PADRAO = "000001"      # Situações tributadas integralmente pelo IBS e CBS
C_IND_OP_PADRAO = "100301"          # Serviços gerais em operação onerosa (CONFERIR no Anexo VIII)


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

                    nfse_file = os.path.join("./rps/processados", os.path.splitext(arq)[0] + ".nfse")
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
    #ambiente = Ambiente.PRODUCAO_RESTRITA
    ambiente = Ambiente.PRODUCAO_REAL

    emissor = NFSeEmissor(pfx_path=pfx_path, pfx_password=pfx_password, ambiente=ambiente)

    # ========================================================================
    # 1. DADOS DO PRESTADOR (EMISSOR DA NOTA)
    # ========================================================================
    # O gerador de RPS do am_manaus manda "prestador" como uma STRING só com
    # o CNPJ (formato original/legado) — não como objeto {"cpf_cnpj":...}.
    # Aceita os dois formatos: se vier um dict (formato novo, ainda não usado
    # em produção), lê os campos de dentro dele; se vier string, usa direto
    # como cpf_cnpj. A IM não tem campo próprio no JSON legado, então
    # continua fixa aqui (ajuste se você emitir por mais de uma IM).
    prestador_json = dados.get("prestador")
    if isinstance(prestador_json, dict):
        prestador_cpf_cnpj = prestador_json.get("cpf_cnpj", "20637193000101")
        prestador_im = prestador_json.get("inscricao_municipal", "23086401")
    elif isinstance(prestador_json, str) and prestador_json.strip():
        prestador_cpf_cnpj = re.sub(r"\D", "", prestador_json)
        prestador_im = "23086401"
    else:
        prestador_cpf_cnpj = "20637193000101"
        prestador_im = "23086401"

    prestador = Prestador(
        # Obrigatório
        cpf_cnpj=prestador_cpf_cnpj,  # CNPJ sem formatação
        inscricao_municipal=prestador_im,
        #razao_social="COLEGIO VETOR LTDA",
        optante_simples_nacional=False,
        op_simp_nac=1,  # 1-Não Optante, 2-MEI, 3-ME/EPP
    )

    # ========================================================================
    # 2. DADOS DO TOMADOR (CLIENTE)
    # ========================================================================
    # Campos obrigatórios: cpf_cnpj
    # Campos opcionais: razao_social, endereco, telefone, email, inscricao_municipal
    #
    # Formato legado (o que o am_manaus realmente gera): cpf/nome/email/
    # endereco soltos na raiz do JSON. Se um bloco "tomador" (dict) existir,
    # usa ele em vez disso — mas isso não é o que está em produção hoje.
    tomador_json = dados.get("tomador")
    if isinstance(tomador_json, dict):
        tomador_cpf = tomador_json["cpf"]
        tomador_nome = tomador_json["nome"]
        tomador_email = tomador_json.get("email")
        endereco_json = tomador_json["endereco"]
    else:
        tomador_cpf = dados["cpf"]
        tomador_nome = dados["nome"]
        tomador_email = dados.get("email")
        endereco_json = dados["endereco"]

    endereco_tomador = Endereco(
        logradouro=endereco_json["logradouro"],
        numero=endereco_json["numero"] or "0",
        bairro=endereco_json["bairro"],
        codigo_municipio=endereco_json["cidade"],
        uf=endereco_json["uf"],
        cep=endereco_json["cep"],
        # Corrigido: o complemento do endereço (ex: "CJ CELETRA") estava sendo
        # lido do JSON mas nunca passado para o modelo — se perdia no XML.
        complemento=endereco_json.get("complemento") or None,
    )

    tomador = Tomador(
        # Obrigatório
        cpf_cnpj=tomador_cpf,  # CPF/CNPJ sem formatação
        # Opcionais
        razao_social=tomador_nome,
        endereco=endereco_tomador,
        email=tomador_email or None,
    )

    # ========================================================================
    # 3. DADOS DO SERVIÇO PRESTADO
    # ========================================================================
    # Campos obrigatórios: codigo_servico, descricao, valor_servico
    # Campos opcionais: valor_deducoes, valor_desconto, valor_liquido,
    #                   iss_retido, codigo_municipio, tributos, codigo_nbs

    servico_json = dados["servicos"][0]

    # cTribNac/cTribMun/cNBS: no JSON legado (o que o am_manaus gera) esses
    # três códigos ficam soltos na RAIZ do documento, valendo pra nota
    # inteira — não dentro de cada item de "servicos". Também aceita a
    # variante por-serviço, em snake_case ou camelCase, caso algum dia o
    # gerador passe a mandar assim.
    def _campo(*chaves, obrigatorio=True):
        for origem in (servico_json, dados):
            for chave in chaves:
                if chave in origem and origem[chave] not in (None, ""):
                    return origem[chave]
        if obrigatorio:
            raise KeyError(chaves[0])
        return None

    c_trib_nac = _campo("c_trib_nac", "cTribNac")
    c_trib_mun = _campo("c_trib_mun", "cTribMun")
    c_nbs = _campo("c_nbs", "cNBS")

    # Corrigido: Decimal(float) herda o erro de precisão binária do float
    # (ex: Decimal(980.1) vira 980.099999999999909...). Usar Decimal(str(x))
    # evita esse problema na origem, em vez de confiar no arredondamento do
    # ".2f" na hora de formatar.
    valor_servico = Decimal(str(servico_json["valor"]))
    valor_desconto = Decimal(str(servico_json.get("desconto", 0)))
    valor_deducoes = Decimal(str(servico_json.get("deducoes", 0)))

    # Corrigido: o tributo ISS estava sendo montado com o VALOR DO SERVIÇO
    # inteiro (980.10) como se fosse o valor do imposto, e com alíquota
    # travada em 0 — ou seja, os campos reais do JSON (aliq_iss, valor_iss,
    # base_iss) eram ignorados e a alíquota do ISS nunca aparecia no XML
    # (o builder só emite <pAliq> quando aliquota > 0).
    tributo_iss = Tributo(
        aliquota=Decimal(str(servico_json.get("aliq_iss", 0))),
        valor=Decimal(str(servico_json.get("valor_iss", 0))),
        base_calculo=Decimal(str(servico_json.get("base_iss", 0))),
        codigo_tributacao=c_trib_mun,
        descricao="ISS",
    )

    servico = Servico(
        # Obrigatórios
        codigo_servico=re.sub(r"\D", "", c_trib_nac),  # Ver lista em https://www.gov.br/nfse/pt-br/mei-e-demais-empresas/codigos-de-tributacao-nacional-nbs
        descricao=servico_json["descricao"],
        valor_servico=valor_servico,  # Valor do serviço
        codigo_tributacao_municipal=re.sub(r"\D", "", c_trib_mun),
        # Opcionais - Valores
        valor_deducoes=valor_deducoes,
        valor_desconto=valor_desconto,
        # Opcionais - Tributação
        iss_retido=bool(servico_json.get("iss_retido", False)),
        codigo_municipio=dados.get("c_loc_emi", "1302603"),  # Código IBGE do município de prestação (Ver lista em https://www.ibge.gov.br/explica/codigos-dos-municipios.php)
        codigo_nbs=re.sub(r"\D", "", c_nbs),  # https://www.gov.br/mdic/pt-br/images/REPOSITORIO/scs/decos/NBS/Anexoa_Ia_NBSa_2.0a_coma_alteraa_esa_6.12.18.pdf
        tributos=[tributo_iss],
    )

    # Observação do item de serviço (referência, aluno, turma etc.) — o campo
    # "aluno" do JSON já vem embutido no texto de "observacao" pelo sistema de
    # origem, então basta repassar a observação como está.
    # ATENÇÃO: o xml_builder atual ainda não emite o campo <xInfComp>/<infAdic>
    # a partir de DPS.observacoes — isso fica registrado aqui apenas para o
    # dia em que esse suporte for adicionado ao builder.
    observacao = servico_json.get("observacao")

    # ========================================================================
    # 3b. GRUPO IBS/CBS (Reforma Tributária) — obrigatório desde 03/08/2026
    # para emissores integrados via Web Service.
    # ========================================================================
    # IMPORTANTE: o layout da DPS NÃO tem campo para enviar a alíquota do
    # IBS/CBS (pIBS/vIBS/pCBS/vCBS) — esses valores são calculados pelo
    # sistema nacional a partir do CST + cClassTrib e devolvidos no XML da
    # NFS-e de retorno, não são enviados por você. As alíquotas informativas
    # do bloco "_ibscbs_informativo" do JSON (se presente) são, portanto,
    # apenas para registro/reconciliação no seu lado — não têm campo de
    # destino na DPS.
    ibscbs_json = dados.get("ibscbs", {})
    trib_json = ibscbs_json.get("trib", {})

    def _decimal_opt(valor):
        return Decimal(str(valor)) if valor is not None else None

    tributacao_ibscbs = IBSCBSTributacao(
        cst=trib_json.get("cst", CST_IBS_CBS_PADRAO),  # ver aviso no topo do arquivo
        c_class_trib=trib_json.get("c_class_trib", C_CLASS_TRIB_PADRAO),  # ver aviso no topo do arquivo
        c_cred_pres=trib_json.get("c_cred_pres") or None,
        cst_regular=trib_json.get("cst_regular") or None,
        c_class_trib_regular=trib_json.get("c_class_trib_regular") or None,
        p_dif_uf=_decimal_opt(trib_json.get("p_dif_uf")),
        p_dif_mun=_decimal_opt(trib_json.get("p_dif_mun")),
        p_dif_cbs=_decimal_opt(trib_json.get("p_dif_cbs")),
    )

    destinatario_json = ibscbs_json.get("destinatario")
    destinatario_ibscbs = None
    if ibscbs_json.get("ind_dest") == "1" and destinatario_json:
        destinatario_ibscbs = IBSCBSDestinatario(
            cpf_cnpj=destinatario_json["cpf_cnpj"],
            razao_social=destinatario_json["razao_social"],
        )

    ibscbs = IBSCBS(
        c_ind_op=ibscbs_json.get("c_ind_op", C_IND_OP_PADRAO),  # ver aviso no topo do arquivo
        ind_dest=ibscbs_json.get("ind_dest", "0"),  # "0" = destinatário é o próprio tomador
        trib=tributacao_ibscbs,
        fin_nfse=ibscbs_json.get("fin_nfse", "0"),  # "0" = NFS-e regular
        ind_final=ibscbs_json.get("ind_final") or None,
        tp_oper=ibscbs_json.get("tp_oper") or None,
        tp_ente_gov=ibscbs_json.get("tp_ente_gov") or None,
        destinatario=destinatario_ibscbs,
    )

    # ========================================================================
    # 4. CRIAÇÃO DO DPS (DECLARAÇÃO DE PRESTAÇÃO DE SERVIÇO)
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
        tp_amb=1 if ambiente == Ambiente.PRODUCAO_REAL else 2, # 1-Produção, 2-Homologação
        numero_rps=dados["num_nf"].lstrip("0") or "0",  # Número do RPS (Recibo de Prestação de Serviço)
        serie_rps=dados.get("serie_rps", "00002"),  # Série do RPS (até 5 dígitos)
        data_emissao=datetime.strptime(dados["data_emissao"], "%d/%m/%Y"),
        c_loc_emi=dados.get("c_loc_emi", "1302603"),  # Código IBGE do município emissor (obrigatório para gerar o ID)
        # Opcionais - Configurações
        natureza_operacao=int(dados.get("natureza_operacao", 1)),  # 1-Tributação no município, 2-Tributação fora do município
        optante_simples_nacional=False,
        incentivador_cultural=False,
        observacoes=observacao,
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
        resultado = emissor.emitir_nota(
            dps,
            validate_xml=False,
            # Salva uma cópia do XML assinado (o mesmo enviado ao webservice)
            # em ./rps/xml_enviados/{ID do DPS}.xml — útil pra depurar erros
            # retornados pela API sem precisar reconstruir o XML na mão.
            salvar_xml_em="./rps/xml_enviados/",
        )
        print("✓ Nota fiscal emitida com sucesso!")
        return resultado

    except Exception as e:
        print(f"✗ Erro ao emitir nota fiscal: {str(e)}")
        return False

if __name__ == "__main__":
    main()

