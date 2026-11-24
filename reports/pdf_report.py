from __future__ import annotations

from datetime import datetime
from io import BytesIO
from pathlib import Path
from html import escape
from uuid import uuid4
import math
import re
import unicodedata

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    KeepTogether, Image, PageBreak,
)

from storage.history_identity import RAIZ_PROJETO

METRICAS = (
    "IAE", "ISE", "ITAE", "ITSE", "Overshoot", "Tempo_Acomodacao",
    "Tempo_Subida", "Erro_Regime", "Var_Saida", "Var_Controle",
    "Cruzamentos_SP",
)
METRICAS_EXTRAS = (
    "Overshoot_Seguranca", "Esforco_Maximo", "PV_Max", "PV_Min",
    "MV_Max", "MV_Min", "Segmentos_Completos", "Segmentos_Parciais",
    "Segmentos_Sem_Acomodacao",
)

def _fontes():
    candidatos = [
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
    ]
    for normal, negrito in candidatos:
        if Path(normal).is_file() and Path(negrito).is_file():
            if "RelatorioPID" not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont("RelatorioPID", normal))
                pdfmetrics.registerFont(TTFont("RelatorioPID-Bold", negrito))
                pdfmetrics.registerFontFamily(
                    "RelatorioPID", normal="RelatorioPID",
                    bold="RelatorioPID-Bold",
                )
            return "RelatorioPID", "RelatorioPID-Bold"
    return "Helvetica", "Helvetica-Bold"


def _texto(valor):
    if valor is None:
        return "Não informado"
    return str(valor)


def _fmt(valor, digitos=5):
    if valor is None:
        return "—"
    if isinstance(valor, bool):
        return str(valor)
    try:
        numero = float(valor)
    except (ValueError, TypeError):
        return str(valor)
    if not math.isfinite(numero):
        return str(numero)
    if numero == 0:
        return "0"
    if abs(numero) < 10 ** (-digitos):
        return f"{numero:.6g}"  
    return f"{numero:.{digitos}f}".rstrip("0").rstrip(".")


def _p(texto, estilo):
    return Paragraph(escape(_texto(texto)).replace("\n", "<br/>"), estilo)



def _tabela(dados, larguras, estilos, titulo=None):
    linhas = [[_p(v, estilos["cabecalho"]) for v in dados[0]]]

    for linha in dados[1:]:
        linhas.append([_p(v, estilos["celula"]) for v in linha])

    tabela = Table(
        linhas,
        colWidths=larguras,
        repeatRows=1,
        hAlign="LEFT"
    )

    tabela.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEABOVE", (0, 0), (-1, 0), 0.6, colors.black),
        ("LINEBELOW", (0, 0), (-1, 0), 0.6, colors.black),
        ("LINEBELOW", (0, 1), (-1, -1), 0.2, colors.black),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))

    return tabela



def _titulo_secao(story, texto, estilos):
    story.append(Spacer(1, 11))
    story.append(_p(texto, estilos["secao"]))
    story.append(Spacer(1, 5))



def _pagina(canvas, doc):
    canvas.saveState()

    largura, _ = A4

    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.black)

    canvas.drawRightString(
        largura - 19 * mm,
        12 * mm,
        str(doc.page)
    )

    canvas.restoreState()


def caminho_pdf(nome_malha="avaliacao_pid", pasta=None):
    pasta = Path(pasta) if pasta is not None else RAIZ_PROJETO / "relatorios"
    pasta.mkdir(parents=True, exist_ok=True)
    slug = unicodedata.normalize("NFKD", str(nome_malha))
    slug = slug.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^A-Za-z0-9_-]+", "_", slug).strip("_")[:45] or "malha"
    sufixo = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid4().hex[:6]
    return pasta / f"relatorio_{slug}_{sufixo}.pdf"


