# Testes Automatizados

Este diretório contém testes automatizados para validar o XML gerado contra o schema XSD oficial.

## Estrutura

- `test_xml_builder.py` - Testes de validação do XML gerado
- `test_client.py` - Testes do cliente da API
- `conftest.py` - Configuração global do pytest
- `run_tests.py` - Script auxiliar para executar os testes

## Executando os Testes

### Opção 1: Usando pytest diretamente

```bash
# Todos os testes
pytest tests/

# Apenas testes de XML
pytest tests/test_xml_builder.py

# Com output detalhado
pytest tests/ -v

# Com cobertura de código
pytest tests/ --cov=src --cov-report=html
```

### Opção 2: Usando o script auxiliar

```bash
python tests/run_tests.py
```

### Opção 3: Executar um teste específico

```bash
pytest tests/test_xml_builder.py::TestXMLBuilder::test_xml_validation_against_xsd -v
```

## O que os Testes Validam

✅ **Estrutura do XML**: Verifica se todos os elementos obrigatórios estão presentes  
✅ **Validação XSD**: Valida o XML gerado contra o schema oficial  
✅ **Geração de ID**: Testa a lógica de construção do ID do DPS  
✅ **Cenários diversos**: Testa com/sem tomador, CPF/CNPJ, etc  
✅ **Estrutura de tributação**: Valida a estrutura do `tribMun` e `totTrib`

## Requisitos

- Arquivo XSD em `schemas/DPS_v1.00.xsd`
- Dependências instaladas: `pip install -r requirements.txt`

## Integração Contínua

Os testes podem ser integrados em pipelines CI/CD para garantir que o código sempre gera XMLs válidos.

