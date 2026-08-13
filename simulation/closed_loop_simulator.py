import numpy as np
import control as ct
from models.delay_models import obter_pade
from models.first_order import criar_planta_primeira_ordem
from models.second_order import criar_planta_segunda_ordem
from tests.setpoint_test import gerar_sp_desvio
from controllers.pid import criar_controlador_pid
from metrics.integral_indices import calcular_indices_integrais
from metrics.temporal_indices import calcular_indices_temporais
from metrics.oscillation_indices import calcular_indices_oscilacao

class AvaliadorPID:
    def __init__(self, K, tau, T, setpoint, Ts, tipo_planta=1, zeta=1.0, t_duracao=30.0, amp_degrau=5.0, t_estab=5.0, int_testes=5.0, tolerancia_rp=0.02, sentido_teste=3, criterio_parada=2):
        self.K = K
        self.tau = tau
        self.T = T
        self.setpoint = setpoint
        self.Ts = Ts
        self.tipo_planta = tipo_planta
        self.zeta = zeta

        self.t_duracao = t_duracao
        self.amp_degrau = amp_degrau
        self.t_estab = t_estab
        self.int_testes = int_testes
        self.tolerancia_rp = tolerancia_rp
        self.sentido_teste = sentido_teste

        self.criterio_parada = criterio_parada

        self.tempo_base = max(tau * 15, T * 15, 10.0)
        self.t_metrica = np.arange(0, self.tempo_base, self.Ts)
        self.dt_metrica = self.Ts

        self.t_ensaio = np.arange(0, self.t_duracao, self.Ts)
        
        self.sp_desvio = gerar_sp_desvio(self.t_ensaio, self.sentido_teste, self.t_estab, self.amp_degrau, self.int_testes)
        self.sp_ensaio = self.sp_desvio + self.setpoint

        num_pade, den_pade = obter_pade(self.T)

        # Tipo de planta
        if self.tipo_planta == 1:
            self.planta = criar_planta_primeira_ordem(self.K, self.tau, num_pade, den_pade)
        elif self.tipo_planta == 2:
            self.planta = criar_planta_segunda_ordem(self.K, self.tau, self.zeta, num_pade, den_pade)
        else:
            raise ValueError("Tipo de planta inválido.")

    def calcular_indices(self, Kp, Ki, Kd, num_repeticoes=1):
        controlador_disc, PI_disc = criar_controlador_pid(Kp, Ki, Kd, self.Ts)
        planta_disc = ct.sample_system(self.planta, self.Ts, method='zoh')

        malha_y = ct.minreal((PI_disc * planta_disc) / (1 + controlador_disc * planta_disc), verbose=False)
        malha_u = ct.minreal(PI_disc / (1 + controlador_disc * planta_disc), verbose=False)

        chaves_metricas = [
            "IAE", "ISE", "ITAE", "ITSE", "Overshoot",
            "Tempo_Acomodacao", "Tempo_Subida", "Desvio_Media_Saida",
            "Var_Saida", "Var_Controle", "Cruzamentos_SP", "Harris_Index"
        ]
        total_indices = {k: 0.0 for k in chaves_metricas}

        y_ensaio_acumulado = np.zeros_like(self.t_ensaio)
        u_ensaio_acumulado = np.zeros_like(self.t_ensaio)


        for rep in range(num_repeticoes):
            try:
                _, y_unit = ct.step_response(malha_y, self.t_metrica)
                _, u_unit = ct.step_response(malha_u, self.t_metrica)

                if np.any(np.isnan(y_unit)) or np.any(np.isinf(y_unit)) or np.max(np.abs(y_unit)) > 100:
                    raise ValueError("Instável")
            except Exception:
                return {k: 1e6 for k in chaves_metricas}

            ruido_amplitude = 0.02 * abs(self.setpoint) if self.setpoint != 0 else 0.02
            ruido_sensor = np.random.normal(0, ruido_amplitude, len(self.t_metrica))

            y = (y_unit * self.setpoint) + ruido_sensor
            e = self.setpoint - y
            dt = self.dt_metrica
            t = self.t_metrica

            overshoot, t_acomodacao, t_subida, desvio_media_saida = calcular_indices_temporais(y, self.setpoint, e, t, self.tolerancia_rp)
            var_saida, var_controle, cruzamentos, harris_index = calcular_indices_oscilacao(y, self.setpoint, u_unit, controlador_disc, planta_disc, self.t_metrica, ruido_amplitude)
            iae, ise, itae, itse = calcular_indices_integrais(e, t, dt)

            total_indices["IAE"] += iae
            total_indices["ISE"] += ise
            total_indices["ITAE"] += itae
            total_indices["ITSE"] += itse
            total_indices["Overshoot"] += overshoot
            total_indices["Tempo_Acomodacao"] += t_acomodacao
            total_indices["Tempo_Subida"] += t_subida
            total_indices["Desvio_Media_Saida"] += desvio_media_saida
            total_indices["Var_Saida"] += var_saida
            total_indices["Var_Controle"] += var_controle
            total_indices["Cruzamentos_SP"] += cruzamentos
            total_indices["Harris_Index"] += harris_index

            try:
                _, y_desvio = ct.forced_response(malha_y, self.t_ensaio, U=self.sp_desvio)
                _, u_desvio = ct.forced_response(malha_u, self.t_ensaio, U=self.sp_desvio)
                ruido_ensaio = np.random.normal(0, ruido_amplitude, len(self.t_ensaio))
                y_ensaio_acumulado += (y_desvio + self.setpoint) + ruido_ensaio
                u_ensaio_acumulado += (u_desvio + (self.setpoint / self.K))
            except Exception:
                pass

        # =====================================================================
        # CÁLCULO DAS MÉDIAS FINAIS E CRITÉRIO DE PARADA
        # =====================================================================
        resultado_medio = {k: v / num_repeticoes for k, v in total_indices.items()}

        y_medio = y_ensaio_acumulado / num_repeticoes
        u_medio = u_ensaio_acumulado / num_repeticoes

        if self.criterio_parada == 1:
            band = self.tolerancia_rp * abs(self.setpoint)
            e_ensaio = np.abs(self.sp_ensaio - y_medio)
            idx_fora = np.where(e_ensaio > band)[0]

            if len(idx_fora) > 0:
                idx_parada = min(idx_fora[-1] + 20, len(self.t_ensaio))
            else:
                idx_parada = len(self.t_ensaio)

            resultado_medio["t_ensaio"] = self.t_ensaio[:idx_parada]
            resultado_medio["y_ensaio"] = y_medio[:idx_parada]
            resultado_medio["u_ensaio"] = u_medio[:idx_parada]
            resultado_medio["sp_ensaio"] = self.sp_ensaio[:idx_parada]

        else:
            resultado_medio["t_ensaio"] = self.t_ensaio
            resultado_medio["y_ensaio"] = y_medio
            resultado_medio["u_ensaio"] = u_medio
            resultado_medio["sp_ensaio"] = self.sp_ensaio


        resultado_medio["Esforco_Maximo"] = np.max(np.abs(u_medio))
        resultado_medio["PV_Max"] = np.max(y_medio)
        resultado_medio["PV_Min"] = np.min(y_medio)

        # NOVO: Capturando a saturação do atuador
        resultado_medio["MV_Max"] = np.max(u_medio)
        resultado_medio["MV_Min"] = np.min(u_medio)

        return resultado_medio