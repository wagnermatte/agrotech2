# Servidor web do AgroTech (Flask)
# Para rodar: .venv/bin/python app.py  e abrir http://127.0.0.1:5001

import inspect
import json
import os
import textwrap
from datetime import datetime, timedelta

from flask import Flask, render_template, request, redirect, url_for, abort, Response

import validarArquivo as va


app = Flask(__name__)

arquivoDados = va.arquivoPadrao

# guarda resultados que demoram para calcular (o CSV de 168h tem 600 mil linhas)
memoria = {}

# datetime.weekday(): 0 = segunda-feira
diasSemana = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]


# ---------- funções de apresentação (só formatam, não calculam indicadores) ----------

# organiza a linha do tempo em dias x 24 horas, com os segundos de cada estado
# (análises salvas antes desta versão não têm "segundos": a grade continua funcionando)

def grade_detalhada(linha):
    dias = {}

    for item in linha:
        dia, hora = item["hora"].split(" ")

        if dia not in dias:
            dias[dia] = [None] * 24

        segundos = item.get("segundos") or {}
        dias[dia][int(hora[:2])] = {
            "estado": item["estado"],
            "segundos": segundos,
        }

    grade = []

    for dia, horas in dias.items():
        data = datetime.strptime(dia, "%Y-%m-%d")
        grade.append({
            "dia": dia,
            "rotulo": data.strftime("%d/%m"),
            "semana": diasSemana[data.weekday()],
            "inicio": data.strftime(va.formatoCampoData),
            "fim": (data + timedelta(days=1)).strftime(va.formatoCampoData),
            "horas": horas,
        })

    return grade


# lista os dias que existem no arquivo, para os atalhos do formulário

def dias_do_periodo(disponivel):
    dia = disponivel["inicio"].replace(hour=0, minute=0, second=0)
    dias = []

    while dia < disponivel["fim"]:
        dias.append({
            "inicio": dia.strftime(va.formatoCampoData),
            "semana": diasSemana[dia.weekday()],
            "numero": dia.strftime("%d"),
        })
        dia += timedelta(days=1)

    return dias


@app.template_filter("horas")
def filtro_horas(segundos):
    return va.formatar_numero((segundos or 0) / 3600)


@app.template_filter("milhar")
def filtro_milhar(valor):
    return "{:,}".format(int(valor)).replace(",", ".")


@app.template_filter("curta")
def filtro_curta(texto):
    # "2026-11-03 07:00:00" vira "03/11 07:00"
    return f"{texto[8:10]}/{texto[5:7]} {texto[11:16]}"


@app.context_processor
def variaveis_globais():
    return {
        "nomes": va.nomesEstados,
        "estados": list(va.nomesEstados.keys()),
        "numero": va.formatar_numero,
        "arquivo": arquivoDados,
    }


# ---------- dados usados por mais de uma página ----------

def resumo_semana():
    if "semana" not in memoria:
        resultado = va.processar_arquivo(arquivoDados)
        intervalos = resultado["intervalos"]
        memoria["semana"] = {
            "grade": grade_detalhada(va.calcular_linha_do_tempo(intervalos)),
            "metricas": resultado["metricas"],
            "indicadores": va.calcular_indicadores(resultado["metricas"]["permanencia"]),
            "quantidade_intervalos": len(intervalos),
            "motor_desligado": va.calcular_motor_desligado(intervalos),
        }
    return memoria["semana"]


def periodo():
    if "periodo" not in memoria:
        memoria["periodo"] = va.periodo_disponivel(arquivoDados)
    return memoria["periodo"]


# pega o código-fonte das funções para mostrar na página
def codigo(funcao):
    return inspect.getsource(funcao).strip()


# mostra como a análise mais recente está gravada no disco
# (a linha do tempo é cortada em 2 horas para caber na página)
def exemplo_analise():
    analises = va.listar_analises()
    if not analises:
        return None

    analise = dict(analises[0])
    horas = len(analise.get("linha_do_tempo", []))
    analise["linha_do_tempo"] = analise.get("linha_do_tempo", [])[:2]

    return {
        "id": analise["id"],
        "texto": json.dumps(analise, ensure_ascii=False, indent=2),
        "horas": horas,
        "tamanho": os.path.getsize(os.path.join(va.pastaAnalises, analise["id"] + ".json")),
        "quantidade": len(analises),
    }


# recorta um pedaço de um arquivo, entre dois textos
def trecho(nomeArquivo, comeco, fim):
    with open(nomeArquivo, encoding="utf-8") as arquivo:
        texto = arquivo.read()
    posicaoInicio = texto.index(comeco)
    posicaoFim = texto.index(fim, posicaoInicio)
    return textwrap.dedent(texto[posicaoInicio:posicaoFim]).rstrip()