def _normalizados(ranking, pids, brutos, pesos):
    status = {r["id"]: r["status"] for r in ranking}
    indices_ok = [i for i, pid in enumerate(pids)
                  if status.get(pid["id"]) == "Aprovado"]
    saida = []
    for i, pid in enumerate(pids):
        if i not in indices_ok:
            saida.append({k: 1.0 for k in METRICAS})
            continue
        vals = {}
        for metrica in METRICAS:
            candidatos = [brutos[j][metrica] for j in indices_ok]
            mn, mx = min(candidatos), max(candidatos)
            vals[metrica] = 0.0 if mx == mn else (brutos[i][metrica] - mn) / (mx - mn)
        saida.append(vals)
    return saida


def gerar_relatorio_pdf(dados, destino=None, figura=None):
    destino = Path(destino) if destino is not None else caminho_pdf(
        dados.get("nome_malha", "avaliacao_pid")
    )
    destino.parent.mkdir(parents=True, exist_ok=True)
    pdf_bytes = gerar_relatorio_pdf_bytes(dados, figura=figura)
    destino.write_bytes(pdf_bytes)
    return destino


def gerar_relatorio_pdf_bytes(dados, figura=None):
    """Retorna PDF em bytes, apropriado a uma resposta HTTP."""
    normal, bold = _fontes()
    sheet = getSampleStyleSheet()
    estilos = {
        "fontes": (normal, bold),

        "titulo": ParagraphStyle(
            "pid_titulo",
            parent=sheet["Title"],
            fontName=bold,
            fontSize=13,
            leading=17,
            alignment=TA_CENTER,
            textColor=colors.black,
            spaceAfter=8
        ),

        "subtitulo": ParagraphStyle(
            "pid_sub",
            parent=sheet["Normal"],
            fontName=normal,
            fontSize=9,
            leading=12,
            alignment=TA_CENTER,
            textColor=colors.black
        ),

        "secao": ParagraphStyle(
            "pid_secao",
            parent=sheet["Heading2"],
            fontName=bold,
            fontSize=10.5,
            leading=14,
            textColor=colors.black
        ),

        "corpo": ParagraphStyle(
            "pid_corpo",
            parent=sheet["BodyText"],
            fontName=normal,
            fontSize=9,
            leading=13,
            textColor=colors.black
        ),

        "cabecalho": ParagraphStyle(
            "pid_th",
            parent=sheet["Normal"],
            fontName=bold,
            fontSize=8,
            leading=11,
            textColor=colors.black
        ),

        "celula": ParagraphStyle(
            "pid_td",
            parent=sheet["Normal"],
            fontName=normal,
            fontSize=8,
            leading=11,
            textColor=colors.black
        ),
    }

    buffer = BytesIO()
    largura_pagina, altura_pagina = A4
    largura_util = largura_pagina - 38 * mm
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            leftMargin=19 * mm, rightMargin=19 * mm,
                            topMargin=19 * mm, bottomMargin=20 * mm,
                            title="Relatório técnico - Avaliação multicritério PID",
                            author="Ferramenta de avaliação multicritério PID")
    story = []
    story.append(_p("Relatório de Avaliação Multicritério de Controladores PID", estilos["titulo"]))
    story.append(_p(datetime.now().strftime("%d/%m/%Y"), estilos["subtitulo"]))
    _titulo_secao(story, "1. Identificação e modelo da malha", estilos)
    meta = [
        ("Malha", dados.get("nome_malha")),
        ("Responsável", dados.get("responsavel_tecnico")),
        ("Variável controlada (PV)", dados.get("var_controlada")),
        ("Variável manipulada (MV)", dados.get("var_manipulada")),
        ("Unidade informada da PV", dados.get("unidade_engenharia")),
        ("Tipo de planta", dados.get("tipo_planta")),
        ("Ganho estático K", _fmt(dados.get("K"), 9)),
        ("Constante de tempo tau", _fmt(dados.get("tau"), 9)),
        ("Atraso de transporte T", _fmt(dados.get("T"), 9)),
        ("Amortecimento zeta", _fmt(dados.get("zeta"), 9)),
        ("SP inicial", _fmt(dados.get("SP"), 9)),
        ("MV inicial", _fmt(dados.get("MV0"), 9)),
        ("Fonte da planta", dados.get("referencia")),
    ]
    meta = [(a, str(b)) for a,b in meta if b is not None]
    story.append(_tabela([["Campo", "Valor"]] + meta,
                         [57*mm, largura_util-57*mm], estilos))

    _titulo_secao(story, "2. Condições e restrições do ensaio", estilos)
    ensaio = [
        ("Tempo de amostragem Ts", dados.get("tempo_amostragem")),
        ("Duração máxima", dados.get("t_duracao_max")),
        ("Tempo inicial de estabilização", dados.get("t_estabilizacao")),
        ("Intervalo entre degraus", dados.get("intervalo_testes")),
        ("Amplitude de degrau", dados.get("amp_degrau")),
        ("Sentido do teste", dados.get("sentido_teste")),
        ("Critério de parada", dados.get("criterio_parada")),
        ("Repetições", dados.get("num_repeticoes")),
        ("Tolerância de acomodação (%)", dados.get("tolerancia_rp")),
        ("Limite de overshoot (%)", dados.get("limite_overshoot")),
        ("Limite de esforço", dados.get("limite_esforco")),
        ("Faixa permitida de PV", dados.get("faixa_pv")),
        ("Faixa permitida de SP", dados.get("faixa_sp")),
        ("Faixa permitida de MV", dados.get("faixa_mv")),
    ]
    ensaio = [(a, _fmt(b, 8) if isinstance(b, (int,float)) else _texto(b))
              for a,b in ensaio if b is not None]
    story.append(_tabela([["Parâmetro", "Valor"]] + ensaio,
                         [85*mm, largura_util-85*mm], estilos))

    ranking = dados["ranking"]
    pids = dados["lista_pids"]
    brutos = dados["lista_indices_brutos"]
    pesos = dados["pesos"]
    if len(pids) != len(brutos):
        raise ValueError("Os indicadores devem corresponder à lista de PIDs por posição.")
    pos_por_id = {r["id"]: r for r in ranking}

    _titulo_secao(story, "3. Ranking e decisão", estilos)
    linhas = [["Posição", "PID", "Kp", "Ki", "Kd", "Score J", "Situação"]]
    for i, r in enumerate(ranking, 1):
        linhas.append([str(i), f"#{r['id']}", _fmt(r.get("Kp"), 7),
                      _fmt(r.get("Ki"), 9), _fmt(r.get("Kd"), 7),
                      _fmt(r.get("score"), 6), r.get("status", "")])
    story.append(_tabela(linhas, [14*mm, 15*mm, 25*mm, 28*mm, 25*mm, 23*mm,
                                  largura_util-130*mm], estilos))
    aprovados = [r for r in ranking if r.get("status") == "Aprovado"]
    if aprovados:
        melhor = min(aprovados, key=lambda r: r["score"])
        story.append(Spacer(1, 5))
        story.append(_p(f"Menor Score entre os aprovados: PID #{melhor['id']} (J = {_fmt(melhor['score'], 6)}).", estilos["corpo"]))
    else:
        story.append(Spacer(1, 5))
        story.append(_p("Nenhum PID foi aprovado pelas verificações da avaliação.", estilos["corpo"]))
    story.append(_p("Observação: menor J significa melhor colocação apenas no conjunto comparado; "
                    "reprovados recebem Score convencional de bloqueio.", estilos["corpo"]))

    _titulo_secao(story, "4. Pesos utilizados no Score", estilos)
    linhas = [["Indicador", "Peso (%)"]] + [
        [nome, _fmt(float(pesos[nome])*100, 5)] for nome in METRICAS if nome in pesos
    ]
    story.append(_tabela(linhas, [largura_util*0.64, largura_util*0.36], estilos))
    story.append(Spacer(1, 4))
    story.append(_p("Pesos exibidos arredondados; os valores fornecidos pelo algoritmo não são alterados.", estilos["corpo"]))

    titulo_primeiro_pid = [
        Spacer(1, 11),
        _p("5. Indicadores brutos por controlador", estilos["secao"]),
        Spacer(1, 5),
    ]
    for i, pid in enumerate(pids):
        ind = brutos[i]
        linhas = [[f"PID #{pid['id']} — Indicador", "Valor"]]
        for nome in METRICAS + METRICAS_EXTRAS:
            if nome in ind:
                linhas.append([nome, _fmt(ind[nome], 6)])
        story.append(KeepTogether((titulo_primeiro_pid if i == 0 else []) + [
            _p(f"PID #{pid['id']} — {pos_por_id.get(pid['id'], {}).get('status','')}", estilos["secao"]),
            Spacer(1, 4),
            _tabela(linhas, [largura_util*0.63, largura_util*0.37], estilos),
            Spacer(1, 9),
        ]))

    norm = dados.get("lista_indices_normalizados")
    if norm is None:
        norm = _normalizados(ranking, pids, brutos, pesos)
    _titulo_secao(story, "6. Indicadores normalizados (Min-Max)", estilos)
    story.append(_p("Valores entre 0 e 1 (quanto menor, melhor). Candidatos bloqueados são "
                    "exibidos com 1 como penalidade convencional. Quando min = max, a escala "
                    "empregada pelo programa atribui 0 aos aprovados.", estilos["corpo"]))
    for ini in range(0, len(pids), 4):
        grupo = pids[ini:ini+4]
        linhas = [["Indicador", "Peso (%)"] + [f"PID #{p['id']}" for p in grupo]]
        for nome in METRICAS:
            linhas.append([nome, _fmt(float(pesos.get(nome, 0))*100, 3)] + [
                _fmt(norm[ini+j].get(nome), 4) for j in range(len(grupo))
            ])
        colunas = [55*mm, 25*mm] + [(largura_util-80*mm)/len(grupo)]*len(grupo)
        story.append(Spacer(1, 6))
        story.append(_tabela(linhas, colunas, estilos))

    if figura is not None:
        _titulo_secao(story, "7. Gráficos da simulação", estilos)
        img_buffer = BytesIO()
        figura.savefig(img_buffer, format="png", dpi=140, bbox_inches="tight")
        img_buffer.seek(0)
        img = Image(img_buffer)
        img.drawWidth = largura_util
        img.drawHeight = min(img.imageHeight * largura_util / img.imageWidth, 175*mm)
        story.append(img)
    else:
        _titulo_secao(story, "7. Gráficos da simulação", estilos)
        story.append(_p("Gráficos não incluídos: esta via de exportação utiliza os "
                        "indicadores e o ranking disponíveis, sem refazer a simulação.", estilos["corpo"]))

    doc.build(story, onFirstPage=_pagina, onLaterPages=_pagina)
    return buffer.getvalue()


