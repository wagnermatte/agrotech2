# Servidor web do AgroTech (Flask)
# Para rodar: .venv/bin/python app.py  e abrir http://127.0.0.1:5001

import inspect
import textwrap

from flask import Flask, render_template, request, redirect, url_for, abort, Response

import validarArquivo as va


app = Flask(__name__)

arquivoDados = va.arquivoPadrao

# guarda resultados que demoram para calcular (o CSV de 168h tem 600 mil linhas)
memoria = {}


def resumo_semana():
    if "semana" not in memoria:
        resultado = va.processar_arquivo(arquivoDados)
        intervalos = resultado["intervalos"]
        memoria["semana"] = {
            "dias": va.linha_do_tempo_por_dia(va.calcular_linha_do_tempo(intervalos)),
            "metricas": resultado["metricas"],
            "indicadores": va.calcular_indicadores(resultado["metricas"]["permanencia"]),
            "quantidade_intervalos": len(intervalos),
        }
    return memoria["semana"]


def periodo():
    if "periodo" not in memoria:
        memoria["periodo"] = va.periodo_disponivel(arquivoDados)
    return memoria["periodo"]


# pega o código-fonte das funções para mostrar na página
def codigo(funcao):
    return inspect.getsource(funcao).strip()


# recorta um pedaço de um arquivo, entre dois textos
def trecho(nomeArquivo, comeco, fim):
    with open(nomeArquivo, encoding="utf-8") as arquivo:
        texto = arquivo.read()
    posicaoInicio = texto.index(comeco)
    posicaoFim = texto.index(fim, posicaoInicio)
    return textwrap.dedent(texto[posicaoInicio:posicaoFim]).rstrip()


@app.route("/")
def inicio():
    return render_template(
        "home.html",
        semana=resumo_semana(),
        nomes=va.nomesEstados,
        numero=va.formatar_numero,
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
        "gerador": trecho("telemetriaCriar.py", "        # Operação simulada", "        escritor.writerow"),
    }

    return render_template(
        "como_funciona.html",
        semana=resumo_semana(),
        codigos=codigos,
        nomes=va.nomesEstados,
        numero=va.formatar_numero,
        constantes={
            "dtMaximoSeg": va.dtMaximoSeg,
            "minimoIntervalos": va.minimoIntervalos,
        },
    )


@app.route("/gerar-analise", methods=["GET", "POST"])
def gerar_analise():
    erro = None
    disponivel = periodo()
    campos = {
        "nome": "",
        "inicio": disponivel["inicio"].strftime(va.formatoCampoData),
        "fim": disponivel["fim"].strftime(va.formatoCampoData),
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

    return render_template(
        "gerar_analise.html",
        erro=erro,
        campos=campos,
        disponivel=disponivel,
        arquivo=arquivoDados,
        analises=va.listar_analises(),
        numero=va.formatar_numero,
    )


@app.route("/analise/<identificador>")
def ver_analise(identificador):
    analise = va.carregar_analise(identificador)
    if analise is None:
        abort(404)

    return render_template(
        "analise.html",
        analise=analise,
        dias=va.linha_do_tempo_por_dia(analise["linha_do_tempo"]),
        nomes=va.nomesEstados,
        numero=va.formatar_numero,
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
