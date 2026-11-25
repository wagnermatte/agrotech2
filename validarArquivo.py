# VALIDAR:
# - Se o arquivo é CSV
# - Se o arquivo não está vazio
# - Presença das colunas obrigatórias
# - Normalização e validação dos estados operacionais
# - Ordenação por horário
# - Ausência de linhas duplicadas
# - Mínimo de 60 intervalos registrados

import csv
import os
import math
import json
from datetime import datetime


mapaColunas = {
    "tempo": ["timestamps", "timestamp"],
    "estado": ["STATE", "operational_state"],
    "velocidade": ["CAN1.CCVS1.WheelBasedVehicleSpeed", "ground_speed"],
    "rpm": ["CAN1.EEC1.EngineSpeed", "engine_speed"],
}

colunasObrigatorias = ["tempo", "estado"]

mapaEstados = {
    "W": "Working",
    "WORKING": "Working",
    "T": "Turning",
    "TURNING": "Turning",
    "M": "Moving",
    "MOVING": "Moving",
    "I": "Idle",
    "IDLE": "Idle",
}

estadoDesconhecido = "desconhecido"
dtMaximoSeg = 5
minimoIntervalos = 60
formatoTempo = "%Y-%m-%d %H:%M:%S"
arquivoPadrao = "telemetria_168h.csv"


class AgroTechError(Exception):
    """Base para todos os erros previstos."""


class ArquivoInvalidoError(AgroTechError):
    """Arquivo ausente, com extensão errada, vazio ou ilegível."""


class ColunaObrigatoriaError(AgroTechError):
    """Falta uma coluna obrigatória."""


class DadosInsuficientesError(AgroTechError):
    """Quantidade insuficiente de registros válidos."""


def validar_arquivo(caminho):
    if not os.path.isfile(caminho):
        raise ArquivoInvalidoError(
            f"Arquivo não encontrado: {caminho}"
        )

    if not caminho.lower().endswith(".csv"):
        raise ArquivoInvalidoError(
            f"Formato inválido (esperado .csv): {caminho}"
        )

    if os.path.getsize(caminho) == 0:
        raise ArquivoInvalidoError(
            f"Arquivo vazio: {caminho}"
        )


# Ler CSV

def ler_csv(caminho):
    validar_arquivo(caminho)

    try:
        with open(
            caminho,
            "r",
            encoding="utf-8-sig",
            newline=""
        ) as arquivo:
            leitor = csv.DictReader(arquivo)

            if leitor.fieldnames is None:
                raise ArquivoInvalidoError(
                    "O CSV não possui cabeçalho."
                )

            registros = list(leitor)

            if not registros:
                raise DadosInsuficientesError(
                    "O CSV não contém registros."
                )

            return registros

    except AgroTechError:
        raise

    except (OSError, UnicodeDecodeError, csv.Error) as erro:
        raise ArquivoInvalidoError(
            f"Não foi possível ler o arquivo: {erro}"
        ) from erro


# identificar e validar colunas

def validar_colunas(registros):
    if not registros:
        raise DadosInsuficientesError(
            "Não existem dados para validar."
        )

    colunasArquivo = list(registros[0].keys())
    colunasEncontradas = {}

    for nomePadrao, alternativas in mapaColunas.items():
        for alternativa in alternativas:
            for colunaArquivo in colunasArquivo:
                if colunaArquivo is None:
                    continue

                if colunaArquivo.strip().lower() == alternativa.lower():
                    colunasEncontradas[nomePadrao] = colunaArquivo
                    break

            if nomePadrao in colunasEncontradas:
                break

    colunasAusentes = []

    for colunaObrigatoria in colunasObrigatorias:
        if colunaObrigatoria not in colunasEncontradas:
            colunasAusentes.append(colunaObrigatoria)

    if colunasAusentes:
        raise ColunaObrigatoriaError(
            "Colunas obrigatórias ausentes: " + ", ".join(colunasAusentes)
        )

    return colunasEncontradas


# normalizar os nomes das colunas

def normalizar_colunas(registros, colunasEncontradas):
    registrosNormalizados = []

    for registro in registros:
        novoRegistro = {}

        for nomePadrao, nomeOriginal in colunasEncontradas.items():
            novoRegistro[nomePadrao] = registro.get(nomeOriginal, "")

        registrosNormalizados.append(novoRegistro)

    return registrosNormalizados


