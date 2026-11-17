[![DOI](https://zenodo.org/badge/1104954910.svg)](https://doi.org/10.5281/zenodo.17730387)

[![PyPI version](https://img.shields.io/pypi/v/pyontl.svg)](https://pypi.org/project/pyontl/)

# pyontl

Cliente Python para descobrir e consultar os dados do Observatório Nacional de
Transporte e Logística (ONTL), com resultados em DataFrames do pandas.

O catálogo é obtido diretamente da API do ONTL.

## Instalação

Requer Python 3.8 ou superior. Para instalar ou atualizar:

```bash
pip install --upgrade pyontl
```

Para desenvolvimento:

```bash
git clone https://github.com/DevSciHub/pyontl.git
cd pyontl
pip install -e .
```

## Novidades da versão 1.1.0

- Catálogo online e busca por texto e tema, sem depender de planilha local.
- Objetos `Dataset` com descrição, colunas e metadados acessíveis.
- Consultas com filtros gerais, paginação e informações de origem no DataFrame.
- Validação de filtros e erros explícitos para falhas e downloads incompletos.
- Compatibilidade com as funções anteriores; falhas agora lançam exceções.

## Encontrar dados

```python
import pyontl

catalogo = pyontl.catalogo()
print(catalogo[["dataset", "nome", "tema", "consultavel"]].head())

# Ignora acentos e diferenças entre maiúsculas e minúsculas.
resultados = pyontl.buscar("pedagio")
print(resultados[["dataset", "nome", "caminho"]])

# Filtra também pelo tema principal. Todas as palavras precisam ocorrer.
resultados = pyontl.buscar("rodovias", tema="infraestruturas")

# Força a atualização do catálogo.
catalogo = pyontl.catalogo(atualizar=True)
```

A busca considera nome, descrição, identificador e todo o caminho de categorias.
O DataFrame contém `id`, `dataset`, `nome`, `descricao`, `tema`, `caminho`, `url`
e `consultavel`. Algumas entradas do site não informam identificador para API:
elas continuam no catálogo, com `dataset=None` e `consultavel=False`.
`consultavel=True` indica um identificador disponível, sem verificar a saúde do endpoint.

O catálogo usa a [árvore do próprio portal](https://ontl-apim.infrasa.gov.br/api/gerencial/tree).
Fica em cache **somente na memória do processo**, por até uma hora. Em uma nova
sessão, ou após expirar o cache, é necessária conexão. Falhas são explícitas;
a biblioteca não substitui o catálogo por uma planilha ou uma cópia desatualizada.
O endpoint usado pelo frontend pode mudar: uma resposta incompatível gera `ResponseError`.

## Entender um dataset

```python
fonte = pyontl.dataset("antt_pracaspedagio")
print(fonte.descricao)
print(fonte.colunas)  # nome, tipo e filtravel
print(fonte.metadados)  # resposta completa de /meta
```

O objeto carrega os metadados na primeira necessidade e os reutiliza. Crie outro
objeto para atualizar a estrutura. Consultar um identificador conhecido não
depende do catálogo; apenas a propriedade `descricao` consulta esse catálogo.

## Consultar registros

```python
df = fonte.consultar(filtros={"int_ano": 2023, "vhr_uf": "SP"})
print(df.head())
print(df.attrs)  # origem, filtros, ordenação, total e data da consulta em UTC

# Interface equivalente sem criar um objeto explicitamente:
df = pyontl.consultar(
    "antt_pracaspedagio",
    filtros={"int_ano": 2023},
    order_by="int_idapracaspedagio",
    order_dir="asc",
    per_page=100,
)
```

Os filtros usam **os nomes reais das colunas**, validados em `/meta`, e a semântica
de igualdade da API. Valores aceitos: strings, inteiros, floats finitos, booleanos
e datas Python, convertidas para ISO 8601. Listas, valores nulos e parâmetros de
controle da paginação não são aceitos como filtros. Não há conversão automática
de tipos dos dados retornados nem interpretação automática do significado do ano.

`filtros` é opcional, mas o servidor pode exigir pelo menos um filtro para o
dataset escolhido. Não presumimos que todos tenham `int_ano`: alguns usam
`int_anoreferencia`, outros não possuem ano. Consulte `fonte.colunas` primeiro.

`per_page` aceita valores de 1 a 1000. Sem `order_by`, a biblioteca escolhe uma
coluna que comece por `int_ida`, ou a primeira coluna informada. Prefira uma
coluna única para ordenar, quando disponível. A API não oferece aqui uma leitura
transacional: registros podem mudar durante o download, e uma ordenação com
empates pode comprometer a consistência entre páginas.

Todas as páginas são carregadas em memória. Se o total estiver disponível,
a biblioteca confere quantos registros recebeu. Sem total, continua até uma
página vazia. Páginas repetidas, totais alterados e término prematuro geram erro.
Os dados de um download interrompido **não são retornados parcialmente**.
Um resultado legitimamente vazio preserva os nomes das colunas.

## Tratar falhas

```python
try:
    df = pyontl.consultar("antt_pracaspedagio", filtros={"int_ano": 2023})
except ValueError as erro:
    print("Revise os filtros ou as opções:", erro)
except pyontl.ONTLError as erro:
    print("Não foi possível concluir a consulta:", erro)
```

- `APIError`: falhas de conexão ou HTTP; contém `url` e `status_code` quando disponíveis.
- `ResponseError`: JSON, metadados, catálogo ou página incompatíveis com o esperado.
- `IncompleteDownloadError`: paginação inconsistente ou incompleta.

As requisições usam timeout de 60 segundos e até três novas tentativas para falhas
transitórias de conexão e respostas 429, 500, 502, 503 e 504. Os resultados finais
continuam sujeitos à disponibilidade e à qualidade dos dados do ONTL.

## Compatibilidade com as funções anteriores

```python
df = pyontl.getDataset(year=2023)
meta = pyontl.getMetadados("antt_pracaspedagio")
colunas = pyontl.getMetadados_filterableColumns("antt_pracaspedagio")
```

As assinaturas e os padrões dessas funções foram preservados. **Mudança de
comportamento:** falhas agora lançam exceções em vez de imprimir mensagens e
retornar dados vazios ou incompletos. `getDataset()` mantém a ordenação descendente
original; as novas consultas usam ordem ascendente por padrão.

## Desenvolvimento e testes

```bash
python -m unittest discover -s tests -v
```

Os testes não acessam a rede. Cobrem descoberta do catálogo, cache, filtros,
metadados, paginação, falhas HTTP e compatibilidade. Consultas à API real podem
retornar resultados diferentes conforme atualizações na fonte.

Licença MIT.
