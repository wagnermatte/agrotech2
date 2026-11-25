# Interface gráfica simples para o AgroTech
# Usa o tkinter, que já vem junto com o Python (não precisa instalar nada).
# Para abrir: python3 interface.py

import tkinter as tk
from tkinter import filedialog

from validarArquivo import (
    processar_arquivo,
    formatar_numero,
    AgroTechError,
    arquivoPadrao,
)


nomesEstados = {
    "Working": "Trabalhando",
    "Turning": "Manobrando",
    "Moving": "Deslocando",
    "Idle": "Ocioso",
    "desconhecido": "Desconhecido",
}


# abre a janela para escolher o arquivo CSV

def escolher_arquivo():
    caminho = filedialog.askopenfilename(
        title="Escolha o arquivo CSV",
        filetypes=[("Arquivos CSV", "*.csv"), ("Todos os arquivos", "*.*")]
    )

    if caminho:
        campoArquivo.delete(0, tk.END)
        campoArquivo.insert(0, caminho)


# escreve uma linha na caixa de resultado

def escrever(texto):
    caixaResultado.insert(tk.END, texto + "\n")


# chama as funções do validarArquivo.py e mostra o resultado

def processar():
    caixaResultado.delete("1.0", tk.END)

    caminho = campoArquivo.get().strip()

    if caminho == "":
        escrever("Erro: informe o caminho do arquivo.")
        return

    escrever("Processando, aguarde...")
    janela.update()

    try:
        resultado = processar_arquivo(caminho)
    except AgroTechError as erro:
        caixaResultado.delete("1.0", tk.END)
        escrever(f"Erro: {erro}")
        return

    caixaResultado.delete("1.0", tk.END)

    intervalos = resultado["intervalos"]
    metricas = resultado["metricas"]

    escrever("Arquivo processado com sucesso.")
    escrever(f"Quantidade de intervalos válidos: {len(intervalos)}")

    escrever("")
    escrever("PERMANÊNCIA POR ESTADO")

    for estado, dados in metricas["permanencia"].items():
        escrever(
            f"{nomesEstados[estado]}: "
            f"{formatar_numero(dados['percentual'])}% "
            f"({formatar_numero(dados['segundos'])} segundos)"
        )

    escrever("")
    escrever("ROTAÇÃO DO MOTOR (RPM)")
    escrever(f"RPM médio: {formatar_numero(metricas['rpm']['media'])}")
    escrever(f"RPM máximo: {formatar_numero(metricas['rpm']['maximo'])}")

    escrever("")
    escrever("VELOCIDADE (unidade original do CSV)")
    escrever(
        f"Velocidade média em operação: "
        f"{formatar_numero(metricas['velocidade']['media'])}"
    )
    escrever(
        f"Velocidade máxima: "
        f"{formatar_numero(metricas['velocidade']['maximo'])}"
    )


# montagem da janela

janela = tk.Tk()
janela.title("AgroTech - Telemetria")
janela.geometry("600x500")

titulo = tk.Label(janela, text="AgroTech - Análise de Telemetria", font=("Arial", 16))
titulo.pack(pady=10)

textoArquivo = tk.Label(janela, text="Arquivo CSV:")
textoArquivo.pack()

campoArquivo = tk.Entry(janela, width=60)
campoArquivo.insert(0, arquivoPadrao)
campoArquivo.pack(pady=5)

botaoEscolher = tk.Button(janela, text="Escolher arquivo", command=escolher_arquivo)
botaoEscolher.pack(pady=5)

botaoProcessar = tk.Button(janela, text="Processar", command=processar)
botaoProcessar.pack(pady=5)

caixaResultado = tk.Text(janela, width=70, height=18)
caixaResultado.pack(pady=10)

janela.mainloop()
