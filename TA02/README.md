# Calibração de Câmera com OpenCV

Projeto desenvolvido para a disciplina de **Visão Computacional**, com o
objetivo de calibrar uma câmera, obter seus parâmetros, corrigir a distorção da
lente e projetar pontos conhecidos do espaço 3D em imagens 2D.

O projeto utiliza **Python** e **OpenCV** e permite trabalhar com webcam USB,
câmera IP/RTSP ou arquivo de vídeo.

## Objetivos

- Capturar imagens de um tabuleiro quadriculado em diferentes posições;
- Detectar automaticamente os cantos internos do tabuleiro;
- Calcular a matriz intrínseca da câmera;
- Obter os coeficientes de distorção radial e tangencial;
- Calcular o erro de reprojeção da calibração;
- Remover a distorção presente nas imagens;
- Estimar a posição e a orientação do tabuleiro;
- Projetar pontos 3D conhecidos em coordenadas 2D;
- Gerar imagens, arquivos CSV e JSON para utilização no relatório.

## Estrutura do projeto

```text
camera_calibration/
├── config.example.json
├── data/
│   ├── calibracao/
│   └── validacao/
├── relatorio/
│   └── ROTEIRO.md
├── resultados/
├── src/
│   ├── common.py
│   ├── capture.py
│   ├── calibrate.py
│   ├── undistort.py
│   ├── project_points.py
│   └── run_pipeline.py
├── executar.sh
├── Makefile
├── requirements.txt
└── README.md
```

## Preparação inicial

Dê permissão de execução ao script:

```bash
chmod +x executar.sh
```

Crie o ambiente virtual e instale as dependências:

```bash
./executar.sh setup
```

Esse comando:

1. Cria o ambiente virtual `.venv`;
2. Atualiza o `pip`;
3. Instala NumPy e OpenCV;
4. Cria o arquivo `config.json`, caso ainda não exista;
5. Prepara as pastas de dados e resultados.

## Configuração do tabuleiro

Antes da captura, edite o arquivo `config.json`:

```json
{
  "board": {
    "columns": 9,
    "rows": 6,
    "square_size_mm": 30.0
  },
  "capture": {
    "source": "0",
    "width": 1920,
    "height": 1080
  }
}
```

- `columns`: número de cantos internos na horizontal;
- `rows`: número de cantos internos na vertical;
- `square_size_mm`: lado real de cada quadrado, em milímetros;
- `source`: índice da webcam, caminho de vídeo ou endereço da câmera;
- `width` e `height`: resolução utilizada em todo o experimento.

> O OpenCV utiliza a quantidade de **cantos internos**, não a quantidade de
> quadrados do tabuleiro.

## Teste do ambiente

Para verificar a sintaxe, as dependências e os comandos do projeto:

```bash
./executar.sh test
```

O teste mostra as versões do OpenCV e NumPy e verifica todos os scripts sem
precisar das imagens da câmera.

## Captura das imagens

### Webcam padrão

```bash
./executar.sh capture 0
```

Durante a captura:

- Pressione `Espaço` ou `C` para salvar uma imagem;
- Pressione `Q` ou `Esc` para encerrar.

Capture entre **15 e 30 imagens**, variando:

- Posição do tabuleiro;
- Distância em relação à câmera;
- Inclinação e rotação;
- Presença do tabuleiro no centro e nas bordas da imagem.

Evite imagens borradas, repetidas, com reflexos ou com o tabuleiro cortado.

### Imagens de validação

Depois da captura principal, registre imagens separadas para validar os
resultados:

```bash
./executar.sh validation 0
```

Essas imagens são armazenadas em `data/validacao/` e não participam do cálculo
inicial da calibração. Algumas delas devem mostrar o tabuleiro para o
experimento de projeção 3D para 2D.

### Câmera IP/RTSP

```bash
./executar.sh capture 'rtsp://usuario:senha@endereco/rota'
```

Não salve credenciais, endereços internos ou URLs privadas no GitHub.

## Execução dos experimentos

### Calibração

```bash
./executar.sh calibrate
```

O programa detecta os cantos, calcula a matriz intrínseca, os coeficientes de
distorção e os erros de reprojeção.

### Remoção da distorção

```bash
./executar.sh undistort
```

São produzidas imagens corrigidas e comparações lado a lado entre a imagem
original e a imagem sem distorção.

### Projeção de pontos 3D para 2D

```bash
./executar.sh project
```

O programa utiliza `solvePnP` para estimar a pose do tabuleiro e
`projectPoints` para determinar as coordenadas dos pontos 3D na imagem.

### Pipeline completo

Depois de preencher as pastas `data/calibracao/` e `data/validacao/`, execute:

```bash
./executar.sh all
```

Esse comando testa o ambiente e executa automaticamente:

1. Verificação das imagens;
2. Calibração da câmera;
3. Remoção da distorção;
4. Estimativa da pose;
5. Projeção dos pontos 3D;
6. Exportação dos resultados.

## Comandos disponíveis

| Comando | Função |
|---|---|
| `./executar.sh setup` | Cria o ambiente e instala as dependências |
| `./executar.sh test` | Testa dependências, sintaxe e comandos |
| `./executar.sh capture 0` | Captura imagens de calibração |
| `./executar.sh validation 0` | Captura imagens de validação |
| `./executar.sh calibrate` | Executa somente a calibração |
| `./executar.sh undistort` | Corrige a distorção das imagens |
| `./executar.sh project` | Executa a projeção 3D para 2D |
| `./executar.sh all` | Executa o experimento completo |
| `./executar.sh help` | Exibe a ajuda do script |

## Resultados gerados

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

### Principais informações

- `calibration.json`: matriz intrínseca e coeficientes de distorção;
- `calibration.npz`: parâmetros utilizados pelos demais scripts;
- `reprojection_errors.csv`: erro de cada imagem de calibração;
- `undistortion.json`: parâmetros usados na correção;
- `projected_points.csv`: coordenadas 3D e suas projeções 2D;
- `poses.json`: rotação, translação e erro de cada imagem;
- `comparacoes/`: imagens para demonstrar a correção no relatório;
- `projecao/imagens/`: pontos e eixos projetados sobre as imagens.

## Sistema de coordenadas

O primeiro canto interno do tabuleiro representa a origem `(0, 0, 0)`:

- O eixo X acompanha as colunas do tabuleiro;
- O eixo Y acompanha as linhas;
- O eixo Z é perpendicular ao plano do tabuleiro;
- As medidas utilizadas pelo projeto estão em milímetros.

## Recomendações para a calibração

- Mantenha a mesma resolução em todas as etapas;
- Não altere o foco, o zoom ou a lente depois da calibração;
- Faça o tabuleiro ocupar diferentes regiões da imagem;
- Utilize imagens com boa iluminação e nitidez;
- Confira as imagens em `cantos_detectados/`;
- Analise o erro geral e o erro individual das imagens;
- Repita a calibração caso existam imagens com erro muito elevado.

As imagens brutas das pastas `data/calibracao/` e `data/validacao/` são
ignoradas por padrão pelo `.gitignore`.

