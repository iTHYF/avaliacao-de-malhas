
import numpy as np
import matplotlib.pyplot as plt
from metrics.composite_indices import DecisorDeMetricas
from simulation.closed_loop_simulator import AvaliadorPID
from storage.history_service import HistoryService
from storage.history_cli import consultar_historico
from appy import gerar_explicacao

# Banco de plantas de primeira ordem com atraso (FOPDT).
# Todos os ganhos abaixo foram CALCULADOS PREVIAMENTE, fora do software.
# A ferramenta somente avalia esses candidatos; ela NAO realiza sintonia.
# Referencias: Wood & Berry (1973); Vinante & Luyben (1972);
# Skogestad (SIMC); Ziegler & Nichols (1942); Cohen & Coon (1953).
# As plantas 1-3 sao modelos FOPDT normalizados, nao modelos industriais medidos.
# As plantas 4-6 sao CANAIS SISO de plantas originalmente multivariaveis.

METODOS = (
    "SIMC-PI rapido (lambda=L)",
    "SIMC-PI conservador (lambda=3L)",
    "IMC-PID (lambda=2L)",
    "Ziegler-Nichols PID (curva de reacao)",
    "Cohen-Coon PID (curva de reacao)",
)


def obter_configuracoes_plantas():
    # Convenção: ganhos paralelos C(s) = Kp + Ki/s + Kd*s.
    # O modulo controllers/pid.py acrescenta um filtro a acao derivativa.
    # As plantas 1-3 usam unidade de tempo normalizada (u.t.).
    # G11 Wood-Berry e Vinante-Luyben utilizam minutos; G22 usa segundos.
    return {
        "1": {
            "desc": "FOPDT normalizada — atraso dominante",
            "codigo": "FOPDT_Atraso_Dominante",
            "K": 1.0, "tau": 0.2, "T": 1.0, "SP": 1.0,
            "unidade_tempo": "u.t.",
            "referencia": "Modelo normalizado FOPDT (caso didatico)",
            "Ts": 0.02, "t_estab": 5.0, "int_testes": 20.0, "t_duracao": 55.0,
            "pids": [
                (0.100000000, 0.500000000, 0.0),
                (0.050000000, 0.250000000, 0.0),
                (0.280000000, 0.400000000, 0.040000000),
                (0.240000000, 0.120000000, 0.120000000),
                (0.516666667, 0.441666667, 0.098412698),
            ],
        },
        "2": {
            "desc": "FOPDT normalizada — atraso intermediario",
            "codigo": "FOPDT_Intermediaria",
            "K": 1.0, "tau": 2.0, "T": 1.0, "SP": 1.0,
            "unidade_tempo": "u.t.",
            "referencia": "Modelo normalizado FOPDT (caso didatico)",
            "Ts": 0.02, "t_estab": 5.0, "int_testes": 30.0, "t_duracao": 76.0,
            "pids": [
                (1.000000000, 0.500000000, 0.0),
                (0.500000000, 0.250000000, 0.0),
                (1.000000000, 0.400000000, 0.400000000),
                (2.400000000, 1.200000000, 1.200000000),
                (2.916666667, 1.416666667, 0.972222222),
            ],
        },
        "3": {
            "desc": "FOPDT normalizada — inercia dominante",
            "codigo": "FOPDT_Inercia_Dominante",
            "K": 1.0, "tau": 5.0, "T": 1.0, "SP": 1.0,
            "unidade_tempo": "u.t.",
            "referencia": "Modelo normalizado FOPDT (caso didatico)",
            "Ts": 0.02, "t_estab": 10.0, "int_testes": 60.0, "t_duracao": 150.0,
            "pids": [
                (2.500000000, 0.500000000, 0.0),
                (1.250000000, 0.250000000, 0.0),
                (2.200000000, 0.400000000, 1.000000000),
                (6.000000000, 3.000000000, 3.000000000),
                (6.916666667, 3.041666667, 2.426900585),
            ],
        },
        "4": {
            "desc": "Wood-Berry G11 — canal SISO da destilacao",
            "codigo": "Wood_Berry_G11_Benchmark",
            "K": 12.8, "tau": 16.7, "T": 1.0, "SP": 0.5,
            "unidade_tempo": "min",
            "referencia": "Wood e Berry (1973), canal G11 isolado",
            "Ts": 0.02, "t_estab": 20.0, "int_testes": 100.0, "t_duracao": 255.0,
            "pids": [
                (0.652343750, 0.081542969, 0.0),
                (0.326171875, 0.020385742, 0.0),
                (0.537500000, 0.031250000, 0.260937500),
                (1.565625000, 0.782812500, 0.782812500),
                (1.759114583, 0.732747396, 0.632788660),
            ],
        },
        "5": {
            "desc": "Wood-Berry G22 — canal SISO (estudo de caso)",
            "codigo": "Wood_Berry_G22_Benchmark",
            "K": -19.4, "tau": 864.0, "T": 180.0, "SP": 0.5,
            "unidade_tempo": "s",
            "referencia": "Wood e Berry (1973), canal G22 isolado, em segundos",
            "Ts": 10.0, "t_estab": 300.0, "int_testes": 3500.0, "t_duracao": 8000.0,
            "pids": [
                (-0.123711340, -0.0001431844, 0.0),
                (-0.061855670, -0.0000715922, 0.0),
                (-0.109278351, -0.0001145475, -8.907216495),
                (-0.296907216, -0.0008247423, -26.721649485),
                (-0.342783505, -0.0008400153, -21.617879449),
            ],
        },
        "6": {
            "desc": "Vinante-Luyben G11 — canal SISO da destilacao",
            "codigo": "Vinante_Luyben_G11_Benchmark",
            "K": -2.2, "tau": 7.0, "T": 1.0, "SP": 0.5,
            "unidade_tempo": "min",
            "referencia": "Vinante e Luyben, canal G11 isolado",
            "Ts": 0.02, "t_estab": 10.0, "int_testes": 100.0, "t_duracao": 250.0,
            "pids": [
                (-1.590909091, -0.227272727, 0.0),
                (-0.795454545, -0.113636364, 0.0),
                (-1.363636364, -0.181818182, -0.636363636),
                (-3.818181818, -1.909090909, -1.909090909),
                (-4.356060606, -1.875000000, -1.543920215),
            ],
        },
    }


