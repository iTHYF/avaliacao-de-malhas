import numpy as np
import matplotlib.pyplot as plt
from metrics.composite_indices import DecisorDeMetricas
from simulation.closed_loop_simulator import AvaliadorPID
from storage.history_service import HistoryService
from appy import gerar_explicacao

def obter_configuracoes_plantas():
    return {
        "1": {"desc": "Planta Padrão (Moderada)", "K": 1.0, "tau": 1.0, "T": 1.0, "SP": 1.0},
        "2": {"desc": "Planta Lenta com Alto Atraso", "K": 2.0, "tau": 5.0, "T": 3.0, "SP": 10.0},
        "3": {"desc": "Planta de Baixo Ganho e Alta Inércia", "K": 0.5, "tau": 10.0, "T": 2.0, "SP": 5.0}
    }

def obter_configuracoes_testes():
    return {
        "1": {
            "desc": "Foco em Rapidez (Degrau Agressivo)",
            "malha": {"nome_malha": "Auto_01_Rapidez", "var_controlada": "Vazão", "var_manipulada": "Bomba", "unidade_engenharia": "L/min", "responsavel_tecnico": "Auto 1"},
            "limites": {"f_op_min": -100.0, "f_op_max": 100.0, "l_sp_min": -20.0, "l_sp_max": 20.0, "l_mv_min": -100.0, "l_mv_max": 100.0, "tempo_amostragem": 0.1},
            "ensaio": {"amp_degrau": 1.0, "sentido_teste": 1, "t_estabilizacao": 5.0, "t_duracao_max": 50.0, "criterio_parada": 2, "num_repeticoes": 1, "intervalo_testes": 10.0, "limite_overshoot": 50.0, "limite_esforco": 100.0, "tolerancia_rp_in": 2.0},
            "restricoes": {"ov": 3, "comp": 1, "atu": 0, "rui": 1, "trans": 3, "perm": 1},
            # PIDs rápidos, mas estáveis mesmo com atraso
            "pids": [(0.5, 0.2, 0.0), (0.8, 0.1, 0.0), (0.4, 0.15, 0.0)]
        },
        "2": {
            "desc": "Foco em Robustez (Controladores Conservadores)",
            "malha": {"nome_malha": "Auto_02_Robustez", "var_controlada": "Temperatura", "var_manipulada": "Resistência", "unidade_engenharia": "°C", "responsavel_tecnico": "Auto 2"},
            "limites": {"f_op_min": -100.0, "f_op_max": 100.0, "l_sp_min": -20.0, "l_sp_max": 20.0, "l_mv_min": -100.0, "l_mv_max": 100.0, "tempo_amostragem": 0.1},
            "ensaio": {"amp_degrau": 1.0, "sentido_teste": 2, "t_estabilizacao": 5.0, "t_duracao_max": 60.0, "criterio_parada": 2, "num_repeticoes": 1, "intervalo_testes": 10.0, "limite_overshoot": 10.0, "limite_esforco": 100.0, "tolerancia_rp_in": 5.0},
            "restricoes": {"ov": 1, "comp": 2, "atu": 1, "rui": 3, "trans": 1, "perm": 3},
            # PIDs extremamente lentos e seguros para evitar qualquer overshoot
            "pids": [(0.1, 0.05, 0.0), (0.15, 0.02, 0.0), (0.08, 0.01, 0.0)]
        },
        "3": {
            "desc": "Equilíbrio Geral (Testes em Ambos os Sentidos)",
            "malha": {"nome_malha": "Auto_03_Equilibrio", "var_controlada": "Pressão", "var_manipulada": "Válvula", "unidade_engenharia": "bar", "responsavel_tecnico": "Auto 3"},
            "limites": {"f_op_min": -100.0, "f_op_max": 100.0, "l_sp_min": -20.0, "l_sp_max": 20.0, "l_mv_min": -100.0, "l_mv_max": 100.0, "tempo_amostragem": 0.1},
            "ensaio": {"amp_degrau": 1.0, "sentido_teste": 3, "t_estabilizacao": 5.0, "t_duracao_max": 60.0, "criterio_parada": 2, "num_repeticoes": 1, "intervalo_testes": 15.0, "limite_overshoot": 25.0, "limite_esforco": 100.0, "tolerancia_rp_in": 2.0},
            "restricoes": {"ov": 2, "comp": 3, "atu": 0, "rui": 2, "trans": 2, "perm": 2},
            # PIDs equilibrados
            "pids": [(0.25, 0.1, 0.0), (0.2, 0.05, 0.0), (0.3, 0.15, 0.0)]
        },
        "4": {
            "desc": "Rejeição a Ruído e Esforço Mínimo",
            "malha": {"nome_malha": "Auto_04_Ruido", "var_controlada": "Nível", "var_manipulada": "Bomba", "unidade_engenharia": "%", "responsavel_tecnico": "Auto 4"},
            "limites": {"f_op_min": -100.0, "f_op_max": 100.0, "l_sp_min": -20.0, "l_sp_max": 20.0, "l_mv_min": -100.0, "l_mv_max": 100.0, "tempo_amostragem": 0.1},
            "ensaio": {"amp_degrau": 2.0, "sentido_teste": 1, "t_estabilizacao": 5.0, "t_duracao_max": 50.0, "criterio_parada": 2, "num_repeticoes": 1, "intervalo_testes": 10.0, "limite_overshoot": 15.0, "limite_esforco": 100.0, "tolerancia_rp_in": 2.0},
            "restricoes": {"ov": 3, "comp": 2, "atu": 1, "rui": 3, "trans": 1, "perm": 2},
            # Ganhos baixos geram esforço mínimo (ideal para atuadores sensíveis)
            "pids": [(0.1, 0.05, 0.0), (0.08, 0.02, 0.0), (0.12, 0.04, 0.0)]
        },
        "5": {
            "desc": "Tolerância Zero ao Erro Permanente (Alta Precisão)",
            "malha": {"nome_malha": "Auto_05_Precisao", "var_controlada": "pH", "var_manipulada": "Dosadora", "unidade_engenharia": "pH", "responsavel_tecnico": "Auto 5"},
            "limites": {"f_op_min": -100.0, "f_op_max": 100.0, "l_sp_min": -20.0, "l_sp_max": 20.0, "l_mv_min": -100.0, "l_mv_max": 100.0, "tempo_amostragem": 0.1},
            "ensaio": {"amp_degrau": 1.0, "sentido_teste": 3, "t_estabilizacao": 5.0, "t_duracao_max": 60.0, "criterio_parada": 2, "num_repeticoes": 1, "intervalo_testes": 15.0, "limite_overshoot": 20.0, "limite_esforco": 100.0, "tolerancia_rp_in": 1.0},
            "restricoes": {"ov": 1, "comp": 2, "atu": 0, "rui": 1, "trans": 2, "perm": 1},
            # PIDs focados em zerar o erro com integradores controlados
            "pids": [(0.3, 0.2, 0.0), (0.2, 0.1, 0.0), (0.4, 0.1, 0.0)]
        }
    }

