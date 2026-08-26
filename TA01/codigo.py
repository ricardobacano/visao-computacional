#!/usr/bin/env python3

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

import cv2
import numpy as np
from sklearn.cluster import MiniBatchKMeans
from sklearn.preprocessing import StandardScaler


EXTENSOES = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}
ORIENTACOES = (0, 45, 90, 135)
NOMES_BASE = (
    "gabor_0",
    "gabor_45",
    "gabor_90",
    "gabor_135",
    "circular_anel",
    "diferenca_gaussianas",
    "gradiente_sobel",
    "desvio_padrao_local",
)


def argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Segmenta uma pasta de imagens usando 24 atributos de textura."
    )
    parser.add_argument(
        "--entrada",
        type=Path,
        required=True,
        help="Imagem ou diretório contendo imagens (subpastas também são lidas).",
    )
    parser.add_argument(
        "--saida", type=Path, default=Path("resultados"), help="Diretório de saída."
    )
    parser.add_argument(
        "--grupos", type=int, default=5, help="Quantidade de grupos de textura (K)."
    )
    parser.add_argument(
        "--janela",
        type=int,
        default=21,
        help="Lado ímpar da janela usada para calcular as médias locais.",
    )
    parser.add_argument(
        "--amostras-por-imagem",
        type=int,
        default=8000,
        help="Pixels sorteados por imagem para treinar o agrupamento.",
    )
    parser.add_argument(
        "--tamanho",
        type=int,
        default=512,
        help="Tamanho do recorte quadrado usado no processamento.",
    )
    parser.add_argument(
        "--ajuste",
        choices=("corte", "redimensionar"),
        default="corte",
        help="'corte' preserva proporções; 'redimensionar' força um quadrado.",
    )
    parser.add_argument("--semente", type=int, default=42)
    return parser.parse_args()


def listar_imagens(entrada: Path) -> list[Path]:
    if entrada.is_file():
        return [entrada] if entrada.suffix.lower() in EXTENSOES else []
    if not entrada.is_dir():
        return []
    return sorted(
        caminho
        for caminho in entrada.rglob("*")
        if caminho.is_file() and caminho.suffix.lower() in EXTENSOES
    )


def ler_cinza_quadrada(caminho: Path, tamanho: int, ajuste: str) -> np.ndarray:
    dados = np.fromfile(str(caminho), dtype=np.uint8)
    imagem = cv2.imdecode(dados, cv2.IMREAD_GRAYSCALE)
    if imagem is None:
        raise ValueError("OpenCV não conseguiu decodificar o arquivo")

    if ajuste == "redimensionar":
        return cv2.resize(imagem, (tamanho, tamanho), interpolation=cv2.INTER_AREA)

    altura, largura = imagem.shape
    escala = max(tamanho / largura, tamanho / altura)
    nova_largura = max(tamanho, int(round(largura * escala)))
    nova_altura = max(tamanho, int(round(altura * escala)))
    interpolacao = cv2.INTER_CUBIC if escala > 1 else cv2.INTER_AREA
    imagem = cv2.resize(imagem, (nova_largura, nova_altura), interpolation=interpolacao)
    x0 = (nova_largura - tamanho) // 2
    y0 = (nova_altura - tamanho) // 2
    return imagem[y0 : y0 + tamanho, x0 : x0 + tamanho]


def kernel_circular(tamanho: int = 15) -> np.ndarray:
    """Filtro circular tipo centro-periferia, com soma aproximadamente zero."""
    eixo = np.arange(tamanho, dtype=np.float32) - (tamanho - 1) / 2
    xx, yy = np.meshgrid(eixo, eixo)
    raio = np.sqrt(xx * xx + yy * yy)
    centro = raio <= tamanho * 0.18
    anel = (raio > tamanho * 0.28) & (raio <= tamanho * 0.46)
    kernel = np.zeros((tamanho, tamanho), dtype=np.float32)
    kernel[centro] = -1.0 / max(1, int(centro.sum()))
    kernel[anel] = 1.0 / max(1, int(anel.sum()))
    return kernel


