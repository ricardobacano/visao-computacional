#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"
PYTHON_BIN="${PYTHON_BIN:-python3}"
PYTHON_VENV="$VENV_DIR/bin/python"
PIP_VENV="$VENV_DIR/bin/pip"
cd "$PROJECT_DIR"

setup() {
    command -v "$PYTHON_BIN" >/dev/null 2>&1 || { echo "Erro: python3 nao encontrado."; exit 1; }
    [[ -d "$VENV_DIR" ]] || "$PYTHON_BIN" -m venv "$VENV_DIR"
    "$PIP_VENV" install --upgrade pip
    "$PIP_VENV" install -r requirements.txt
    [[ -f config.json ]] || cp config.example.json config.json
    mkdir -p data/calibracao data/validacao resultados
    echo "Ambiente preparado. Ajuste config.json antes de calibrar."
}

ensure_setup() {
    [[ -x "$PYTHON_VENV" ]] || setup
    [[ -f config.json ]] || cp config.example.json config.json
}

count_images() {
    find "$1" -maxdepth 1 -type f \( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' -o -iname '*.bmp' -o -iname '*.tif' -o -iname '*.tiff' \) | wc -l
}

check_images() {
    local calibration_count validation_count
    calibration_count="$(count_images data/calibracao)"
    validation_count="$(count_images data/validacao)"
    (( calibration_count >= 10 )) || { echo "Erro: coloque pelo menos 10 fotos em data/calibracao (encontradas: $calibration_count)."; exit 1; }
    (( validation_count >= 1 )) || { echo "Erro: coloque ao menos 1 foto em data/validacao."; exit 1; }
    echo "Fotos: $calibration_count para calibracao e $validation_count para validacao."
}

test_program() {
    ensure_setup
    "$PYTHON_VENV" -m compileall -q src
    "$PYTHON_VENV" - <<'PY'
import cv2
import numpy
print(f"OpenCV: {cv2.__version__}")
print(f"NumPy: {numpy.__version__}")
print("Scripts e dependencias verificados.")
PY
}

calibrate() {
    ensure_setup
    "$PYTHON_VENV" src/calibrate.py --config config.json --images data/calibracao --output resultados/calibracao --min-images 10
}

undistort() {
    ensure_setup
    "$PYTHON_VENV" src/undistort.py --images data/validacao --calibration resultados/calibracao/calibration.npz --output resultados/distorcao --alpha 1.0
}

project() {
    ensure_setup
    "$PYTHON_VENV" src/project_points.py --config config.json --images data/validacao --calibration resultados/calibracao/calibration.npz --output resultados/projecao
}

run_all() {
    test_program
    check_images
    "$PYTHON_VENV" src/run_pipeline.py --config config.json --calibration-images data/calibracao --validation-images data/validacao --results resultados --min-images 10 --alpha 1.0
}

show_help() {
    cat <<'EOF'
Uso: ./executar.sh COMANDO

  setup       Cria o ambiente virtual e instala as dependencias
  test        Verifica os scripts e as dependencias
  check       Confere a quantidade de fotos nas pastas
  calibrate   Calcula os parametros da camera
  undistort   Corrige a distorcao das fotos de validacao
  project     Executa a projecao de pontos 3D para 2D
  all         Executa todo o experimento
  help        Mostra esta ajuda
EOF
}

case "${1:-help}" in
    setup) setup ;;
    test) test_program ;;
    check) ensure_setup; check_images ;;
    calibrate) calibrate ;;
    undistort) undistort ;;
    project) project ;;
    all) run_all ;;
    help|-h|--help) show_help ;;
    *) echo "Erro: comando desconhecido: $1"; show_help; exit 1 ;;
esac
