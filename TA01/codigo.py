#!/usr/bin/env python3

"""Segmentação de imagens usando características de textura."""

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


# Formatos de imagem aceitos pelo programa.
EXTENSOES = [".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"]
ORIENTACOES = [0, 45, 90, 135]

NOMES_DOS_FILTROS = [
    "gabor_0",
    "gabor_45",
    "gabor_90",
    "gabor_135",
    "circular_anel",
    "diferenca_gaussianas",
    "gradiente_sobel",
    "desvio_padrao_local",
]


def ler_argumentos():
    parser = argparse.ArgumentParser(
        description="Segmenta imagens usando 24 características de textura."
    )

    parser.add_argument(
        "--entrada",
        type=Path,
        required=True,
        help="Imagem ou pasta contendo as imagens.",
    )
    parser.add_argument(
        "--saida",
        type=Path,
        default=Path("resultados"),
        help="Pasta onde os resultados serão salvos.",
    )
    parser.add_argument(
        "--grupos",
        type=int,
        default=5,
        help="Quantidade de grupos do K-means.",
    )
    parser.add_argument(
        "--janela",
        type=int,
        default=21,
        help="Tamanho da janela usada para calcular as médias locais.",
    )
    parser.add_argument(
        "--amostras-por-imagem",
        type=int,
        default=8000,
        help="Quantidade de pixels usados no treinamento por imagem.",
    )
    parser.add_argument(
        "--tamanho",
        type=int,
        default=512,
        help="Tamanho do recorte quadrado.",
    )
    parser.add_argument(
        "--ajuste",
        choices=["corte", "corte-ajustado", "redimensionar"],
        default="corte",
        help="Forma usada para deixar a imagem quadrada.",
    )
    parser.add_argument(
        "--semente",
        type=int,
        default=42,
        help="Semente usada para repetir o mesmo experimento.",
    )

    return parser.parse_args()


def buscar_imagens(entrada):
    imagens = []

    if entrada.is_file():
        if entrada.suffix.lower() in EXTENSOES:
            imagens.append(entrada)
        return imagens

    if not entrada.is_dir():
        return imagens

    # rglob também procura imagens dentro das subpastas.
    for caminho in entrada.rglob("*"):
        if caminho.is_file() and caminho.suffix.lower() in EXTENSOES:
            imagens.append(caminho)

    imagens.sort()
    return imagens


def carregar_imagem(caminho, tamanho, ajuste):
    dados = np.frombuffer(caminho.read_bytes(), dtype=np.uint8)
    imagem = cv2.imdecode(dados, cv2.IMREAD_GRAYSCALE)

    if imagem is None:
        raise ValueError("o OpenCV não conseguiu abrir a imagem")

    if ajuste == "redimensionar":
        return cv2.resize(
            imagem,
            (tamanho, tamanho),
            interpolation=cv2.INTER_AREA,
        )

    altura, largura = imagem.shape

    if ajuste == "corte":
        if largura < tamanho or altura < tamanho:
            raise ValueError(
                f"a imagem possui {largura}x{altura}, mas o corte exige "
                f"pelo menos {tamanho}x{tamanho} pixels"
            )

        inicio_x = (largura - tamanho) // 2
        inicio_y = (altura - tamanho) // 2

        return imagem[
            inicio_y : inicio_y + tamanho,
            inicio_x : inicio_x + tamanho,
        ]

    # O corte ajustado redimensiona sem deformar e depois recorta o centro.
    escala = max(tamanho / largura, tamanho / altura)
    nova_largura = max(tamanho, int(round(largura * escala)))
    nova_altura = max(tamanho, int(round(altura * escala)))

    if escala > 1:
        interpolacao = cv2.INTER_CUBIC
    else:
        interpolacao = cv2.INTER_AREA

    imagem = cv2.resize(
        imagem,
        (nova_largura, nova_altura),
        interpolation=interpolacao,
    )

    inicio_x = (nova_largura - tamanho) // 2
    inicio_y = (nova_altura - tamanho) // 2

    return imagem[
        inicio_y : inicio_y + tamanho,
        inicio_x : inicio_x + tamanho,
    ]