# converter valores numericos

def converter_numero(valor):
    if valor is None:
        return None

    valor = valor.strip()

    if valor == "":
        return None

    try:
        return float(valor.replace(",", "."))
    except ValueError:
        return None


# validar e converter horários

def validar_timestamps(registros):
    registrosValidos = []

    for registro in registros:
        valorTempo = registro.get("tempo")

        if valorTempo is None:
            continue

        valorTempo = valorTempo.strip()

        try:
            tempoConvertido = datetime.strptime(
                valorTempo,
                formatoTempo
            )

            registro["tempo"] = tempoConvertido
            registrosValidos.append(registro)

        except (ValueError, TypeError):
            # Registros com horário inválido são descartados.
            continue

    if not registrosValidos:
        raise DadosInsuficientesError(
            "Nenhum registro possui um horário válido."
        )

    return registrosValidos


# traduzir e validar os estados/momentos

def normalizar_estados(registros):
    for registro in registros:
        valorEstado = registro.get("estado")

        if valorEstado is None:
            registro["estado"] = estadoDesconhecido
            continue

        estadoNormalizado = valorEstado.strip().upper()

        registro["estado"] = mapaEstados.get(
            estadoNormalizado,
            estadoDesconhecido
        )

    return registros


# normalizar velocidade

def normalizar_valores_numericos(registros):
    for registro in registros:
        if "velocidade" in registro:
            registro["velocidade"] = converter_numero(
                registro["velocidade"]
            )

        if "rpm" in registro:
            registro["rpm"] = converter_numero(
                registro["rpm"]
            )

    return registros


# remover linhas duplicadas

def remover_duplicatas(registros):
    registrosUnicos = []
    registrosVistos = set()

    for registro in registros:
        identificador = tuple(
            sorted(registro.items())
        )

        if identificador not in registrosVistos:
            registrosVistos.add(identificador)
            registrosUnicos.append(registro)

    if not registrosUnicos:
        raise DadosInsuficientesError(
            "Nenhum registro permaneceu após remover duplicidades."
        )

    return registrosUnicos


# ordenar os registros por horário

def ordenar_registros(registros):
    return sorted(
        registros,
        key=lambda registro: registro["tempo"]
    )


# caluclar e validar os intervalos

def validar_intervalos(registros):
    registrosComIntervalo = []

    for indice in range(1, len(registros)):
        registroAnterior = registros[indice - 1]
        registroAtual = registros[indice]

        diferenca = (
            registroAtual["tempo"]
            - registroAnterior["tempo"]
        )

        intervaloSegundos = diferenca.total_seconds()

        if 0 < intervaloSegundos <= dtMaximoSeg:
            novoRegistro = registroAtual.copy()
            novoRegistro["intervalo_segundos"] = intervaloSegundos

            registrosComIntervalo.append(novoRegistro)

    if not registrosComIntervalo:
        raise DadosInsuficientesError(
            "Nenhum intervalo de tempo válido foi encontrado."
        )

    return registrosComIntervalo


# validar a quantidade minima de intervalos

def validar_quantidade_intervalos(intervalos):
    quantidade = len(intervalos)

    if quantidade < minimoIntervalos:
        raise DadosInsuficientesError(
            f"Foram encontrados apenas {quantidade} intervalos válidos. "
            f"O mínimo necessário é {minimoIntervalos}."
        )


# calcular o percentual de permanência por estado

def calcular_permanencia_estados(intervalos):
    tempoPorEstado = {
        "Working": 0.0,
        "Turning": 0.0,
        "Moving": 0.0,
        "Idle": 0.0,
        estadoDesconhecido: 0.0,
    }

    for intervalo in intervalos:
        estado = intervalo["estado"]
        duracao = intervalo["intervalo_segundos"]
        tempoPorEstado[estado] += duracao

    tempoTotal = sum(tempoPorEstado.values())

    if tempoTotal <= 0:
        raise DadosInsuficientesError(
            "Não há tempo válido para calcular a permanência."
        )

    permanencia = {}

    for estado, segundos in tempoPorEstado.items():
        permanencia[estado] = {
            "segundos": segundos,
            "percentual": (segundos / tempoTotal) * 100,
        }

    return permanencia


