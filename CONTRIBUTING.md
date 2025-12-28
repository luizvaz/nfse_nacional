# Guia de Contribuição

Obrigado por considerar contribuir com o projeto Python SDK - NFSe Nacional! Este documento fornece diretrizes e informações sobre como contribuir.

## 📋 Índice

- [Código de Conduta](#código-de-conduta)
- [Como Posso Contribuir?](#como-posso-contribuir)
- [Processo de Desenvolvimento](#processo-de-desenvolvimento)
- [Padrões de Código](#padrões-de-código)
- [Testes](#testes)
- [Documentação](#documentação)
- [Pull Requests](#pull-requests)

## 📜 Código de Conduta

Este projeto segue um código de conduta. Ao participar, você concorda em manter este código. Seja respeitoso, inclusivo e colaborativo.

## 🤔 Como Posso Contribuir?

### Reportando Bugs

Antes de reportar um bug:
1. Verifique se já não foi reportado nas [Issues](https://github.com/mupisystems/nfse_nacional/issues)
2. Teste com a versão mais recente do código

Ao reportar um bug, inclua:
- **Descrição clara** do problema
- **Passos para reproduzir** (se possível, com código mínimo)
- **Comportamento esperado** vs. **comportamento atual**
- **Ambiente**: Python, OS, versões das dependências
- **Logs/erros** relevantes
- **Screenshots** (se aplicável)

### Sugerindo Melhorias

Para sugerir novas funcionalidades:
1. Verifique se já não foi sugerido
2. Abra uma issue descrevendo:
   - O problema que resolve
   - Como funcionaria
   - Exemplos de uso
   - Benefícios

### Contribuindo com Código

1. **Fork** o repositório
2. **Clone** seu fork:
   ```bash
   git clone https://github.com/mupisystems/nfse_nacional.git
   cd nfse_nacional
   ```
3. **Crie uma branch** para sua feature:
   ```bash
   git checkout -b feature/minha-feature
   # ou
   git checkout -b fix/correcao-bug
   ```
4. **Faça suas alterações**
5. **Teste** suas alterações
6. **Commit** com mensagens descritivas
7. **Push** para seu fork
8. **Abra um Pull Request**

## 🔧 Processo de Desenvolvimento

### Configuração do Ambiente

```bash
# Clone o repositório
git clone https://github.com/mupisystems/nfse_nacional.git
cd nfse_nacional

# Crie um ambiente virtual
python -m venv venv

# Ative o ambiente virtual
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Instale as dependências
pip install -r requirements.txt

# Instale dependências de desenvolvimento (inclui ruff)
pip install -e ".[dev]"
```

### Estrutura de Branches

- `main`: Código estável e em produção
- `develop`: Código em desenvolvimento
- `feature/*`: Novas funcionalidades
- `fix/*`: Correções de bugs
- `docs/*`: Melhorias na documentação

## 📝 Padrões de Código

### Python Style Guide

- Siga [PEP 8](https://www.python.org/dev/peps/pep-0008/)
- Use **type hints** sempre que possível
- Mantenha funções pequenas e focadas
- Use nomes descritivos para variáveis e funções
- Adicione docstrings para classes e funções públicas

### Formatação e Linting

Usamos **Ruff** para formatação e linting (substitui Black e Flake8):

```bash
# Formatar código
ruff format src/ tests/ examples/

# Verificar linting
ruff check src/ tests/ examples/

# Formatar e corrigir problemas automaticamente
ruff check --fix src/ tests/ examples/

# Verificar sem modificar
ruff format --check src/ tests/ examples/
ruff check src/ tests/ examples/
```

**Nota**: Ruff é muito mais rápido que Black + Flake8 e oferece as mesmas funcionalidades.

### Exemplo de Código

```python
from typing import Optional, List
from decimal import Decimal

def calcular_total(servicos: List[Servico]) -> Decimal:
    """
    Calcula o valor total dos serviços.
    
    Args:
        servicos: Lista de serviços prestados
        
    Returns:
        Valor total calculado
        
    Raises:
        ValueError: Se a lista estiver vazia
    """
    if not servicos:
        raise ValueError("Lista de serviços não pode estar vazia")
    
    return sum(servico.valor_servico for servico in servicos)
```

## 🧪 Testes

### Executando Testes

```bash
# Todos os testes
pytest tests/

# Com cobertura
pytest tests/ --cov=src --cov-report=html

# Teste específico
pytest tests/test_xml_builder.py::TestXMLBuilder::test_build_dps_xml_basic

# Com output detalhado
pytest tests/ -v -s
```

### Escrevendo Testes

- ✅ Teste casos de sucesso
- ✅ Teste casos de erro
- ✅ Teste edge cases
- ✅ Mantenha testes independentes
- ✅ Use fixtures quando apropriado
- ✅ Adicione testes para novas funcionalidades

### Exemplo de Teste

```python
import pytest
from src.nfse.models import DPS, Prestador

def test_dps_id_generation(dps_exemplo):
    """Testa a geração do ID do DPS"""
    dps_id = dps_exemplo.get_id()
    
    assert dps_id is not None
    assert dps_id.startswith("DPS")
    assert "3550308" in dps_id  # Código do município
```

### Validação XSD

**IMPORTANTE**: Todos os testes que geram XML devem validar contra o XSD:

```python
def test_xml_validation(xml_builder, dps_exemplo):
    """Testa se o XML gerado passa na validação XSD"""
    if xml_builder._schema is None:
        pytest.skip("Schema XSD não foi carregado")
    
    xml = xml_builder.build_dps_xml(dps_exemplo, validate=True)
    assert xml is not None
```

## 📚 Documentação

### Docstrings

Use docstrings no formato Google:

```python
def processar_dps(dps: DPS, validar: bool = True) -> str:
    """
    Processa um DPS e retorna o XML assinado.
    
    Args:
        dps: Objeto DPS com os dados da nota
        validar: Se True, valida o XML contra o XSD
        
    Returns:
        XML do DPS assinado
        
    Raises:
        ValueError: Se o DPS for inválido
        ValidationError: Se a validação XSD falhar
    """
    pass
```

### Atualizando README

Se sua contribuição adiciona novas funcionalidades ou muda o comportamento:
- Atualize o README.md
- Adicione exemplos se necessário
- Atualize a documentação de API

## 🔄 Pull Requests

### Antes de Abrir um PR

- [ ] Código segue os padrões do projeto
- [ ] Todos os testes passam
- [ ] Novos testes foram adicionados (se aplicável)
- [ ] Documentação foi atualizada
- [ ] Código foi formatado com Ruff (`ruff format`)
- [ ] Não há erros de linting (`ruff check`)
- [ ] Commits têm mensagens descritivas

### Template de PR

```markdown
## Descrição
Breve descrição das mudanças

## Tipo de Mudança
- [ ] Bug fix
- [ ] Nova funcionalidade
- [ ] Breaking change
- [ ] Documentação

## Como foi testado?
Descreva os testes realizados

## Checklist
- [ ] Código segue os padrões do projeto
- [ ] Testes passam
- [ ] Documentação atualizada
- [ ] Sem breaking changes (ou documentados)
```

### Processo de Revisão

1. Um mantenedor revisará seu PR
2. Pode haver sugestões de mudanças
3. Faça as alterações solicitadas
4. Após aprovação, o PR será mergeado

## 🎯 Áreas que Precisam de Contribuição

- 🔍 Melhorias na validação XSD
- 📝 Mais exemplos e documentação
- 🧪 Casos de teste adicionais
- 🌐 Suporte a novos cenários
- 🐛 Correção de bugs conhecidos
- ⚡ Otimizações de performance
- 🔒 Melhorias de segurança

## ❓ Dúvidas?

Se tiver dúvidas sobre como contribuir:
- Abra uma issue com a tag `question`
- Consulte a documentação existente
- Veja exemplos de PRs anteriores

## 🙏 Agradecimentos

Obrigado por contribuir! Cada contribuição, por menor que seja, faz diferença. 🎉

