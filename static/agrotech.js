// Interações do site AgroTech. JavaScript puro, sem bibliotecas.
// Tudo é melhoria progressiva: sem JS, as páginas continuam funcionando.

(function () {
  "use strict";

  var nomes = {
    Working: "Trabalhando", Turning: "Manobrando", Moving: "Deslocando",
    Idle: "Ocioso", desconhecido: "Desconhecido", vazio: "Sem dados"
  };
  var ordem = ["Working", "Turning", "Moving", "Idle", "desconhecido"];

  function dois(n) { return String(n).padStart(2, "0"); }
  function tempo(seg) { return seg >= 60 ? Math.round(seg / 60) + " min" : Math.round(seg) + " s"; }

  // ---------- menu no celular ----------
  var topo = document.querySelector(".topo");
  var botaoMenu = document.querySelector(".menu-botao");
  if (botaoMenu) {
    botaoMenu.addEventListener("click", function () {
      var aberto = topo.classList.toggle("aberto");
      botaoMenu.setAttribute("aria-expanded", aberto);
      botaoMenu.querySelector(".menu-rotulo").textContent = aberto ? "Fechar" : "Menu";
    });
  }

  // ---------- grade da semana: dica ao passar o mouse ----------
  var dica = document.createElement("div");
  dica.className = "dica";
  dica.setAttribute("role", "tooltip");
  dica.hidden = true;
  document.body.appendChild(dica);

  function linha(classe, texto, valor) {
    var s = document.createElement("span");
    s.className = "dica-linha";
    var i = document.createElement("i"); i.className = classe;
    var b = document.createElement("b"); b.textContent = valor;
    s.append(i, texto, b);
    return s;
  }

  function mostrarDica(td) {
    var estado = td.dataset.estado;
    var segundos = {};
    try { segundos = JSON.parse(td.dataset.segundos || "{}"); } catch (e) { segundos = {}; }
    var total = Object.values(segundos).reduce(function (a, b) { return a + b; }, 0);

    dica.replaceChildren();
    var quando = document.createElement("span");
    quando.className = "dica-quando";
    quando.textContent = td.dataset.quando;
    var titulo = document.createElement("strong");
    titulo.className = "dica-estado";
    var cor = document.createElement("i"); cor.className = estado;
    titulo.append(cor, nomes[estado] || estado);
    dica.append(quando, titulo);

    ordem.forEach(function (k) {
      if (segundos[k] > 0) dica.append(linha(k, nomes[k], tempo(segundos[k])));
    });
    if (total > 0 && total < 3540) {
      var nota = document.createElement("span");
      nota.className = "dica-nota";
      nota.textContent = "Hora parcial: " + tempo(total) + " de registro.";
      dica.append(nota);
    }

    dica.hidden = false;
    var r = td.getBoundingClientRect();
    var w = dica.offsetWidth, h = dica.offsetHeight;
    var x = Math.max(8, Math.min(r.left + r.width / 2 - w / 2, window.innerWidth - w - 8));
    var y = r.top - h - 10;
    if (y < 72) y = r.bottom + 10;
    dica.style.left = x + window.scrollX + "px";
    dica.style.top = y + window.scrollY + "px";
  }
  function esconderDica() { dica.hidden = true; }

  document.querySelectorAll("[data-grade] td").forEach(function (td) {
    td.removeAttribute("title"); // a dica substitui o title nativo
    td.addEventListener("mouseenter", function () { mostrarDica(td); });
    td.addEventListener("focus", function () { mostrarDica(td); });
    td.addEventListener("mouseleave", esconderDica);
    td.addEventListener("blur", esconderDica);
  });
  window.addEventListener("scroll", esconderDica, { passive: true });

  // ---------- legenda: destaca um estado ----------
  document.querySelectorAll("[data-legenda]").forEach(function (legenda) {
    var grade = legenda.previousElementSibling;
    var fixo = null;
    var botoes = legenda.querySelectorAll("button");
    function aplicar(filtro) {
      grade.querySelectorAll("td").forEach(function (td) {
        td.classList.toggle("apagado", !!filtro && td.dataset.estado !== filtro);
      });
    }
    botoes.forEach(function (b) {
      b.addEventListener("mouseenter", function () { if (!fixo) aplicar(b.dataset.filtro); });
      b.addEventListener("mouseleave", function () { if (!fixo) aplicar(null); });
      b.addEventListener("click", function () {
        fixo = fixo === b.dataset.filtro ? null : b.dataset.filtro;
        botoes.forEach(function (x) { x.setAttribute("aria-pressed", x.dataset.filtro === fixo); });
        aplicar(fixo);
      });
    });
  });

  // ---------- código: recolher blocos longos ----------
  var limiteLinhas = 16;
  document.querySelectorAll("[data-codigo]").forEach(function (bloco) {
    var linhas = 0;
    bloco.querySelectorAll("pre code").forEach(function (c) { linhas += c.textContent.split("\n").length; });
    if (linhas <= limiteLinhas + 4) return;
    bloco.classList.add("recolhido");
    var botao = document.createElement("button");
    botao.type = "button";
    botao.className = "codigo-mais";
    botao.setAttribute("aria-expanded", "false");
    var resto = linhas - limiteLinhas;
    botao.textContent = "↓ Mostrar as outras " + resto + " linhas";
    botao.addEventListener("click", function () {
      var recolhido = bloco.classList.toggle("recolhido");
      botao.setAttribute("aria-expanded", !recolhido);
      botao.textContent = recolhido ? "↓ Mostrar as outras " + resto + " linhas" : "↑ Recolher o código";
    });
    bloco.append(botao);
  });

  // ---------- índice dos passos acompanha a rolagem ----------
  var linksPasso = document.querySelectorAll(".indice-passos a.passo-link");
  if (linksPasso.length && "IntersectionObserver" in window) {
    var porId = {};
    linksPasso.forEach(function (a) { porId[a.getAttribute("href").slice(1)] = a; });
    var observador = new IntersectionObserver(function (entradas) {
      entradas.forEach(function (e) {
        if (!e.isIntersecting) return;
        linksPasso.forEach(function (a) { a.classList.remove("atual"); });
        var link = porId[e.target.id];
        if (link) link.classList.add("atual");
      });
    }, { rootMargin: "-90px 0px -65% 0px" });
    document.querySelectorAll(".passo[id]").forEach(function (p) { observador.observe(p); });
  }

  // ---------- copiar comandos ----------
  document.querySelectorAll("[data-copiar]").forEach(function (botao) {
    botao.addEventListener("click", function () {
      var texto = document.getElementById(botao.dataset.copiar).textContent.replace(/^\$ /gm, "");
      if (navigator.clipboard) navigator.clipboard.writeText(texto);
      botao.textContent = "Copiado";
      setTimeout(function () { botao.textContent = "Copiar"; }, 1600);
    });
  });

  // ---------- formulário de análise ----------
  var form = document.querySelector("[data-form-analise]");
  if (!form) return;

  function ler(v) {
    var m = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/.exec(v || "");
    return m ? new Date(+m[1], m[2] - 1, +m[3], +m[4], +m[5]) : null;
  }
  function escrever(d) {
    return d.getFullYear() + "-" + dois(d.getMonth() + 1) + "-" + dois(d.getDate()) + "T" + dois(d.getHours()) + ":" + dois(d.getMinutes());
  }
  function curta(d) { return dois(d.getDate()) + "/" + dois(d.getMonth() + 1) + " " + dois(d.getHours()) + ":" + dois(d.getMinutes()); }
  function numero(v, casas) { return v.toFixed(casas).replace(".", ","); }
  function duracao(ms) {
    var h = ms / 3600000;
    if (h >= 24 && h % 24 === 0) return h / 24 + (h === 24 ? " dia" : " dias") + " (" + h + " h)";
    if (h >= 1) return numero(h, h % 1 ? 1 : 0) + " h";
    return Math.round(ms / 60000) + " min";
  }

  var campoNome = form.elements.nome, campoInicio = form.elements.inicio, campoFim = form.elements.fim;
  var minimo = ler(form.dataset.min), maximo = ler(form.dataset.max);
  var chips = form.querySelectorAll("[data-preset]");
  var caixaDias = form.querySelector("[data-dias]");
  var botoesDia = form.querySelectorAll("[data-dia]");
  var selecao = form.querySelector("[data-selecao]");
  var saidaDuracao = form.querySelector("[data-duracao]");
  var saidaPeriodo = form.querySelector("[data-periodo]");
  var resumo = form.querySelector("[data-resumo]");
  var erroCliente = form.querySelector("[data-erro-cliente]");
  var erroServidor = form.querySelector("[data-erro-servidor]");
  var botaoEnviar = form.querySelector("[type=submit]");
  var etapas = form.querySelector("[data-etapas]");
  var sugestaoTexto = form.querySelector("[data-sugestao]");

  var preset = "livre";
  var diaEscolhido = botoesDia.length ? botoesDia[0].dataset.dia : null;

  function aplicar(novo, dia) {
    preset = novo;
    if (dia) diaEscolhido = dia;
    var base = ler(diaEscolhido);
    if (preset === "semana") { campoInicio.value = escrever(minimo); campoFim.value = escrever(maximo); }
    if (preset === "dia" && base) { campoInicio.value = escrever(base); campoFim.value = escrever(new Date(base.getTime() + 86400000)); }
    if (preset === "turno" && base) { campoInicio.value = escrever(new Date(base.getTime() + 7 * 3600000)); campoFim.value = escrever(new Date(base.getTime() + 18 * 3600000)); }
    if (preset === "livre") campoInicio.focus();
    atualizar();
  }

  function detectar() {
    var a = ler(campoInicio.value), b = ler(campoFim.value);
    if (!a || !b) return "livre";
    if (+a === +minimo && +b === +maximo) return "semana";
    var inicioDia = new Date(a.getFullYear(), a.getMonth(), a.getDate());
    diaEscolhido = escrever(inicioDia);
    if (+a === +inicioDia && b - a === 86400000) return "dia";
    if (a - inicioDia === 7 * 3600000 && b - a === 11 * 3600000) return "turno";
    return "livre";
  }

  function sugestao(a, b) {
    if (!a || !b) return "Análise sem nome";
    if (preset === "semana") return "Semana inteira";
    if (preset === "dia") return dois(a.getDate()) + "/" + dois(a.getMonth() + 1) + "/" + a.getFullYear();
    if (preset === "turno") return "Turno de " + dois(a.getDate()) + "/" + dois(a.getMonth() + 1);
    return curta(a) + " a " + curta(b);
  }

  // mesmas mensagens de DadosInsuficientesError em validarArquivo.py
  function validar(a, b) {
    if (!a || !b) return "Data inválida. Use o formato dia/mês/ano e hora.";
    if (a >= b) return "O início do período precisa ser antes do fim.";
    if (b < minimo || a > maximo) return "Não existem registros no período escolhido.";
    var sobra = Math.min(b, maximo) - Math.max(a, minimo);
    if (sobra < 60000) return "O período tem menos de 1 minuto de dados. O mínimo necessário é 60 intervalos válidos.";
    return "";
  }

  function atualizar() {
    var a = ler(campoInicio.value), b = ler(campoFim.value);
    var erro = validar(a, b);

    chips.forEach(function (c) { c.setAttribute("aria-checked", c.dataset.preset === preset); });
    if (caixaDias) caixaDias.hidden = !(preset === "dia" || preset === "turno");
    botoesDia.forEach(function (d) { d.setAttribute("aria-pressed", d.dataset.dia === diaEscolhido); });

    var nomeSugerido = sugestao(a, b);
    campoNome.placeholder = nomeSugerido;
    if (sugestaoTexto) sugestaoTexto.textContent = nomeSugerido;

    var total = maximo - minimo;
    if (selecao && a && b) {
      var ca = Math.max(minimo, Math.min(a, maximo)), cb = Math.max(minimo, Math.min(b, maximo));
      selecao.style.left = ((ca - minimo) / total * 100) + "%";
      selecao.style.width = (Math.max(0, cb - ca) / total * 100) + "%";
    }
    if (selecao) selecao.classList.toggle("erro-sel", !!erro);

    campoInicio.setAttribute("aria-invalid", !!erro);
    campoFim.setAttribute("aria-invalid", !!erro);
    erroCliente.hidden = !erro;
    erroCliente.querySelector("[data-mensagem]").textContent = erro;
    resumo.hidden = !!erro;
    if (!erro) {
      saidaDuracao.textContent = duracao(b - a);
      saidaPeriodo.textContent = curta(a) + " → " + curta(b);
    }
    botaoEnviar.disabled = !!erro;
  }

  chips.forEach(function (c) { c.addEventListener("click", function () { aplicar(c.dataset.preset); }); });
  botoesDia.forEach(function (d) {
    d.addEventListener("click", function () { aplicar(preset === "turno" ? "turno" : "dia", d.dataset.dia); });
  });
  [campoInicio, campoFim].forEach(function (c) {
    c.addEventListener("input", function () {
      if (erroServidor) erroServidor.hidden = true;
      preset = detectar();
      atualizar();
    });
  });

  form.addEventListener("submit", function (e) {
    var a = ler(campoInicio.value), b = ler(campoFim.value);
    if (validar(a, b)) { e.preventDefault(); return; }
    if (!campoNome.value.trim()) campoNome.value = sugestao(a, b);
    botaoEnviar.hidden = true;
    etapas.hidden = false;
    var itens = etapas.querySelectorAll("li"), n = 0;
    function passo() {
      itens.forEach(function (li, i) {
        li.classList.toggle("feita", i < n);
        li.classList.toggle("atual", i === n);
      });
      if (n < itens.length - 1) { n++; setTimeout(passo, 900); }
    }
    passo();
  });

  preset = detectar();
  atualizar();
})();
