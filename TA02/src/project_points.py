"""Estima a pose do tabuleiro e projeta pontos 3D em imagens 2D."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any

import cv2 as cv
import numpy as np

from common import (
    board_from_config,
    create_object_points,
    ensure_same_resolution,
    find_board_corners,
    list_images,
    load_calibration,
    load_config,
    write_json,
)


COLORS = [
    (0, 255, 255),
    (255, 0, 0),
    (0, 255, 0),
    (0, 0, 255),
    (255, 0, 255),
    (255, 255, 0),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--images", default="data/validacao")
    parser.add_argument(
        "--calibration", default="resultados/calibracao/calibration.npz"
    )
    parser.add_argument("--output", default="resultados/projecao")
    return parser.parse_args()


def projection_points(
    config: dict[str, Any], square_sizes_mm: tuple[float, float]
):
    configured = config.get("projection", {}).get("points")
    if not configured:
        square_size_x_mm, square_size_y_mm = square_sizes_mm
        square_size_z_mm = min(square_sizes_mm)
        configured = [
            {"label": "origem", "xyz_mm": [0, 0, 0]},
            {"label": "eixo_x", "xyz_mm": [3 * square_size_x_mm, 0, 0]},
            {"label": "eixo_y", "xyz_mm": [0, 3 * square_size_y_mm, 0]},
            {"label": "eixo_z", "xyz_mm": [0, 0, -3 * square_size_z_mm]},
        ]

    labels: list[str] = []
    coordinates: list[list[float]] = []
    for item in configured:
        label = str(item["label"])
        xyz = [float(value) for value in item["xyz_mm"]]
        if len(xyz) != 3:
            raise ValueError(f"O ponto {label} precisa de tres coordenadas XYZ.")
        labels.append(label)
        coordinates.append(xyz)
    return labels, np.asarray(coordinates, dtype=np.float32)


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    pattern_size, square_sizes_mm = board_from_config(config)
    board_points = create_object_points(pattern_size, square_sizes_mm)
    labels, points_3d = projection_points(config, square_sizes_mm)

    calibration = load_calibration(args.calibration)
    camera_matrix = calibration["camera_matrix"]
    dist_coeffs = calibration["dist_coeffs"]
    image_size = calibration["image_size"]

    output_dir = Path(args.output)
    overlay_dir = output_dir / "imagens"
    overlay_dir.mkdir(parents=True, exist_ok=True)

    csv_rows: list[list[Any]] = []
    poses: list[dict[str, Any]] = []
    image_paths = list_images(args.images)

    for image_path in image_paths:
        image = cv.imread(str(image_path))
        if image is None:
            print(f"[ignorada] leitura falhou: {image_path}")
            continue
        ensure_same_resolution(image, image_size)

        found, corners = find_board_corners(image, pattern_size)
        if not found or corners is None:
            print(f"[ignorada] tabuleiro nao detectado: {image_path}")
            continue

        success, rvec, tvec = cv.solvePnP(
            board_points,
            corners,
            camera_matrix,
            dist_coeffs,
            flags=cv.SOLVEPNP_ITERATIVE,
        )
        if not success:
            print(f"[ignorada] solvePnP falhou: {image_path}")
            continue

        projected_points, _ = cv.projectPoints(
            points_3d, rvec, tvec, camera_matrix, dist_coeffs
        )
        projected_origin, _ = cv.projectPoints(
            np.zeros((1, 3), dtype=np.float32),
            rvec,
            tvec,
            camera_matrix,
            dist_coeffs,
        )
        projected_board, _ = cv.projectPoints(
            board_points, rvec, tvec, camera_matrix, dist_coeffs
        )
        projected_points = projected_points.reshape(-1, 2)
        residuals = corners.reshape(-1, 2) - projected_board.reshape(-1, 2)
        reprojection_rmse = float(
            np.sqrt(np.mean(np.sum(residuals**2, axis=1)))
        )

        overlay = image.copy()
        origin_pixel = tuple(
            np.rint(projected_origin.reshape(2)).astype(int)
        )
        for index, (label, xyz, uv) in enumerate(
            zip(labels, points_3d, projected_points)
        ):
            u, v = float(uv[0]), float(uv[1])
            pixel = (int(round(u)), int(round(v)))
            color = COLORS[index % len(COLORS)]
            in_frame = 0 <= u < image_size[0] and 0 <= v < image_size[1]
            if in_frame:
                cv.circle(overlay, pixel, 7, color, -1, cv.LINE_AA)
                cv.putText(
                    overlay,
                    label,
                    (pixel[0] + 9, pixel[1] - 9),
                    cv.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    color,
                    2,
                    cv.LINE_AA,
                )
                if index in (1, 2, 3):
                    cv.line(overlay, origin_pixel, pixel, color, 3, cv.LINE_AA)

            csv_rows.append(
                [
                    image_path.name,
                    label,
                    *[float(value) for value in xyz],
                    u,
                    v,
                    in_frame,
                    reprojection_rmse,
                ]
            )

        cv.putText(
            overlay,
            f"RMSE reprojecao: {reprojection_rmse:.3f} px",
            (20, image.shape[0] - 25),
            cv.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2,
            cv.LINE_AA,
        )
        cv.imwrite(str(overlay_dir / f"{image_path.stem}_projecao.png"), overlay)
        poses.append(
            {
                "image": image_path.name,
                "rvec": rvec.reshape(-1).tolist(),
                "tvec_mm": tvec.reshape(-1).tolist(),
                "board_reprojection_rmse_px": reprojection_rmse,
            }
        )
        print(f"[ok] {image_path.name}: RMSE={reprojection_rmse:.4f} px")

    if not poses:
        raise RuntimeError("Nenhuma imagem permitiu estimar a pose do tabuleiro.")

    with (output_dir / "projected_points.csv").open(
        "w", encoding="utf-8", newline=""
    ) as file:
        writer = csv.writer(file)
        writer.writerow(
            [
                "image",
                "label",
                "x_mm",
                "y_mm",
                "z_mm",
                "u_px",
                "v_px",
                "inside_image",
                "board_reprojection_rmse_px",
            ]
        )
        writer.writerows(csv_rows)

    write_json(
        output_dir / "poses.json",
        {
            "coordinate_system": (
                "Origem no primeiro canto interno; X nas colunas; Y nas linhas; "
                "Z negativo saindo do plano em direcao a camera."
            ),
            "poses": poses,
        },
    )
    print(f"Projecao concluida para {len(poses)} imagem(ns).")


if __name__ == "__main__":
    main()
