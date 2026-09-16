"""Calcula os parametros intrinsecos e a distorcao de uma camera."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import cv2 as cv
import numpy as np

from common import (
    board_from_config,
    create_object_points,
    find_board_corners,
    list_images,
    load_config,
    write_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--images", default="data/calibracao")
    parser.add_argument("--output", default="resultados/calibracao")
    parser.add_argument("--min-images", type=int, default=10)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    pattern_size, square_size_mm = board_from_config(config)
    object_template = create_object_points(pattern_size, square_size_mm)
    image_paths = list_images(args.images)

    output_dir = Path(args.output)
    corners_dir = output_dir / "cantos_detectados"
    corners_dir.mkdir(parents=True, exist_ok=True)

    object_points: list[np.ndarray] = []
    image_points: list[np.ndarray] = []
    accepted_names: list[str] = []
    rejected_names: list[str] = []
    image_size: tuple[int, int] | None = None

    for image_path in image_paths:
        image = cv.imread(str(image_path))
        if image is None:
            rejected_names.append(image_path.name)
            print(f"[ignorada] leitura falhou: {image_path}")
            continue

        height, width = image.shape[:2]
        current_size = (width, height)
        if image_size is None:
            image_size = current_size
        elif current_size != image_size:
            rejected_names.append(image_path.name)
            print(f"[ignorada] resolucao diferente: {image_path}")
            continue

        found, corners = find_board_corners(image, pattern_size)
        if not found or corners is None:
            rejected_names.append(image_path.name)
            print(f"[ignorada] tabuleiro nao detectado: {image_path}")
            continue

        object_points.append(object_template.copy())
        image_points.append(corners)
        accepted_names.append(image_path.name)

        annotated = image.copy()
        cv.drawChessboardCorners(annotated, pattern_size, corners, found)
        cv.imwrite(str(corners_dir / image_path.name), annotated)
        print(f"[aceita] {image_path.name}")

    if image_size is None:
        raise RuntimeError("Nenhuma imagem valida foi lida.")
    if len(image_points) < args.min_images:
        raise RuntimeError(
            f"Somente {len(image_points)} imagens validas; "
            f"o minimo configurado e {args.min_images}."
        )

    rms, camera_matrix, dist_coeffs, rvecs, tvecs = cv.calibrateCamera(
        object_points,
        image_points,
        image_size,
        None,
        None,
    )

    per_view_errors: list[float] = []
    total_squared_error = 0.0
    total_points = 0
    for obj, observed, rvec, tvec in zip(
        object_points, image_points, rvecs, tvecs
    ):
        projected, _ = cv.projectPoints(
            obj, rvec, tvec, camera_matrix, dist_coeffs
        )
        residuals = observed.reshape(-1, 2) - projected.reshape(-1, 2)
        squared = np.sum(residuals**2, axis=1)
        per_view_errors.append(float(np.sqrt(np.mean(squared))))
        total_squared_error += float(np.sum(squared))
        total_points += len(squared)

    global_rmse = float(np.sqrt(total_squared_error / total_points))
    np.savez_compressed(
        output_dir / "calibration.npz",
        camera_matrix=camera_matrix,
        dist_coeffs=dist_coeffs,
        image_size=np.asarray(image_size, dtype=np.int32),
        rvecs=np.asarray(rvecs),
        tvecs=np.asarray(tvecs),
        image_names=np.asarray(accepted_names),
    )

    views = [
        {"image": name, "reprojection_rmse_px": error}
        for name, error in zip(accepted_names, per_view_errors)
    ]
    report = {
        "board": {
            "internal_corners": list(pattern_size),
            "square_size_mm": square_size_mm,
        },
        "image_size_px": list(image_size),
        "images_total": len(image_paths),
        "images_accepted": len(accepted_names),
        "images_rejected": rejected_names,
        "opencv_rms_px": float(rms),
        "global_reprojection_rmse_px": global_rmse,
        "mean_view_reprojection_rmse_px": float(np.mean(per_view_errors)),
        "max_view_reprojection_rmse_px": float(np.max(per_view_errors)),
        "camera_matrix": camera_matrix.tolist(),
        "distortion_coefficients": dist_coeffs.reshape(-1).tolist(),
        "views": views,
    }
    write_json(output_dir / "calibration.json", report)

    with (output_dir / "reprojection_errors.csv").open(
        "w", encoding="utf-8", newline=""
    ) as file:
        writer = csv.writer(file)
        writer.writerow(["image", "reprojection_rmse_px"])
        for row in views:
            writer.writerow([row["image"], f"{row['reprojection_rmse_px']:.6f}"])

    print("\nCalibracao concluida.")
    print(f"Imagens aceitas: {len(accepted_names)}/{len(image_paths)}")
    print(f"RMS do OpenCV: {rms:.6f} px")
    print(f"RMSE global de reprojecao: {global_rmse:.6f} px")
    print(f"Matriz K:\n{camera_matrix}")
    print(f"Coeficientes de distorcao:\n{dist_coeffs.reshape(-1)}")


if __name__ == "__main__":
    main()

