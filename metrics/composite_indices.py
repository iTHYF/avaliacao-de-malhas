
import numpy as np


class DecisorDeMetricas:
    def __init__(self):
        self.nomes_indices = [
            "IAE",
            "ISE",
            "ITAE",
            "ITSE",
            "Overshoot",
            "Tempo_Acomodacao",
            "Tempo_Subida",
            "Erro_Regime",
            "Var_Saida",
            "Var_Controle",
            "Cruzamentos_SP"
        ]


        self.W = np.array([
            [0.2, 0.4, 0.8,  0.8, 0.2, 0.5,  0.5, 0.2,  0.5, 0.3, 0.1,  0.8, 0.2, 0.1],  # IAE

            [0.8, 0.6, 0.1,  0.4, 0.4, 0.4,  0.5, 0.2,  0.4, 0.4, 0.4,  0.4, 0.6, 0.2],  # ISE

            [0.2, 0.2, 0.2,  0.1, 1.0, 0.5,  0.5, 0.5,  0.2, 0.4, 0.6,  1.0, 0.1, 0.0],  # ITAE

            [0.5, 0.3, 0.1,  0.1, 0.8, 0.5,  0.5, 0.5,  0.2, 0.5, 0.8,  0.8, 0.2, 0.0],  # ITSE

            [1.0, 0.7, 0.0,  0.2, 0.2, 0.2,  0.5, 0.5,  1.0, 0.5, 0.0,  0.2, 0.2, 0.2],  # Overshoot

            [0.5, 0.3, 0.1,  0.4, 0.8, 0.6,  0.5, 0.5,  0.8, 0.5, 0.2,  0.5, 0.5, 0.2],  # Tempo_Acomodacao

            [0.1, 0.3, 0.8,  1.0, 0.1, 0.5,  0.5, 0.5,  0.1, 0.5, 1.0,  0.1, 0.1, 0.2],  # Tempo_Subida

            [0.2, 0.2, 0.2,  0.2, 0.2, 0.2,  0.5, 0.5,  0.2, 0.2, 0.2,  0.8, 0.2, 0.0],  # Erro_Regime

            [0.8, 0.5, 0.1,  0.2, 0.2, 0.2,  0.2, 0.6,  1.0, 0.5, 0.1,  0.2, 0.2, 0.2],  # Var_Saida

            [0.1, 0.1, 0.1,  0.1, 0.1, 0.1,  0.1, 1.0,  0.8, 0.5, 0.2,  0.1, 0.1, 0.1],  # Var_Controle

            [0.5, 0.5, 0.1,  0.1, 0.8, 0.4,  0.1, 1.0,  1.0, 0.5, 0.1,  0.8, 0.2, 0.2]   # Cruzamentos_SP
        ])

    def obter_pesos(
        self,
        p_overshoot,
        p_comportamento,
        p_atuador,
        p_transitorio,
        p_permanente
    ):
        x = np.zeros(14)

        x[p_overshoot - 1] = 1.0
        x[3 + p_comportamento - 1] = 1.0
        x[6 + p_atuador] = 1.0
        x[8 + p_transitorio - 1] = 1.0
        x[11 + p_permanente - 1] = 1.0

        pesos_brutos = np.dot(self.W, x)

        pesos_normalizados = pesos_brutos / np.sum(pesos_brutos)

        return dict(zip(self.nomes_indices, pesos_normalizados))
