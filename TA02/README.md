# Calibração da câmera de um celular com OpenCV

Projeto da disciplina de **Visão Computacional** para calibrar uma câmera de
celular, obter seus parâmetros intrínsecos, corrigir a distorção da lente e
projetar pontos conhecidos do espaço 3D em imagens 2D.

O celular é usado apenas para tirar as fotografias. O processamento é feito no
computador com Python e OpenCV.

## Objetivos

- Detectar os cantos internos de um tabuleiro quadriculado;
- Calcular a matriz intrínseca e os coeficientes de distorção;
- Medir o erro de reprojeção;
- Gerar comparações entre fotos originais e corrigidas;
- Estimar a pose do tabuleiro;
- Projetar pontos 3D em coordenadas 2D;
- Exportar imagens, JSON e CSV para o relatório.

## Estrutura

```text
camera_calibration/
├── config.example.json
├── data/
│   ├── calibracao/       # 15 a 30 fotos do tabuleiro
│   └── validacao/        # fotos usadas nos testes finais
├── relatorio/
│   └── ROTEIRO.md
├── src/
│   ├── common.py
│   ├── calibrate.py
│   ├── undistort.py
│   ├── project_points.py
│   └── run_pipeline.py
├── executar.sh
├── Makefile
├── requirements.txt
└── README.md
```

## 1. Preparar o celular

- Escolha uma única câmera, de preferência a traseira principal `1x`;
- Desative filtros, modo retrato, embelezamento e correções especiais;
- Não use zoom digital nem alterne entre lentes;
- Use a mesma resolução e orientação em todas as fotos;
- Configure o celular para salvar em **JPEG/JPG**, não em HEIC;
- Limpe a lente.

Anote para o relatório o modelo do celular, a câmera/lente escolhida e a
resolução das imagens.

> A calibração pertence à combinação câmera + lente + resolução. Se trocar a
> lente, usar zoom ou mudar a resolução, é necessário calibrar novamente.

## 2. Configurar o tabuleiro

Conte os **cantos internos** e meça o lado de um quadrado em milímetros. Depois:

```bash
chmod +x executar.sh
./executar.sh setup
```

Edite `config.json`:

```json
{
  "board": {
    "columns": 7,
    "rows": 7,
    "square_size_x_mm": 30.0,
    "square_size_y_mm": 30.0
  }
}
```

- `columns`: cantos internos na horizontal;
- `rows`: cantos internos na vertical;
- `square_size_x_mm`: espacamento real entre cantos vizinhos no eixo X;
- `square_size_y_mm`: espacamento real entre cantos vizinhos no eixo Y.

Os valores acima são exemplos e devem ser substituídos pelas medidas reais.

## 3. Tirar e transferir as fotos

### Calibração

Tire entre **15 e 30 fotos** do tabuleiro inteiro, variando posição, distância,
inclinação e rotação. Coloque o tabuleiro também próximo das bordas da imagem.

Evite fotos borradas, repetidas, com reflexos ou com o tabuleiro cortado.
Transfira os arquivos, sem redimensionar ou editar, para:

```text
data/calibracao/
```

### Validação

Tire de 3 a 5 fotos adicionais usando exatamente a mesma lente, resolução e
orientação. Inclua ao menos uma foto do tabuleiro para a projeção 3D → 2D e
uma com o tabuleiro próximo da borda. Transfira para:

```text
data/validacao/
```

Essas fotos não são usadas para calcular a calibração.

## 4. Executar

Verifique o ambiente e as fotos:

```bash
./executar.sh test
./executar.sh check
```

Execute todo o experimento:

```bash
./executar.sh all
```

Ou execute cada etapa:

| Comando | Função |
|---|---|
| `./executar.sh calibrate` | Calcula os parâmetros da câmera |
| `./executar.sh undistort` | Remove a distorção |
| `./executar.sh project` | Projeta os pontos 3D nas imagens |

## Resultados

```text
resultados/
├── calibracao/
│   ├── calibration.npz
│   ├── calibration.json
│   ├── reprojection_errors.csv
│   └── cantos_detectados/
├── distorcao/
│   ├── undistortion.json
│   ├── corrigidas/
│   └── comparacoes/
└── projecao/
    ├── projected_points.csv
    ├── poses.json
    └── imagens/
```

- `calibration.json`: matriz intrínseca, distorção e erros gerais;
- `reprojection_errors.csv`: erro por foto de calibração;
- `comparacoes/`: imagens originais e corrigidas lado a lado;
- `projected_points.csv`: coordenadas 3D e coordenadas 2D calculadas;
- `poses.json`: rotação, translação e erro por imagem;
- `projecao/imagens/`: pontos e eixos desenhados nas fotos.

## Sistema de coordenadas

O primeiro canto interno do tabuleiro representa a origem `(0, 0, 0)`: X
acompanha as colunas, Y acompanha as linhas e Z é perpendicular ao tabuleiro.
As medidas são expressas em milímetros.

## Repositório

Link do GitHub: **adicione aqui o endereço do repositório**.
