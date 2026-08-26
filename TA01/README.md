# Segmentação de imagens por textura

Projeto-base para o primeiro trabalho de Visão Computacional. O programa recebe
uma imagem ou qualquer diretório, encontra as imagens inclusive em subpastas,
converte para cinza, cria recortes de 512 × 512 e categoriza as regiões por
textura.

## Descritor de 24 dimensões

São calculados 8 atributos em cada uma de 3 escalas da pirâmide (1, 1/2 e 1/4):

1. Gabor horizontal (0°)
2. Gabor diagonal (45°)
3. Gabor vertical (90°)
4. Gabor diagonal (135°)
5. filtro circular centro-anel
6. diferença de Gaussianas
7. magnitude do gradiente Sobel
8. desvio-padrão local

Cada resposta vira um atributo pela média em uma janela local. Assim,
`8 filtros × 3 escalas = 24 dimensões`. Os atributos são padronizados e
agrupados por MiniBatch K-means, cuja medida é a distância euclidiana no espaço
de 24 dimensões.

## Estrutura recomendada

```text
trabalho_segmentacao_texturas/
├── codigo.py
├── gerar_imagens_teste.py
├── requirements.txt
├── README.md
├── imagens/
│   ├── foto_01.jpg
│   ├── foto_02.jpg
│   └── ... pelo menos 32 fotografias do grupo
└── resultados/                 # criada automaticamente
```

Uma opção simples de conjunto é **texturas urbanas**: asfalto, calçada, tijolo,
concreto, madeira, grades, paredes e vegetação. Procure incluir mais de uma
textura dentro de cada fotografia para que a segmentação possa ser percebida.

## Instalação

No terminal, dentro da pasta do projeto:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

No Windows, a ativação é `.venv\\Scripts\\activate`.

## Executar nas fotografias

```bash
python codigo.py --entrada ./imagens --saida ./resultados --grupos 5
```

O caminho pode ser relativo ou absoluto e pode apontar para uma única imagem:

```bash
python codigo.py --entrada /caminho/para/minhas_fotos --saida ./resultados
python codigo.py --entrada /caminho/foto.jpg --saida ./resultado_unico
```

Parâmetros mais úteis:

- `--grupos 5`: número de categorias de textura. Experimente 3, 4, 5 e 6.
- `--janela 21`: janela da média local; experimente 15, 21 e 31.
- `--ajuste corte`: preserva a proporção e faz recorte central de 512 × 512.
- `--ajuste redimensionar`: força a imagem inteira para 512 × 512.
- `--amostras-por-imagem 8000`: amostras usadas para treinar o K-means.
- `--semente 42`: torna o experimento repetível.

Use `python codigo.py --help` para ver todas as opções.

## Teste rápido sem fotografias

As imagens sintéticas servem somente para testar a instalação; não substituem
as fotografias exigidas na entrega.

```bash
python gerar_imagens_teste.py --saida ./imagens_teste --quantidade 32
python codigo.py --entrada ./imagens_teste --saida ./resultados_teste --grupos 5
```

## Arquivos de saída

Para cada entrada, o programa salva:

- `*_cinza.png`: recorte realmente analisado;
- `*_grupos.png`: categorização em cores;
- `*_sobreposicao.png`: categorização sobre a fotografia;
- `*_rotulos.png`: identificadores numéricos dos grupos;
- `proporcao_grupos.csv`: percentual ocupado por cada grupo em cada imagem;
- `metadados.json`: parâmetros, nomes dos 24 atributos e centroides do K-means.

As cores representam grupos matemáticos, não nomes semânticos. Por exemplo, o
grupo 2 significa “regiões com respostas de textura parecidas”, e não
necessariamente “asfalto”.

## Experimentos sugeridos para o relatório

Mantenha a mesma semente e compare pelo menos:

```bash
python codigo.py --entrada ./imagens --saida ./resultados_k3 --grupos 3
python codigo.py --entrada ./imagens --saida ./resultados_k5 --grupos 5
python codigo.py --entrada ./imagens --saida ./resultados_j31 --grupos 5 --janela 31
```

Observação: ao copiar, confira se os dois sinais de `--entrada` permaneceram
hífens comuns. Depois, escolha visualmente uma configuração principal e mostre
no artigo exemplos bons, medianos e ruins. Relate também imagens que misturam
texturas ou iluminação, pois isso demonstra análise crítica.

## GitHub

Não envie `.venv` nem a pasta completa de resultados. Envie o código, o
`requirements.txt`, o `README.md`, as 32 imagens utilizadas e alguns resultados
representativos. Depois coloque no artigo um link clicável para o repositório.

```bash
git init
git add codigo.py gerar_imagens_teste.py requirements.txt README.md imagens
git commit -m "Implementa segmentacao por textura"
git branch -M main
git remote add origin URL_DO_SEU_REPOSITORIO
git push -u origin main
```
