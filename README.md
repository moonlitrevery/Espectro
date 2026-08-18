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
```

O último comando imprime quantas estações únicas restam por município
depois da limpeza e da deduplicação.
