import numpy as np
import matplotlib.pyplot as plt
from metrics.composite_indices import DecisorDeMetricas
from simulation.closed_loop_simulator import AvaliadorPID
from storage.history_service import HistoryService

def gerar_explicacao(ov, comp, atu, trans, perm, pesos):
    explicacoes = []
    if ov == 1: explicacoes.append("Restrição de OVERSHOOT: O sistema puniu severamente controladores que ultrapassam o alvo.")
    if comp == 1: explicacoes.append("Foco em RAPIDEZ: O sistema deu peso ao Tempo de Subida e penalizou a lentidão.")
    elif comp == 2: explicacoes.append("Foco em PRECISÃO FINAL: O peso foi focado em anular o erro a longo prazo.")
    if atu == 1: explicacoes.append("Restrição no ATUADOR: A Variância do Controle e a Oscilação receberam grande importância para evitar desgaste mecânico.")
    if trans == 1: explicacoes.append("Regime TRANSITÓRIO Suave: Oscilações puras (cruzamentos de setpoint) e trepidação na subida foram fortemente penalizadas.")
    elif trans == 3: explicacoes.append("Regime TRANSITÓRIO Agressivo: Permitiu-se certa oscilação inicial em troca de atingir o setpoint mais rápido.")
    if perm == 1: explicacoes.append("Regime PERMANENTE (Intolerável): O multiplicador de tempo (ITAE/ITSE) foi ativado ao máximo para eliminar erros fixos.")
    elif perm == 3: explicacoes.append("Regime PERMANENTE (Tolerado): A penalidade por desvios de longo prazo (ITAE/ITSE) foi removida nesta etapa.")

    if not explicacoes:
        explicacoes.append("Modo EQUILÍBRIO: Todas as métricas receberam pesos balanceados, buscando um controlador versátil e estável.")

    return "\n".join([f" - {item}" for item in explicacoes])