# calcular mínimo e máximo dos valores numéricos válidos

def calcular_extremos(registros, coluna, estadosPermitidos=None):
    valores = []

    for registro in registros:
        if estadosPermitidos is not None:
            if registro.get("estado") not in estadosPermitidos:
                continue

        valor = registro.get(coluna)

        if valor is not None and math.isfinite(valor):
            valores.append(valor)

    if not valores:
        return {"minimo": None, "media": None, "maximo": None}

    return {
        "minimo": min(valores),
        "media": sum(valores) / len(valores),
        "maximo": max(valores),
    }


def calcular_metricas(registros, intervalos):
    velocidade = calcular_extremos(registros, "velocidade")

    velocidadeEmOperacao = calcular_extremos(
        registros,
        "velocidade",
        estadosPermitidos=["Working", "Turning", "Moving"]
    )

    velocidade["media"] = velocidadeEmOperacao["media"]

    return {
        "permanencia": calcular_permanencia_estados(intervalos),
        "rpm": calcular_extremos(registros, "rpm"),
        "velocidade": velocidade,
    }


def formatar_numero(valor):
    if valor is None:
        return "Sem dados válidos"

    return f"{valor:.2f}".replace(".", ",")


def exibir_metricas(metricas):
    nomesEstados = {
        "Working": "Trabalhando",
        "Turning": "Manobrando",
        "Moving": "Deslocando",
        "Idle": "Ocioso",
        estadoDesconhecido: "Desconhecido",
    }

    print("\nPERMANÊNCIA POR ESTADO")

    for estado, dados in metricas["permanencia"].items():
        print(
            f"{nomesEstados[estado]}: "
            f"{formatar_numero(dados['percentual'])}% "
            f"({formatar_numero(dados['segundos'])} segundos)"
        )

    print("\nROTAÇÃO DO MOTOR (RPM)")
    print(f"RPM médio: {formatar_numero(metricas['rpm']['media'])}")
    print(f"RPM máximo: {formatar_numero(metricas['rpm']['maximo'])}")

    print("\nVELOCIDADE (unidade original do CSV)")
    print(
        f"Velocidade média em operação: "
        f"{formatar_numero(metricas['velocidade']['media'])}"
    )
    print(
        f"Velocidade máxima: "
        f"{formatar_numero(metricas['velocidade']['maximo'])}"
    )


# processar arquivo completo

def processar_arquivo(caminho):
    registros = ler_csv(caminho)

    colunasEncontradas = validar_colunas(registros)

    registros = normalizar_colunas(
        registros,
        colunasEncontradas
    )

    registros = validar_timestamps(registros)
    registros = normalizar_estados(registros)
    registros = normalizar_valores_numericos(registros)
    registros = remover_duplicatas(registros)
    registros = ordenar_registros(registros)

    intervalos = validar_intervalos(registros)

    validar_quantidade_intervalos(intervalos)

    return {
        "intervalos": intervalos,
        "metricas": calcular_metricas(registros, intervalos),
    }


# ============================================================
# FUNÇÕES ADICIONADAS PARA A VERSÃO WEB (páginas /gerar-analise)
# ============================================================

pastaAnalises = "analises"
formatoCampoData = "%Y-%m-%dT%H:%M"

nomesEstados = {
    "Working": "Trabalhando",
    "Turning": "Manobrando",
    "Moving": "Deslocando",
    "Idle": "Ocioso",
    estadoDesconhecido: "Desconhecido",
}


# lê o arquivo e devolve os registros já limpos e ordenados
# (mesmos passos do processar_arquivo, antes do cálculo dos intervalos)

def preparar_registros(caminho):
    registros = ler_csv(caminho)
    colunasEncontradas = validar_colunas(registros)
    registros = normalizar_colunas(registros, colunasEncontradas)
    registros = validar_timestamps(registros)
    registros = normalizar_estados(registros)
    registros = normalizar_valores_numericos(registros)
    registros = remover_duplicatas(registros)
    registros = ordenar_registros(registros)
    return registros


# descobre o primeiro e o último horário do arquivo

