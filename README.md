# NFSe Nacional - Python SDK

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

SDK Python para integração com a API de emissão de Notas Fiscais de Serviço (NFSe) da Nota Nacional. Este projeto facilita a emissão de NFSe seguindo o padrão nacional, incluindo construção do XML, assinatura digital e comunicação com a API oficial.

## 📋 Índice

- [Características](#-características)
- [Instalação](#-instalação)
- [Uso Rápido](#-uso-rápido)
- [Reforma Tributária: IBS e CBS](#-reforma-tributária-ibs-e-cbs)
- [Documentação](#-documentação)
- [Estrutura do Projeto](#-estrutura-do-projeto)
- [Desenvolvimento](#-desenvolvimento)
- [Contribuindo](#-contribuindo)
- [Licença](#-licença)
- [Suporte](#-suporte)

## ✨ Características

- ✅ **Conformidade com XSD**: Geração de XML validado contra o schema oficial
- ✅ **Reforma Tributária (IBS/CBS)**: Suporte ao grupo `IBSCBS` do leiaute v1.01
- ✅ **Assinatura Digital**: Suporte a certificados A1 (.pfx) para assinatura XML
- ✅ **Autenticação Automática**: Autenticação via certificado digital (sem necessidade de API keys)
- ✅ **Validação Integrada**: Validação XSD antes do envio
- ✅ **Ambientes Separados**: Suporte para produção restrita e produção real
- ✅ **Testes Automatizados**: Suite completa de testes com validação XSD
- ✅ **Type Hints**: Código totalmente tipado para melhor experiência de desenvolvimento
- ✅ **Documentação Completa**: Exemplos e documentação detalhada

## 🚀 Instalação

### Pré-requisitos

- Python 3.8 ou superior
- Certificado digital A1 (.pfx) válido
- Arquivos XSD da especificação (disponíveis em `schemas/`)

### Instalação (recomendado: ambiente virtual)

O uso de um ambiente virtual é **fortemente recomendado**. Em distribuições
Debian/Ubuntu, instalar as dependências diretamente no Python do sistema
costuma falhar com erros do tipo
`Cannot uninstall urllib3, RECORD file not found. Hint: The package was
installed by debian.` — isso acontece porque o pacote foi instalado pelo `apt`
e o `pip` não consegue gerenciá-lo. O venv evita esse conflito por completo.

```bash
# Clone o repositório
git clone https://github.com/luizvaz/nfse_nacional.git
cd nfse_nacional

# Crie o ambiente virtual
python3 -m venv .venv

# Ative o ambiente virtual
# Linux/Mac:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate

# Instale as dependências
pip install --upgrade pip
pip install -r requirements.txt
```

> Lembre-se de ativar o venv (`source .venv/bin/activate`) sempre que for
> executar os scripts do projeto, inclusive em produção.

### Instalação sem ambiente virtual

Se realmente não for possível usar um venv em distribuições com Python
gerenciado externamente (PEP 668):

```bash
pip3 install -r requirements.txt --break-system-packages --ignore-installed
```

O `--ignore-installed` impede que o `pip` tente desinstalar pacotes
gerenciados pelo `apt`. Funciona, mas mistura pacotes de origens diferentes
no mesmo ambiente — prefira o venv sempre que possível.

## 💡 Uso Rápido

### Exemplo Básico

```python
from src.nfse.emissor import NFSeEmissor
from src.nfse.api_client import Ambiente
from src.nfse.models import DPS, Prestador, Tomador, Servico, Endereco, Tributo
from decimal import Decimal
from datetime import datetime

# 1. Configure o emissor
emissor = NFSeEmissor(
    pfx_path="caminho/para/certificado.pfx",
    pfx_password="senha_do_certificado",
    ambiente=Ambiente.PRODUCAO_RESTRITA  # ou Ambiente.PRODUCAO_REAL
)

# 2. Crie os dados do prestador
prestador = Prestador(
    cpf_cnpj="12345678000190",
    inscricao_municipal="123456",
    optante_simples_nacional=True,
    op_simp_nac=3,  # ME/EPP
    reg_apuracao_sn=1,
    p_tot_trib_sn=Decimal("15.00")
)

# 3. Crie os dados do tomador
tomador = Tomador(
    cpf_cnpj="98765432000100",
    razao_social="Cliente Exemplo Ltda"
)

# 4. Crie os dados do serviço
servico = Servico(
    codigo_servico="140101",  # cTribNac: exatamente 6 dígitos
    descricao="Desenvolvimento de software",
    valor_servico=Decimal("1000.00"),
    codigo_municipio="3550308"  # Código IBGE
)

# 5. Crie o DPS
dps = DPS(
    prestador=prestador,
    tomador=tomador,
    servicos=[servico],
    numero_rps="100000000000001",
    serie_rps="00001",
    data_emissao=datetime.now(),
    c_loc_emi="3550308"  # Código IBGE do município emissor
)

# 6. Emita a nota fiscal
resultado = emissor.emitir_nota(dps, validate_xml=True)
print(f"Nota emitida: {resultado}")
```

### Exemplo Completo

Consulte o arquivo [`examples/exemplo_basico.py`](examples/exemplo_basico.py) para um exemplo completo e comentado com todos os campos disponíveis.

### Exemplos disponíveis

| Arquivo | Descrição |
|---|---|
| [`examples/exemplo_basico.py`](examples/exemplo_basico.py) | Emissão completa de uma NFS-e, com todos os campos comentados |
| [`examples/consulta_nfse.py`](examples/consulta_nfse.py) | Consulta em lote: verifica quais DPS de uma faixa já geraram NFS-e |
| [`examples/consulta_status_sefaz.py`](examples/consulta_status_sefaz.py) | Consulta o status do serviço da SEFAZ (NF-e/NFC-e) — utilitário de apoio, ver nota abaixo |

#### Consulta em lote de NFS-e

Percorre uma faixa de números de RPS e verifica quais já geraram NFS-e,
recuperando a chave de acesso das notas encontradas. Útil para conferir
lotes emitidos e auditar lacunas de numeração.

Os dados do prestador vêm do arquivo `.env` (ou de variáveis de ambiente),
e podem ser sobrescritos por linha de comando:

```bash
# .env
PFX_PATH=/caminho/para/cert.pfx
PFX_PASSWORD=senha-do-certificado
NFSE_CNPJ=12345678000190
NFSE_INSCRICAO_MUNICIPAL=123456
NFSE_CODIGO_MUNICIPIO=3550308
NFSE_SERIE_DPS=00001
NFSE_AMBIENTE=producao_restrita
```

```bash
# Consulta os RPS de 8 a 38, usando a configuração do .env
python examples/consulta_nfse.py --inicio 8 --fim 38

# Produção real, exportando o resultado
python examples/consulta_nfse.py --inicio 1 --fim 100 --producao --json lote.json

# Sobrescrevendo o prestador na linha de comando
python examples/consulta_nfse.py --inicio 1 --fim 50 \
    --cnpj 12345678000190 --municipio 3550308 --serie 00002

# Apenas as notas já emitidas
python examples/consulta_nfse.py --inicio 1 --fim 50 --somente-emitidas
```

Saída:

```
Consultando RPS 1 a 3
  Prestador : 12345678000190
  Município : 3550308
  Série     : 00001
  Ambiente  : producao_restrita

RPS      1  ✓ emitida     chaveAcesso: 3526000000000000...
RPS      2  – não emitida  (E2404)
RPS      3  ✗ erro         HTTP 500 [-]: Internal Server Error

Resumo: 1 emitida(s), 1 não emitida(s), 1 com erro.
```

#### Consulta de status da SEFAZ (NF-e)

> ⚠️ Este utilitário consulta a **SEFAZ estadual de NF-e**, não a API da
> NFS-e Nacional — são sistemas distintos. Ele é oferecido como apoio a
> quem opera os dois, por exemplo para checar a disponibilidade do SEFAZ
> antes de uma rotina de emissão. Requer a dependência opcional `PyNFe`
> (`pip install PyNFe`), que não faz parte das dependências deste SDK.

```bash
# Consulta o ambiente de produção de MG
python examples/consulta_status_sefaz.py --uf MG

# Homologação, modelo NFC-e, com timeout
python examples/consulta_status_sefaz.py --uf SP --modelo nfce --homologacao --timeout 30

# Saída em JSON, para integrações e monitoramento
python examples/consulta_status_sefaz.py --uf MG --json
```

O script retorna códigos de saída que permitem usá-lo em cron e
monitoramento:

| Código | Significado |
|---|---|
| `0` | Serviço em operação (cStat 107) |
| `1` | Serviço indisponível ou resposta inesperada |
| `2` | Erro de configuração (certificado ausente, UF inválida) |
| `3` | Erro de comunicação (rede, timeout, TLS) |

```bash
python examples/consulta_status_sefaz.py --uf MG || notifica-equipe.sh
```

Configuração via variáveis de ambiente (aceita arquivo `.env`):
`PFX_PATH`, `PFX_PASSWORD` e `SEFAZ_UF` (UF padrão quando `--uf` é omitido).

## 🏛️ Reforma Tributária: IBS e CBS

A partir do leiaute **v1.01** da NFS-e Nacional, a DPS passou a contar com o
grupo `IBSCBS`, referente ao IBS (Imposto sobre Bens e Serviços) e à CBS
(Contribuição sobre Bens e Serviços). Para emissores integrados via Web
Service, o preenchimento desse grupo passou a ser exigido a partir de
**03/08/2026**.

### Como preencher

```python
from src.nfse.models import DPS, IBSCBS, IBSCBSTributacao

# Situação e classificação tributária (grupo gIBSCBS)
tributacao = IBSCBSTributacao(
    cst="000",              # CST: 3 dígitos (000 = tributação integral)
    c_class_trib="000001",  # cClassTrib: 6 dígitos (CST + complemento)
)

ibscbs = IBSCBS(
    c_ind_op="100301",  # cIndOp: código indicador da operação (6 dígitos)
    ind_dest="0",       # 0 = destinatário é o próprio tomador
    trib=tributacao,
)

dps = DPS(
    prestador=prestador,
    servicos=[servico],
    tomador=tomador,
    # ... demais campos ...
    ibscbs=ibscbs,  # grupo IBS/CBS
)
```

O XML resultante inclui o grupo como **elemento irmão** de `<serv>` e
`<valores>`, dentro de `<infDPS>`:

```xml
<infDPS Id="DPS...">
  <!-- ... -->
  <serv>...</serv>
  <valores>...</valores>
  <IBSCBS>
    <finNFSe>0</finNFSe>
    <cIndOp>100301</cIndOp>
    <indDest>0</indDest>
    <valores>
      <trib>
        <gIBSCBS>
          <CST>000</CST>
          <cClassTrib>000001</cClassTrib>
        </gIBSCBS>
      </trib>
    </valores>
  </IBSCBS>
</infDPS>
```

### ⚠️ Pontos de atenção

**1. A DPS não envia alíquotas nem valores de IBS/CBS.**
Campos como `vBC`, `pIBS`, `vIBS`, `pCBS` e `vCBS` **não** fazem parte da
DPS enviada. Eles são calculados pelo sistema nacional a partir do
`CST` + `cClassTrib` e retornados no XML da **NFS-e** (grupo `TCRTCIBSCBS`).
As alíquotas de teste de 2026 (0,1% IBS e 0,9% CBS) não possuem campo de
destino no envio.

**2. O grupo `IBSCBS` não fica dentro de `<serv>`.**
Ele é irmão de `<serv>` e `<valores>` em `<infDPS>`, conforme o tipo
`TCRTCInfoIBSCBS` do XSD v1.01.

**3. `CST`, `cClassTrib` e `cIndOp` dependem da natureza do serviço.**
Os valores do exemplo (`000` / `000001` / `100301`) correspondem à
tributação integral em operação onerosa e servem como ponto de partida.
Operações com isenção, imunidade, redução de alíquota ou regimes
específicos exigem códigos diferentes. O `cIndOp` deve ser obtido da
tabela de correlação oficial (Anexo VIII), que cruza item de serviço, NBS
e `cClassTrib`. **Confirme os códigos com seu contador antes de emitir em
produção real.**

### Modelos disponíveis

| Modelo | Corresponde a | Descrição |
|---|---|---|
| `IBSCBS` | `TCRTCInfoIBSCBS` | Grupo principal declarado pelo emitente |
| `IBSCBSTributacao` | `TCRTCInfoTributosSitClas` | Grupo `gIBSCBS`: CST, cClassTrib, crédito presumido, tributação regular e diferimento |
| `IBSCBSDestinatario` | `TCRTCInfoDest` | Destinatário do serviço (obrigatório quando `ind_dest="1"`) |

## 📚 Documentação

### Componentes Principais

#### NFSeEmissor
Classe principal que orquestra todo o fluxo de emissão:
- Construção do XML do DPS
- Assinatura digital com certificado A1
- Envio para a API da Nota Nacional

#### XMLBuilder
Constrói o XML do DPS conforme o schema XSD oficial:
```python
from src.nfse.xml_builder import XMLBuilder

# Leiaute v1.01 (com suporte a IBS/CBS)
builder = XMLBuilder(xsd_path="schemas/DPS_v1.01.xsd", versao="1.01")
xml = builder.build_dps_xml(dps, validate=True)
```

#### APIClient
Comunicação direta com os endpoints da API:

```python
from src.nfse.api_client import Ambiente, APIClient

api = APIClient(Ambiente.PRODUCAO_RESTRITA, pfx_path, pfx_password)

# POST /nfse — envia o DPS assinado
resultado = api.enviar_dps(xml_assinado)

# GET /dps/{id} — consulta a NFS-e gerada a partir de uma DPS
nota = api.consultar_dps(dps.get_id())

# GET /nfse/{chaveAcesso} — consulta a NFS-e pela chave de acesso
nota = api.consultar_nota(resultado["chaveAcesso"])
```

#### Modelos de Dados
- `DPS`: Declaração de Prestação de Serviço
- `Prestador`: Dados do prestador (emissor)
- `Tomador`: Dados do tomador (cliente)
- `Servico`: Dados do serviço prestado
- `Tributo`: Informações de tributação (ISSQN)
- `Endereco`: Dados de endereço
- `IBSCBS`: Grupo IBS/CBS da Reforma Tributária
- `IBSCBSTributacao`: Situação e classificação tributária do IBS/CBS
- `IBSCBSDestinatario`: Destinatário do serviço para fins de IBS/CBS

### Tratamento de erros

A API retorna os erros em JSON, com um código próprio (`E2404`, `E0001`…).
O SDK converte essas respostas em exceções tipadas, permitindo tratar cada
situação de forma específica:

| Exceção | Quando ocorre |
|---|---|
| `NFSeError` | Classe base de todas as exceções do SDK |
| `NFSeAPIError` | A API respondeu com erro HTTP. Expõe `status_code`, `codigo`, `descricao` e `payload` |
| `NFSeNotFoundError` | Recurso não encontrado (HTTP 404). Subclasse de `NFSeAPIError` |
| `NFSeConnectionError` | Falha de comunicação (rede, timeout, TLS) |

O caso mais comum é consultar uma DPS que ainda não virou NFS-e: a API
responde `404` com o código `E2404`. Isso é uma resposta **esperada** da
consulta, não uma falha:

```python
from src.nfse.exceptions import NFSeNotFoundError, NFSeAPIError

try:
    resultado = api_client.consultar_dps(id_dps)
    print(f"Chave de acesso: {resultado['chaveAcesso']}")
except NFSeNotFoundError:
    print("DPS ainda não gerou NFS-e")
except NFSeAPIError as e:
    print(f"Erro {e.status_code} [{e.codigo}]: {e.descricao}")
```

Todas herdam de `Exception`, então código que já capturava exceções
genéricas continua funcionando.

### Regras de formato dos principais campos

Erros de validação XSD costumam vir do formato dos códigos. Os mais comuns:

| Campo | Modelo | Formato exigido | Exemplo |
|---|---|---|---|
| `cTribNac` | `Servico.codigo_servico` | 6 dígitos | `140101` |
| `cTribMun` | `Servico.codigo_tributacao_municipal` | 3 dígitos | `100` |
| `cNBS` | `Servico.codigo_nbs` | 9 dígitos | `122052000` |
| `serie` | `DPS.serie_rps` | numérico, até 5 dígitos | `00002` |
| `nDPS` | `DPS.numero_rps` | numérico, até 15 dígitos | `1746` |
| `CST` | `IBSCBSTributacao.cst` | 3 dígitos | `000` |
| `cClassTrib` | `IBSCBSTributacao.c_class_trib` | 6 dígitos | `000001` |
| `cIndOp` | `IBSCBS.c_ind_op` | 6 dígitos | `100301` |
| `Id` do `infDPS` | gerado por `DPS.get_id()` | `DPS` + 42 dígitos | — |

> 💡 Ao ler valores de fontes externas (JSON, CSV, ERP), use
> `re.sub(r"\D", "", valor)` para remover a formatação de códigos como
> `08.02.01` → `080201`. Para valores monetários vindos de JSON, use
> `Decimal(str(valor))` em vez de `Decimal(valor)`, evitando o erro de
> precisão binária do `float` (`Decimal(980.1)` resulta em
> `980.09999999999990905052982270717620849609375`).

### Fluxo de Emissão

1. **Construção do XML**: Monta o XML da Declaração de Prestação de Serviço (DPS) com todos os dados necessários
2. **Assinatura Digital**: Assina o XML com certificado digital A1 (.pfx)
3. **Validação XSD**: Valida o XML assinado contra o schema oficial (opcional)
4. **Envio para API**: Envia o XML comprimido (gzip) e codificado (base64) para a API

## 📁 Estrutura do Projeto

```
nfse_nacional/
├── src/
│   └── nfse/              # Módulo principal
│       ├── __init__.py
│       ├── models.py      # Modelos de dados
│       ├── xml_builder.py # Construtor de XML
│       ├── signer.py      # Assinatura digital
│       ├── api_client.py  # Cliente HTTP
│       ├── emissor.py     # Classe principal
│       ├── exceptions.py  # Exceções tipadas da API
│       └── config.py      # Configurações
├── tests/                  # Testes automatizados
│   ├── test_xml_builder.py
│   ├── test_client.py
│   └── conftest.py
├── examples/              # Exemplos de uso
│   ├── exemplo_basico.py          # Emissão completa de NFS-e
│   ├── consulta_nfse.py           # Consulta em lote de NFS-e emitidas
│   └── consulta_status_sefaz.py   # Status da SEFAZ NF-e (requer PyNFe)
├── schemas/               # Arquivos XSD (v1.00 e v1.01)
│   ├── DPS_v1.01.xsd          # Leiaute atual (com IBS/CBS)
│   ├── tiposComplexos_v1.01.xsd
│   ├── tiposSimples_v1.01.xsd
│   ├── NFSe_v1.01.xsd
│   ├── evento_v1.01.xsd
│   ├── DPS_v1.00.xsd          # Leiaute anterior (mantido)
│   └── ...
├── requirements.txt       # Dependências
├── pyproject.toml        # Configuração do projeto
└── README.md
```

### Versões de schema

O diretório `schemas/` contém as duas versões do leiaute:

- **v1.01** — leiaute atual, inclui o grupo `IBSCBS` da Reforma Tributária.
  Use `DPS_v1.01.xsd` com `XMLBuilder(versao="1.01")`.
- **v1.00** — leiaute anterior, mantido para compatibilidade. Não possui
  os elementos de IBS/CBS.

## 🛠️ Desenvolvimento

### Executando os Testes

> Ative o ambiente virtual antes (`source .venv/bin/activate`). Se aparecer
> `No module named pytest`, as dependências ainda não foram instaladas —
> veja a seção [Instalação](#-instalação).

```bash
# Todos os testes
pytest tests/

# Com cobertura de código
pytest tests/ --cov=src --cov-report=html

# Apenas testes de validação XML
pytest tests/test_xml_builder.py -v

# Apenas testes do grupo IBS/CBS
pytest tests/test_xml_builder.py::TestIBSCBS -v

# Com output detalhado
pytest tests/ -v -s
```

### Validação XSD

Os testes validam automaticamente o XML gerado contra o schema XSD oficial:
- ✅ Estrutura do XML
- ✅ Elementos obrigatórios
- ✅ Tipos de dados
- ✅ Valores permitidos
- ✅ Geração correta do ID do DPS
- ✅ Conformidade do grupo `IBSCBS` com o tipo `TCRTCInfoIBSCBS` (v1.01)

#### Problema conhecido no XSD oficial v1.01

O tipo `TSSerieDPS` (elemento `<serie>`) do arquivo `tiposSimples_v1.01.xsd`
declara o padrão `^0{0,4}\d{1,5}$`. Em XSD, `^` e `$` **não** são âncoras —
são tratados como caracteres literais, ao contrário do que ocorre em regex
PCRE/Python. Na prática, isso faz com que **qualquer** valor de `<serie>`
seja rejeitado ao validar o documento completo contra o schema oficial.

Trata-se de um erro no schema publicado, não na geração do XML. Consequências:

- Validar o documento inteiro (`validate=True`) contra `DPS_v1.01.xsd`
  falhará nesse campo, mesmo com uma série válida.
- A validação por tipo específico (como fazemos nos testes do grupo
  `IBSCBS`) funciona normalmente.

Enquanto o schema não for corrigido na origem, use `validate=False` ao
emitir com o leiaute v1.01, ou valide apenas os grupos de interesse.

### Formatação de Código

Usamos `ruff` para linting e formatação (substitui black e flake8):
```bash
# Instalar ruff
pip install ruff

# Formatar código
ruff format src/ tests/ examples/

# Verificar linting
ruff check src/ tests/ examples/

# Formatar e verificar linting
ruff check --fix src/ tests/ examples/
```

## 🤝 Contribuindo

Contribuições são muito bem-vindas! Este é um projeto open source e estamos abertos a melhorias, correções e novas funcionalidades.

**📖 Leia nosso [Guia de Contribuição](CONTRIBUTING.md) para detalhes completos.**

### Formas de Contribuir

- 🐛 **Reportar bugs**: Use o [template de bug report](https://github.com/mupisystems/nfse_nacional/issues/new?template=bug_report.md)
- 💡 **Sugerir funcionalidades**: Use o [template de feature request](https://github.com/mupisystems/nfse_nacional/issues/new?template=feature_request.md)
- 💻 **Contribuir com código**: Veja o [Guia de Contribuição](CONTRIBUTING.md)
- 📝 **Melhorar documentação**: Corrija erros ou adicione exemplos
- 🧪 **Adicionar testes**: Aumente a cobertura de testes
- 🔍 **Revisar código**: Ajude a revisar Pull Requests

### Processo Rápido

1. **Fork** o projeto
2. **Crie uma branch** (`git checkout -b feature/MinhaFeature`)
3. **Commit** suas mudanças (`git commit -m 'Adiciona MinhaFeature'`)
4. **Push** para a branch (`git push origin feature/MinhaFeature`)
5. **Abra um Pull Request**

### Áreas que Precisam de Contribuição

- 🔍 Melhorias na validação XSD
- 📝 Documentação adicional e exemplos
- 🧪 Mais casos de teste
- 🌐 Suporte a outros formatos/cenários
- 🐛 Correção de bugs
- ⚡ Otimizações de performance

## 📝 Mudanças recentes

### Suporte ao leiaute v1.01 (Reforma Tributária)

**Adicionado**

- Grupo `IBSCBS` na DPS, com os modelos `IBSCBS`, `IBSCBSTributacao` e
  `IBSCBSDestinatario`, posicionado como irmão de `<serv>` e `<valores>`
  conforme o tipo `TCRTCInfoIBSCBS`.
- Schemas XSD v1.01 em `schemas/`, mantendo os v1.00 para compatibilidade.
- Testes do grupo `IBSCBS`, incluindo validação contra o XSD oficial.
- Exceções tipadas em `src/nfse/exceptions.py` (`NFSeError`, `NFSeAPIError`,
  `NFSeNotFoundError`, `NFSeConnectionError`), preservando `status_code`,
  `codigo` e `descricao` retornados pela API. Antes, qualquer erro HTTP
  virava uma `Exception` genérica com o JSON bruto na mensagem, obrigando o
  chamador a inspecionar texto para distinguir um "não encontrado" de uma
  falha real.
- Exemplo `examples/consulta_nfse.py`: consulta em lote de NFS-e a partir do
  identificador da DPS, com CLI, exportação JSON e resumo por situação.
- Exemplo `examples/consulta_status_sefaz.py`: consulta o status do serviço
  da SEFAZ (NF-e/NFC-e) via PyNFe, com CLI, saída JSON e códigos de saída
  próprios para uso em monitoramento.
- Dependências declaradas em `pyproject.toml` (`requests`, `requests_pkcs12`,
  `lxml`, `xmlschema`, `signxml`, `python-dateutil`) — antes o campo
  `dependencies` estava vazio e a instalação do pacote não trazia nada.

**Corrigido**

- `DPS.get_id()` gerava a série como texto (`"NF"` por padrão), quebrando o
  padrão `DPS[0-9]{42}` exigido para o atributo `Id` do `infDPS`. Agora a
  série é normalizada para 5 dígitos numéricos.
- `api_client.py` não definia `Pkcs12Adapter` quando a dependência opcional
  `requests-pkcs12` estava ausente, impedindo o uso de mocks nos testes.
- `requirements.txt` estava codificado em UTF-16 (gerado no Windows), o que
  causava falhas de leitura em ambientes Linux/CI. Convertido para UTF-8.
- Fixture de teste usava `cTribNac` com 4 dígitos, violando o padrão de
  6 dígitos do schema.
- `APIClient.consultar_nota()` recebia `numero_nota` e `codigo_verificacao`,
  mas montava a URL apenas com o segundo — que era opcional. Chamar o método
  com um argumento gerava a URL `/nfse/None`, e o primeiro parâmetro era
  ignorado. Conforme o manual oficial, o endpoint é `GET /nfse/{chaveAcesso}`;
  o método agora recebe `chave_acesso`. **Mudança incompatível** para quem
  chamava com dois argumentos.
- Docstrings de `enviar_dps()`, `consultar_dps()` e `consultar_nota()`
  descreviam parâmetros inexistentes (herdados de copiar/colar). Agora
  documentam a assinatura real, o endpoint correspondente e as exceções
  levantadas.
- `NFSeEmissor` ganhou o método `consultar_dps()`, que antes existia apenas
  no `APIClient`.

## 📄 Licença

Este projeto está licenciado sob a Licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.

## 💬 Suporte

- 📖 **Documentação**: Consulte os exemplos em `examples/`
- 🐛 **Bugs**: Reporte em [Issues](https://github.com/mupisystems/nfse_nacional/issues)
- 💡 **Sugestões**: Abra uma [Issue](https://github.com/mupisystems/nfse_nacional/issues) com a tag `enhancement`

## 🙏 Agradecimentos

Agradecemos a todos os contribuidores que ajudam a melhorar este projeto!

---

**Nota**: Este projeto não é oficialmente afiliado à Nota Nacional ou à Receita Federal. É uma implementação open source da comunidade para facilitar a integração com a API oficial.
