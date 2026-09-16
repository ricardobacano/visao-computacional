"""Executa calibracao, correcao de distorcao e projecao 3D para 2D."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--calibration-images", default="data/calibracao")
    parser.add_argument("--validation-images", default="data/validacao")
    parser.add_argument("--results", default="resultados")
    parser.add_argument("--min-images", type=int, default=10)
    parser.add_argument("--alpha", type=float, default=1.0)
    return parser.parse_args()


def run(command: list[str]) -> None:
    print("\n$", " ".join(command))
    subprocess.run(command, check=True)


def main() -> None:
    args = parse_args()
    source_dir = Path(__file__).resolve().parent
    results = Path(args.results)
    calibration_file = results / "calibracao" / "calibration.npz"

    run(
        [
            sys.executable,
            str(source_dir / "calibrate.py"),
            "--config",
            args.config,
            "--images",
            args.calibration_images,
            "--output",
            str(results / "calibracao"),
            "--min-images",
            str(args.min_images),
        ]
    )
    run(
        [
            sys.executable,
            str(source_dir / "undistort.py"),
            "--images",
            args.validation_images,
            "--calibration",
            str(calibration_file),
            "--output",
            str(results / "distorcao"),
            "--alpha",
            str(args.alpha),
        ]
    )
    run(
        [
            sys.executable,
            str(source_dir / "project_points.py"),
            "--config",
            args.config,
            "--images",
            args.validation_images,
            "--calibration",
            str(calibration_file),
            "--output",
            str(results / "projecao"),
        ]
    )
    print("\nPipeline concluido.")


if __name__ == "__main__":
    main()

