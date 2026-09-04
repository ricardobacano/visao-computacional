#!/usr/bin/env python3

"""Executa várias configurações do programa codigo.py."""

import argparse
import csv
import json
import subprocess
import sys
import time
from pathlib import Path


# Cada item possui: quantidade de grupos e tamanho da janela.
CONFIGURACOES_PADRAO = [
    (3, 21),
    (5, 15),
    (5, 21),
    (5, 31),
    (6, 21),
]

EXTENSOES = [".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"]


def converter_configuracao(texto):
    try:
        partes = texto.split(":")

        if len(partes) != 2:
            raise ValueError

        grupos = int(partes[0])
        janela = int(partes[1])

    except ValueError as erro:
        raise argparse.ArgumentTypeError(
            "use o formato GRUPOS:JANELA, por exemplo 5:21"
        ) from erro

    if grupos < 2:
        raise argparse.ArgumentTypeError("GRUPOS deve ser pelo menos 2")

    if janela < 3 or janela % 2 == 0:
        raise argparse.ArgumentTypeError(
            "JANELA deve ser ímpar e pelo menos 3"
        )

    return grupos, janela


def ler_argumentos():
    parser = argparse.ArgumentParser(
        description="Executa o codigo.py com diferentes valores de K e janela."
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
        default=Path("resultados_experimentos"),
        help="Pasta principal dos resultados.",
    )
    parser.add_argument(
        "--configuracoes",
        type=converter_configuracao,
        nargs="+",
        default=CONFIGURACOES_PADRAO,
        metavar="K:JANELA",
        help="Configurações como 3:21 5:21 6:31.",
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
        "--amostras-por-imagem",
        type=int,
        default=8000,
        help="Quantidade de amostras por imagem.",
    )
    parser.add_argument(
        "--semente",
        type=int,
        default=42,
        help="Semente usada em todos os experimentos.",
    )

    return parser.parse_args()


def contar_imagens(entrada):
    if entrada.is_file():
        if entrada.suffix.lower() in EXTENSOES:
            return 1
        return 0

    if not entrada.is_dir():
        return 0

    quantidade = 0

    for caminho in entrada.rglob("*"):
        if caminho.is_file() and caminho.suffix.lower() in EXTENSOES:
            quantidade += 1

    return quantidade


def criar_comando(args, codigo, destino, grupos, janela):
    # O mesmo Python do ambiente virtual executa o codigo.py.
    comando = [
        sys.executable,
        str(codigo),
        "--entrada",
        str(args.entrada),
        "--saida",
        str(destino),
        "--grupos",
        str(grupos),
        "--janela",
        str(janela),
        "--tamanho",
        str(args.tamanho),
        "--ajuste",
        args.ajuste,
        "--amostras-por-imagem",
        str(args.amostras_por_imagem),
        "--semente",
        str(args.semente),
    ]

    return comando


def criar_linha_resumo(nome, grupos, janela, destino, retorno, duracao):
    linha = {
        "experimento": nome,
        "grupos": grupos,
        "janela": janela,
        "status": "ok" if retorno == 0 else "erro",
        "tempo_segundos": duracao,
        "quantidade_imagens": "",
        "inercia_kmeans": "",
        "iteracoes_kmeans": "",
        "diretorio_resultados": str(destino.resolve()),
    }

    caminho_metadados = destino / "metadados.json"

    if retorno == 0 and caminho_metadados.is_file():
        texto = caminho_metadados.read_text(encoding="utf-8")
        metadados = json.loads(texto)

        linha["quantidade_imagens"] = metadados["quantidade_imagens"]
        linha["inercia_kmeans"] = round(
            float(metadados["inercia_kmeans"]),
            6,
        )
        linha["iteracoes_kmeans"] = metadados["iteracoes_kmeans"]

    return linha


def salvar_resumo(caminho, linhas):
    colunas = [
        "experimento",
        "grupos",
        "janela",
        "status",
        "tempo_segundos",
        "quantidade_imagens",
        "inercia_kmeans",
        "iteracoes_kmeans",
        "diretorio_resultados",
    ]

    with caminho.open("w", newline="", encoding="utf-8") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=colunas)
        escritor.writeheader()
        escritor.writerows(linhas)


def executar_experimentos(args):
    quantidade_imagens = contar_imagens(args.entrada)

    if quantidade_imagens == 0:
        print(
            f"ERRO: nenhuma imagem encontrada em {args.entrada}",
            file=sys.stderr,
        )
        return 1

    args.saida.mkdir(parents=True, exist_ok=True)

    codigo = Path(__file__).resolve().with_name("codigo.py")
    caminho_resumo = args.saida / "resumo_experimentos.csv"
    linhas_resumo = []
    total = len(args.configuracoes)

    if not codigo.is_file():
        print(f"ERRO: arquivo não encontrado: {codigo}", file=sys.stderr)
        return 1

    print(f"Serão executados {total} experimentos.")

    for numero, configuracao in enumerate(args.configuracoes, start=1):
        grupos, janela = configuracao
        nome = f"k{grupos}_j{janela}"
        destino = args.saida / nome

        print(f"\n[{numero}/{total}] K={grupos}, janela={janela}")

        comando = criar_comando(
            args,
            codigo,
            destino,
            grupos,
            janela,
        )

        inicio = time.perf_counter()
        processo = subprocess.run(comando, check=False)
        duracao = round(time.perf_counter() - inicio, 3)

        linha = criar_linha_resumo(
            nome,
            grupos,
            janela,
            destino,
            processo.returncode,
            duracao,
        )
        linhas_resumo.append(linha)

        # O CSV é atualizado após cada teste para não perder resultados.
        salvar_resumo(caminho_resumo, linhas_resumo)

        if processo.returncode != 0:
            print(
                "Experimentos interrompidos após a primeira falha.",
                file=sys.stderr,
            )
            return 1

    print(f"\nResumo salvo em: {caminho_resumo.resolve()}")
    return 0


def main():
    args = ler_argumentos()
    return executar_experimentos(args)


if __name__ == "__main__":
    raise SystemExit(main())