def executar_sistema():
    print("="*80)
    print(f"{'SELEÇÃO E OTIMIZAÇÃO DE CONTROLADORES PID':^80}")
    print("="*80)

    print("\n[ CADASTRO DA MALHA ]")
    nome_malha = input("Nome da malha: ")
    var_controlada = input("Variável controlada: ")
    var_manipulada = input("Variável manipulada: ")
    unidade_engenharia = input("Unidade de engenharia: ")
    responsavel_tecnico = input("Responsável técnico: ")

    print("\n[ LIMITES E PARÂMETROS OPERACIONAIS ]")
    f_op_min = float(input("Faixa operacional segura - Mínimo: "))
    f_op_max = float(input("Faixa operacional segura - Máximo: "))
    faixa_operacional = [f_op_min, f_op_max]

    l_sp_min = float(input("Limite mínimo do Setpoint: "))
    l_sp_max = float(input("Limite máximo do Setpoint: "))
    limites_sp = [l_sp_min, l_sp_max]

    l_mv_min = float(input("Limite mínimo da variável manipulada: "))
    l_mv_max = float(input("Limite máximo da variável manipulada: "))
    limites_mv = [l_mv_min, l_mv_max]

    tempo_amostragem = float(input("Tempo de amostragem (s): "))

    print("\n[ CONFIGURAÇÃO DO ENSAIO ]")
    amp_degrau = float(input("Amplitude da variação do setpoint: "))
    sentido_teste = int(input("Sentido do teste [1] Subida  [2] Descida  [3] Ambos: "))
    t_estabilizacao = float(input("Tempo de estabilização antes do ensaio (s): "))
    t_duracao_max = float(input("Duração máxima do ensaio (s): "))
    criterio_parada = int(input("Critério de parada [1] Acomodação  [2] Tempo máximo: "))
    num_repeticoes = int(input("Número de repetições: ")) # pyright: ignore[reportUndefinedVariable]
    intervalo_testes = float(input("Intervalo entre testes (s): "))
    limite_overshoot = float(input("Limite máximo de overshoot permitido (em percentagem sem '%'): "))
    limite_esforco = float(input("Limite máximo de esforço de controle: "))
    tolerancia_rp_in = float(input("Tolerância de regime permanente (em percentagem sem '%'): "))
    tolerancia_rp = tolerancia_rp_in / 100.0

    print("\n[ DADOS DA PLANTA FÍSICA ]")
    tipo_planta = int(input("Tipo de Planta [1] 1ª Ordem [2] 2ª Ordem: "))
    K = float(input("Insira o ganho da planta (K): "))
    tau = float(input("Insira a constante de tempo (tau): "))

    zeta = 1.0 
    if tipo_planta == 2:
        zeta = float(input("Insira o fator de amortecimento (zeta): "))

    T = float(input("Insira o atraso de transporte (T): "))
    SP = float(input("Insira o valor do Setpoint (SP): "))
    MV0 = float(input("Ponto de operação inicial da variável manipulada (MV0): "))

    print("\n[ QUESTIONÁRIO DE RESTRIÇÕES ]")
    ov = int(input("1. O quanto o sistema pode ultrapassar o setpoint?\n[1] Não pode  [2] Pouco  [3] Indiferente\nResposta: "))
    comp = int(input("\n2. Qual a prioridade principal da malha?\n[1] Rapidez  [2] Precisão final  [3] Equilíbrio\nResposta: "))
    atu = int(input("\n3. O atuador possui limitações?\n[0] Não  [1] Sim\nResposta (0-1): "))
    trans = int(input("\n4. Como deve ser a resposta no regime transitório?\n[1] Suave, sem oscilação  [2] Balanceada  [3] Agressiva\nResposta: "))
    perm = int(input("\n5. Qual a importância do erro de regime permanente?\n[1] Intolerável  [2] Pouco tolerado  [3] Tolerado\nResposta: "))

    decisor = DecisorDeMetricas()
    pesos = decisor.obter_pesos(ov, comp, atu, trans, perm)

    qtd_pids = int(input("\nQuantos PIDs deseja comparar? "))
    lista_pids = []
    lista_indices_brutos = []
    avaliador = AvaliadorPID(K, tau, T, SP, tempo_amostragem, tipo_planta, zeta, t_duracao_max, amp_degrau, t_estabilizacao, intervalo_testes, tolerancia_rp, sentido_teste, criterio_parada, MV0=MV0)

    print("\n[ INSERÇÃO DOS PARÂMETROS ]")
    for i in range(qtd_pids):
        print(f"--- PID #{i+1} ---")
        kp = float(input(f" Kp: "))
        ki = float(input(f" Ki: "))
        kd = float(input(f" Kd: "))

        ind_brutos = avaliador.calcular_indices(kp, ki, kd, num_repeticoes)

        lista_pids.append({"id": i+1, "Kp": kp, "Ki": ki, "Kd": kd})
        lista_indices_brutos.append(ind_brutos)

    if qtd_pids < 2:
        print("\n[Erro] O ranqueamento exige ao menos 2 PIDs para cálculo da normalização.")
        return

    limites_metricas = {}
    pids_validos_idx = []

    for i, res in enumerate(lista_indices_brutos):
        if (res["IAE"] < 1e5 and
            res["Overshoot_Seguranca"] <= limite_overshoot and
            res["Esforco_Maximo"] <= limite_esforco and
            res["PV_Max"] <= faixa_operacional[1] and
            res["PV_Min"] >= faixa_operacional[0] and
            res["MV_Max"] <= limites_mv[1] and
            res["MV_Min"] >= limites_mv[0]):
            pids_validos_idx.append(i)

    if len(pids_validos_idx) == 0:
        print("\n[Erro] Nenhum controlador passou pelas travas de segurança. Não é possível calcular o ranking.")
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
            for metrica in decisor.nomes_indices:
                ind_norm[metrica] = 1.0
            ranking.append({**pid, "score": 1.0, "status": "Instável"})

        elif ind_bruto["Overshoot_Seguranca"] > limite_overshoot:
            for metrica in decisor.nomes_indices:
                ind_norm[metrica] = 1.0
            ranking.append({**pid, "score": 1.0, "status": "Bloq. (Overshoot)"})

        elif ind_bruto["Esforco_Maximo"] > limite_esforco:
            for metrica in decisor.nomes_indices:
                ind_norm[metrica] = 1.0
            ranking.append({**pid, "score": 1.0, "status": "Bloq. (Esforço)"})

        elif ind_bruto["PV_Max"] > faixa_operacional[1] or ind_bruto["PV_Min"] < faixa_operacional[0]:
            for metrica in decisor.nomes_indices:
                ind_norm[metrica] = 1.0
            ranking.append({**pid, "score": 1.0, "status": "Bloq. (Faixa Op.)"})

        elif ind_bruto["MV_Max"] > limites_mv[1] or ind_bruto["MV_Min"] < limites_mv[0]:
            for metrica in decisor.nomes_indices:
                ind_norm[metrica] = 1.0
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
    print(f" Malha Operacional : {nome_malha}")
    print(f" Ação de Controle  : {var_manipulada} -> {var_controlada} ({unidade_engenharia})")
    print(f" Eng. Responsável  : {responsavel_tecnico}")
    print(f" Critério de Acom. : {tolerancia_rp * 100}% de tolerância")

    print("\n" + "="*95)
    print(f"{'TABELA DE ÍNDICES NORMALIZADOS':^95}") 
    print("="*95)
    cabecalho = f"{'MÉTRICA':<20} | {'PESO (%)':<10} |"
    for pid in lista_pids:
        cabecalho += f" PID #{pid['id']:<8} |"
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
        print(f"{pfx:<5} | PID {res['id']:<2} | {res['Kp']:<8.3f} | {res['Ki']:<8.3f} | {res['Kd']:<8.3f} | {res['score']:<8.4f} | {res['status']}")
    print("="*70)

    vencedor = ranking[0]
    if vencedor['status'] == "Aprovado":
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
        print(gerar_explicacao(ov, comp, atu, trans, perm, pesos))
        print("*"*70 + "\n")

    plt.style.use('seaborn-v0_8-whitegrid')
    fig = plt.figure(figsize=(14, 10))

    # 1. Gráfico da Resposta ao Ensaio
    ax1 = plt.subplot(2, 2, 1)
    ax1.step(lista_indices_brutos[0]["t_ensaio"], lista_indices_brutos[0]["sp_ensaio"],
             color='black', linestyle='--', label=f'Perfil de Setpoint', linewidth=2, where='post')

    for idx, pid in enumerate(lista_pids):
        if lista_indices_brutos[idx]["IAE"] < 1e5:
            ax1.step(lista_indices_brutos[idx]["t_ensaio"], lista_indices_brutos[idx]["y_ensaio"],
                     label=f"PID #{pid['id']}", linewidth=2, where='post')
    ax1.set_title('Resposta do sistema com controladores PID e Alterações no SP (Malha Fechada)', fontsize=12, fontweight='bold')
    ax1.set_xlabel('Tempo (s)')
    ax1.set_ylabel('SP')
    ax1.legend()

    ax2 = plt.subplot(2, 2, 2)
    for idx, pid in enumerate(lista_pids):
        if lista_indices_brutos[idx]["IAE"] < 1e5:
            ax2.step(lista_indices_brutos[idx]["t_ensaio"], lista_indices_brutos[idx]["u_ensaio"],
                     label=f"PID #{pid['id']}", linewidth=2, where='post')
    ax2.set_title('Sinal de Controle / Esforço do Atuador: u(t)', fontsize=12, fontweight='bold')
    ax2.set_xlabel('Tempo (s)')
    ax2.set_ylabel('Amplitude do Comando')
    ax2.legend()

    ax3 = plt.subplot(2, 1, 2)
    pids_estaveis = [r for r in ranking if r['status'] == 'Aprovado']

    if pids_estaveis:
        ids_barras = [f"PID #{r['id']}" for r in pids_estaveis]
        scores_barras = [r['score'] for r in pids_estaveis]
        cores = ['#2ca02c' if r['id'] == vencedor['id'] else '#7f7f7f' for r in pids_estaveis]

        barras = ax3.bar(ids_barras, scores_barras, color=cores, width=0.5)
        ax3.set_title('Score Final', fontsize=12, fontweight='bold')
        ax3.set_ylabel('Pontuação Normalizada Acumulada')

        for barra in barras:
            altura = barra.get_height()
            ax3.text(barra.get_x() + barra.get_width()/2., altura + 0.01,
                     f'{altura:.4f}', ha='center', va='bottom', fontweight='bold')
    else:
        ax3.text(0.5, 0.5, 'Nenhum PID aprovado para ranqueamento.', ha='center', va='center', fontsize=12)
        ax3.axis('off')

    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    executar_sistema()