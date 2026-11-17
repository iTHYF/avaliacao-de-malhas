
import os
import time
import uuid

import numpy as np
import pandas as pd


class ExcelRepository:
    COLUNAS_NUMERICAS = {
        "Avaliacoes": ["Ponto_Operacao_SP"],
        "Ensaios": [
            "Sentido_Degrau", "Amplitude_Degrau",
            "Duracao_Configurada_Ensaio"
        ],
        "Controladores": ["Kp", "Ki", "Kd", "Indice_Global_J"],
        "Metricas": [
            "IAE", "ISE", "ITAE", "ITSE", "Overshoot_perc",
            "Tempo_Acomodacao", "Tempo_Subida", "Erro_Regime",
            "Var_Saida", "Var_Controle", "Cruzamentos_SP"
        ],
        "Pesos": ["Peso"],
        "Info_Planta": ["K_Planta", "Tau_Planta", "Atraso_Planta"],
    }

    def __init__(self, filepath):
        self.filepath = filepath

    def get_existing_data(self):
        if not os.path.exists(self.filepath):
            return None

        return pd.read_excel(
            self.filepath,
            sheet_name=None
        )

    @staticmethod
    def _normalizar_valor_numerico(valor):
        """
        Extrai valores escalares de arrays NumPy e NamedSignal.

        Exemplo:
            NamedSignal(array(0.67657993))
            -> 0.67657993

        Valores ausentes e numeros comuns sao preservados.
        Arrays com mais de um elemento nao sao aceitos.
        """

        if isinstance(valor, np.ndarray):
            array = np.asarray(valor)

            if array.size != 1:
                raise ValueError(
                    "Esperado um unico valor numerico, "
                    f"mas foram encontrados {array.size} elementos."
                )

            return array.item()

        return valor

    def _garantir_tipos_numericos(self, sheet_name, df):
        df = df.copy()

        for coluna in self.COLUNAS_NUMERICAS.get(sheet_name, []):
            if coluna not in df.columns:
                continue

            try:
                # Converte NamedSignal e arrays escalares
                # em valores Python comuns.
                valores = [
                    self._normalizar_valor_numerico(valor)
                    for valor in df[coluna].tolist()
                ]

                serie = pd.Series(
                    valores,
                    index=df.index
                )

                # Valida e converte a coluna para numeros.
                df[coluna] = pd.to_numeric(
                    serie,
                    errors="raise"
                )

            except (ValueError, TypeError) as exc:
                raise ValueError(
                    f"Nao foi possivel converter a coluna "
                    f"'{coluna}' da aba '{sheet_name}' "
                    f"em numero. Detalhe: {exc}"
                ) from exc

        return df

    def save_history(self, new_dfs_dict):
        existing_data = self.get_existing_data()
        final_data = {}

        if existing_data:
            for sheet_name, df in existing_data.items():
                final_data[sheet_name] = df.copy()

        for sheet_name, new_df in new_dfs_dict.items():
            if sheet_name in final_data:
                if sheet_name == "Info_Planta":
                    final_data[sheet_name] = new_df.copy()
                else:
                    final_data[sheet_name] = pd.concat(
                        [final_data[sheet_name], new_df],
                        ignore_index=True
                    )
            else:
                final_data[sheet_name] = new_df.copy()

        # Garante que os valores destinados ao Excel
        # sejam realmente numericos.
        for sheet_name, df in final_data.items():
            final_data[sheet_name] = (
                self._garantir_tipos_numericos(
                    sheet_name, df
                )
            )

        temp_filepath = (
            f"{self.filepath}.{uuid.uuid4().hex}.tmp.xlsx"
        )

        max_retries = 3

        for attempt in range(max_retries):
            try:
                with pd.ExcelWriter(
                    temp_filepath,
                    engine="openpyxl"
                ) as writer:
                    for sheet_name, df in final_data.items():
                        df.to_excel(
                            writer,
                            sheet_name=sheet_name,
                            index=False
                        )

                # Confere se o arquivo pode ser lido.
                pd.read_excel(
                    temp_filepath,
                    sheet_name=None
                )

                # Substitui o destino somente depois
                # da gravacao bem-sucedida.
                os.replace(
                    temp_filepath,
                    self.filepath
                )

                return True

            except PermissionError:
                if attempt < max_retries - 1:
                    time.sleep(0.5)
                else:
                    raise

            finally:
                if os.path.exists(temp_filepath):
                    try:
                        os.remove(temp_filepath)
                    except OSError:
                        pass
