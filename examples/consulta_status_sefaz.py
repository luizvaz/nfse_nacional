"""
Consulta do status do serviço da SEFAZ (NF-e / NFC-e)

ATENÇÃO — ESCOPO DESTE EXEMPLO
------------------------------
Este script consulta a **SEFAZ estadual de NF-e**, e não a API da NFS-e
Nacional. São sistemas distintos:

- NF-e / NFC-e  → SEFAZ estadual, biblioteca PyNFe (usada aqui)
- NFS-e Nacional → API nacional de serviços, este SDK (`src/nfse/`)

Ele está aqui como utilitário de apoio para quem opera os dois sistemas
(por exemplo, para verificar a disponibilidade do SEFAZ antes de uma rotina
de emissão). Requer a dependência opcional `PyNFe`, que **não** faz parte
das dependências deste SDK:

    pip install PyNFe

USO
---
    # Consulta padrão (produção, modelo nfe), UF via variável de ambiente
    python examples/consulta_status_sefaz.py --uf MG

    # Ambiente de homologação
    python examples/consulta_status_sefaz.py --uf MG --homologacao

    # NFC-e, com timeout customizado
    python examples/consulta_status_sefaz.py --uf SP --modelo nfce --timeout 30

    # Saída em JSON (útil para integrações e monitoramento)
    python examples/consulta_status_sefaz.py --uf MG --json

CÓDIGOS DE SAÍDA (exit codes)
-----------------------------
    0 - Serviço em operação (cStat 107)
    1 - Serviço indisponível ou resposta inesperada da SEFAZ
    2 - Erro de configuração (certificado ausente, UF inválida, etc.)
    3 - Erro de comunicação (rede, timeout, TLS)

Isso permite usar o script em monitoramento e cron:

    python examples/consulta_status_sefaz.py --uf MG || alerta.sh
"""

import argparse
import json
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, Optional

# Adiciona o diretório raiz do projeto ao PYTHONPATH
# Isso permite executar o script diretamente, sem instalar o pacote
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass  # dotenv é opcional


# Exit codes (ver docstring do módulo)
EXIT_OK = 0
EXIT_SERVICO_INDISPONIVEL = 1
EXIT_ERRO_CONFIG = 2
EXIT_ERRO_COMUNICACAO = 3

# cStat 107 = "Serviço em Operação". Qualquer outro código indica
# indisponibilidade, paralisação temporária ou erro na requisição.
CSTAT_SERVICO_EM_OPERACAO = "107"

# UFs aceitas pela SEFAZ (inclui os ambientes nacionais AN e EX)
UFS_VALIDAS = {
    "RO",
    "AC",
    "AM",
    "RR",
    "PA",
    "AP",
    "TO",
    "MA",
    "PI",
    "CE",
    "RN",
    "PB",
    "PE",
    "AL",
    "SE",
    "BA",
    "MG",
    "ES",
    "RJ",
    "SP",
    "PR",
    "SC",
    "RS",
    "MS",
    "MT",
    "GO",
    "DF",
    "AN",
    "EX",
}

# Campos extraídos da resposta (retStatusServico), na ordem de exibição.
# Nem todos são retornados por todas as UFs — os ausentes são ignorados.
CAMPOS_RESPOSTA = (
    ("cStat", "Código de status"),
    ("xMotivo", "Motivo"),
    ("tpAmb", "Ambiente"),
    ("verAplic", "Versão do aplicativo"),
    ("cUF", "Código da UF"),
    ("dhRecbto", "Data/hora do recebimento"),
    ("tMed", "Tempo médio de resposta (s)"),
    ("dhRetorno", "Previsão de retorno"),
    ("xObs", "Observação"),
)

DESCRICAO_AMBIENTE = {"1": "Produção", "2": "Homologação"}


def _local_name(tag: str) -> str:
    """Remove o namespace de uma tag XML: '{http://...}cStat' -> 'cStat'."""
    return tag.rsplit("}", 1)[-1]


