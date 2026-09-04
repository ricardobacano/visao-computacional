# Segmentação de imagens por textura

Trabalho desenvolvido para a disciplina de Visão Computacional. O objetivo é
identificar e agrupar regiões com texturas semelhantes em fotografias de
paisagens e cenas de ambientes externos.

As imagens são convertidas para tons de cinza e recortadas para `512 × 512` pixels
antes do processamento.

## Visão geral

O programa aplica filtros clássicos de processamento de imagens para descrever
a textura de cada região. Depois, os vetores obtidos são padronizados e
agrupados com MiniBatch K-means, usando distância euclidiana.

O processamento segue estas etapas:

1. localização das imagens na pasta de entrada e em suas subpastas;
2. conversão das fotografias para tons de cinza;
3. recorte central de `512 × 512` pixels;
4. aplicação de oito atributos de textura;
5. processamento em três escalas;
6. cálculo da média local em janelas sobrepostas;
7. formação de um vetor de 24 dimensões para cada pixel;
8. padronização dos atributos;
9. agrupamento por MiniBatch K-means;
10. geração dos mapas coloridos, sobreposições e arquivos de resultados.

## Descritor de textura

São utilizados oito atributos em cada escala:

| Número | Atributo |
|---:|---|
| 1 | Filtro Gabor com orientação de 0° |
| 2 | Filtro Gabor com orientação de 45° |
| 3 | Filtro Gabor com orientação de 90° |
| 4 | Filtro Gabor com orientação de 135° |
| 5 | Filtro circular centro-anel |
| 6 | Diferença de Gaussianas |
| 7 | Magnitude do gradiente Sobel |
| 8 | Desvio-padrão local |

O mesmo conjunto é aplicado em três níveis de uma pirâmide Gaussiana:

- escala original;
- metade da largura e da altura;
- um quarto da largura e da altura.

Assim, cada ponto da imagem é representado por:

```text
8 atributos × 3 escalas = 24 dimensões
```

As respostas dos filtros são resumidas por médias em janelas locais
sobrepostas. No experimento principal foi utilizada uma janela de `21 × 21`
pixels.

## Tecnologias utilizadas

- Python 3;
- OpenCV;
- NumPy;
- scikit-learn;
- Bash para automatizar a instalação e a execução.

## Estrutura do projeto

```text
trabalho_segmentacao_texturas/
├── codigo.py
├── executar.sh
├── executar_experimentos.py
├── requirements.txt
├── README.md
├── imagens/
│   ├── foto_001.png
│   ├── foto_002.png
│   └── ... 50 fotografias
├── resultados/                    # criada pelo modo principal
└── resultados_experimentos/       # criada pelo modo de experimentos
```

As pastas de resultados são criadas automaticamente durante a execução.

## Requisitos

- Python 3.9 ou superior;
- módulo `venv` disponível;
- fotografias com pelo menos 512 pixels de largura e 512 pixels de altura.

Não é necessário instalar as bibliotecas manualmente. O `executar.sh` cria um
ambiente virtual local e instala as dependências na primeira utilização.

## Execução principal

Coloque as fotografias na pasta `imagens/` e abra um terminal na raiz do
projeto. Depois execute:

```bash
chmod +x executar.sh
```

O modo principal utiliza os parâmetros escolhidos após os experimentos:

```text
K = 5 grupos
janela = 21 × 21 pixels
tamanho = 512 × 512 pixels
ajuste = recorte central
semente = 42
```

Os resultados são gravados em `resultados/`.

## Execução com caminhos personalizados

O programa aceita caminhos relativos ou absolutos:

```bash
./executar.sh \
  --entrada /caminho/para/fotografias \
  --saida ./meus_resultados \
  --grupos 5 \
  --janela 21
```

O caminho de entrada pode apontar para uma pasta ou para uma única imagem. As
extensões aceitas são `.jpg`, `.jpeg`, `.png`, `.bmp`, `.tif`, `.tiff` e
`.webp`.

## Ajuste das imagens

O modo padrão é `corte`, que retira uma região central de `512 × 512` sem
deformar a textura:

```bash
./executar.sh --ajuste corte
```

Também estão disponíveis:

- `corte-ajustado`: preserva a proporção, redimensiona e depois recorta;
- `redimensionar`: força a imagem inteira para o tamanho informado.

O redimensionamento direto não é recomendado para os resultados finais, pois
pode esticar ou comprimir os padrões de textura.

## Experimentos

Para testar automaticamente diferentes valores de K e de janela, execute:

```bash
./executar.sh --experimentos
```

São avaliadas cinco configurações:

| Experimento | Grupos (K) | Janela |
|---|---:|---:|
| `k3_j21` | 3 | 21 × 21 |
| `k5_j15` | 5 | 15 × 15 |
| `k5_j21` | 5 | 21 × 21 |
| `k5_j31` | 5 | 31 × 31 |
| `k6_j21` | 6 | 21 × 21 |

Cada experimento recebe uma pasta própria dentro de
`resultados_experimentos/`. O arquivo `resumo_experimentos.csv` registra o
tempo, a quantidade de imagens, a inércia e o número de iterações.

## Configuração escolhida

Após a análise numérica e visual dos resultados das 50 fotografias, foi
selecionada a configuração `K=5` com janela `21 × 21`.

| Configuração | Comportamento observado |
|---|---|
| K=3, janela 21 | Une texturas diferentes e produz regiões muito amplas |
| K=5, janela 15 | Produz maior fragmentação e muitas regiões pequenas |
| **K=5, janela 21** | **Apresenta o melhor equilíbrio entre detalhes e continuidade** |
| K=5, janela 31 | Suaviza as regiões e pode eliminar detalhes importantes |
| K=6, janela 21 | Aumenta a complexidade sem melhoria visual evidente |

A inércia foi utilizada como informação complementar. A decisão principal foi
baseada na coerência visual das regiões e na preservação das transições entre
texturas.

## Arquivos gerados

Para cada fotografia, o programa salva quatro imagens:

- `*_cinza.png`: recorte em tons de cinza realmente analisado;
- `*_grupos.png`: mapa colorido dos grupos encontrados;
- `*_sobreposicao.png`: grupos sobrepostos à imagem em cinza;
- `*_rotulos.png`: identificadores numéricos dos grupos.

Também são produzidos:

- `proporcao_grupos.csv`: porcentagem ocupada por cada grupo em cada imagem;
- `metadados.json`: parâmetros, nomes dos 24 atributos, centroides e dados do
  treinamento.

Na execução principal com 50 fotografias foram gerados 200 arquivos PNG.

## Significado das cores

As cores representam grupos matemáticos de textura e não categorias semânticas
predefinidas. Portanto, um grupo não significa necessariamente “vegetação”,
“céu” ou “asfalto”. Ele reúne regiões que apresentaram vetores próximos no
espaço de 24 dimensões.

Os números e as cores dos grupos podem mudar quando o conjunto de fotografias,
o valor de K ou o tamanho da janela são alterados.

## Limpeza

Para remover somente as pastas de resultados:

```bash
./executar.sh --limpar-resultados
```

Para remover somente o ambiente virtual:

```bash
./executar.sh --limpar-ambiente
```

Para remover resultados e ambiente virtual:

```bash
./executar.sh --limpar-tudo
```
