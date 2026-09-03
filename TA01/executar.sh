#!/usr/bin/env bash

# Execução simplificada do projeto de segmentação por textura.
# Arquivos Python necessários: codigo.py e executar_experimentos.py.

set -Eeuo pipefail

diretorio_projeto="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
entrada_imagens="$diretorio_projeto/imagens"
saida_resultados="$diretorio_projeto/resultados"
quantidade_grupos="5"
tamanho_janela="21"
tamanho_imagem="512"
ajuste_imagem="corte"
modo_experimentos="nao"
saida_personalizada="nao"
limpar_resultados="nao"
limpar_ambiente="nao"
opcao_execucao_informada="nao"

mostrar_ajuda() {
    printf '%s\n' \
        "Uso: bash executar.sh [opções]" \
        "" \
        "Sem opções, processa ./imagens e grava em ./resultados." \
        "" \
        "Execução:" \
        "  --experimentos          Executa as combinações de K e janela" \
        "  --entrada CAMINHO       Usa outra imagem ou pasta de imagens" \
        "  --saida CAMINHO         Usa outra pasta de resultados" \
        "  --grupos NUMERO         Número de grupos do K-means (padrão: 5)" \
        "  --janela NUMERO         Tamanho ímpar da janela (padrão: 21)" \
        "  --tamanho NUMERO        Lado do recorte em pixels (padrão: 512)" \
        "  --ajuste MODO           corte, corte-ajustado ou redimensionar" \
        "" \
        "Limpeza:" \
        "  --limpar-resultados     Apaga resultados e resultados_*" \
        "  --limpar-ambiente       Apaga somente o ambiente virtual .venv" \
        "  --limpar-tudo           Apaga resultados, resultados_* e .venv" \
        "  -h, --help              Mostra esta ajuda" \
        "" \
        "Exemplos:" \
        "  bash executar.sh" \
        "  bash executar.sh --experimentos" \
        "  bash executar.sh --entrada /caminho/fotos --grupos 4" \
        "  bash executar.sh --limpar-resultados" \
        "  bash executar.sh --limpar-ambiente" \
        "  bash executar.sh --limpar-tudo"
}

falhar() {
    printf 'ERRO: %s\n' "$1" >&2
    exit 1
}

remover_diretorio_seguro() {
    local alvo="$1"

    case "$alvo" in
        "$diretorio_projeto/.venv"|"$diretorio_projeto/resultados"|"$diretorio_projeto"/resultados_*)
            ;;
        *)
            falhar "tentativa de apagar um caminho não permitido: $alvo"
            ;;
    esac

    if [[ -e "$alvo" || -L "$alvo" ]]; then
        rm -rf -- "$alvo"
        printf 'Removido: %s\n' "$alvo"
        return 0
    fi

    return 1
}

