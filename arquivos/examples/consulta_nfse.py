"""
Consulta em lote de NFS-e a partir do identificador da DPS

Percorre uma faixa de números de RPS/DPS e verifica, para cada um, se já
existe uma NFS-e correspondente na API da NFS-e Nacional. Útil para:

- Conferir quais notas de um lote foram efetivamente emitidas
- Recuperar a chave de acesso de notas já processadas
- Auditar lacunas de numeração

COMO FUNCIONA
-------------
O identificador da DPS é derivado dos dados do prestador e da numeração,
segundo a regra:

    DPS + cód. município (7) + tipo inscrição (1) + CNPJ/CPF (14)
        + série (5) + número (15)

Por isso montamos um objeto `DPS` mínimo (sem serviços) apenas para gerar o
identificador com `dps.get_id()`, e consultamos a API com ele.

RESPOSTA "NÃO ENCONTRADA"
-------------------------
Quando a DPS ainda não gerou NFS-e, a API responde HTTP 404 com o código
`E2404` ("Não foi gerada uma NFS-e com o identificador de DPS informado").
Isso é uma resposta esperada da consulta, não uma falha — o SDK a expõe
como `NFSeNotFoundError`, tratada aqui como "não emitida".

USO
---
    # Consulta os RPS de 8 a 38, usando os dados do .env
    python examples/consulta_nfse.py --inicio 8 --fim 38

    # Produção real
    python examples/consulta_nfse.py --inicio 1 --fim 100 --producao

    # Sobrescrevendo os dados do prestador na linha de comando
    python examples/consulta_nfse.py --inicio 1 --fim 50 \
        --cnpj 12345678000190 --municipio 3550308 --serie 00002

    # Exporta o resultado em JSON
    python examples/consulta_nfse.py --inicio 1 --fim 50 --json resultado.json

    # Exibe apenas as notas encontradas
    python examples/consulta_nfse.py --inicio 1 --fim 50 --somente-emitidas

CONFIGURAÇÃO
------------
Nenhum dado do prestador está fixo no código. Configure via arquivo `.env`
(ou variáveis de ambiente), e sobrescreva pontualmente por linha de comando
quando necessário:

    PFX_PATH             Caminho do certificado A1 (.pfx)
    PFX_PASSWORD         Senha do certificado
    NFSE_CNPJ            CNPJ/CPF do prestador, sem formatação
    NFSE_INSCRICAO_MUNICIPAL  Inscrição municipal do prestador
    NFSE_CODIGO_MUNICIPIO     Código IBGE do município emissor (7 dígitos)
    NFSE_SERIE_DPS       Série do DPS (padrão: 00001)
    NFSE_AMBIENTE        "producao_real" ou "producao_restrita" (padrão)

Exemplo de `.env`:

    PFX_PATH=/caminho/para/cert.pfx
    PFX_PASSWORD=senha-do-certificado
    NFSE_CNPJ=12345678000190
    NFSE_INSCRICAO_MUNICIPAL=123456
    NFSE_CODIGO_MUNICIPIO=3550308
    NFSE_SERIE_DPS=00001
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Adiciona o diretório raiz do projeto ao PYTHONPATH
# Isso permite executar o script diretamente, sem instalar o pacote
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.nfse.api_client import Ambiente, APIClient  # noqa: E402
from src.nfse.exceptions import (  # noqa: E402
    NFSeAPIError,
    NFSeConnectionError,
    NFSeNotFoundError,
)
from src.nfse.models import DPS, Prestador  # noqa: E402

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass  # dotenv é opcional


# Valores padrão usados quando nada é informado (nem .env, nem CLI).
# Os dados do prestador NÃO têm padrão: precisam ser configurados.
SERIE_DPS_PADRAO = "00001"

# Exit codes
EXIT_OK = 0
EXIT_ERRO_CONFIG = 2
EXIT_ERRO_COMUNICACAO = 3


def montar_prestador(cnpj: str, inscricao_municipal: Optional[str] = None) -> Prestador:
    """
    Cria o prestador usado para derivar o identificador da DPS.

    Args:
        cnpj: CNPJ (14 dígitos) ou CPF (11 dígitos) do prestador, sem formatação
        inscricao_municipal: Inscrição municipal (opcional para montar o ID)
    """
    return Prestador(
        cpf_cnpj=cnpj,
        inscricao_municipal=inscricao_municipal,
        optante_simples_nacional=False,
        op_simp_nac=1,  # 1-Não Optante, 2-MEI, 3-ME/EPP
    )


def montar_id_dps(
    prestador: Prestador, numero_rps: int, serie: str, codigo_municipio: str
) -> str:
    """
    Monta o identificador da DPS para um número de RPS.

    O objeto DPS é criado apenas para reaproveitar a lógica de formação do
    identificador (`get_id()`); nenhum serviço é necessário para isso.

    Args:
        prestador: Prestador emissor
        numero_rps: Número do RPS/DPS
        serie: Série do DPS
        codigo_municipio: Código IBGE do município emissor
    """
    dps = DPS(
        prestador=prestador,
        servicos=[],
        numero_rps=str(numero_rps),
        serie_rps=serie,
        data_emissao=datetime.now(),
        c_loc_emi=codigo_municipio,
        natureza_operacao=1,
        optante_simples_nacional=False,
        incentivador_cultural=False,
    )
    return dps.get_id()


def consultar_faixa(
    api_client: APIClient,
    prestador: Prestador,
    inicio: int,
    fim: int,
    serie: str,
    codigo_municipio: str,
    exibir_progresso: bool = True,
    somente_emitidas: bool = False,
) -> List[Dict[str, Any]]:
    """
    Consulta uma faixa de RPS e retorna o resultado de cada um.

    Args:
        api_client: Cliente já autenticado
        prestador: Prestador usado para montar o identificador
        inicio: Primeiro número de RPS (inclusive)
        fim: Último número de RPS (inclusive)
        serie: Série do DPS
        codigo_municipio: Código IBGE do município emissor
        exibir_progresso: Imprime cada resultado conforme é consultado
        somente_emitidas: Exibe apenas os RPS que geraram NFS-e

    Returns:
        Lista de dicionários com o resultado de cada RPS consultado
    """
    resultados: List[Dict[str, Any]] = []

    for numero_rps in range(inicio, fim + 1):
        id_dps = montar_id_dps(prestador, numero_rps, serie, codigo_municipio)
        registro: Dict[str, Any] = {"rps": numero_rps, "id_dps": id_dps}

        try:
            resposta = api_client.consultar_dps(id_dps)
            registro["situacao"] = "emitida"
            registro["chave_acesso"] = resposta.get("chaveAcesso")
            registro["resposta"] = resposta

            if exibir_progresso:
                chave = registro["chave_acesso"] or "(sem chaveAcesso na resposta)"
                print(f"RPS {numero_rps:>6}  ✓ emitida     chaveAcesso: {chave}")

        except NFSeNotFoundError as e:
            # Resposta esperada: a DPS ainda não gerou NFS-e (código E2404)
            registro["situacao"] = "nao_emitida"
            registro["codigo_erro"] = e.codigo
            registro["descricao_erro"] = e.descricao

            if exibir_progresso and not somente_emitidas:
                print(f"RPS {numero_rps:>6}  – não emitida  ({e.codigo or 'sem código'})")

        except NFSeAPIError as e:
            # Outros erros da API: registra e segue para o próximo RPS
            registro["situacao"] = "erro"
            registro["status_code"] = e.status_code
            registro["codigo_erro"] = e.codigo
            registro["descricao_erro"] = e.descricao or e.texto

            if exibir_progresso:
                print(
                    f"RPS {numero_rps:>6}  ✗ erro         "
                    f"HTTP {e.status_code} [{e.codigo or '-'}]: "
                    f"{e.descricao or e.texto}",
                    file=sys.stderr,
                )

        resultados.append(registro)

    return resultados


def resumir(resultados: List[Dict[str, Any]]) -> Dict[str, int]:
    """Conta quantos RPS caíram em cada situação."""
    resumo = {"emitida": 0, "nao_emitida": 0, "erro": 0}
    for registro in resultados:
        situacao = registro.get("situacao", "erro")
        resumo[situacao] = resumo.get(situacao, 0) + 1
    return resumo


def _parse_args(argv: Optional[list] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Consulta em lote de NFS-e a partir do identificador da DPS.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Variáveis de ambiente (podem vir de um arquivo .env):\n"
            "  PFX_PATH                  Caminho do certificado A1 (.pfx)\n"
            "  PFX_PASSWORD              Senha do certificado\n"
            "  NFSE_CNPJ                 CNPJ/CPF do prestador, sem formatação\n"
            "  NFSE_INSCRICAO_MUNICIPAL  Inscrição municipal do prestador\n"
            "  NFSE_CODIGO_MUNICIPIO     Código IBGE do município emissor\n"
            "  NFSE_SERIE_DPS            Série do DPS\n"
            "  NFSE_AMBIENTE             producao_real | producao_restrita\n"
        ),
    )
    parser.add_argument(
        "--inicio", type=int, required=True, help="Primeiro número de RPS (inclusive)."
    )
    parser.add_argument(
        "--fim", type=int, required=True, help="Último número de RPS (inclusive)."
    )
    parser.add_argument(
        "--cnpj",
        default=os.getenv("NFSE_CNPJ"),
        help="CNPJ/CPF do prestador, sem formatação. Padrão: variável NFSE_CNPJ.",
    )
    parser.add_argument(
        "--inscricao-municipal",
        default=os.getenv("NFSE_INSCRICAO_MUNICIPAL"),
        help="Inscrição municipal. Padrão: variável NFSE_INSCRICAO_MUNICIPAL.",
    )
    parser.add_argument(
        "--municipio",
        default=os.getenv("NFSE_CODIGO_MUNICIPIO"),
        help=(
            "Código IBGE do município emissor (7 dígitos). "
            "Padrão: variável NFSE_CODIGO_MUNICIPIO."
        ),
    )
    parser.add_argument(
        "--serie",
        default=os.getenv("NFSE_SERIE_DPS", SERIE_DPS_PADRAO),
        help=f"Série do DPS. Padrão: variável NFSE_SERIE_DPS ou {SERIE_DPS_PADRAO}.",
    )
    parser.add_argument(
        "--producao",
        action="store_true",
        default=os.getenv("NFSE_AMBIENTE", "").lower() == "producao_real",
        help=(
            "Consulta o ambiente de produção real (padrão: produção restrita). "
            "Também pode ser definido com NFSE_AMBIENTE=producao_real."
        ),
    )
    parser.add_argument(
        "--somente-emitidas",
        action="store_true",
        help="Exibe apenas os RPS que já geraram NFS-e.",
    )
    parser.add_argument(
        "--json",
        metavar="ARQUIVO",
        dest="arquivo_json",
        help="Salva o resultado completo da consulta em um arquivo JSON.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list] = None) -> int:
    """Ponto de entrada. Retorna o código de saída do processo."""
    args = _parse_args(argv)

    if args.inicio > args.fim:
        print("Erro: --inicio não pode ser maior que --fim.", file=sys.stderr)
        return EXIT_ERRO_CONFIG

    # ------------------------------------------------------------------
    # Dados do prestador (via .env ou linha de comando)
    # ------------------------------------------------------------------
    if not args.cnpj:
        print(
            "Erro: informe o CNPJ/CPF do prestador com --cnpj "
            "ou defina a variável NFSE_CNPJ.",
            file=sys.stderr,
        )
        return EXIT_ERRO_CONFIG

    cnpj = "".join(filter(str.isdigit, args.cnpj))
    if len(cnpj) not in (11, 14):
        print(
            f"Erro: CNPJ/CPF inválido: {args.cnpj!r}. "
            "Informe 14 dígitos (CNPJ) ou 11 dígitos (CPF).",
            file=sys.stderr,
        )
        return EXIT_ERRO_CONFIG

    if not args.municipio:
        print(
            "Erro: informe o código IBGE do município com --municipio "
            "ou defina a variável NFSE_CODIGO_MUNICIPIO.",
            file=sys.stderr,
        )
        return EXIT_ERRO_CONFIG

    codigo_municipio = "".join(filter(str.isdigit, args.municipio))
    if len(codigo_municipio) != 7:
        print(
            f"Erro: código de município inválido: {args.municipio!r}. "
            "O código IBGE tem 7 dígitos.",
            file=sys.stderr,
        )
        return EXIT_ERRO_CONFIG

    serie = "".join(filter(str.isdigit, args.serie)).zfill(5)
    if len(serie) > 5:
        print(
            f"Erro: série inválida: {args.serie!r}. Máximo de 5 dígitos.",
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

    ambiente = Ambiente.PRODUCAO_REAL if args.producao else Ambiente.PRODUCAO_RESTRITA

    try:
        api_client = APIClient(ambiente, pfx_path, pfx_password)
    except Exception as e:  # noqa: BLE001 - erro de certificado/dependência
        print(f"Erro ao inicializar o cliente da API: {e}", file=sys.stderr)
        return EXIT_ERRO_CONFIG

    prestador = montar_prestador(cnpj, args.inscricao_municipal)

    print(
        f"Consultando RPS {args.inicio} a {args.fim}\n"
        f"  Prestador : {cnpj}\n"
        f"  Município : {codigo_municipio}\n"
        f"  Série     : {serie}\n"
        f"  Ambiente  : {ambiente.value}\n"
    )

    try:
        resultados = consultar_faixa(
            api_client=api_client,
            prestador=prestador,
            inicio=args.inicio,
            fim=args.fim,
            serie=serie,
            codigo_municipio=codigo_municipio,
            somente_emitidas=args.somente_emitidas,
        )
    except NFSeConnectionError as e:
        print(f"\nErro de comunicação com a API: {e}", file=sys.stderr)
        return EXIT_ERRO_COMUNICACAO
    except KeyboardInterrupt:
        print("\nConsulta interrompida pelo usuário.", file=sys.stderr)
        return EXIT_ERRO_COMUNICACAO

    resumo = resumir(resultados)
    print(
        f"\nResumo: {resumo['emitida']} emitida(s), "
        f"{resumo['nao_emitida']} não emitida(s), "
        f"{resumo['erro']} com erro."
    )

    if args.arquivo_json:
        with open(args.arquivo_json, "w", encoding="utf-8") as f:
            json.dump(resultados, f, ensure_ascii=False, indent=2)
        print(f"Resultado salvo em: {args.arquivo_json}")

    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
