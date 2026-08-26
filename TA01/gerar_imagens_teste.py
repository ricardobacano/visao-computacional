#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--saida", type=Path, default=Path("imagens_teste"))
    parser.add_argument("--quantidade", type=int, default=32)
    parser.add_argument("--tamanho", type=int, default=512)
    parser.add_argument("--semente", type=int, default=123)
    args = parser.parse_args()
    args.saida.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(args.semente)

    y, x = np.mgrid[0 : args.tamanho, 0 : args.tamanho]
    for indice in range(args.quantidade):
        periodo = 10 + 3 * (indice % 6)
        angulo = np.deg2rad((indice % 8) * 22.5)
        coordenada = x * np.cos(angulo) + y * np.sin(angulo)
        listras = 70 * (np.sin(2 * np.pi * coordenada / periodo) > 0)
        centro = (args.tamanho - 1) / 2
        circulos = 45 * (
            np.sin(np.hypot(x - centro, y - centro) / (4 + indice % 5)) > 0
        )
        ruido = rng.normal(0, 10 + indice % 4 * 4, size=(args.tamanho, args.tamanho))
        imagem = np.clip(80 + listras + circulos + ruido, 0, 255).astype(np.uint8)
        cv2.imwrite(str(args.saida / f"teste_{indice + 1:02d}.png"), imagem)

    print(f"Criadas {args.quantidade} imagens de teste em {args.saida.resolve()}")


if __name__ == "__main__":
    main()