while (( $# > 0 )); do
    case "$1" in
        --experimentos)
            modo_experimentos="sim"
            opcao_execucao_informada="sim"
            shift
            ;;
        --entrada)
            (( $# >= 2 )) ||
                falhar "informe um caminho depois de --entrada"

            entrada_imagens="$2"
            opcao_execucao_informada="sim"
            shift 2
            ;;
        --saida)
            (( $# >= 2 )) ||
                falhar "informe um caminho depois de --saida"

            saida_resultados="$2"
            saida_personalizada="sim"
            opcao_execucao_informada="sim"
            shift 2
            ;;
        --grupos)
            (( $# >= 2 )) ||
                falhar "informe um número depois de --grupos"

            quantidade_grupos="$2"
            opcao_execucao_informada="sim"
            shift 2
            ;;
        --janela)
            (( $# >= 2 )) ||
                falhar "informe um número depois de --janela"

            tamanho_janela="$2"
            opcao_execucao_informada="sim"
            shift 2
            ;;
        --tamanho)
            (( $# >= 2 )) ||
                falhar "informe um número depois de --tamanho"

            tamanho_imagem="$2"
            opcao_execucao_informada="sim"
            shift 2
            ;;
        --ajuste)
            (( $# >= 2 )) ||
                falhar "informe um modo depois de --ajuste"

            ajuste_imagem="$2"
            opcao_execucao_informada="sim"
            shift 2
            ;;
        --limpar-resultados)
            limpar_resultados="sim"
            shift
            ;;
        --limpar-ambiente)
            limpar_ambiente="sim"
            shift
            ;;
        --limpar-tudo)
            limpar_resultados="sim"
            limpar_ambiente="sim"
            shift
            ;;
        -h|--help)
            mostrar_ajuda
            exit 0
            ;;
        *)
            falhar "opção desconhecida: $1 (use --help)"
            ;;
    esac
done

# As opções de limpeza apenas limpam e encerram o script.
if [[ "$limpar_resultados" == "sim" ||
      "$limpar_ambiente" == "sim" ]]; then

    if [[ "$opcao_execucao_informada" == "sim" ]]; then
        falhar "as opções de limpeza devem ser executadas separadamente"
    fi

    if [[ "$limpar_resultados" == "sim" ]]; then
        quantidade_removida=0

        for alvo in \
            "$diretorio_projeto/resultados" \
            "$diretorio_projeto"/resultados_*
        do
            if remover_diretorio_seguro "$alvo"; then
                quantidade_removida=$((quantidade_removida + 1))
            fi
        done

        if (( quantidade_removida == 0 )); then
            printf '%s\n' "Nenhuma pasta de resultados encontrada."
        fi
    fi

    if [[ "$limpar_ambiente" == "sim" ]]; then
        if ! remover_diretorio_seguro "$diretorio_projeto/.venv"; then
            printf '%s\n' "O ambiente virtual .venv não existe."
        fi
    fi

    printf '%s\n' "Limpeza concluída."
    exit 0
fi

command -v python3 >/dev/null 2>&1 ||
    falhar "Python 3 não foi encontrado"

python_ambiente="$diretorio_projeto/.venv/bin/python"

if [[ ! -x "$python_ambiente" ]]; then
    printf '%s\n' "[1/4] Criando o ambiente virtual .venv..."

    if ! python3 -m venv "$diretorio_projeto/.venv"; then
        falhar "não foi possível criar .venv. Instale python3-venv"
    fi
else
    printf '%s\n' "[1/4] Ambiente virtual já existe."
fi

printf '%s\n' \
    "[2/4] Conferindo OpenCV, NumPy e scikit-learn..."

if ! "$python_ambiente" \
    -c "import cv2, numpy, sklearn" \
    >/dev/null 2>&1
then
    printf '%s\n' "Instalando as dependências..."

    "$python_ambiente" -m pip install \
        "numpy>=1.24,<3" \
        "opencv-python>=4.8,<5" \
        "scikit-learn>=1.3,<2"
else
    printf '%s\n' "Dependências já instaladas."
fi

printf '%s\n' \
    "[3/4] Usando as fotografias de: $entrada_imagens"

[[ -e "$entrada_imagens" ]] ||
    falhar "caminho não encontrado: $entrada_imagens"

if [[ "$modo_experimentos" == "sim" ]]; then
    if [[ "$saida_personalizada" == "nao" ]]; then
        saida_resultados="$diretorio_projeto/resultados_experimentos"
    fi

    printf '%s\n' \
        "[4/4] Executando as combinações de K e janela..."

    "$python_ambiente" \
        "$diretorio_projeto/executar_experimentos.py" \
        --entrada "$entrada_imagens" \
        --saida "$saida_resultados" \
        --tamanho "$tamanho_imagem" \
        --ajuste "$ajuste_imagem"

    printf '\n%s\n' \
        "Experimentos concluídos. Abra: $saida_resultados"
else
    printf '%s\n' \
        "[4/4] Extraindo as 24 características e agrupando..."

    "$python_ambiente" "$diretorio_projeto/codigo.py" \
        --entrada "$entrada_imagens" \
        --saida "$saida_resultados" \
        --grupos "$quantidade_grupos" \
        --janela "$tamanho_janela" \
        --tamanho "$tamanho_imagem" \
        --ajuste "$ajuste_imagem"

    printf '\n%s\n' \
        "Tudo pronto. Abra os resultados em: $saida_resultados"
fi