def criar_figura_api(dados):
    from matplotlib.figure import Figure

    brutos = dados["lista_indices_brutos"]
    pids = dados["lista_pids"]
    ranking = dados["ranking"]
    if not brutos or not all("t_ensaio" in ind for ind in brutos):
        return None

    figura = Figure(figsize=(11, 8), dpi=130)
    ax1, ax2, ax3 = figura.add_subplot(2, 2, 1), figura.add_subplot(2, 2, 2), figura.add_subplot(2, 1, 2)
    primeiro = brutos[0]
    ax1.step(primeiro["t_ensaio"], primeiro["sp_ensaio"],
             color="black", linestyle="--", label="Setpoint", where="post", linewidth=1.5)
    for pid, ind in zip(pids, brutos):
        if ind.get("IAE", 1e6) >= 1e5:
            continue
        ax1.step(ind["t_ensaio"], ind["y_ensaio"], where="post", label=f"PID #{pid['id']}")
        ax2.step(ind["t_ensaio"], ind["u_ensaio"], where="post", label=f"PID #{pid['id']}")
    unidade = dados.get("unidade_tempo", "unidade de tempo do ensaio")
    ax1.set_title("Resposta da PV e referência")
    ax1.set_xlabel(f"Tempo ({unidade})")
    ax1.set_ylabel("PV / SP")
    ax1.grid(True, alpha=0.25)
    ax1.legend(fontsize=8)
    ax2.set_title("Sinal da variável manipulada (MV)")
    ax2.set_xlabel(f"Tempo ({unidade})")
    ax2.set_ylabel("MV")
    ax2.grid(True, alpha=0.25)
    ax2.legend(fontsize=8)
    aprovados = [r for r in ranking if r["status"] == "Aprovado"]
    if aprovados:
        ax3.bar([f"PID #{r['id']}" for r in aprovados], [r["score"] for r in aprovados],
                color="#54769A")
        for i, r in enumerate(aprovados):
            ax3.text(i, r["score"] + 0.008, f"{r['score']:.4f}", ha="center", fontsize=8)
        ax3.set_ylim(top=max(0.05, max(r["score"] for r in aprovados)*1.20))
    else:
        ax3.text(.5, .5, "Nenhum PID aprovado", ha="center", va="center")
        ax3.set_axis_off()
    ax3.set_title("Score global dos controladores aprovados")
    ax3.set_ylabel("Score J (menor é melhor)")
    figura.tight_layout()
    return figura