def periodo_disponivel(caminho):
    registros = preparar_registros(caminho)
    return {
        "inicio": registros[0]["tempo"],
        "fim": registros[-1]["tempo"],
    }


# converte o texto do formulário (ex: 2026-11-01T07:00) em datetime

def converter_data_formulario(texto):
    try:
        return datetime.strptime(texto.strip(), formatoCampoData)
    except (ValueError, AttributeError):
        raise DadosInsuficientesError(
            f"Data inválida: {texto}. Use o formato dia/mês/ano e hora."
        )


# mantém apenas os registros dentro do período escolhido

def filtrar_por_periodo(registros, inicio, fim):
    if inicio >= fim:
        raise DadosInsuficientesError(
            "O início do período precisa ser antes do fim."
        )

    filtrados = []

    for registro in registros:
        if inicio <= registro["tempo"] <= fim:
            filtrados.append(registro)

    if not filtrados:
        raise DadosInsuficientesError(
            "Não existem registros no período escolhido."
        )

    return filtrados


# indicadores do documento do projeto (seção 4.1)

def calcular_indicadores(permanencia):
    return {
        "utilizacao_produtiva": permanencia["Working"]["percentual"],
        "taxa_parada": permanencia["Idle"]["percentual"],
    }


# soma o tempo em que a máquina ficou ociosa com o motor desligado (RPM 0)

def calcular_motor_desligado(intervalos):
    segundos = 0.0

    for intervalo in intervalos:
        if intervalo["estado"] == "Idle" and intervalo.get("rpm") == 0:
            segundos += intervalo["intervalo_segundos"]

    return segundos


# agrupa os intervalos por hora e guarda o estado que mais apareceu

def calcular_linha_do_tempo(intervalos):
    horas = {}

    for intervalo in intervalos:
        hora = intervalo["tempo"].strftime("%Y-%m-%d %H:00")

        if hora not in horas:
            horas[hora] = {}

        estado = intervalo["estado"]
        horas[hora][estado] = (
            horas[hora].get(estado, 0) + intervalo["intervalo_segundos"]
        )

    linha = []

    for hora, tempos in horas.items():
        estadoPredominante = max(tempos, key=tempos.get)
        linha.append({"hora": hora, "estado": estadoPredominante, "segundos": tempos})

    return linha


# organiza a linha do tempo em dias (linhas) e horas (colunas)

def linha_do_tempo_por_dia(linha):
    dias = {}

    for item in linha:
        dia, hora = item["hora"].split(" ")
        numeroHora = int(hora[:2])

        if dia not in dias:
            dias[dia] = [None] * 24

        dias[dia][numeroHora] = item["estado"]

    return dias


# processa só um período do arquivo

def processar_periodo(caminho, inicio, fim):
    registros = preparar_registros(caminho)
    registros = filtrar_por_periodo(registros, inicio, fim)

    intervalos = validar_intervalos(registros)
    validar_quantidade_intervalos(intervalos)

    metricas = calcular_metricas(registros, intervalos)

    return {
        "intervalos": intervalos,
        "metricas": metricas,
        "indicadores": calcular_indicadores(metricas["permanencia"]),
        "linha_do_tempo": calcular_linha_do_tempo(intervalos),
        "motor_desligado": calcular_motor_desligado(intervalos),
    }


# salva a análise em um arquivo .json dentro da pasta "analises"

def salvar_analise(nome, caminho, inicio, fim, resultado):
    os.makedirs(pastaAnalises, exist_ok=True)

    criadoEm = datetime.now()
    identificador = criadoEm.strftime("%Y%m%d-%H%M%S")

    analise = {
        "id": identificador,
        "nome": nome or "Análise sem nome",
        "arquivo": caminho,
        "inicio": inicio.strftime(formatoTempo),
        "fim": fim.strftime(formatoTempo),
        "criado_em": criadoEm.strftime(formatoTempo),
        "quantidade_intervalos": len(resultado["intervalos"]),
        "metricas": resultado["metricas"],
        "indicadores": resultado["indicadores"],
        "linha_do_tempo": resultado["linha_do_tempo"],
        "motor_desligado": resultado.get("motor_desligado"),
    }

    caminhoJson = os.path.join(pastaAnalises, identificador + ".json")

    with open(caminhoJson, "w", encoding="utf-8") as arquivo:
        json.dump(analise, arquivo, ensure_ascii=False, indent=2)

    return analise