def parse_resposta_status(xml_texto: str) -> Dict[str, str]:
    """
    Extrai os campos da resposta de status da SEFAZ.

    A resposta vem encapsulada em um envelope SOAP, cujo namespace varia
    conforme a UF e a versão do serviço. Em vez de fixar os namespaces
    (que quebra quando a SEFAZ muda a versão do SOAP), percorremos a árvore
    comparando apenas o nome local de cada elemento.

    Args:
        xml_texto: Corpo da resposta HTTP da SEFAZ

    Returns:
        Dicionário com os campos encontrados (ex: {"cStat": "107", ...})

    Raises:
        ET.ParseError: Se a resposta não for um XML válido
    """
    root = ET.fromstring(xml_texto)

    nomes_desejados = {campo for campo, _ in CAMPOS_RESPOSTA}
    encontrados: Dict[str, str] = {}

    for elemento in root.iter():
        nome = _local_name(elemento.tag)
        if nome in nomes_desejados and elemento.text:
            # Mantém a primeira ocorrência: em respostas com erro de schema,
            # a SEFAZ pode repetir cStat/xMotivo em níveis diferentes.
            encontrados.setdefault(nome, elemento.text.strip())

    return encontrados


def formatar_saida(campos: Dict[str, str]) -> str:
    """Formata os campos extraídos para leitura humana."""
    linhas = []
    largura = max(len(rotulo) for _, rotulo in CAMPOS_RESPOSTA)

    for campo, rotulo in CAMPOS_RESPOSTA:
        valor = campos.get(campo)
        if not valor:
            continue
        if campo == "tpAmb":
            valor = f"{valor} ({DESCRICAO_AMBIENTE.get(valor, 'desconhecido')})"
        linhas.append(f"{rotulo:<{largura}} : {valor}")

    return "\n".join(linhas)


def consultar_status(
    uf: str,
    pfx_path: str,
    pfx_password: str,
    homologacao: bool = False,
    modelo: str = "nfe",
    timeout: Optional[int] = None,
) -> str:
    """
    Consulta o status do serviço na SEFAZ e retorna o XML de resposta.

    Args:
        uf: Sigla da UF (ex: "MG"). Aceita minúsculas.
        pfx_path: Caminho para o certificado A1 (.pfx)
        pfx_password: Senha do certificado
        homologacao: True para o ambiente de homologação
        modelo: "nfe" ou "nfce"
        timeout: Timeout da requisição em segundos

    Returns:
        Corpo da resposta HTTP (XML da SEFAZ)

    Raises:
        ImportError: Se a PyNFe não estiver instalada
    """
    try:
        from pynfe.processamento.comunicacao import ComunicacaoSefaz
    except ImportError as e:
        raise ImportError(
            "A biblioteca PyNFe não está instalada. Instale com: pip install PyNFe"
        ) from e

    con = ComunicacaoSefaz(uf.upper(), pfx_path, pfx_password, homologacao)
    resposta = con.status_servico(modelo, timeout)
    return resposta.text


