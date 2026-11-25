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