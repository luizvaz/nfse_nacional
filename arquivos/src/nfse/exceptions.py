"""
Exceções da API de NFSe Nacional

A API retorna erros em JSON, no formato:

    {
      "tipoAmbiente": 1,
      "dataHoraProcessamento": "2026-08-29T06:42:15.6154287-03:00",
      "erro": {
        "codigo": "E2404",
        "descricao": "Não foi gerada uma NFS-e com o identificador de DPS informado"
      }
    }

As classes abaixo preservam esses campos, permitindo tratar cada situação de
forma específica em vez de inspecionar o texto da mensagem.

Todas herdam de `Exception`, mantendo compatibilidade com código que já
captura exceções genéricas.
"""

from typing import Any, Dict, Optional


class NFSeError(Exception):
    """Exceção base para todos os erros deste SDK"""


class NFSeConnectionError(NFSeError):
    """Falha de comunicação com a API (rede, timeout, TLS)"""


class NFSeAPIError(NFSeError):
    """
    A API respondeu com um código de erro HTTP.

    Attributes:
        status_code: Código HTTP da resposta (ex: 400, 404, 500)
        codigo: Código de erro da API (ex: "E2404"), quando disponível
        descricao: Descrição do erro retornada pela API, quando disponível
        payload: Corpo da resposta já convertido em dict, quando for JSON
        texto: Corpo bruto da resposta
    """

    def __init__(
        self,
        status_code: int,
        texto: str,
        codigo: Optional[str] = None,
        descricao: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
    ):
        self.status_code = status_code
        self.texto = texto
        self.codigo = codigo
        self.descricao = descricao
        self.payload = payload or {}

        if codigo and descricao:
            mensagem = f"Erro {status_code} [{codigo}]: {descricao}"
        else:
            mensagem = f"Erro {status_code}: {texto}"

        super().__init__(mensagem)


class NFSeNotFoundError(NFSeAPIError):
    """
    O recurso consultado não existe (HTTP 404).

    O caso mais comum é o código "E2404" — a DPS consultada ainda não gerou
    uma NFS-e. Isso costuma ser uma resposta esperada, e não uma falha:

        try:
            resultado = api_client.consultar_dps(codigo)
        except NFSeNotFoundError:
            print("DPS ainda não emitida")
    """