def respostas_textura(imagem: np.ndarray) -> list[np.ndarray]:
    """Retorna oito mapas de resposta na escala recebida."""
    img = imagem.astype(np.float32) / 255.0
    respostas: list[np.ndarray] = []

    for graus in ORIENTACOES:
        kernel = cv2.getGaborKernel(
            ksize=(15, 15),
            sigma=3.0,
            theta=math.radians(graus),
            lambd=7.0,
            gamma=0.55,
            psi=0,
            ktype=cv2.CV_32F,
        )
        kernel /= np.sum(np.abs(kernel)) + 1e-8
        resposta = cv2.filter2D(img, cv2.CV_32F, kernel, borderType=cv2.BORDER_REFLECT)
        respostas.append(np.abs(resposta))

    circular = cv2.filter2D(
        img, cv2.CV_32F, kernel_circular(), borderType=cv2.BORDER_REFLECT
    )
    respostas.append(np.abs(circular))

    suave_1 = cv2.GaussianBlur(img, (0, 0), sigmaX=1.0)
    suave_2 = cv2.GaussianBlur(img, (0, 0), sigmaX=2.4)
    respostas.append(np.abs(suave_1 - suave_2))

    gx = cv2.Sobel(img, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(img, cv2.CV_32F, 0, 1, ksize=3)
    respostas.append(cv2.magnitude(gx, gy))

    media = cv2.boxFilter(img, cv2.CV_32F, (9, 9), normalize=True)
    media_quadrados = cv2.boxFilter(img * img, cv2.CV_32F, (9, 9), normalize=True)
    variancia = np.maximum(media_quadrados - media * media, 0)
    respostas.append(np.sqrt(variancia))

    assert len(respostas) == 8
    return respostas


def extrair_descritor(imagem: np.ndarray, janela: int) -> np.ndarray:
    """Gera H x W x 24 atributos: médias locais de 8 filtros em 3 escalas."""
    altura, largura = imagem.shape
    atual = imagem
    atributos: list[np.ndarray] = []

    for _escala in range(3):
        for resposta in respostas_textura(atual):
            media_local = cv2.boxFilter(
                resposta,
                cv2.CV_32F,
                (janela, janela),
                normalize=True,
                borderType=cv2.BORDER_REFLECT,
            )
            if media_local.shape != (altura, largura):
                media_local = cv2.resize(
                    media_local, (largura, altura), interpolation=cv2.INTER_LINEAR
                )
            atributos.append(media_local)
        atual = cv2.pyrDown(atual)

    descritor = np.stack(atributos, axis=-1).astype(np.float32)
    if descritor.shape[2] != 24:
        raise RuntimeError(f"Descritor deveria ter 24 dimensões: {descritor.shape}")
    return descritor


def paleta_grupos(quantidade: int) -> np.ndarray:
    hsv = np.zeros((quantidade, 1, 3), dtype=np.uint8)
    hsv[:, 0, 0] = np.linspace(0, 179, quantidade, endpoint=False).astype(np.uint8)
    hsv[:, 0, 1] = 210
    hsv[:, 0, 2] = 240
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)[:, 0, :]


def nome_saida(caminho: Path, indice: int) -> str:
    seguro = "".join(c if c.isalnum() or c in "-_" else "_" for c in caminho.stem)
    return f"{indice:03d}_{seguro}"


def salvar_png(caminho: Path, imagem: np.ndarray) -> None:
    ok, buffer = cv2.imencode(".png", imagem)
    if not ok:
        raise OSError(f"Falha ao codificar {caminho}")
    caminho.write_bytes(buffer.tobytes())