def criar_filtro_circular(tamanho=15):
    eixo = np.arange(tamanho, dtype=np.float32)
    eixo = eixo - (tamanho - 1) / 2

    x, y = np.meshgrid(eixo, eixo)
    raio = np.sqrt(x * x + y * y)

    centro = raio <= tamanho * 0.18
    anel = (raio > tamanho * 0.28) & (raio <= tamanho * 0.46)

    filtro = np.zeros((tamanho, tamanho), dtype=np.float32)
    filtro[centro] = -1.0 / max(1, int(centro.sum()))
    filtro[anel] = 1.0 / max(1, int(anel.sum()))

    return filtro


def aplicar_filtros(imagem):
    imagem_float = imagem.astype(np.float32) / 255.0
    respostas = []

    # Quatro filtros Gabor, um para cada orientação pedida no trabalho.
    for angulo in ORIENTACOES:
        filtro_gabor = cv2.getGaborKernel(
            ksize=(15, 15),
            sigma=3.0,
            theta=math.radians(angulo),
            lambd=7.0,
            gamma=0.55,
            psi=0,
            ktype=cv2.CV_32F,
        )

        soma = np.sum(np.abs(filtro_gabor)) + 1e-8
        filtro_gabor = filtro_gabor / soma

        resposta = cv2.filter2D(
            imagem_float,
            cv2.CV_32F,
            filtro_gabor,
            borderType=cv2.BORDER_REFLECT,
        )
        respostas.append(np.abs(resposta))

    # Quinta característica: filtro circular centro-anel.
    resposta_circular = cv2.filter2D(
        imagem_float,
        cv2.CV_32F,
        criar_filtro_circular(),
        borderType=cv2.BORDER_REFLECT,
    )
    respostas.append(np.abs(resposta_circular))

    # Sexta característica: diferença entre duas suavizações gaussianas.
    gaussiana_1 = cv2.GaussianBlur(imagem_float, (0, 0), sigmaX=1.0)
    gaussiana_2 = cv2.GaussianBlur(imagem_float, (0, 0), sigmaX=2.4)
    respostas.append(np.abs(gaussiana_1 - gaussiana_2))

    # Sétima característica: intensidade do gradiente Sobel.
    gradiente_x = cv2.Sobel(imagem_float, cv2.CV_32F, 1, 0, ksize=3)
    gradiente_y = cv2.Sobel(imagem_float, cv2.CV_32F, 0, 1, ksize=3)
    respostas.append(cv2.magnitude(gradiente_x, gradiente_y))

    # O desvio-padrão local é a oitava característica.
    media = cv2.boxFilter(
        imagem_float,
        cv2.CV_32F,
        (9, 9),
        normalize=True,
    )
    media_quadrados = cv2.boxFilter(
        imagem_float * imagem_float,
        cv2.CV_32F,
        (9, 9),
        normalize=True,
    )
    variancia = media_quadrados - media * media
    variancia = np.maximum(variancia, 0)
    respostas.append(np.sqrt(variancia))

    if len(respostas) != 8:
        raise RuntimeError("deveriam existir 8 respostas de textura")

    return respostas


def criar_descritor(imagem, tamanho_janela):
    altura, largura = imagem.shape
    imagem_da_escala = imagem
    caracteristicas = []

    # O mesmo conjunto de oito características é usado em três escalas.
    for numero_escala in range(3):
        respostas = aplicar_filtros(imagem_da_escala)

        for resposta in respostas:
            media_local = cv2.boxFilter(
                resposta,
                cv2.CV_32F,
                (tamanho_janela, tamanho_janela),
                normalize=True,
                borderType=cv2.BORDER_REFLECT,
            )

            if media_local.shape != (altura, largura):
                media_local = cv2.resize(
                    media_local,
                    (largura, altura),
                    interpolation=cv2.INTER_LINEAR,
                )

            caracteristicas.append(media_local)

        if numero_escala < 2:
            imagem_da_escala = cv2.pyrDown(imagem_da_escala)

    descritor = np.stack(caracteristicas, axis=-1)
    descritor = descritor.astype(np.float32)

    if descritor.shape[2] != 24:
        raise RuntimeError(
            f"o descritor deveria possuir 24 dimensões: {descritor.shape}"
        )

    return descritor