# ---------- páginas ----------

@app.route("/")
def inicio():
    return render_template(
        "home.html",
        semana=resumo_semana(),
        disponivel=periodo(),
        analises=va.listar_analises()[:3],
    )


@app.route("/como-funciona")
def como_funciona():
    codigos = {
        "mapas": trecho("validarArquivo.py", "mapaColunas = {", "estadoDesconhecido ="),
        "constantes": trecho("validarArquivo.py", "estadoDesconhecido =", "arquivoPadrao ="),
        "processar_arquivo": codigo(va.processar_arquivo),
        "ler_csv": codigo(va.ler_csv),
        "validar_colunas": codigo(va.validar_colunas),
        "validar_timestamps": codigo(va.validar_timestamps),
        "normalizar_estados": codigo(va.normalizar_estados),
        "converter_numero": codigo(va.converter_numero),
        "remover_duplicatas": codigo(va.remover_duplicatas),
        "validar_intervalos": codigo(va.validar_intervalos),
        "validar_quantidade_intervalos": codigo(va.validar_quantidade_intervalos),
        "calcular_permanencia_estados": codigo(va.calcular_permanencia_estados),
        "calcular_metricas": codigo(va.calcular_metricas),
        "erros": codigo(va.AgroTechError) + "\n\n\n" + codigo(va.ArquivoInvalidoError)
                 + "\n\n\n" + codigo(va.ColunaObrigatoriaError) + "\n\n\n" + codigo(va.DadosInsuficientesError),
        "processar_periodo": codigo(va.processar_periodo),
        "calcular_linha_do_tempo": codigo(va.calcular_linha_do_tempo),
        "salvar_analise": codigo(va.salvar_analise),
        "carregar_analise": codigo(va.listar_analises) + "\n\n\n" + codigo(va.carregar_analise),
        "gerador": trecho("telemetriaCriar.py", "        # Operação simulada", "        escritor.writerow"),
    }

    return render_template(
        "como_funciona.html",
        semana=resumo_semana(),
        codigos=codigos,
        constantes={
            "dtMaximoSeg": va.dtMaximoSeg,
            "minimoIntervalos": va.minimoIntervalos,
        },
        exemplo=exemplo_analise(),
        pastaAnalises=va.pastaAnalises,
    )


@app.route("/gerar-analise", methods=["GET", "POST"])
def gerar_analise():
    erro = None
    erroTipo = None
    disponivel = periodo()

    # links como "Analisar 03/11" no quadro da semana já chegam com o período preenchido
    campos = {
        "nome": request.args.get("nome", ""),
        "inicio": request.args.get("inicio") or disponivel["inicio"].strftime(va.formatoCampoData),
        "fim": request.args.get("fim") or disponivel["fim"].strftime(va.formatoCampoData),
    }

    if request.method == "POST":
        campos["nome"] = request.form.get("nome", "").strip()
        campos["inicio"] = request.form.get("inicio", "")
        campos["fim"] = request.form.get("fim", "")

        try:
            inicioPeriodo = va.converter_data_formulario(campos["inicio"])
            fimPeriodo = va.converter_data_formulario(campos["fim"])
            resultado = va.processar_periodo(arquivoDados, inicioPeriodo, fimPeriodo)
            analise = va.salvar_analise(campos["nome"], arquivoDados, inicioPeriodo, fimPeriodo, resultado)
            return redirect(url_for("ver_analise", identificador=analise["id"]))
        except va.AgroTechError as e:
            erro = str(e)
            erroTipo = type(e).__name__

    return render_template(
        "gerar_analise.html",
        erro=erro,
        erro_tipo=erroTipo,
        campos=campos,
        disponivel=disponivel,
        dias=dias_do_periodo(disponivel),
        formato=va.formatoCampoData,
        analises=va.listar_analises(),
    )


@app.route("/analise/<identificador>")
def ver_analise(identificador):
    analise = va.carregar_analise(identificador)
    if analise is None:
        abort(404)

    return render_template(
        "analise.html",
        analise=analise,
        dias=grade_detalhada(analise["linha_do_tempo"]),
    )


@app.route("/analise/<identificador>/pdf")
def baixar_pdf(identificador):
    analise = va.carregar_analise(identificador)
    if analise is None:
        abort(404)

    return Response(
        va.gerar_pdf(analise),
        mimetype="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=analise-{identificador}.pdf"},
    )


if __name__ == "__main__":
    # porta 5001 porque no macOS a 5000 é usada pelo Receptor AirPlay
    app.run(debug=True, port=5001)
