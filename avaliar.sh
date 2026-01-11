#!/usr/bin/env bash

STATISTICS_PATH='runs/stats/'
STATISTICS='statistics.csv'
CAMINHO_GRAFO='dataset/grafo.json'
CAMINHO_VEICULOS='dataset/veiculos.json'
CAMINHO_PEDIDOS='dataset/pedidos.json'
CAMINHO_EVENTOS_TRANSITO='dataset/eventos_transito.json'
PYTHON=python
VENV=venv
SRC=src

ALGO_NAV=("bfs" "dfs" "ucs")
ALGO_ALOCACAO=("heuristico" "simples")

numReps=$1
dinamico=$2

echo -e "A remover ficheiro antigo de estatísticas..."
cd "$STATISTICS_PATH" || exit
rm -rf "$STATISTICS"
cd - > /dev/null
echo -e "Ficheiro antigo de estatísticas removido"
echo -e "A executar testes..."

make test

echo -e "Testes concluídos"
echo -e "A executar a comparação..."
cd "$STATISTICS_PATH" || exit
touch $STATISTICS
cd - > /dev/null

count=1
while [ $count -le "$numReps" ]; do
  for i in "${ALGO_NAV[@]}"; do
    for j in "${ALGO_ALOCACAO[@]}"; do
      $PYTHON "$SRC/main.py" "$CAMINHO_GRAFO" "$CAMINHO_VEICULOS" "$CAMINHO_PEDIDOS" "$i" "$j" "$SPEED" --no-display
    done
  done
  ((count++))
done

echo -e "Comparação concluída"
echo -e "Resultados: "

RED="\033[1;31m"
GREEN="\033[1;32m"
CYAN="\033[1;36m"
YELLOW="\033[1;33m"
RESET="\033[0m"

cd "$STATISTICS_PATH" || exit
awk -F, -v OFS=',' -v RED="$RED" -v GREEN="$GREEN" -v CYAN="$CYAN" -v YELLOW="$YELLOW" -v RESET="$RESET" '
NR==1 {
    for(i=1;i<=NF;i++) header[i]=$i
    next
}
{
    key=$2 "|" $3
    count[key]++
    for(i=1;i<=NF;i++){
        if($i ~ /^[0-9.+-eE]+$/){
            sum[key,i]+=$i
        } else {
            val[key,i]=$i
        }
    }
}
END {
    # Print header
    for(i=1;i<=NF;i++){
        if(i==2) printf "%s%s%s", CYAN, "ALGORITMO de NAVEGAÇÃO", RESET
        else if(i==3) printf "%s%s%s", YELLOW, "ALGORITMO de ALOCAÇÃO", RESET
        else printf "%s", header[i]
        if(i<NF) printf " | "
    }
    print ""
    print "---------------------------------------------------------------"

    # Print averaged rows
    for(k in count){
        split(k, arr, "|")
        for(i=1;i<=NF;i++){
            if(i==2) printf "%s%s%s", RED, arr[1], RESET
            else if(i==3) printf "%s%s%s", GREEN, arr[2], RESET
            else if(sum[k,i]){
                avg = sum[k,i]/count[k]
                printf "%.2f", avg
            } else {
                printf "%s", val[k,i]
            }
            if(i<NF) printf " | "
        }
        print ""
    }
}' "$STATISTICS" | column -s '|' -t

cd - > /dev/null