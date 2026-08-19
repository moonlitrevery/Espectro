# Espectro

Alocação de canais de frequência entre ERBs de Bauru-SP via coloração de
grafos, com dados abertos da ANATEL: guloso, Welsh-Powell e DSATUR
implementados do zero, comparados em instâncias reais de diferentes escalas.

## Modelagem do grafo

- **Vértices:** cada ERB licenciada. Uma estação da ANATEL (`NumEstacao`)
  é um ponto com latitude/longitude reais.
- **Arestas:** duas ERBs são ligadas se a distância geográfica entre elas
  (fórmula de **haversine**, em km) for menor que um raio de interferência
  `D` (parâmetro configurável). Não usamos distância euclidiana sobre graus
  de latitude/longitude.
- O grafo é **não-direcionado** e **não ponderado**.
- **Cores = canais de frequência.** Objetivo: colorir com o menor número
  de cores possível de modo que vértices adjacentes nunca recebam a mesma
  cor.

### Hipótese / limitação

O raio `D` é uma **simplificação** da interferência real. Interferência
depende também de potência, relevo e direção da antena — nada disso entra
neste modelo. O trabalho trata o problema como coloração clássica sobre um
grafo de disco unitário geográfico.

### Por que deduplicar antes do grafo

O CSV da ANATEL tem **uma linha por emissão licenciada** (frequência e
azimute). A mesma estação se repete. Se isso não for resolvido antes de
montar o grafo, surgem vários vértices na mesma coordenada.

## Fonte de dados

Dataset *Estações Licenciadas a Operar no Serviço Móvel Pessoal* (ANATEL),
via Portal Brasileiro de Dados Abertos / Spectrum-E.

Arquivo local (não versionado no git, ~2 milhões de linhas):

```text
data/ERBs - Anatel.csv
```

Filtro geográfico deste trabalho: município de **Bauru** (instância
principal) e vizinhos **Agudos**, **Pederneiras** e **Piratininga**.

Contagem após limpeza e deduplicação pelo `NumEstacao` (CSV atual):

| Município   | Linhas no CSV | Estações únicas |
|-------------|---------------|-----------------|
| Bauru       | 8.641         | 1.295           |
| Agudos      | 1.423         | 279             |
| Pederneiras | 1.152         | 373             |
| Piratininga | 2.759         | 216             |
| **Total**   | **13.975**    | **2.163**       |

## Instâncias de teste

| id          | Recorte                            | D      | n     | arestas | densidade |
|-------------|------------------------------------|--------|-------|---------|-----------|
| `small`     | Agudos + Pederneiras + Piratininga | 1 km   | 868   | 44.759  | 11,9%     |
| `medium`    | só Bauru                           | 1 km   | 1.295 | 55.958  | 6,7%      |
| `large`     | Bauru + vizinhos                   | 1 km   | 2.163 | 100.720 | 4,3%      |
| `large_d05` | mesmos vértices da grande          | 0,5 km | 2.163 | 75.048  | 3,2%      |
| `large_d20` | mesmos vértices da grande          | 2 km   | 2.163 | 173.854 | 7,4%      |

A pequena, a média e a grande usam o **mesmo D** para isolar o efeito do
tamanho. As duas últimas isolam o efeito do raio (vértices iguais, D
diferente).

```bash
uv run python -m src.instances
```

Imprime n, m, densidade e isolados de cada instância.

```bash
uv run python -m src.analysis
```

Roda os três algoritmos em cada instância, valida a coloração, estima o
piso por clique e imprime cores, gap e tempo. Este é o número que entra
na tabela de resultados do relatório.

Colunas usadas do CSV (separador `|`): `NumEstacao`,
`Municipio.NomeMunicipio`, `Latitude`, `Longitude`, `NomeEntidade`,
`EnderecoEstacao`, `Tecnologia`, `FreqTxMHz`, `SiglaUf`.

## Como executar

Python 3.11+ e [uv](https://docs.astral.sh/uv/). Não usamos `pip` nem
`requirements.txt`.

```bash
uv sync
uv run pytest
uv run python -m src.data_prep
uv run python -m src.graph_builder
```

`data_prep` imprime as estações únicas por município. `graph_builder`
monta o grafo para alguns valores de `D` (0,5 / 1 / 2 / 5 km) e mostra
número de arestas, densidade e graus — para o relatório e para escolher
o raio das instâncias.

O `D` padrão do código é **1 km** (alcance típico de macrocélula urbana).
É um parâmetro, não um resultado: as instâncias vão variar esse valor.

```bash
uv run python -m src.coloring.greedy_natural
```

Roda o guloso natural no grafo com `D = 1 km` e imprime quantas cores
ele usou, ao lado do teto teórico Δ+1.

```bash
uv run python -m src.coloring.welsh_powell
```

Compara Welsh–Powell com o guloso natural no mesmo grafo.

```bash
uv run python -m src.coloring.dsatur
```

Compara os três algoritmos (natural, Welsh–Powell, DSATUR) em D = 1 km.

```bash
uv run python -m src.coloring.validator
```

Roda os três algoritmos e valida cada coloração de forma independente
(nenhum par adjacente com a mesma cor).

```bash
uv run python -m src.lower_bound
```

Estima um clique grande (piso para χ) e compara com as três colorações.
Se o número de cores coincidir com o piso, a coloração é ótima naquela
instância.
