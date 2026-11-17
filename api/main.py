import logging
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from api.schemas import AvaliacaoRequest, AvaliacaoResponse
from api.evaluation_service import avaliar_controladores

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