# lista as análises salvas, da mais nova para a mais antiga

def listar_analises():
    if not os.path.isdir(pastaAnalises):
        return []

    analises = []

    for nomeArquivo in sorted(os.listdir(pastaAnalises), reverse=True):
        if nomeArquivo.endswith(".json"):
            identificador = nomeArquivo[:-5]
            analises.append(carregar_analise(identificador))

    return analises


# abre uma análise salva pelo identificador

def carregar_analise(identificador):
    # só aceita letras, números e "-" para não abrir arquivos de fora da pasta
    if not identificador.replace("-", "").isalnum():
        return None

    caminhoJson = os.path.join(pastaAnalises, identificador + ".json")

    if not os.path.isfile(caminhoJson):
        return None

    with open(caminhoJson, "r", encoding="utf-8") as arquivo:
        return json.load(arquivo)


# gera o PDF de uma análise salva (usa a biblioteca fpdf2)

def gerar_pdf(analise):
    from fpdf import FPDF

    coresEstados = {
        "Working": (46, 125, 79),
        "Turning": (217, 162, 27),
        "Moving": (52, 102, 168),
        "Idle": (163, 172, 165),
        estadoDesconhecido: (181, 71, 58),
    }

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(True, margin=15)

    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, "AgroTech - Relatório de análise", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, analise["nome"], new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, f"Período: {analise['inicio']} até {analise['fim']}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, f"Arquivo: {analise['arquivo']}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, f"Gerado em: {analise['criado_em']}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, f"Intervalos válidos: {analise['quantidade_intervalos']}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    metricas = analise["metricas"]
    indicadores = analise["indicadores"]

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Indicadores", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, f"Utilização produtiva: {formatar_numero(indicadores['utilizacao_produtiva'])}%", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, f"Taxa de parada: {formatar_numero(indicadores['taxa_parada'])}%", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Permanência por estado", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)

    for estado, dados in metricas["permanencia"].items():
        horas = dados["segundos"] / 3600
        cor = coresEstados[estado]
        larguraBarra = dados["percentual"] * 0.8

        pdf.cell(40, 7, nomesEstados[estado])
        pdf.cell(45, 7, f"{formatar_numero(dados['percentual'])}% ({formatar_numero(horas)} h)")

        if larguraBarra > 0:
            pdf.set_fill_color(*cor)
            pdf.rect(pdf.get_x(), pdf.get_y() + 1.5, larguraBarra, 4, style="F")

        pdf.ln(7)

    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Rotação do motor (RPM)", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, f"RPM médio: {formatar_numero(metricas['rpm']['media'])}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, f"RPM máximo: {formatar_numero(metricas['rpm']['maximo'])}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Velocidade (unidade original do CSV)", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, f"Velocidade média em operação: {formatar_numero(metricas['velocidade']['media'])}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, f"Velocidade máxima: {formatar_numero(metricas['velocidade']['maximo'])}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Estado predominante por hora", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 8)

    dias = linha_do_tempo_por_dia(analise["linha_do_tempo"])
    larguraHora = 6

    for dia, horas in dias.items():
        pdf.cell(22, 5, dia)
        x = pdf.get_x()
        y = pdf.get_y()

        for numeroHora, estado in enumerate(horas):
            if estado is not None:
                pdf.set_fill_color(*coresEstados[estado])
                pdf.rect(x + numeroHora * larguraHora, y + 0.5, larguraHora - 0.6, 4, style="F")

        pdf.ln(5)

    pdf.ln(3)
    pdf.cell(0, 5, "Cores: verde = Trabalhando, amarelo = Manobrando, azul = Deslocando, cinza = Ocioso, vermelho = Desconhecido")

    return bytes(pdf.output())


# main do programa

if __name__ == "__main__":
    try:
        resultado = processar_arquivo(arquivoPadrao)
        intervalos = resultado["intervalos"]

        print("Arquivo processado com sucesso.")
        print(f"Quantidade de intervalos válidos: {len(intervalos)}")

        exibir_metricas(resultado["metricas"])

    except AgroTechError as erro:
        print(f"Erro: {erro}")