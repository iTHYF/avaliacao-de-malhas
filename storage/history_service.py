
from datetime import datetime
import pandas as pd
from storage.excel_repository import ExcelRepository
from storage.history_identity import caminho_historico


class HistoryService:
    def _gerar_id_avaliacao(self, existing_data):
        while True:
            now = datetime.now()
            novo_id = now.strftime("AV-%Y%m%d-%H%M%S-") + f"{now.microsecond // 1000:03d}"
            
            if existing_data is not None and 'Avaliacoes' in existing_data:
                df_av = existing_data['Avaliacoes']
                if 'ID_Avaliacao' in df_av.columns and novo_id in df_av['ID_Avaliacao'].values:
                    continue 
            return novo_id, now

    def _inferir_tipo_controlador(self, kp, ki, kd):
        if ki == 0 and kd == 0: return "P"
        if kd == 0: return "PI"
        return "PID"

    def salvar_avaliacao(self, dados_app):
        K = float(dados_app.get("K", 0.0))
        tau = float(dados_app.get("tau", 0.0))
        T = float(dados_app.get("T", 0.0))
        
        filepath = caminho_historico(
             dados_app.get("responsavel_tecnico"),
                 dados_app.get("nome_malha"),
                       K,
                       tau, 
                       T
                       )
        
        filepath.parent.mkdir(parents=True, exist_ok=True)
        repo = ExcelRepository(str(filepath))
        
        existing_data = repo.get_existing_data()
        id_avaliacao, data_hora = self._gerar_id_avaliacao(existing_data)
    
        av_df = pd.DataFrame([{
            "ID_Avaliacao": id_avaliacao, 
            "Nome_Malha": dados_app.get("nome_malha", ""), 
            "Ponto_Operacao_SP": dados_app.get("SP", 0.0),
            "Data_Hora": data_hora, 
            "Modo_Operacao": "Simulado", 
            "Responsavel": dados_app.get("responsavel_tecnico", ""), 
            "Schema_Version": "1.2"
        }])
        
        info_planta_df = pd.DataFrame([{
            "K_Planta": K, 
            "Tau_Planta": tau, 
            "Atraso_Planta": T,
            "Var_Controlada_PV": dados_app.get("var_controlada", ""), 
            "Var_Manipulada_MV": dados_app.get("var_manipulada", ""), 
            "Unidade": dados_app.get("unidade_engenharia", "")
        }])
        
        id_ensaio = f"ENS-{id_avaliacao}-01"
        ensaios_df = pd.DataFrame([{
            "ID_Ensaio": id_ensaio, "ID_Avaliacao": id_avaliacao, 
            "Sentido_Degrau": dados_app.get("sentido_teste", 0), 
            "Amplitude_Degrau": dados_app.get("amp_degrau", 0.0), 
            "Duracao_Configurada_Ensaio": dados_app.get("t_duracao_max", 0.0), 
            "Caminho_Dados_Brutos": pd.NA
        }])

        controladores_list = []
        metricas_list = []
        
        ranking = dados_app.get("ranking", [])
        lista_indices_brutos = dados_app["lista_indices_brutos"]
        lista_pids = dados_app["lista_pids"]
        pesos = dados_app["pesos"]

        # O ranking pode estar ordenado por Score e ter IDs nao sequenciais.
        if len(lista_pids) != len(lista_indices_brutos):
            raise ValueError("Quantidade de PIDs diferente da quantidade de resultados brutos.")
        indices_por_id = {}
        for pid_config, indices in zip(lista_pids, lista_indices_brutos):
            pid_id = pid_config["id"]
            if pid_id in indices_por_id:
                raise ValueError(f"ID de PID duplicado: {pid_id}")
            indices_por_id[pid_id] = indices

        if set(pesos) != {"IAE", "ISE", "ITAE", "ITSE", "Overshoot", "Tempo_Acomodacao",
                          "Tempo_Subida", "Erro_Regime", "Var_Saida", "Var_Controle", "Cruzamentos_SP"}:
            raise ValueError("Dicionario de pesos incompleto ou com metricas desconhecidas.")

        for idx, pid_info in enumerate(ranking):
            seq = idx + 1
            id_ctrl = f"CTRL-{id_avaliacao}-{seq:02d}"
            id_metrica = f"MET-{id_avaliacao}-{seq:02d}"
            
            kp, ki, kd = pid_info.get("Kp", 0), pid_info.get("Ki", 0), pid_info.get("Kd", 0)
            tipo = self._inferir_tipo_controlador(kp, ki, kd)

            controladores_list.append({
                "ID_Controlador": id_ctrl, "ID_Avaliacao": id_avaliacao, "Tipo": tipo,
                "Kp": kp, "Ki": ki if ki != 0 else pd.NA, "Kd": kd if kd != 0 else pd.NA,
                "Indice_Global_J": pid_info.get("score", 0.0), "Classificacao": pid_info.get("status", "")
            })
            
            pid_id = pid_info["id"]
            if pid_id not in indices_por_id:
                raise ValueError(f"Nao foram encontrados indicadores do PID {pid_id}.")
            ind_brutos = indices_por_id[pid_id]

            metricas_list.append({
                "ID_Metrica": id_metrica, "ID_Ensaio": id_ensaio, "ID_Controlador": id_ctrl, "ID_Avaliacao": id_avaliacao,
                "IAE": ind_brutos["IAE"], "ISE": ind_brutos["ISE"], "ITAE": ind_brutos["ITAE"], "ITSE": ind_brutos["ITSE"],
                "Overshoot_perc": ind_brutos["Overshoot"], "Tempo_Acomodacao": ind_brutos["Tempo_Acomodacao"], "Tempo_Subida": ind_brutos["Tempo_Subida"],
                "Erro_Regime": ind_brutos["Erro_Regime"],
                "Var_Saida": ind_brutos["Var_Saida"],
                "Var_Controle": ind_brutos["Var_Controle"],
                "Cruzamentos_SP": ind_brutos["Cruzamentos_SP"]
            })

        repo.save_history({
            "Avaliacoes": av_df, 
            "Ensaios": ensaios_df,
            "Controladores": pd.DataFrame(controladores_list), 
            "Metricas": pd.DataFrame(metricas_list),
            "Pesos": pd.DataFrame([
                {"ID_Avaliacao": id_avaliacao, "Metrica": nome, "Peso": float(peso)}
                for nome, peso in pesos.items()
            ]),
            "Info_Planta": info_planta_df
        })
