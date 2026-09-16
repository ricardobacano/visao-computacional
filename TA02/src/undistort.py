"""Remove a distorcao e cria comparacoes entre imagens originais e corrigidas."""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2 as cv

from common import (
    ensure_same_resolution,
    list_images,
    load_calibration,
    write_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--images", default="data/validacao")
    parser.add_argument(
        "--calibration", default="resultados/calibracao/calibration.npz"
    )
    parser.add_argument("--output", default="resultados/distorcao")
    parser.add_argument(
        "--alpha",
        type=float,
        default=1.0,
        help="0 corta bordas invalidas; 1 preserva maior campo de visao.",
    )
    return parser.parse_args()


def add_title(image, title: str):
    titled = image.copy()
    cv.rectangle(titled, (0, 0), (330, 45), (0, 0, 0), -1)
    cv.putText(
        titled,
        title,
        (12, 31),
        cv.FONT_HERSHEY_SIMPLEX,
        0.8,
        (255, 255, 255),
        2,
        cv.LINE_AA,
    )
    return titled


def main() -> None:
    args = parse_args()
    if not 0.0 <= args.alpha <= 1.0:
        raise ValueError("alpha deve estar entre 0 e 1.")

    calibration = load_calibration(args.calibration)
    camera_matrix = calibration["camera_matrix"]
    dist_coeffs = calibration["dist_coeffs"]
    image_size = calibration["image_size"]
    image_paths = list_images(args.images)

    output_dir = Path(args.output)
    corrected_dir = output_dir / "corrigidas"
    comparison_dir = output_dir / "comparacoes"
    corrected_dir.mkdir(parents=True, exist_ok=True)
    comparison_dir.mkdir(parents=True, exist_ok=True)

    new_camera_matrix, roi = cv.getOptimalNewCameraMatrix(
        camera_matrix,
        dist_coeffs,
        image_size,
        args.alpha,
        image_size,
    )

    processed = 0
    for image_path in image_paths:
        image = cv.imread(str(image_path))
        if image is None:
            print(f"[ignorada] leitura falhou: {image_path}")
            continue
        ensure_same_resolution(image, image_size)

        corrected = cv.undistort(
            image, camera_matrix, dist_coeffs, None, new_camera_matrix
        )
        corrected_path = corrected_dir / f"{image_path.stem}_corrigida.png"
        cv.imwrite(str(corrected_path), corrected)

        comparison = cv.hconcat(
            [add_title(image, "Original"), add_title(corrected, "Corrigida")]
        )
        cv.imwrite(
            str(comparison_dir / f"{image_path.stem}_comparacao.jpg"),
            comparison,
        )
        processed += 1
        print(f"[ok] {image_path.name}")

    write_json(
        output_dir / "undistortion.json",
        {
            "alpha": args.alpha,
            "roi_xywh": [int(value) for value in roi],
            "original_camera_matrix": camera_matrix.tolist(),
            "new_camera_matrix": new_camera_matrix.tolist(),
            "images_processed": processed,
        },
    )
    print(f"Correcao concluida: {processed} imagem(ns).")


if __name__ == "__main__":
    main()

