"""Funcoes compartilhadas pelos scripts de calibracao."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import cv2 as cv
import numpy as np


IMAGE_EXTENSIONS = {".bmp", ".jpeg", ".jpg", ".png", ".tif", ".tiff"}


def load_config(path: str | Path) -> dict[str, Any]:
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(
            f"Configuracao nao encontrada: {config_path}. "
            "Copie config.example.json para config.json e ajuste os valores."
        )
    with config_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def board_from_config(
    config: dict[str, Any],
) -> tuple[tuple[int, int], tuple[float, float]]:
    board = config.get("board", {})
    columns = int(board.get("columns", 0))
    rows = int(board.get("rows", 0))
    square_size_x_mm = float(board.get("square_size_x_mm", 0.0))
    square_size_y_mm = float(board.get("square_size_y_mm", 0.0))

    if columns < 2 or rows < 2:
        raise ValueError("columns e rows devem indicar os cantos internos do tabuleiro.")
    if square_size_x_mm <= 0 or square_size_y_mm <= 0:
        raise ValueError(
            "square_size_x_mm e square_size_y_mm devem ser maiores que zero."
        )

    return (columns, rows), (square_size_x_mm, square_size_y_mm)


def create_object_points(
    pattern_size: tuple[int, int], square_sizes_mm: tuple[float, float]
) -> np.ndarray:
    """Cria os cantos 3D do tabuleiro no plano Z=0, em milimetros."""
    columns, rows = pattern_size
    square_size_x_mm, square_size_y_mm = square_sizes_mm
    points = np.zeros((columns * rows, 3), dtype=np.float32)
    grid = np.mgrid[0:columns, 0:rows].T.reshape(-1, 2)
    points[:, 0] = grid[:, 0] * square_size_x_mm
    points[:, 1] = grid[:, 1] * square_size_y_mm
    return points


def list_images(path: str | Path) -> list[Path]:
    input_path = Path(path)
    if input_path.is_file():
        if input_path.suffix.lower() not in IMAGE_EXTENSIONS:
            raise ValueError(f"Arquivo nao reconhecido como imagem: {input_path}")
        return [input_path]
    if not input_path.is_dir():
        raise FileNotFoundError(f"Entrada nao encontrada: {input_path}")

    images = sorted(
        item
        for item in input_path.iterdir()
        if item.is_file() and item.suffix.lower() in IMAGE_EXTENSIONS
    )
    if not images:
        raise FileNotFoundError(f"Nenhuma imagem encontrada em: {input_path}")
    return images


def find_board_corners(
    image: np.ndarray, pattern_size: tuple[int, int]
) -> tuple[bool, np.ndarray | None]:
    gray = cv.cvtColor(image, cv.COLOR_BGR2GRAY)
    flags = cv.CALIB_CB_ADAPTIVE_THRESH | cv.CALIB_CB_NORMALIZE_IMAGE
    found, corners = cv.findChessboardCorners(gray, pattern_size, flags)
    if not found:
        return False, None

    criteria = (
        cv.TERM_CRITERIA_EPS + cv.TERM_CRITERIA_MAX_ITER,
        50,
        0.001,
    )
    refined = cv.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
    return True, refined


def load_calibration(path: str | Path) -> dict[str, Any]:
    calibration_path = Path(path)
    if not calibration_path.exists():
        raise FileNotFoundError(f"Calibracao nao encontrada: {calibration_path}")

    with np.load(calibration_path) as data:
        required = {"camera_matrix", "dist_coeffs", "image_size"}
        missing = required.difference(data.files)
        if missing:
            raise ValueError(f"Arquivo de calibracao incompleto: {sorted(missing)}")
        return {
            "camera_matrix": data["camera_matrix"],
            "dist_coeffs": data["dist_coeffs"],
            "image_size": tuple(int(value) for value in data["image_size"]),
        }


def write_json(path: str | Path, content: dict[str, Any]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        json.dump(content, file, ensure_ascii=False, indent=2)
        file.write("\n")


def ensure_same_resolution(image: np.ndarray, expected_size: tuple[int, int]) -> None:
    height, width = image.shape[:2]
    if (width, height) != expected_size:
        raise ValueError(
            f"Resolucao da imagem {(width, height)} difere da calibracao "
            f"{expected_size}. Use a mesma resolucao em todo o experimento."
        )
