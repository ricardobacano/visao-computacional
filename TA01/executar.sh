#!/usr/bin/env bash

set -Eeuo pipefail

diretorio_projeto="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
entrada_imagens="$diretorio_projeto/imagens"
saida_resultados="$diretorio_projeto/resultados"
quantidade_grupos="5"
tamanho_janela="21"
modo_teste="nao"

mostrar_ajuda() {
    printf '%s\n' \
        "U  so: bash executar.sh [opções]" \
        "" \
        "Sem opções, lê ./imagens e grava em ./resultados." \
        "" \
        "Opções:" \
        "  --teste             Gera 32 imagens sintéticas e processa o teste" \
        "  --entrada CAMINHO   Usa outra imagem ou pasta de imagens" \
        "  --saida CAMINHO     Usa outra pasta de resultados" \
        "  --grupos NUMERO     Número de grupos do K-means (padrão: 5)" \
        "  --janela NUMERO     Tamanho ímpar da janela (padrão: 21)" \
        "  -h, --help          Mostra esta ajuda" \
        "" \
        "Exemplos:" \
        "  bash executar.sh" \
        "  bash executar.sh --teste" \
        "  bash executar.sh --entrada /caminho/fotos --grupos 4"
}

falhar() {
    printf 'ERRO: %s\n' "$1" >&2
    exit 1
}

while (( $# > 0 )); do
    case "$1" in
        --teste)
            modo_teste="sim"
            shift
            ;;
        --entrada)
            (( $# >= 2 )) || falhar "informe um caminho depois de --entrada"
            entrada_imagens="$2"
            shift 2
            ;;
        --saida)
            (( $# >= 2 )) || falhar "informe um caminho depois de --saida"
            saida_resultados="$2"
            shift 2
            ;;
        --grupos)
            (( $# >= 2 )) || falhar "informe um número depois de --grupos"
            quantidade_grupos="$2"
            shift 2
            ;;
        --janela)
            (( $# >= 2 )) || falhar "informe um número depois de --janela"
            tamanho_janela="$2"
            shift 2
            ;;
        -h|--help)
            mostrar_ajuda
            exit 0
            ;;
        *)
            falhar "opção desconhecida: $1 (use --help para consultar)"
            ;;
    esac
done

command -v python3 >/dev/null 2>&1 || falhar "Python 3 não foi encontrado"

python_ambiente="$diretorio_projeto/.venv/bin/python"

if [[ ! -x "$python_ambiente" ]]; then
    printf '%s\n' "[1/4] Criando o ambiente virtual .venv..."
    if ! python3 -m venv "$diretorio_projeto/.venv"; then
        falhar "não foi possível criar .venv. No Ubuntu, instale o pacote python3-venv."
    fi
else
    printf '%s\n' "[1/4] Ambiente virtual já existe."
fi

printf '%s\n' "[2/4] Conferindo OpenCV, NumPy e scikit-learn..."
if ! "$python_ambiente" -c "import cv2, numpy, sklearn" >/dev/null 2>&1; then
    printf '%s\n' "Instalando as dependências (isso ocorre apenas na primeira execução)..."
    "$python_ambiente" -m pip install -r "$diretorio_projeto/requirements.txt"
else
    printf '%s\n' "Dependências já instaladas."
fi

if [[ "$modo_teste" == "sim" ]]; then
    entrada_imagens="$diretorio_projeto/imagens_teste"
    saida_resultados="$diretorio_projeto/resultados_teste"
    printf '%s\n' "[3/4] Gerando 32 imagens sintéticas para o teste..."
    "$python_ambiente" "$diretorio_projeto/gerar_imagens_teste.py" \
        --saida "$entrada_imagens" \
        --quantidade 32
else
    printf '%s\n' "[3/4] Usando as fotografias de: $entrada_imagens"
    [[ -e "$entrada_imagens" ]] || falhar "caminho de entrada não encontrado: $entrada_imagens"
fi

printf '%s\n' "[4/4] Extraindo as 24 características e agrupando as texturas..."
"$python_ambiente" "$diretorio_projeto/codigo.py" \
    --entrada "$entrada_imagens" \
    --saida "$saida_resultados" \
    --grupos "$quantidade_grupos" \
    --janela "$tamanho_janela"

printf '\n%s\n' "Tudo pronto. Abra os resultados em: $saida_resultados"