def processar(args: argparse.Namespace) -> None:
    if args.grupos < 2:
        raise ValueError("--grupos deve ser pelo menos 2")
    if args.janela < 3 or args.janela % 2 == 0:
        raise ValueError("--janela deve ser ímpar e pelo menos 3")
    if args.tamanho < 64:
        raise ValueError("--tamanho deve ser pelo menos 64")

    caminhos = listar_imagens(args.entrada)
    if not caminhos:
        raise FileNotFoundError(f"Nenhuma imagem encontrada em: {args.entrada}")

    args.saida.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(args.semente)
    amostras: list[np.ndarray] = []
    validas: list[Path] = []

    print(f"Encontradas {len(caminhos)} imagens. Extraindo amostras para o K-means...")
    for indice, caminho in enumerate(caminhos, start=1):
        try:
            imagem = ler_cinza_quadrada(caminho, args.tamanho, args.ajuste)
            descritor = extrair_descritor(imagem, args.janela).reshape(-1, 24)
            quantidade = min(args.amostras_por_imagem, descritor.shape[0])
            posicoes = rng.choice(descritor.shape[0], quantidade, replace=False)
            amostras.append(descritor[posicoes])
            validas.append(caminho)
            print(f"  [{indice}/{len(caminhos)}] {caminho.name}")
        except Exception as erro:
            print(f"  AVISO: ignorando {caminho}: {erro}", file=sys.stderr)

    if not validas:
        raise RuntimeError("Nenhuma imagem pôde ser processada")
    if len(validas) < 32:
        print(
            f"AVISO: foram processadas {len(validas)} imagens; o enunciado pede ao menos 32.",
            file=sys.stderr,
        )

    treino = np.concatenate(amostras, axis=0)
    scaler = StandardScaler()
    treino_normalizado = scaler.fit_transform(treino)
    kmeans = MiniBatchKMeans(
        n_clusters=args.grupos,
        random_state=args.semente,
        batch_size=4096,
        n_init=10,
        max_iter=200,
    )
    kmeans.fit(treino_normalizado)
    del treino, treino_normalizado, amostras

    paleta = paleta_grupos(args.grupos)
    linhas_csv: list[list[object]] = []
    print("Gerando imagens categorizadas...")

    for indice, caminho in enumerate(validas, start=1):
        imagem = ler_cinza_quadrada(caminho, args.tamanho, args.ajuste)
        descritor = extrair_descritor(imagem, args.janela)
        plano = descritor.reshape(-1, 24)
        rotulos = kmeans.predict(scaler.transform(plano)).reshape(imagem.shape)
        colorida = paleta[rotulos]
        base_bgr = cv2.cvtColor(imagem, cv2.COLOR_GRAY2BGR)
        sobreposta = cv2.addWeighted(base_bgr, 0.42, colorida, 0.58, 0)

        prefixo = nome_saida(caminho, indice)
        salvar_png(args.saida / f"{prefixo}_cinza.png", imagem)
        salvar_png(args.saida / f"{prefixo}_grupos.png", colorida)
        salvar_png(args.saida / f"{prefixo}_sobreposicao.png", sobreposta)
        salvar_png(args.saida / f"{prefixo}_rotulos.png", rotulos.astype(np.uint8))

        contagens = np.bincount(rotulos.ravel(), minlength=args.grupos)
        porcentagens = 100.0 * contagens / contagens.sum()
        linhas_csv.append(
            [str(caminho), *[round(float(valor), 4) for valor in porcentagens]]
        )
        print(f"  [{indice}/{len(validas)}] {caminho.name}")

    with (args.saida / "proporcao_grupos.csv").open("w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.writer(arquivo)
        escritor.writerow(["imagem", *[f"grupo_{i}_percentual" for i in range(args.grupos)]])
        escritor.writerows(linhas_csv)

    nomes_atributos = [
        f"escala_{escala}_{nome}"
        for escala in (1, 2, 3)
        for nome in NOMES_BASE
    ]
    metadados = {
        "entrada": str(args.entrada),
        "quantidade_imagens": len(validas),
        "tamanho": [args.tamanho, args.tamanho],
        "janela": args.janela,
        "grupos": args.grupos,
        "dimensoes_descritor": 24,
        "atributos": nomes_atributos,
        "orientacoes_gabor_graus": list(ORIENTACOES),
        "escalas_piramide": [1, 0.5, 0.25],
        "centroides_padronizados": kmeans.cluster_centers_.tolist(),
        "media_padronizacao": scaler.mean_.tolist(),
        "escala_padronizacao": scaler.scale_.tolist(),
        "semente": args.semente,
    }
    (args.saida / "metadados.json").write_text(
        json.dumps(metadados, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Concluído. Resultados salvos em: {args.saida.resolve()}")


def main() -> int:
    try:
        processar(argumentos())
        return 0
    except Exception as erro:
        print(f"ERRO: {erro}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
