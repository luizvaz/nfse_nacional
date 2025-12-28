# Schemas XSD

Esta pasta contém os arquivos XSD (XML Schema Definition) que definem a especificação do XML do DPS (Declaração de Prestação de Serviço).

## Estrutura Esperada

Coloque aqui todos os arquivos `.xsd` baixados da especificação oficial da NFSe Nacional.

Exemplo:
```
schemas/
├── DPS_v1.00.xsd
├── NFSe_v1.00.xsd
└── outros_arquivos.xsd
```

## Uso

Os arquivos XSD podem ser utilizados para:
- Validação do XML gerado antes do envio
- Documentação da estrutura esperada
- Geração automática de código (opcional)

## Validação

Você pode validar o XML gerado contra o XSD usando a biblioteca `lxml`:

```python
from lxml import etree

# Carregar o schema
schema_doc = etree.parse('schemas/DPS.xsd')
schema = etree.XMLSchema(schema_doc)

# Validar XML
xml_doc = etree.parse('dps.xml')
schema.assertValid(xml_doc)  # Levanta exceção se inválido
```

