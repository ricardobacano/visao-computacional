"""Captura quadros de webcam, camera IP/RTSP ou arquivo de video."""

from __future__ import annotations

import argparse
import os
import time
from datetime import datetime
from pathlib import Path

import cv2 as cv

from common import load_config, parse_capture_source


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--source", help="Indice (0), arquivo ou URL RTSP.")
    parser.add_argument("--output", default="data/calibracao")
    parser.add_argument("--width", type=int)
    parser.add_argument("--height", type=int)
    parser.add_argument(
        "--auto-count",
        type=int,
        default=0,
        help="Captura automaticamente N imagens; zero ativa o modo manual.",
    )
    parser.add_argument("--interval", type=float, default=2.0)
    parser.add_argument("--no-preview", action="store_true")
    return parser.parse_args()


def save_frame(frame, output_dir: Path, sequence: int) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    output_path = output_dir / f"calib_{sequence:03d}_{timestamp}.png"
    if not cv.imwrite(str(output_path), frame):
        raise OSError(f"Nao foi possivel salvar {output_path}")
    return output_path


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    capture_config = config.get("capture", {})

    source_value = (
        args.source
        or os.getenv("CAMERA_SOURCE")
        or str(capture_config.get("source", "0"))
    )
    source = parse_capture_source(source_value)
    width = args.width or capture_config.get("width")
    height = args.height or capture_config.get("height")

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    camera = cv.VideoCapture(source)
    if width:
        camera.set(cv.CAP_PROP_FRAME_WIDTH, int(width))
    if height:
        camera.set(cv.CAP_PROP_FRAME_HEIGHT, int(height))
    if not camera.isOpened():
        raise RuntimeError("Nao foi possivel abrir a fonte de video.")

    automatic = args.auto_count > 0
    if not automatic and args.no_preview:
        raise ValueError("O modo manual precisa da janela de preview.")

    captured = 0
    last_capture = time.monotonic() - args.interval
    print("Fonte aberta. Pressione ESPACO/C para salvar e Q/ESC para sair.")

    try:
        while True:
            ok, frame = camera.read()
            if not ok:
                raise RuntimeError("Falha ao receber quadro da fonte de video.")

            display = frame.copy()
            cv.putText(
                display,
                f"capturadas: {captured}",
                (20, 35),
                cv.FONT_HERSHEY_SIMPLEX,
                0.9,
                (0, 255, 0),
                2,
                cv.LINE_AA,
            )

            if not args.no_preview:
                cv.imshow("Captura para calibracao", display)
                key = cv.waitKey(1) & 0xFF
            else:
                key = 255

            should_save = key in (ord("c"), ord(" "))
            if automatic and time.monotonic() - last_capture >= args.interval:
                should_save = True

            if should_save:
                captured += 1
                saved = save_frame(frame, output_dir, captured)
                last_capture = time.monotonic()
                print(f"[{captured}] {saved}")

            if key in (ord("q"), 27):
                break
            if automatic and captured >= args.auto_count:
                break
    finally:
        camera.release()
        cv.destroyAllWindows()

    print(f"Captura finalizada: {captured} imagem(ns).")


if __name__ == "__main__":
    main()