def criar_paleta(quantidade_grupos):
    cores_hsv = np.zeros((quantidade_grupos, 1, 3), dtype=np.uint8)
    tons = np.linspace(0, 179, quantidade_grupos, endpoint=False)

    cores_hsv[:, 0, 0] = tons.astype(np.uint8)
    cores_hsv[:, 0, 1] = 210
    cores_hsv[:, 0, 2] = 240

    cores_bgr = cv2.cvtColor(cores_hsv, cv2.COLOR_HSV2BGR)
    return cores_bgr[:, 0, :]


def criar_nome_saida(caminho, numero):
    nome = ""

    for caractere in caminho.stem:
        if caractere.isalnum() or caractere in "-_":
            nome += caractere
        else:
            nome += "_"

    return f"{numero:03d}_{nome}"


def salvar_imagem(caminho, imagem):
    sucesso, dados = cv2.imencode(".png", imagem)

    if not sucesso:
        raise OSError(f"não foi possível salvar {caminho}")

    caminho.write_bytes(dados.tobytes())


def validar_configuracao(args):
    if args.grupos < 2:
        raise ValueError("--grupos deve ser pelo menos 2")

    if args.janela < 3 or args.janela % 2 == 0:
        raise ValueError("--janela deve ser ímpar e pelo menos 3")

    if args.tamanho < 64:
        raise ValueError("--tamanho deve ser pelo menos 64")

    if args.amostras_por_imagem < 1:
        raise ValueError("--amostras-por-imagem deve ser pelo menos 1")


def validar_pastas(entrada, saida):
    if not entrada.is_dir():
        return

    entrada_completa = entrada.resolve()
    saida_completa = saida.resolve()

    if saida_completa == entrada_completa:
        raise ValueError("a pasta de saída não pode ser igual à pasta de entrada")

    if entrada_completa in saida_completa.parents:
        raise ValueError("a pasta de saída não pode ficar dentro da pasta de entrada")


def coletar_amostras(args, caminhos, gerador_aleatorio):
    amostras = []
    imagens_validas = []
    total = len(caminhos)

    print(f"Encontradas {total} imagens.")
    print("Extraindo amostras para treinar o K-means...")

    for numero, caminho in enumerate(caminhos, start=1):
        try:
            imagem = carregar_imagem(caminho, args.tamanho, args.ajuste)
            descritor = criar_descritor(imagem, args.janela)
            descritor = descritor.reshape(-1, 24)

            quantidade = min(args.amostras_por_imagem, descritor.shape[0])
            posicoes = gerador_aleatorio.choice(
                descritor.shape[0],
                quantidade,
                replace=False,
            )

            amostras.append(descritor[posicoes])
            imagens_validas.append(caminho)
            print(f"  [{numero}/{total}] {caminho.name}")

        except Exception as erro:
            print(
                f"  AVISO: ignorando {caminho}: {erro}",
                file=sys.stderr,
            )

    return amostras, imagens_validas


def treinar_kmeans(amostras, quantidade_grupos, semente):
    dados_treinamento = np.concatenate(amostras, axis=0)

    # A padronização evita que uma característica domine as outras.
    padronizador = StandardScaler()
    dados_padronizados = padronizador.fit_transform(dados_treinamento)

    kmeans = MiniBatchKMeans(
        n_clusters=quantidade_grupos,
        random_state=semente,
        batch_size=4096,
        n_init=10,
        max_iter=200,
    )
    kmeans.fit(dados_padronizados)

    return padronizador, kmeans


