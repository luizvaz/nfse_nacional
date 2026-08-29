# Atualização do nfse_nacional

Este zip mantém a mesma estrutura de pastas do repositório: é só copiar o
conteúdo de `arquivos/` para a raiz do seu clone, sobrescrevendo os
arquivos existentes.

## Como aplicar

```bash
cd /opt/nfse_nacional          # raiz do seu clone
unzip -o atualizacao_repo.zip -d /tmp/upd
cp -r /tmp/upd/arquivos/* .
source .venv/bin/activate
python3 -m pytest tests/ -q    # 19 passed
git status                     # confira o diff antes de commitar
git add -A
git commit -m "Suporte a IBS/CBS (v1.01), exceções tipadas, exemplos e correções"
git push
```

Também incluí `mudancas_completas.patch` com o diff inteiro, caso prefira
`git apply mudancas_completas.patch` em vez de copiar os arquivos (só
funciona se seu working tree estiver igual ao estado em que este pacote foi
gerado — se você já tiver aplicado pacotes anteriores desta conversa, use a
cópia direta acima).

## O que muda

**Arquivos novos**
- `src/nfse/exceptions.py` — exceções tipadas da API (`NFSeError`,
  `NFSeAPIError`, `NFSeNotFoundError`, `NFSeConnectionError`)
- `examples/consulta_nfse.py` — consulta em lote de NFS-e por DPS
- `examples/consulta_status_sefaz.py` — status do serviço SEFAZ (NF-e)
- `emite_nfse.py` — seu script de emissão a partir de JSON, corrigido
- `schemas/*_v1.01.xsd` — schemas oficiais da Reforma Tributária (IBS/CBS)

**Arquivos modificados**
- `src/nfse/models.py` — grupo `IBSCBS`/`IBSCBSTributacao`/
  `IBSCBSDestinatario`; correção do `get_id()` (série de 5 dígitos)
- `src/nfse/xml_builder.py` — geração do bloco `<IBSCBS>` no XML da DPS
- `src/nfse/api_client.py` — exceções tipadas; correção do endpoint de
  `consultar_nota` (usava o parâmetro errado na URL)
- `src/nfse/emissor.py` — `consultar_nota` corrigido; novo `consultar_dps`
- `src/nfse/__init__.py` — exporta os novos modelos e exceções
- `tests/conftest.py`, `tests/test_client.py`, `tests/test_xml_builder.py`
  — fixture corrigida, 9 testes novos (IBSCBS + tratamento de erros)
- `pyproject.toml` — dependências declaradas (estava vazio)
- `requirements.txt` — convertido de UTF-16 para UTF-8
- `README.md` — documentação de tudo isso

## Antes de rodar em produção real

O `emite_nfse.py` usa valores de CST/cClassTrib/cIndOp padrão para o IBS/CBS
que **precisam ser confirmados com seu contador** para o seu tipo de
serviço — isso está marcado com aviso no topo do arquivo. Veja também a
seção "Reforma Tributária: IBS e CBS" do README.

## Não consegui dar push direto

Esta sessão não tem autorização de escrita no seu repositório GitHub (o
proxy de git bloqueou a tentativa com 403). Por isso o pacote — se quiser
que eu tente de novo em algum momento, me avise que reviso as permissões
disponíveis aqui.
