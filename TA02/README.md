# Calibração de câmera com OpenCV

Projeto em Python para capturar imagens, calibrar uma câmera, remover a
distorção da lente e projetar pontos conhecidos do espaço 3D em imagens 2D.

## Por que Python?

O OpenCV oferece em Python as mesmas funções principais usadas em C++ neste
experimento. Python reduz o código auxiliar, facilita a exportação de CSV/JSON e
é suficiente para calibração offline. A versão C++ só seria necessária por
exigência da disciplina ou por restrições severas de desempenho em tempo real.

## Estrutura

```text
camera_calibration/
├── config.example.json
├── data/
│   ├── calibracao/
│   └── validacao/
├── relatorio/
├── resultados/
├── src/
│   ├── capture.py
│   ├── calibrate.py
│   ├── undistort.py
│   ├── project_points.py
│   ├── run_pipeline.py
│   └── common.py
├── Makefile
└── requirements.txt
```

## Instalação

No Linux:

```bash
make setup
```

Ou manualmente:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp config.example.json config.json
```

Edite `config.json` antes de capturar as imagens:

- `columns`: quantidade de cantos internos na horizontal;
- `rows`: quantidade de cantos internos na vertical;
- `square_size_mm`: lado real de cada quadrado, em milímetros;
- `width` e `height`: resolução que será mantida em todas as etapas;
- `projection.points`: pontos 3D que serão projetados.

## 1. Captura

Webcam local:

```bash
.venv/bin/python src/capture.py --source 0
```

Pressione `Espaço` ou `C` para salvar e `Q` ou `Esc` para sair. Capture entre
15 e 30 imagens, mudando posição, inclinação, rotação e distância do tabuleiro.

Para câmera IP, prefira uma variável de ambiente para não gravar credenciais no
histórico do projeto:

```bash
export CAMERA_SOURCE='rtsp://usuario:senha@endereco/rota'
.venv/bin/python src/capture.py
unset CAMERA_SOURCE
```

O script também aceita captura automática, útil quando não há teclado próximo:

```bash
.venv/bin/python src/capture.py --auto-count 20 --interval 3
```

Separe algumas fotografias que não participaram da calibração em
`data/validacao/`. Elas devem conter o tabuleiro para o experimento 3D→2D. Uma
imagem adicional do ambiente, com linhas retas, ajuda a demonstrar a remoção da
distorção.

## 2. Calibração

```bash
.venv/bin/python src/calibrate.py --config config.json
```

Principais saídas:

- `resultados/calibracao/calibration.npz`: parâmetros para os demais scripts;
- `resultados/calibracao/calibration.json`: matrizes e métricas legíveis;
- `resultados/calibracao/reprojection_errors.csv`: erro por imagem;
- `resultados/calibracao/cantos_detectados/`: conferência visual.

## 3. Remoção da distorção

```bash
.venv/bin/python src/undistort.py --alpha 1.0
```

`alpha=1` preserva mais campo de visão e pode deixar bordas pretas. `alpha=0`
prioriza pixels válidos e produz mais recorte. O script salva imagens corrigidas
e comparações lado a lado.

## 4. Projeção 3D para 2D

```bash
.venv/bin/python src/project_points.py --config config.json
```

O sistema de coordenadas usa o primeiro canto interno como origem. X segue as
colunas, Y segue as linhas e Z negativo aponta para fora do tabuleiro, em
direção à câmera. O script estima a pose com `solvePnP`, projeta os pontos com
`projectPoints` e gera:

- `resultados/projecao/projected_points.csv`;
- `resultados/projecao/poses.json`;
- imagens com pontos e eixos sobrepostos.

## Execução completa

Depois que as pastas de calibração e validação estiverem preenchidas:

```bash
.venv/bin/python src/run_pipeline.py --config config.json
```

Ou:

```bash
make pipeline
```

## Cuidados com câmera empresarial

- Mantenha lente, foco, zoom e resolução fixos durante todo o experimento.
- Não publique endereços IP, credenciais ou configuração da rede.
- Revise as imagens para retirar pessoas, documentos, telas e áreas internas.
- O `.gitignore` impede por padrão o envio das imagens brutas ao Git.
- Publique apenas evidências autorizadas e necessárias ao relatório.

