from datetime import datetime
import pandas as pd
from storage.excel_repository import ExcelRepository

class HistoryService:
    def __init__(self):
        self.repo = ExcelRepository()

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
        existing_data = self.repo.get_existing_data()
        id_avaliacao, data_hora = self._gerar_id_avaliacao(existing_data)
                
        av_df = pd.DataFrame([{"ID_Avaliacao": id_avaliacao, "Data_Hora": data_hora, "Modo_Operacao": "Simulado", "Responsavel": dados_app.get("responsavel_tecnico", ""), "Schema_Version": "1.0"}])
        malhas_df = pd.DataFrame([{"ID_Avaliacao": id_avaliacao, "Nome_Malha": dados_app.get("nome_malha", ""), "Var_Controlada_PV": dados_app.get("var_controlada", ""), "Var_Manipulada_MV": dados_app.get("var_manipulada", ""), "Unidade": dados_app.get("unidade_engenharia", ""), "Ponto_Operacao_SP": dados_app.get("SP", 0.0), "K_Planta": dados_app.get("K", 0.0), "Tau_Planta": dados_app.get("tau", 0.0), "Atraso_Planta": dados_app.get("T", 0.0)}])
        id_ensaio = f"ENS-{id_avaliacao}-01"
        ensaios_df = pd.DataFrame([{"ID_Ensaio": id_ensaio, "ID_Avaliacao": id_avaliacao, "Sentido_Degrau": dados_app.get("sentido_teste", 0), "Amplitude_Degrau": dados_app.get("amp_degrau", 0.0), "Duracao_Configurada_Ensaio": dados_app.get("t_duracao_max", 0.0), "Caminho_Dados_Brutos": pd.NA}])

        controladores_list = []
        metricas_list = []
        
        ranking = dados_app.get("ranking", [])
        lista_indices_brutos = dados_app.get("lista_indices_brutos", [])
        
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
            

            brutos_idx = pid_info['id'] - 1
            ind_brutos = lista_indices_brutos[brutos_idx]

            metricas_list.append({
                "ID_Metrica": id_metrica, "ID_Ensaio": id_ensaio, "ID_Controlador": id_ctrl, "ID_Avaliacao": id_avaliacao,
                "IAE": ind_brutos.get("IAE", 0.0), "ISE": ind_brutos.get("ISE", 0.0), "ITAE": ind_brutos.get("ITAE", 0.0), "ITSE": ind_brutos.get("ITSE", 0.0),
                "Overshoot_perc": ind_brutos.get("Overshoot", 0.0), "Tempo_Acomodacao": ind_brutos.get("Tempo_Acomodacao", 0.0), "Tempo_Subida": ind_brutos.get("Tempo_Subida", 0.0)
            })

        self.repo.save_history({
            "Avaliacoes": av_df, "Malhas": malhas_df, "Ensaios": ensaios_df,
            "Controladores": pd.DataFrame(controladores_list), "Metricas": pd.DataFrame(metricas_list)
        })