def dados_para_pdf_api(requisicao, resposta):
    pesos = __import__("metrics.composite_indices", fromlist=["DecisorDeMetricas"]).DecisorDeMetricas().obter_pesos(
        requisicao.restricoes.ov, requisicao.restricoes.comp, requisicao.restricoes.atu,
        requisicao.restricoes.trans, requisicao.restricoes.perm
    )
    ids = {r.id: r for r in resposta.ranking}
    brutos = [m.model_dump(exclude={"id"}) for m in resposta.metricas]
    return {
        "nome_malha": requisicao.malha.nome_malha,
        "responsavel_tecnico": requisicao.malha.responsavel_tecnico,
        "var_controlada": requisicao.malha.var_controlada,
        "var_manipulada": requisicao.malha.var_manipulada,
        "unidade_engenharia": requisicao.malha.unidade_engenharia,
        "tipo_planta": requisicao.planta.tipo_planta.name,
        "K": requisicao.planta.K,
        "tau": requisicao.planta.tau,
        "T": requisicao.planta.T,
        "zeta": requisicao.planta.zeta if requisicao.planta.tipo_planta.value == 2 else None,
        "SP": requisicao.planta.SP,
        "MV0": requisicao.planta.MV0,
        "tempo_amostragem": requisicao.ensaio.tempo_amostragem,
        "t_duracao_max": requisicao.ensaio.t_duracao_max,
        "t_estabilizacao": requisicao.ensaio.t_estabilizacao,
        "intervalo_testes": requisicao.ensaio.intervalo_testes,
        "amp_degrau": requisicao.ensaio.amp_degrau,
        "sentido_teste": requisicao.ensaio.sentido_teste.name,
        "criterio_parada": requisicao.ensaio.criterio_parada.name,
        "num_repeticoes": requisicao.ensaio.num_repeticoes,
        "tolerancia_rp": requisicao.ensaio.tolerancia_rp,
        "limite_overshoot": requisicao.limites.limite_overshoot,
        "limite_esforco": requisicao.limites.limite_esforco,
        "faixa_pv": [requisicao.limites.f_op_min, requisicao.limites.f_op_max],
        "faixa_sp": [requisicao.limites.l_sp_min, requisicao.limites.l_sp_max],
        "faixa_mv": [requisicao.limites.l_mv_min, requisicao.limites.l_mv_max],
        "lista_pids": [p.model_dump() for p in requisicao.controladores],
        "lista_indices_brutos": brutos,
        "ranking": [{"id": r.id, "Kp": next(p.Kp for p in requisicao.controladores if p.id == r.id),
                     "Ki": next(p.Ki for p in requisicao.controladores if p.id == r.id),
                     "Kd": next(p.Kd for p in requisicao.controladores if p.id == r.id),
                     "score": r.score, "status": r.status} for r in resposta.ranking],
        "pesos": pesos,
    }