def obter_teste_original_woodberry():
    # Caso ja auditado no artigo. NAO alterar ganhos ou condicoes.
    return {
            "desc": "Estudo de Caso: Coluna de Wood-Berry (5 PIDs Graduais)",
            "malha": {
                "nome_malha": "Coluna_Wood_Berry", 
                "var_controlada": "Composição do Fundo", 
                "var_manipulada": "Vazão de Vapor no Refervedor", 
                "unidade_engenharia": "mol %", 
                "responsavel_tecnico": "Thyfanne Dayane"
            },
            "limites": {
                "f_op_min": 0.35, "f_op_max": 0.75, 
                "l_sp_min": 0.0, "l_sp_max": 1.0, 
                "l_mv_min": -0.5, "l_mv_max": 0.5, 
                "tempo_amostragem": 10.0
            },
            "ensaio": {
                "amp_degrau": 0.1, "sentido_teste": 3, 
                "t_estabilizacao": 300.0, "t_duracao_max": 8000.0, 
                "criterio_parada": 2, "num_repeticoes": 1, 
                "intervalo_testes": 3500.0, "limite_overshoot": 15.0, 
                "limite_esforco": 1.5, "tolerancia_rp_in": 2.0
            },
            "restricoes": {"ov": 1, "comp": 3, "atu": 1, "trans": 1, "perm": 1},
            "pids": [
                (-0.043, -0.00005, 0.0),     
                (-0.080, -0.00009, 0.0),     
                (-0.124, -0.00014, 0.0),     
                (-0.200, -0.00040, -10.0),   
                (-0.297, -0.00083, -26.73)   
            ]
        }


def configurar_benchmark(planta, responsavel):
    # Limites amplos ilustrativos para triagem numerica, NAO limites industriais.
    # Os mesmos limites numericos nao implicam as mesmas unidades fisicas.
    return {
        "desc": "Cinco sintonias calculadas (SIMC, IMC, ZN, Cohen-Coon)",
        "malha": {
            "nome_malha": planta["codigo"],
            "var_controlada": "Saida do canal SISO",
            "var_manipulada": "Entrada do canal SISO",
            "unidade_engenharia": "unidade do modelo",
            "responsavel_tecnico": responsavel,
        },
        "limites": {
            "f_op_min": -1.0, "f_op_max": 3.0,
            "l_sp_min": -1.0, "l_sp_max": 3.0,
            "l_mv_min": -5.0, "l_mv_max": 5.0,
            "tempo_amostragem": planta["Ts"],
        },
        "ensaio": {
            "amp_degrau": 0.1,
            "sentido_teste": 3,
            "t_estabilizacao": planta["t_estab"],
            "t_duracao_max": planta["t_duracao"],
            "criterio_parada": 2,
            "num_repeticoes": 1,
            "intervalo_testes": planta["int_testes"],
            "limite_overshoot": 15.0,
            "limite_esforco": 5.0,
            "tolerancia_rp_in": 2.0,
        },
        "restricoes": {"ov": 1, "comp": 3, "atu": 1, "trans": 1, "perm": 1},
        "pids": planta["pids"],
        "metodos": METODOS,
    }