def executar_sistema_automatico():
    print("="*80)
    print(f"{'SELEÇÃO E OTIMIZAÇÃO DE CONTROLADORES PID (MODO AUTOMÁTICO)':^80}")
    print("="*80)
    
    # 1. ESCOLHA DA PLANTA
    plantas = obter_configuracoes_plantas()
    print("\nPlantas Pré-Configuradas Disponíveis:")
    for key, p in plantas.items():
        print(f"[{key}] {p['desc']} (K={p['K']}, tau={p['tau']}, T={p['T']}, SP={p['SP']})")
        
    escolha_planta = input("\nEscolha a planta que deseja testar (1-3): ")
    if escolha_planta not in plantas:
        print("Escolha inválida. Encerrando.")
        return
        
    planta_cfg = plantas[escolha_planta]
    K, tau, T, SP = planta_cfg["K"], planta_cfg["tau"], planta_cfg["T"], planta_cfg["SP"]
    tipo_planta, zeta = 1, 1.0

    # 2. ESCOLHA DO TESTE
    configuracoes = obter_configuracoes_testes()
    print("\nTestes Pré-Configurados Disponíveis:")
    for key, val in configuracoes.items():
        print(f"[{key}] {val['desc']}")
        
    escolha_teste = input("\nEscolha o teste que deseja executar (1-5): ")
    if escolha_teste not in configuracoes:
        print("Escolha inválida. Encerrando.")
        return
        
    cfg = configuracoes[escolha_teste]
    
    nome_malha = cfg["malha"]["nome_malha"]
    var_controlada = cfg["malha"]["var_controlada"]
    var_manipulada = cfg["malha"]["var_manipulada"]
    unidade_engenharia = cfg["malha"]["unidade_engenharia"]
    responsavel_tecnico = cfg["malha"]["responsavel_tecnico"]
    
    faixa_operacional = [cfg["limites"]["f_op_min"], cfg["limites"]["f_op_max"]]
    limites_mv = [cfg["limites"]["l_mv_min"], cfg["limites"]["l_mv_max"]]
    tempo_amostragem = cfg["limites"]["tempo_amostragem"]
    
    amp_degrau = cfg["ensaio"]["amp_degrau"]
    sentido_teste = cfg["ensaio"]["sentido_teste"]
    t_estabilizacao = cfg["ensaio"]["t_estabilizacao"]
    t_duracao_max = cfg["ensaio"]["t_duracao_max"]
    criterio_parada = cfg["ensaio"]["criterio_parada"]
    num_repeticoes = cfg["ensaio"]["num_repeticoes"]
    intervalo_testes = cfg["ensaio"]["intervalo_testes"]
    limite_overshoot = cfg["ensaio"]["limite_overshoot"]
    limite_esforco = cfg["ensaio"]["limite_esforco"]
    tolerancia_rp = cfg["ensaio"]["tolerancia_rp_in"] / 100.0
    
    ov, comp, atu, rui, trans, perm = cfg["restricoes"].values()
    qtd_pids = len(cfg["pids"])

    decisor = DecisorDeMetricas()
    pesos = decisor.obter_pesos(ov, comp, atu, rui, trans, perm)

    lista_pids = []
    lista_indices_brutos = []
    avaliador = AvaliadorPID(K, tau, T, SP, tempo_amostragem, tipo_planta, zeta, t_duracao_max, amp_degrau, t_estabilizacao, intervalo_testes, tolerancia_rp, sentido_teste, criterio_parada)

    for i, (kp, ki, kd) in enumerate(cfg["pids"]):
        ind_brutos = avaliador.calcular_indices(kp, ki, kd, num_repeticoes)
        lista_pids.append({"id": i+1, "Kp": kp, "Ki": ki, "Kd": kd})
        lista_indices_brutos.append(ind_brutos)

    limites_metricas = {}
    pids_validos_idx = []

    for i, res in enumerate(lista_indices_brutos):
        if (res["IAE"] < 1e5 and res["Overshoot"] <= limite_overshoot and
            res["Esforco_Maximo"] <= limite_esforco and res["PV_Max"] <= faixa_operacional[1] and
            res["PV_Min"] >= faixa_operacional[0] and res["MV_Max"] <= limites_mv[1] and
            res["MV_Min"] >= limites_mv[0]):
            pids_validos_idx.append(i)

    if len(pids_validos_idx) == 0:
        print("\n[Erro] Nenhum controlador passou nas travas de segurança (Instabilidade, Overshoot, Esforço, PV ou Saturação da MV).")
        return

    for metrica in decisor.nomes_indices:
        valores_limpos = [lista_indices_brutos[i][metrica] for i in pids_validos_idx]
        limites_metricas[metrica] = {"min": min(valores_limpos), "max": max(valores_limpos)}

    lista_indices_normalizados = []
    ranking = []
    for idx, pid in enumerate(lista_pids):
        ind_bruto = lista_indices_brutos[idx]
        ind_norm = {}

        if ind_bruto["IAE"] >= 1e5:
            for metrica in decisor.nomes_indices: ind_norm[metrica] = 1.0
            ranking.append({**pid, "score": 1.0, "status": "Instável"})
        elif ind_bruto["Overshoot"] > limite_overshoot:
            for metrica in decisor.nomes_indices: ind_norm[metrica] = 1.0
            ranking.append({**pid, "score": 1.0, "status": "Bloq. (Overshoot)"})
        elif ind_bruto["Esforco_Maximo"] > limite_esforco:
            for metrica in decisor.nomes_indices: ind_norm[metrica] = 1.0
            ranking.append({**pid, "score": 1.0, "status": "Bloq. (Esforço)"})
        elif ind_bruto["PV_Max"] > faixa_operacional[1] or ind_bruto["PV_Min"] < faixa_operacional[0]:
            for metrica in decisor.nomes_indices: ind_norm[metrica] = 1.0
            ranking.append({**pid, "score": 1.0, "status": "Bloq. (Faixa Op.)"})
        elif ind_bruto["MV_Max"] > limites_mv[1] or ind_bruto["MV_Min"] < limites_mv[0]:
            for metrica in decisor.nomes_indices: ind_norm[metrica] = 1.0
            ranking.append({**pid, "score": 1.0, "status": "Bloq. (Saturação)"})
        else:
            score = 0.0
            for metrica in decisor.nomes_indices:
                val = ind_bruto[metrica]
                vmin = limites_metricas[metrica]["min"]
                vmax = limites_metricas[metrica]["max"]
                norm = 0.0 if vmax == vmin else (val - vmin) / (vmax - vmin)
                ind_norm[metrica] = norm
                score += norm * pesos[metrica]
            ranking.append({**pid, "score": score, "status": "Aprovado"})
        lista_indices_normalizados.append(ind_norm)

    dados_app = {
        "nome_malha": nome_malha, "var_controlada": var_controlada, 
        "var_manipulada": var_manipulada, "unidade_engenharia": unidade_engenharia,
        "responsavel_tecnico": responsavel_tecnico, "SP": SP, "K": K, 
        "tau": tau, "T": T, "sentido_teste": sentido_teste,
        "amp_degrau": amp_degrau, "t_duracao_max": t_duracao_max,
        "ranking": ranking, "lista_indices_brutos": lista_indices_brutos
    }
    
    try:
        service = HistoryService()
        service.salvar_avaliacao(dados_app)
    except Exception as e:
        print(f"\n[AVISO] Não foi possível salvar o histórico. O relatório prosseguirá em memória. Detalhe: {e}")

    print("\n" + "#"*95)
    print(f"{'RELATÓRIO TÉCNICO':^95}")
    print("#"*95)
    print(f" Malha Operacional : {nome_malha} (K={K}, tau={tau}, T={T})")
    print(f" Ação de Controle  : {var_manipulada} -> {var_controlada} ({unidade_engenharia})")
    print(f" Eng. Responsável  : {responsavel_tecnico}")
    print(f" Critério de Acom. : {tolerancia_rp * 100}% de tolerância")

    print("\n" + "="*95)
    print(f"{'TABELA DE ÍNDICES NORMALIZADOS':^95}") 
    print("="*95)
    cabecalho = f"{'MÉTRICA':<20} | {'PESO (%)':<10} |"
    for pid in lista_pids: cabecalho += f" PID #{pid['id']:<8} |"
    print(cabecalho)
    print("-" * len(cabecalho))

    for metrica in decisor.nomes_indices:
        peso_formatado = f"{pesos[metrica]*100:.1f}%"
        linha = f"{metrica:<20} | {peso_formatado:<10} |"
        for idx in range(qtd_pids):
            val_norm = lista_indices_normalizados[idx][metrica]
            if (lista_indices_brutos[idx]["IAE"] >= 1e5 or
                lista_indices_brutos[idx]["Overshoot"] > limite_overshoot or
                lista_indices_brutos[idx]["Esforco_Maximo"] > limite_esforco or
                lista_indices_brutos[idx]["PV_Max"] > faixa_operacional[1] or
                lista_indices_brutos[idx]["PV_Min"] < faixa_operacional[0] or
                lista_indices_brutos[idx]["MV_Max"] > limites_mv[1] or
                lista_indices_brutos[idx]["MV_Min"] < limites_mv[0]):
                linha += f" {'1.00 (Max)':<12} |"
            else:
                destaque = " (*)" if val_norm == 0.0 else ""
                linha += f" {val_norm:<6.4f}{destaque:<6} |"
        print(linha)
    print("="*95)

    ranking.sort(key=lambda x: x["score"])

    print("\n" + "="*70)
    print(f"{'RANKING DE DESEMPENHO':^70}")
    print("="*70)
    print(f"{'Pos':<5} | {'ID':<6} | {'Kp':<8} | {'Ki':<8} | {'Kd':<8} | {'Score':<8} | {'Status'}")
    print("-" * 70)

    for pos, res in enumerate(ranking):
        pfx = "#1" if pos == 0 and res["status"] == "Aprovado" else f"#{pos+1}"
        print(f"{pfx:<5} | PID {res['id']:<2} | {res['Kp']:<8.3f} | {res['Ki']:<8.3f} | {res['Kd']:<8.3f} | {res['score']:<8.4f} | {res['status']}")
    print("="*70)

    if ranking and ranking[0]['status'] == "Aprovado":
        vencedor = ranking[0]
        print("\n" + "*"*70)
        print(">>> DIAGNÓSTICO DO SISTEMA <<<")
        print("*"*70)
        print(f"O MELHOR controlador para os seus requisitos é o PID #{vencedor['id']}.")

        pesos_ordenados = sorted(pesos.items(), key=lambda x: x[1], reverse=True)
        top_3_metricas = [f"{k} ({v*100:.1f}%)" for k, v in pesos_ordenados[:3]]

        print(f"\nAo longo da normalização, o PID #{vencedor['id']} obteve a menor penalidade")
        print(f"nas três métricas mais importantes para a sua malha:")
        print(f"Top 3 Métricas: {', '.join(top_3_metricas)}.")
        print("\nJustificativa baseada nas restrições:")
        print(gerar_explicacao(ov, comp, atu, rui, trans, perm, pesos))
        print("*"*70 + "\n")

    plt.style.use('seaborn-v0_8-whitegrid')
    fig = plt.figure(figsize=(14, 10))

    ax1 = plt.subplot(2, 2, 1)
    ax1.step(lista_indices_brutos[0]["t_ensaio"], lista_indices_brutos[0]["sp_ensaio"], color='black', linestyle='--', label=f'Perfil de Setpoint', linewidth=2, where='post')
    for idx, pid in enumerate(lista_pids):
        if lista_indices_brutos[idx]["IAE"] < 1e5:
            ax1.step(lista_indices_brutos[idx]["t_ensaio"], lista_indices_brutos[idx]["y_ensaio"], label=f"PID #{pid['id']}", linewidth=2, where='post')
    ax1.set_title('Resposta do sistema com controladores PID e Alterações no SP', fontsize=12, fontweight='bold')
    ax1.set_xlabel('Tempo (s)')
    ax1.set_ylabel('SP')
    ax1.legend()

    ax2 = plt.subplot(2, 2, 2)
    for idx, pid in enumerate(lista_pids):
        if lista_indices_brutos[idx]["IAE"] < 1e5:
            ax2.step(lista_indices_brutos[idx]["t_ensaio"], lista_indices_brutos[idx]["u_ensaio"], label=f"PID #{pid['id']}", linewidth=2, where='post')
    ax2.set_title('Sinal de Controle / Esforço do Atuador: u(t)', fontsize=12, fontweight='bold')
    ax2.set_xlabel('Tempo (s)')
    ax2.set_ylabel('Amplitude do Comando')
    ax2.legend()

    ax3 = plt.subplot(2, 1, 2)
    pids_estaveis = [r for r in ranking if r['status'] == 'Aprovado']
    if pids_estaveis:
        ids_barras = [f"PID #{r['id']}" for r in pids_estaveis]
        scores_barras = [r['score'] for r in pids_estaveis]
        cores = ['#2ca02c' if r['id'] == ranking[0]['id'] else '#7f7f7f' for r in pids_estaveis]
        barras = ax3.bar(ids_barras, scores_barras, color=cores, width=0.5)
        ax3.set_title('Score Final', fontsize=12, fontweight='bold')
        ax3.set_ylabel('Pontuação Normalizada Acumulada')
        for barra in barras:
            altura = barra.get_height()
            ax3.text(barra.get_x() + barra.get_width()/2., altura + 0.01, f'{altura:.4f}', ha='center', va='bottom', fontweight='bold')
    else:
        ax3.text(0.5, 0.5, 'Nenhum PID aprovado para ranqueamento.', ha='center', va='center', fontsize=12)
        ax3.axis('off')

    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    executar_sistema_automatico()