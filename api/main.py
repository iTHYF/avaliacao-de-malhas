import logging
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, FileResponse, Response
from api.schemas import AvaliacaoRequest, AvaliacaoResponse
from api.evaluation_service import avaliar_controladores
from storage.history_query_service import HistoryQueryService
from reports.pdf_report import gerar_relatorio_pdf_bytes, dados_para_pdf_api, criar_figura_api


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="API de Avaliação de Malhas PID")

@app.get("/")
def home():
    return {"status": "ok"}

@app.post("/api/v1/evaluate", response_model=AvaliacaoResponse)
def evaluate_pids(request: AvaliacaoRequest):
    try:
        return avaliar_controladores(request)
    except Exception as e:
        logger.error(f"Erro interno no processamento da avaliacao: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "Ocorreu um erro interno durante a simulacao. O processamento foi abortado."}
        )


@app.post(
    "/api/v1/evaluate/pdf", response_class=Response,
    responses={200: {"content": {"application/pdf": {}}, "description": "Relatório PDF"}},
)
def evaluate_pids_pdf(request: AvaliacaoRequest):
    try:
        resultado, detalhes = avaliar_controladores(
            request,
            retornar_detalhes=True
        )

        dados = dados_para_pdf_api(request, resultado)
        dados["lista_indices_brutos"] = detalhes["lista_indices_brutos"]
        dados["pesos"] = detalhes["pesos"]

        figura = criar_figura_api(dados)
        pdf = gerar_relatorio_pdf_bytes(dados, figura=figura)

        return Response(
            content=pdf,
            media_type="application/pdf",
            headers={
                "Content-Disposition": 'attachment; filename="relatorio_pid.pdf"'
            },
        )

    except Exception as erro:
        logger.error(
            "Falha ao gerar avaliacao PDF: %s",
            erro,
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="Falha ao gerar a avaliacao e o relatorio PDF."
        ) from erro

@app.get("/api/v1/historico/avaliacoes")
def listar_historico(
    responsavel: str,
    nome_malha: str,
    K: float,
    tau: float,
    T: float
):
    try:
        servico = HistoryQueryService()

        avaliacoes = servico.listar_avaliacoes(
            responsavel, nome_malha, K, tau, T
        )

        return {"avaliacoes": avaliacoes}

    except ValueError as erro:
        raise HTTPException(
            status_code=400,
            detail=str(erro)
        ) from erro

    except (OSError, RuntimeError) as erro:
        logger.error("Erro ao listar historico: %s", erro)
        raise HTTPException(
            status_code=500,
            detail="Falha ao ler o historico."
        ) from erro


@app.get("/api/v1/historico/exportar")
def exportar_historico(
    responsavel: str,
    nome_malha: str,
    K: float,
    tau: float,
    T: float
):
    try:
        servico = HistoryQueryService()

        arquivo = servico.arquivo_validado(
            responsavel, nome_malha, K, tau, T
        )

    except ValueError as erro:
        raise HTTPException(
            status_code=400,
            detail=str(erro)
        ) from erro

    except (OSError, RuntimeError) as erro:
        logger.error("Erro ao exportar historico: %s", erro)
        raise HTTPException(
            status_code=500,
            detail="Falha ao ler o historico."
        ) from erro

    if arquivo is None:
        raise HTTPException(
            status_code=404,
            detail="Historico nao encontrado."
        )

    return FileResponse(
        path=str(arquivo),
        filename=arquivo.name,
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        )
    )


@app.get("/api/v1/historico/avaliacoes/{id_avaliacao}")
def consultar_avaliacao_historica(
    id_avaliacao: str,
    responsavel: str,
    nome_malha: str,
    K: float,
    tau: float,
    T: float
):
    try:
        servico = HistoryQueryService()

        resultado = servico.obter_avaliacao(
            id_avaliacao,
            responsavel,
            nome_malha,
            K,
            tau,
            T
        )

    except ValueError as erro:
        raise HTTPException(
            status_code=400,
            detail=str(erro)
        ) from erro

    except (OSError, RuntimeError) as erro:
        logger.error("Erro ao consultar avaliacao: %s", erro)
        raise HTTPException(
            status_code=500,
            detail="Falha ao ler o historico."
        ) from erro

    if resultado is None:
        raise HTTPException(
            status_code=404,
            detail="Avaliacao nao encontrada."
        )

    return resultado