def executar_sistema_automatico():
    print("="*80)
    print(f"{'AVALIAÇÃO MULTICRITÉRIO DE PID (TESTES PRÉ-CONFIGURADOS)':^80}")
    print("="*80)
    
    plantas = obter_configuracoes_plantas()
    print("\nPlantas de referencia (primeira ordem + atraso):")
    for key, p in plantas.items():
        print(
            f"[{key}] {p['desc']} "
            f"(K={p['K']}, tau={p['tau']}, T={p['T']}, "
            f"tempo em {p['unidade_tempo']})"
        )

    escolha_planta = input("\nEscolha a planta (1-6): ").strip()
    if escolha_planta not in plantas:
        print("Escolha invalida. Encerrando.")
        return

    planta_cfg = plantas[escolha_planta]
    K, tau, T, SP = (
        planta_cfg["K"], planta_cfg["tau"], planta_cfg["T"], planta_cfg["SP"]
    )
    unidade_tempo = planta_cfg["unidade_tempo"]
    tipo_planta, zeta = 1, 1.0

    print("\nConjuntos disponiveis:")
    print("[1] Cinco controladores calculados (SIMC, IMC, ZN, Cohen-Coon)")
    if escolha_planta == "5":
        print("[2] Reproduzir estudo de caso Wood-Berry G22 original (artigo)")
    escolha_teste = input("Selecione o conjunto: ").strip()

    if escolha_teste == "1":
        responsavel = input(
            "Responsavel por este teste [Teste_Benchmark]: "
        ).strip() or "Teste_Benchmark"
        cfg = configurar_benchmark(planta_cfg, responsavel)
        print(
            "\n[AVISO] Limites das plantas de referencia sao "
            "ilustrativos, nao limites industriais certificados."
        )
    elif escolha_teste == "2" and escolha_planta == "5":
        cfg = obter_teste_original_woodberry()
    else:
        print("Conjunto invalido para esta planta.")
        return

    try:
        MV0 = float(input(
            "Ponto de operacao inicial da MV (MV0) [0]: "
        ).strip().replace(",", ".") or "0")
    except ValueError:
        print("Valor invalido para MV0.")
        return

    metodos = cfg.get("metodos") or (
        "PI original #1", "PI original #2", "PI original #3",
        "PID original #4", "PID original #5"
    )
    
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
    
    ov, comp, atu, trans, perm = cfg["restricoes"].values()
    qtd_pids = len(cfg["pids"])
    if len(metodos) != qtd_pids:
        raise ValueError("Quantidade de metodos diferente da de controladores.")

    decisor = DecisorDeMetricas()
    pesos = decisor.obter_pesos(ov, comp, atu, trans, perm)

    lista_pids = []
    lista_indices_brutos = []
    avaliador = AvaliadorPID(K, tau, T, SP, tempo_amostragem, tipo_planta, zeta, t_duracao_max, amp_degrau, t_estabilizacao, intervalo_testes, tolerancia_rp, sentido_teste, criterio_parada, MV0=MV0)

    for i, (kp, ki, kd) in enumerate(cfg["pids"]):
        ind_brutos = avaliador.calcular_indices(kp, ki, kd, num_repeticoes)
        lista_pids.append({
            "id": i + 1, "Kp": kp, "Ki": ki, "Kd": kd,
            "metodo": metodos[i]
        })
        lista_indices_brutos.append(ind_brutos)

    limites_metricas = {}
    print("\n" + "=" * 75)
    print("AUDITORIA NUMERICA — CONTROLADORES PRE-CONFIGURADOS")
    print("=" * 75)

    for i, res in enumerate(lista_indices_brutos):
        print(f"\nPID #{i+1} — {metodos[i]}")

        for metrica in decisor.nomes_indices:
            print(f"  {metrica:<22}: {res[metrica]:.6f}")

        ov_seguranca = res["Overshoot_Seguranca"]

        print(f"  {'Overshoot de segurança':<22}: {ov_seguranca:.4f}%")
        print(f"  {'Limite permitido':<22}: {limite_overshoot:.4f}%")

        if ov_seguranca > limite_overshoot:
            print("  RESULTADO OV: REPROVADO")
        else:
            print("  RESULTADO OV: APROVADO")

        print(f"  Janelas completas: {res['Segmentos_Completos']}")
        print(f"  Janelas parciais: {res['Segmentos_Parciais']}")
        print(f"  Sem acomodação: {res['Segmentos_Sem_Acomodacao']}")

    print("=" * 75)
    
    pids_validos_idx = []

    for i, res in enumerate(lista_indices_brutos):
        if (res["IAE"] < 1e5 and res["Overshoot_Seguranca"] <= limite_overshoot and
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
        elif ind_bruto["Overshoot_Seguranca"] > limite_overshoot:
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
        "ranking": ranking, "lista_indices_brutos": lista_indices_brutos,
        "lista_pids": lista_pids, "pesos": pesos
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
    print(f" Unidade de tempo : {unidade_tempo}")
    print(f" Fonte da planta  : {planta_cfg['referencia']}")
    janelas_completas = sum(seg["completo"] for seg in avaliador.segmentos)
    janelas_parciais = sum(not seg["completo"] for seg in avaliador.segmentos)
    print(f" Janelas avaliadas  : {janelas_completas} completas; "
          f"{janelas_parciais} parcial(is) excluída(s) do Score")

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
                lista_indices_brutos[idx]["Overshoot_Seguranca"] > limite_overshoot or
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
        print(f"{pfx:<5} | PID {res['id']:<2} | {res['Kp']:<8.3f} | {res['Ki']:<10.6f} | {res['Kd']:<8.3f} | {res['score']:<8.4f} | {res['status']}")
    print("="*70)
    print("\nORIGEM DOS GANHOS (valores pre-calculados):")
    for pid in lista_pids:
        print(f"  PID #{pid['id']}: {pid['metodo']}")
    print(f"  Planta: {planta_cfg['referencia']}")
    print("  Metodo de sintonia nao recalculado neste programa.")

    if ranking and ranking[0]['status'] == "Aprovado":
        vencedor = ranking[0]
        print("\n" + "*"*70)
        print(">>> DIAGNÓSTICO DO SISTEMA <<<")
        print("*"*70)
        print(f"O MELHOR controlador para os seus requisitos é o PID #{vencedor['id']}.")

        pesos_ordenados = sorted(pesos.items(), key=lambda x: x[1], reverse=True)
        top_3_metricas = [f"{k} ({v*100:.1f}%)" for k, v in pesos_ordenados[:3]]

        print(f"\nO PID #{vencedor['id']} obteve o menor Score global.")
        print(f"As três métricas de maior peso na avaliação foram:")
        print(f"Top 3 Métricas: {', '.join(top_3_metricas)}.")
        print("\nJustificativa baseada nas restrições:")
        print(gerar_explicacao(ov, comp, atu, trans, perm, pesos))
        print("*"*70 + "\n")

    plt.style.use('seaborn-v0_8-whitegrid')
    fig = plt.figure(figsize=(14, 10))

    ax1 = plt.subplot(2, 2, 1)
    ax1.step(lista_indices_brutos[0]["t_ensaio"], lista_indices_brutos[0]["sp_ensaio"], color='black', linestyle='--', label=f'Perfil de Setpoint', linewidth=2, where='post')
    for idx, pid in enumerate(lista_pids):
        if lista_indices_brutos[idx]["IAE"] < 1e5:
            ax1.step(lista_indices_brutos[idx]["t_ensaio"], lista_indices_brutos[idx]["y_ensaio"], label=f"PID #{pid['id']}", linewidth=2, where='post')
    ax1.set_title('Resposta do sistema com controladores PID e Alterações no SP', fontsize=12, fontweight='bold')
    ax1.set_xlabel(f'Tempo ({unidade_tempo})')
    ax1.set_ylabel('SP')
    ax1.legend()

    ax2 = plt.subplot(2, 2, 2)
    for idx, pid in enumerate(lista_pids):
        if lista_indices_brutos[idx]["IAE"] < 1e5:
            ax2.step(lista_indices_brutos[idx]["t_ensaio"], lista_indices_brutos[idx]["u_ensaio"], label=f"PID #{pid['id']}", linewidth=2, where='post')
    ax2.set_title('Sinal de Controle / Esforço do Atuador: u(t)', fontsize=12, fontweight='bold')
    ax2.set_xlabel(f'Tempo ({unidade_tempo})')
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
    while True:
        print("\n========== MENU PRINCIPAL ==========")
        print("[1] Realizar avaliacao PID")
        print("[2] Consultar historico")
        print("[0] Sair")
        opcao = input("Escolha: ").strip()
        if opcao == "1":
            executar_sistema_automatico()
        elif opcao == "2":
            consultar_historico()
        elif opcao == "0":
            break
        else:
            print("Opcao invalida.")
