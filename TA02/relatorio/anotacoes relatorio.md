# Anotações para o relátorio. 

## 1. Introdução

- Objetivo da calibração.
- Câmera escolhida e aplicação do experimento.

## 2. Materiais e configuração

- Marca e modelo da câmera.
- Resolução, foco e lente utilizados.
- Quantidade de cantos internos e tamanho real dos quadrados.
- Quantidade total de imagens e condições de captura.
- Usar algum modelo IEE ou SBC para criar o relatorio. 

## 3. Metodologia

- Detecção dos cantos e refinamento subpixel.
- Estimação dos parâmetros com `calibrateCamera`.
- Cálculo do erro de reprojeção.
- Remoção da distorção.
- Estimação de pose com `solvePnP`.
- Projeção dos pontos 3D com `projectPoints`.

## 4. Resultados

- Matriz intrínseca K.
- Coeficientes de distorção.
- RMS retornado pelo OpenCV e RMSE global.
- Tabela de erro por imagem.
- Comparações visuais antes/depois.
- Coordenadas 3D e respectivas coordenadas 2D.
- Imagens com os pontos projetados.
