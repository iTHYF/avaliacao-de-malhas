import logging

from metrics.composite_indices import DecisorDeMetricas
from simulation.closed_loop_simulator import AvaliadorPID

from storage.history_service import HistoryService
from api.schemas import AvaliacaoRequest, AvaliacaoResponse, PIDRanking, PIDMetricas

logger = logging.getLogger(__name__)

def _montar_dados_historico(req: AvaliacaoRequest, ranking: list, lista_indices_brutos: list) -> dict:
    return {
        "nome_malha": req.malha.nome_malha,
        "var_controlada": req.malha.var_controlada,
        "var_manipulada": req.malha.var_manipulada,
        "unidade_engenharia": req.malha.unidade_engenharia,
        "responsavel_tecnico": req.malha.responsavel_tecnico,
        "SP": req.planta.SP, "K": req.planta.K, "tau": req.planta.tau, "T": req.planta.T,
        "sentido_teste": req.ensaio.sentido_teste,
        "amp_degrau": req.ensaio.amp_degrau,
        "t_duracao_max": req.ensaio.t_duracao_max,
        "ranking": ranking,
        "lista_indices_brutos": lista_indices_brutos
    }

def _montar_resposta_api(ranking_interno: list, req_controladores: list, lista_indices_brutos: list) -> AvaliacaoResponse:
    ranking_api = [
        PIDRanking(id=r["id"], score=r["score"], status=r["status"]) 
        for r in ranking_interno
    ]
    
    metricas_api = []
    for idx, pid in enumerate(req_controladores):
        ind_bruto = lista_indices_brutos[idx]
        
        metricas_api.append(PIDMetricas(
            id=pid.id,
            IAE=float(ind_bruto["IAE"]),
            ISE=float(ind_bruto["ISE"]),
            ITAE=float(ind_bruto["ITAE"]),
            ITSE=float(ind_bruto["ITSE"]),
            Overshoot=float(ind_bruto["Overshoot"]),
            Tempo_Acomodacao=float(ind_bruto["Tempo_Acomodacao"]),
            Tempo_Subida=float(ind_bruto["Tempo_Subida"]),
            Erro_Regime=float(ind_bruto["Erro_Regime"]),
            Var_Saida=float(ind_bruto["Var_Saida"]),
            Var_Controle=float(ind_bruto["Var_Controle"]),
            Cruzamentos_SP=float(ind_bruto["Cruzamentos_SP"]),
            Esforco_Maximo=float(ind_bruto["Esforco_Maximo"]),
            PV_Max=float(ind_bruto["PV_Max"]),
            PV_Min=float(ind_bruto["PV_Min"]),
            MV_Max=float(ind_bruto["MV_Max"]),
            MV_Min=float(ind_bruto["MV_Min"])
        ))

    return AvaliacaoResponse(ranking=ranking_api, metricas=metricas_api)

def avaliar_controladores(req: AvaliacaoRequest) -> AvaliacaoResponse:
    decisor = DecisorDeMetricas()
    pesos = decisor.obter_pesos(
        req.restricoes.ov, req.restricoes.comp, req.restricoes.atu, 
        req.restricoes.trans, req.restricoes.perm
    )
    
    tolerancia_rp_decimal = req.ensaio.tolerancia_rp / 100.0
    
    avaliador = AvaliadorPID(
        K=req.planta.K, 
        tau=req.planta.tau, 
        T=req.planta.T, 
        setpoint=req.planta.SP, 
        Ts=req.ensaio.tempo_amostragem, 
        tipo_planta=req.planta.tipo_planta, 
        zeta=req.planta.zeta, 
        t_duracao=req.ensaio.t_duracao_max, 
        amp_degrau=req.ensaio.amp_degrau, 
        t_estab=req.ensaio.t_estabilizacao, 
        int_testes=req.ensaio.intervalo_testes,
        tolerancia_rp=tolerancia_rp_decimal, 
        sentido_teste=req.ensaio.sentido_teste,
        criterio_parada=req.ensaio.criterio_parada,
        MV0=req.planta.MV0
    )

    lista_indices_brutos = []
    lista_pids_dicts = []
    
    for pid in req.controladores:
        ind_brutos = avaliador.calcular_indices(pid.Kp, pid.Ki, pid.Kd, req.ensaio.num_repeticoes)
        lista_indices_brutos.append(ind_brutos)
        lista_pids_dicts.append({"id": pid.id, "Kp": pid.Kp, "Ki": pid.Ki, "Kd": pid.Kd})
        
    limites_metricas = {}
    pids_validos_idx = []
    
    for i, res in enumerate(lista_indices_brutos):
        if (res["IAE"] < 1e5 and
            res["Overshoot_Seguranca"] <= req.limites.limite_overshoot and
            res["Esforco_Maximo"] <= req.limites.limite_esforco and
            res["PV_Max"] <= req.limites.f_op_max and
            res["PV_Min"] >= req.limites.f_op_min and
            res["MV_Max"] <= req.limites.l_mv_max and
            res["MV_Min"] >= req.limites.l_mv_min):
            pids_validos_idx.append(i)

    for metrica in decisor.nomes_indices:
        if len(pids_validos_idx) > 0:
            valores_limpos = [lista_indices_brutos[i][metrica] for i in pids_validos_idx]
            limites_metricas[metrica] = {"min": min(valores_limpos), "max": max(valores_limpos)}
        else:
            limites_metricas[metrica] = {"min": 0, "max": 0}

    ranking_interno = []
    for idx, pid in enumerate(lista_pids_dicts):
        ind_bruto = lista_indices_brutos[idx]
        
        if ind_bruto["IAE"] >= 1e5:
            ranking_interno.append({**pid, "score": 1.0, "status": "Instável"})
        elif ind_bruto["Overshoot_Seguranca"] > req.limites.limite_overshoot:
            ranking_interno.append({**pid, "score": 1.0, "status": "Bloq. (Overshoot)"})
        elif ind_bruto["Esforco_Maximo"] > req.limites.limite_esforco:
            ranking_interno.append({**pid, "score": 1.0, "status": "Bloq. (Esforço)"})
        elif ind_bruto["PV_Max"] > req.limites.f_op_max or ind_bruto["PV_Min"] < req.limites.f_op_min:
            ranking_interno.append({**pid, "score": 1.0, "status": "Bloq. (Faixa Op.)"})
        elif ind_bruto["MV_Max"] > req.limites.l_mv_max or ind_bruto["MV_Min"] < req.limites.l_mv_min:
            ranking_interno.append({**pid, "score": 1.0, "status": "Bloq. (Saturação)"})
        else:
            score = 0.0
            for metrica in decisor.nomes_indices:
                val = ind_bruto[metrica]
                vmin = limites_metricas[metrica]["min"]
                vmax = limites_metricas[metrica]["max"]
                norm = 0.0 if vmax == vmin else (val - vmin) / (vmax - vmin)
                score += norm * pesos[metrica]
            ranking_interno.append({**pid, "score": score, "status": "Aprovado"})
            
    ranking_interno.sort(key=lambda x: x["score"])
    
    try:
        dados_historico = _montar_dados_historico(req, ranking_interno, lista_indices_brutos)
        HistoryService().salvar_avaliacao(dados_historico)
    except Exception as e:
        logger.error(f"Erro ao salvar historico no Excel: {e}")

    return _montar_resposta_api(ranking_interno, req.controladores, lista_indices_brutos)