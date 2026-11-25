import csv
import random
from datetime import datetime, timedelta


# Configurações
maquina = "MAQ001"
dataInicial = datetime(2026, 11, 1, 0, 0, 0)
horasMonitoramento = 168
arquivoSaida = "telemetria_168h.csv"

# Deixa a simulação reproduzível.
random.seed(42)

quantidadeSegundos = horasMonitoramento * 60 * 60

with open(
    arquivoSaida,
    "w",
    encoding="utf-8-sig",
    newline=""
) as arquivo:

    escritor = csv.DictWriter(
        arquivo,
        fieldnames=[
            "machine_id",
            "timestamp",
            "operational_state",
            "ground_speed",
            "engine_speed",
        ]
    )

    escritor.writeheader()

    # Inclui o ponto final para representar 168 horas entre medições.
    for segundo in range(quantidadeSegundos + 1):
        horario = dataInicial + timedelta(seconds=segundo)

        # Operação simulada das 07h às 18h.
        if 7 <= horario.hour < 18:
            # Ciclo de 10 minutos:
            # 7 minutos trabalhando;
            # 1 minuto manobrando;
            # 1 minuto deslocando;
            # 1 minuto ocioso.
            posicaoCiclo = segundo % 600

            if posicaoCiclo < 420:
                estado = "W"
                velocidade = random.uniform(5, 9)
                rpm = random.uniform(1700, 2100)

            elif posicaoCiclo < 480:
                estado = "T"
                velocidade = random.uniform(2, 4)
                rpm = random.uniform(1200, 1600)

            elif posicaoCiclo < 540:
                estado = "M"
                velocidade = random.uniform(10, 20)
                rpm = random.uniform(1400, 2000)

            else:
                estado = "I"
                velocidade = 0
                rpm = random.uniform(800, 900)

        else:
            # Motor desligado, sem deslocamento.
            # Como o modelo atual não possui estado "Off",
            # estes períodos também recebem "I".
            estado = "I"
            velocidade = 0
            rpm = 0

        escritor.writerow({
            "machine_id": maquina,
            "timestamp": horario.strftime("%Y-%m-%d %H:%M:%S"),
            "operational_state": estado,
            "ground_speed": round(velocidade, 2),
            "engine_speed": round(rpm, 1),
        })

print(f"CSV criado: {arquivoSaida}")
print(f"Medições: {quantidadeSegundos + 1}")
print(f"Início: {dataInicial}")
print(
    "Fim:",
    dataInicial + timedelta(hours=horasMonitoramento)
)