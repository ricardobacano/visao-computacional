#!/usr/bin/env bash

set -Eeuo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"
PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_PYTHON="$VENV_DIR/bin/python"
VENV_PIP="$VENV_DIR/bin/pip"

cd "$PROJECT_DIR"

setup() {
    echo "=== Preparando ambiente virtual ==="

    if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
        echo "Erro: python3 não foi encontrado."
        exit 1
    fi

    if [[ ! -d "$VENV_DIR" ]]; then
        "$PYTHON_BIN" -m venv "$VENV_DIR"
    fi

    "$VENV_PIP" install --upgrade pip
    "$VENV_PIP" install -r requirements.txt

    if [[ ! -f config.json ]]; then
        cp config.example.json config.json
        echo "Arquivo config.json criado."
    fi

    mkdir -p \
        data/calibracao \
        data/validacao \
        resultados

    echo "=== Ambiente preparado com sucesso ==="
}

ensure_setup() {
    if [[ ! -x "$VENV_PYTHON" ]]; then
        setup
    fi

    if [[ ! -f config.json ]]; then
        cp config.example.json config.json
    fi
}

test_program() {
    ensure_setup

    echo "=== Verificando sintaxe dos scripts ==="
    "$VENV_PYTHON" -m compileall -q src

    echo "=== Verificando dependências ==="
    "$VENV_PYTHON" - <<'PY'
import cv2
import numpy

print(f"OpenCV: {cv2.__version__}")
print(f"NumPy: {numpy.__version__}")
print("Dependências carregadas corretamente.")
PY

    echo "=== Verificando comandos ==="
    "$VENV_PYTHON" src/capture.py --help >/dev/null
    "$VENV_PYTHON" src/calibrate.py --help >/dev/null
    "$VENV_PYTHON" src/undistort.py --help >/dev/null
    "$VENV_PYTHON" src/project_points.py --help >/dev/null
    "$VENV_PYTHON" src/run_pipeline.py --help >/dev/null

    echo "=== Todos os testes básicos passaram ==="
}

capture() {
    ensure_setup

    local source="${1:-0}"

    echo "=== Iniciando captura pela fonte: $source ==="
    "$VENV_PYTHON" src/capture.py \
        --config config.json \
        --source "$source" \
        --output data/calibracao
}

capture_validation() {
    ensure_setup

    local source="${1:-0}"

    echo "=== Capturando imagens de validação ==="
    "$VENV_PYTHON" src/capture.py \
        --config config.json \
        --source "$source" \
        --output data/validacao
}

calibrate() {
    ensure_setup

    echo "=== Executando calibração ==="
    "$VENV_PYTHON" src/calibrate.py \
        --config config.json \
        --images data/calibracao \
        --output resultados/calibracao \
        --min-images 10
}

undistort() {
    ensure_setup

    echo "=== Removendo distorção ==="
    "$VENV_PYTHON" src/undistort.py \
        --images data/validacao \
        --calibration resultados/calibracao/calibration.npz \
        --output resultados/distorcao \
        --alpha 1.0
}

project_points() {
    ensure_setup

    echo "=== Projetando pontos 3D para 2D ==="
    "$VENV_PYTHON" src/project_points.py \
        --config config.json \
        --images data/validacao \
        --calibration resultados/calibracao/calibration.npz \
        --output resultados/projecao
}

check_images() {
    local calibration_count
    local validation_count

    calibration_count="$(
        find data/calibracao \
            -maxdepth 1 \
            -type f \
            ! -name '.gitkeep' |
            wc -l
    )"

    validation_count="$(
        find data/validacao \
            -maxdepth 1 \
            -type f \
            ! -name '.gitkeep' |
            wc -l
    )"

    if (( calibration_count < 10 )); then
        echo "Erro: são necessárias pelo menos 10 imagens de calibração."
        echo "Encontradas: $calibration_count"
        exit 1
    fi

    if (( validation_count < 1 )); then
        echo "Erro: nenhuma imagem de validação foi encontrada."
        exit 1
    fi

    echo "Imagens de calibração: $calibration_count"
    echo "Imagens de validação: $validation_count"
}

run_all() {
    ensure_setup
    test_program
    check_images

    echo "=== Executando pipeline completo ==="
    "$VENV_PYTHON" src/run_pipeline.py \
        --config config.json \
        --calibration-images data/calibracao \
        --validation-images data/validacao \
        --results resultados \
        --min-images 10 \
        --alpha 1.0

    echo "=== Execução concluída ==="
    echo "Resultados disponíveis em: $PROJECT_DIR/resultados"
}

show_help() {
    echo "Uso: ./executar.sh COMANDO [FONTE]"
    echo
    echo "Comandos:"
    echo "  setup                  Cria o venv e instala as dependências"
    echo "  test                   Testa sintaxe, dependências e scripts"
    echo "  capture [fonte]        Captura imagens para calibração"
    echo "  validation [fonte]     Captura imagens para validação"
    echo "  calibrate              Executa somente a calibração"
    echo "  undistort              Executa a remoção da distorção"
    echo "  project                Executa a projeção 3D para 2D"
    echo "  all                    Executa todos os experimentos"
    echo "  help                   Mostra esta ajuda"
    echo
    echo "Exemplos:"
    echo "  ./executar.sh setup"
    echo "  ./executar.sh test"
    echo "  ./executar.sh capture 0"
    echo "  ./executar.sh validation 0"
    echo "  ./executar.sh all"
}

COMMAND="${1:-help}"

case "$COMMAND" in
    setup)
        setup
        ;;
    test)
        test_program
        ;;
    capture)
        capture "${2:-0}"
        ;;
    validation)
        capture_validation "${2:-0}"
        ;;
    calibrate)
        calibrate
        ;;
    undistort)
        undistort
        ;;
    project)
        project_points
        ;;
    all)
        run_all
        ;;
    help|-h|--help)
        show_help
        ;;
    *)
        echo "Erro: comando desconhecido: $COMMAND"
        echo
        show_help
        exit 1
        ;;
esac