def _parse_args(argv: Optional[list] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Consulta o status do serviço da SEFAZ (NF-e / NFC-e).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Variáveis de ambiente (podem vir de um arquivo .env):\n"
            "  PFX_PATH      Caminho do certificado A1 (.pfx)\n"
            "  PFX_PASSWORD  Senha do certificado\n"
            "  SEFAZ_UF      UF padrão, usada quando --uf não é informado\n"
        ),
    )
    parser.add_argument(
        "--uf",
        default=os.getenv("SEFAZ_UF"),
        help="Sigla da UF a consultar (ex: MG). Padrão: variável SEFAZ_UF.",
    )
    parser.add_argument(
        "--modelo",
        default="nfe",
        choices=("nfe", "nfce"),
        help="Modelo do documento fiscal (padrão: nfe).",
    )
    parser.add_argument(
        "--homologacao",
        action="store_true",
        help="Consulta o ambiente de homologação (padrão: produção).",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=None,
        help="Timeout da requisição, em segundos.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="saida_json",
        help="Exibe o resultado em JSON, em vez do formato legível.",
    )
    parser.add_argument(
        "--xml",
        action="store_true",
        help="Exibe também o XML bruto retornado pela SEFAZ.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list] = None) -> int:
    """Ponto de entrada. Retorna o código de saída do processo."""
    args = _parse_args(argv)

    # ------------------------------------------------------------------
    # Validação da configuração
    # ------------------------------------------------------------------
    if not args.uf:
        print(
            "Erro: informe a UF com --uf ou defina a variável SEFAZ_UF.",
            file=sys.stderr,
        )
        return EXIT_ERRO_CONFIG

    uf = args.uf.upper()
    if uf not in UFS_VALIDAS:
        print(
            f"Erro: UF inválida: {args.uf!r}. Valores aceitos: {', '.join(sorted(UFS_VALIDAS))}",
            file=sys.stderr,
        )
        return EXIT_ERRO_CONFIG

    pfx_path = os.getenv("PFX_PATH", "./cert.pfx")
    pfx_password = os.getenv("PFX_PASSWORD")

    if not Path(pfx_path).is_file():
        print(
            f"Erro: certificado não encontrado em {pfx_path!r}. "
            "Defina a variável de ambiente PFX_PATH.",
            file=sys.stderr,
        )
        return EXIT_ERRO_CONFIG

    if not pfx_password:
        print(
            "Erro: a variável de ambiente PFX_PASSWORD não está definida.",
            file=sys.stderr,
        )
        return EXIT_ERRO_CONFIG

    # ------------------------------------------------------------------
    # Consulta
    # ------------------------------------------------------------------
    try:
        xml_resposta = consultar_status(
            uf=uf,
            pfx_path=pfx_path,
            pfx_password=pfx_password,
            homologacao=args.homologacao,
            modelo=args.modelo,
            timeout=args.timeout,
        )
    except ImportError as e:
        print(f"Erro: {e}", file=sys.stderr)
        return EXIT_ERRO_CONFIG
    except Exception as e:  # noqa: BLE001 - erros de rede/TLS/certificado
        print(f"Erro de comunicação com a SEFAZ: {e}", file=sys.stderr)
        return EXIT_ERRO_COMUNICACAO

    # ------------------------------------------------------------------
    # Interpretação da resposta
    # ------------------------------------------------------------------
    try:
        campos = parse_resposta_status(xml_resposta)
    except ET.ParseError as e:
        print(f"Erro: resposta da SEFAZ não é um XML válido: {e}", file=sys.stderr)
        print(xml_resposta, file=sys.stderr)
        return EXIT_SERVICO_INDISPONIVEL

    if not campos.get("cStat"):
        print("Erro: resposta da SEFAZ não contém o campo cStat.", file=sys.stderr)
        print(xml_resposta, file=sys.stderr)
        return EXIT_SERVICO_INDISPONIVEL

    em_operacao = campos["cStat"] == CSTAT_SERVICO_EM_OPERACAO

    if args.saida_json:
        resultado: Dict[str, Any] = dict(campos)
        resultado["em_operacao"] = em_operacao
        print(json.dumps(resultado, ensure_ascii=False, indent=2))
    else:
        print(formatar_saida(campos))
        print()
        print(
            "✓ Serviço em operação" if em_operacao else "✗ Serviço indisponível ou com restrições"
        )

    if args.xml:
        print("\n--- XML retornado pela SEFAZ ---", file=sys.stderr)
        print(xml_resposta, file=sys.stderr)

    return EXIT_OK if em_operacao else EXIT_SERVICO_INDISPONIVEL


if __name__ == "__main__":
    sys.exit(main())
