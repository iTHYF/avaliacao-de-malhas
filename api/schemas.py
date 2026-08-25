from enum import IntEnum
from pydantic import BaseModel, Field
from typing import List

class TipoPlanta(IntEnum):
    FOPDT = 1
    SOPDT = 2

class SentidoTeste(IntEnum):
    SUBIDA = 1
    DESCIDA = 2
    AMBOS = 3

class CriterioParada(IntEnum):
    ACOMODACAO = 1
    TEMPO_MAXIMO = 2

class MalhaInfo(BaseModel):
    nome_malha: str
    var_controlada: str
    var_manipulada: str
    unidade_engenharia: str
    responsavel_tecnico: str

class LimitesOperacionais(BaseModel):
    f_op_min: float
    f_op_max: float
    l_sp_min: float
    l_sp_max: float
    l_mv_min: float
    l_mv_max: float
    limite_overshoot: float
    limite_esforco: float

class PlantaFisica(BaseModel):
    tipo_planta: TipoPlanta
    K: float
    tau: float
    zeta: float = 1.0
    T: float
    SP: float

class ConfiguracaoEnsaio(BaseModel):
    amp_degrau: float
    sentido_teste: SentidoTeste
    t_estabilizacao: float
    t_duracao_max: float = Field(..., gt=0.0)
    criterio_parada: CriterioParada
    num_repeticoes: int = Field(1, ge=1)
    intervalo_testes: float
    tolerancia_rp: float = Field(..., ge=0.0)
    tempo_amostragem: float = Field(..., gt=0.0)

class QuestionarioRestricoes(BaseModel):
    ov: int = Field(..., ge=1, le=3)
    comp: int = Field(..., ge=1, le=3)
    atu: int = Field(..., ge=0, le=1)
    rui: int = Field(..., ge=1, le=3)
    trans: int = Field(..., ge=1, le=3)
    perm: int = Field(..., ge=1, le=3)

class PIDConfig(BaseModel):
    id: int
    Kp: float
    Ki: float
    Kd: float

class AvaliacaoRequest(BaseModel):
    malha: MalhaInfo
    limites: LimitesOperacionais
    planta: PlantaFisica
    ensaio: ConfiguracaoEnsaio
    restricoes: QuestionarioRestricoes
    controladores: List[PIDConfig]

class PIDRanking(BaseModel):
    id: int
    score: float
    status: str

class PIDMetricas(BaseModel):
    id: int
    IAE: float
    ISE: float
    ITAE: float
    ITSE: float
    Overshoot: float
    Tempo_Acomodacao: float
    Tempo_Subida: float
    Desvio_Media_Saida: float
    Var_Saida: float
    Var_Controle: float
    Cruzamentos_SP: float
    Harris_Index: float
    Esforco_Maximo: float
    PV_Max: float
    PV_Min: float
    MV_Max: float
    MV_Min: float

class AvaliacaoResponse(BaseModel):
    ranking: List[PIDRanking]
    metricas: List[PIDMetricas]