def gerar_resultados(args, imagens_validas, padronizador, kmeans):
    paleta = criar_paleta(args.grupos)
    linhas_csv = []
    total = len(imagens_validas)

    print("Gerando as imagens categorizadas...")

    for numero, caminho in enumerate(imagens_validas, start=1):
        imagem = carregar_imagem(caminho, args.tamanho, args.ajuste)
        descritor = criar_descritor(imagem, args.janela)
        descritor_em_linhas = descritor.reshape(-1, 24)

        dados_padronizados = padronizador.transform(descritor_em_linhas)
        rotulos = kmeans.predict(dados_padronizados)
        rotulos = rotulos.reshape(imagem.shape)

        imagem_grupos = paleta[rotulos]
        imagem_cinza_bgr = cv2.cvtColor(imagem, cv2.COLOR_GRAY2BGR)
        sobreposicao = cv2.addWeighted(
            imagem_cinza_bgr,
            0.42,
            imagem_grupos,
            0.58,
            0,
        )

        nome = criar_nome_saida(caminho, numero)

        salvar_imagem(args.saida / f"{nome}_cinza.png", imagem)
        salvar_imagem(args.saida / f"{nome}_grupos.png", imagem_grupos)
        salvar_imagem(args.saida / f"{nome}_sobreposicao.png", sobreposicao)
        salvar_imagem(
            args.saida / f"{nome}_rotulos.png",
            rotulos.astype(np.uint8),
        )

        contagens = np.bincount(rotulos.ravel(), minlength=args.grupos)
        porcentagens = 100.0 * contagens / contagens.sum()

        linha = [str(caminho)]
        for valor in porcentagens:
            linha.append(round(float(valor), 4))
        linhas_csv.append(linha)

        print(f"  [{numero}/{total}] {caminho.name}")

    return linhas_csv


def salvar_csv(args, linhas_csv):
    caminho_csv = args.saida / "proporcao_grupos.csv"

    cabecalho = ["imagem"]
    for grupo in range(args.grupos):
        cabecalho.append(f"grupo_{grupo}_percentual")

    with caminho_csv.open("w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.writer(arquivo)
        escritor.writerow(cabecalho)
        escritor.writerows(linhas_csv)


def salvar_metadados(args, quantidade_imagens, padronizador, kmeans):
    nomes_dos_atributos = []

    for escala in [1, 2, 3]:
        for nome in NOMES_DOS_FILTROS:
            nomes_dos_atributos.append(f"escala_{escala}_{nome}")

    metadados = {
        "entrada": str(args.entrada),
        "quantidade_imagens": quantidade_imagens,
        "tamanho": [args.tamanho, args.tamanho],
        "ajuste": args.ajuste,
        "janela": args.janela,
        "grupos": args.grupos,
        "amostras_por_imagem": args.amostras_por_imagem,
        "dimensoes_descritor": 24,
        "atributos": nomes_dos_atributos,
        "orientacoes_gabor_graus": ORIENTACOES,
        "escalas_piramide": [1, 0.5, 0.25],
        "centroides_padronizados": kmeans.cluster_centers_.tolist(),
        "inercia_kmeans": float(kmeans.inertia_),
        "iteracoes_kmeans": int(kmeans.n_iter_),
        "media_padronizacao": padronizador.mean_.tolist(),
        "escala_padronizacao": padronizador.scale_.tolist(),
        "semente": args.semente,
    }

    caminho_json = args.saida / "metadados.json"
    texto_json = json.dumps(metadados, ensure_ascii=False, indent=2)
    caminho_json.write_text(texto_json, encoding="utf-8")


def processar(args):
    validar_configuracao(args)

    caminhos = buscar_imagens(args.entrada)
    if not caminhos:
        raise FileNotFoundError(f"nenhuma imagem encontrada em: {args.entrada}")

    validar_pastas(args.entrada, args.saida)
    args.saida.mkdir(parents=True, exist_ok=True)

    gerador_aleatorio = np.random.default_rng(args.semente)

    amostras, imagens_validas = coletar_amostras(
        args,
        caminhos,
        gerador_aleatorio,
    )

    if not imagens_validas:
        raise RuntimeError("nenhuma imagem pôde ser processada")

    if len(imagens_validas) < 32:
        print(
            f"AVISO: foram processadas {len(imagens_validas)} imagens; "
            "o trabalho pede pelo menos 32.",
            file=sys.stderr,
        )

    padronizador, kmeans = treinar_kmeans(
        amostras,
        args.grupos,
        args.semente,
    )

    linhas_csv = gerar_resultados(
        args,
        imagens_validas,
        padronizador,
        kmeans,
    )

    salvar_csv(args, linhas_csv)
    salvar_metadados(
        args,
        len(imagens_validas),
        padronizador,
        kmeans,
    )

    print(f"Concluído. Resultados salvos em: {args.saida.resolve()}")


def main():
    try:
        args = ler_argumentos()
        processar(args)
        return 0
    except Exception as erro:
        print(f"ERRO: {erro}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
