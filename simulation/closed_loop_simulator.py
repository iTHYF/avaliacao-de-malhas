
import numpy as np
import control as ct
from models.delay_models import obter_atraso_discreto
from tests.setpoint_test import gerar_sp_desvio
from controllers.pid import criar_controlador_pid
from metrics.integral_indices import calcular_indices_integrais
from metrics.temporal_indices import calcular_indices_temporais
from metrics.oscillation_indices import calcular_indices_oscilacao

class AvaliadorPID:
    def __init__(self, K, tau, T, setpoint, Ts, tipo_planta=1, zeta=1.0, t_duracao=5000.0, amp_degrau=0.1, t_estab=300.0, int_testes=5.0, tolerancia_rp=0.02, sentido_teste=3, criterio_parada=2, MV0=None):
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
        if MV0 is None:
            raise ValueError("Informe MV0: o ganho K não define o ponto de operação absoluto da MV.")
        self.MV0 = float(MV0)

        self.t_ensaio = np.arange(0, self.t_duracao, self.Ts)
        self.dt = self.Ts

        self.sp_desvio = gerar_sp_desvio(self.t_ensaio, self.sentido_teste, self.t_estab, self.amp_degrau, self.int_testes)
        self.sp_ensaio = self.sp_desvio + self.setpoint
        self.segmentos = self._identificar_segmentos()
        if not any(seg["completo"] for seg in self.segmentos):
            raise ValueError(
                "Nenhum degrau tem janela completa para avaliação. "
                "Aumente a duração máxima ou reduza o intervalo entre testes."
            )

        if self.tipo_planta == 1:
            self.planta_cont_sem_atraso = ct.tf([self.K], [self.tau, 1.0])
        elif self.tipo_planta == 2:
            self.planta_cont_sem_atraso = ct.tf([self.K], [self.tau**2, 2*self.zeta*self.tau, 1.0])
        else:
            raise ValueError("Tipo de planta inválido.")

    def _identificar_segmentos(self):
        if len(self.t_ensaio) < 2:
            return []

        anterior = np.r_[0.0, self.sp_desvio[:-1]]
        indices = np.flatnonzero(~np.isclose(self.sp_desvio, anterior))
        segmentos = []
        for pos, inicio in enumerate(indices):
            fim = int(indices[pos + 1]) if pos + 1 < len(indices) else len(self.t_ensaio)
            if fim <= inicio:
                continue

            sp_inicial = self.setpoint + float(anterior[inicio])
            sp_final = self.setpoint + float(self.sp_desvio[inicio])
            instante = float(self.t_ensaio[inicio])
            if self.sentido_teste == 3:
                completo = (float(self.t_duracao) + self.Ts * 1e-8 >=
                            instante + float(self.int_testes))
            else:
                completo = True
            completo = completo and (fim - inicio >= 2)
            segmentos.append({
                "inicio": int(inicio), "fim": int(fim),
                "sp_inicial": sp_inicial, "sp_final": sp_final,
                "completo": completo,
            })
        return segmentos

    def _resultado_instavel(self):
        nomes = (
            "IAE", "ISE", "ITAE", "ITSE", "Overshoot",
            "Tempo_Acomodacao", "Tempo_Subida", "Erro_Regime",
            "Var_Saida", "Var_Controle", "Cruzamentos_SP"
        )
        resultado = {nome: 1e6 for nome in nomes}
        resultado.update({
            "status_simulacao": "instavel",
            "Overshoot_Seguranca": 1e6,
            "Esforco_Maximo": 1e6,
            "PV_Max": 1e6, "PV_Min": -1e6,
            "MV_Max": 1e6, "MV_Min": -1e6,
            "Segmentos_Completos": 0,
            "Segmentos_Parciais": len(self.segmentos),
            "Segmentos_Sem_Acomodacao": 0,
            "t_ensaio": self.t_ensaio.copy(),
            "sp_ensaio": self.sp_ensaio.copy(),
            "y_ensaio": np.full(self.t_ensaio.shape, np.nan),
            "u_ensaio": np.full(self.t_ensaio.shape, np.nan)
        })
        return resultado

    def calcular_indices(self, Kp, Ki, Kd, num_repeticoes=1):
        controlador_disc, PI_disc = criar_controlador_pid(Kp, Ki, Kd, self.Ts)
        planta_disc_sem_atraso = ct.sample_system(self.planta_cont_sem_atraso, self.Ts, method='zoh')
        atraso_disc = obter_atraso_discreto(self.T, self.Ts)

        planta_disc = planta_disc_sem_atraso * atraso_disc

        planta_ss = ct.ss(planta_disc)
        controlador_ss = ct.ss(controlador_disc)
        PI_ss = ct.ss(PI_disc)

        sys_feedback = ct.feedback(planta_ss, controlador_ss)
        malha_y = PI_ss * sys_feedback

        sys_feedback_u = ct.feedback(1, controlador_ss * planta_ss)
        malha_u = PI_ss * sys_feedback_u

        chaves_metricas = [
            "IAE", "ISE", "ITAE", "ITSE", "Overshoot",
            "Tempo_Acomodacao", "Tempo_Subida", "Erro_Regime",
            "Var_Saida", "Var_Controle", "Cruzamentos_SP"
        ]
        total_indices = {k: 0.0 for k in chaves_metricas}

        y_ensaio_acumulado = np.zeros_like(self.t_ensaio)
        u_ensaio_acumulado = np.zeros_like(self.t_ensaio)
        overshoot_seguranca = 0.0
        segmentos_completos = [seg for seg in self.segmentos if seg["completo"]]
        segmentos_efetivos = self.segmentos
        idx_parada = len(self.t_ensaio)
        sem_acomodacao_total = 0

        for rep in range(num_repeticoes):
            try:
                _, y_desvio = ct.forced_response(malha_y, self.t_ensaio, U=self.sp_desvio)
                _, u_desvio = ct.forced_response(malha_u, self.t_ensaio, U=self.sp_desvio)

            except Exception as exc:
                raise RuntimeError("Falha de execução da simulação PID; verificar biblioteca ou código.") from exc

            if (not np.all(np.isfinite(y_desvio)) or
                not np.all(np.isfinite(u_desvio)) or
                np.max(np.abs(y_desvio)) > 100):
                return self._resultado_instavel()

            PV0 = self.setpoint
            MV0 = self.MV0

            y_abs = y_desvio + PV0

            u_abs = u_desvio + MV0
            sp_abs = self.sp_ensaio

            e_abs = sp_abs - y_abs

            idx_parada = len(self.t_ensaio)
            if self.criterio_parada == 1:
                ultimo_inicio = self.segmentos[-1]["inicio"]
                banda = self.tolerancia_rp * np.abs(sp_abs)
                fora = np.flatnonzero(np.abs(e_abs[ultimo_inicio:]) > banda[ultimo_inicio:])
                if len(fora) == 0:
                    idx_parada = min(len(self.t_ensaio), ultimo_inicio + 20)
                else:
                    idx_parada = min(len(self.t_ensaio), ultimo_inicio + int(fora[-1]) + 21)

            segmentos_efetivos = []
            for seg in self.segmentos:
                if seg["inicio"] >= idx_parada:
                    continue
                efetivo = dict(seg)
                efetivo["fim"] = min(seg["fim"], idx_parada)
                if efetivo["fim"] - efetivo["inicio"] < 2:
                    continue
                if efetivo["fim"] < seg["fim"]:

                    efetivo["completo"] = (
                        self.criterio_parada == 1 and
                        idx_parada < len(self.t_ensaio)
                    )
                segmentos_efetivos.append(efetivo)
            segmentos_completos = [seg for seg in segmentos_efetivos if seg["completo"]]
            if not segmentos_completos:
                raise ValueError("Sem janelas completas no horizonte efetivo da avaliação.")

            for seg in segmentos_efetivos:
                sl = slice(seg["inicio"], seg["fim"])
                y_seg = y_abs[sl]
                u_seg = u_abs[sl]
                t_seg = self.t_ensaio[sl]
                sp_final = seg["sp_final"]
                e_seg = sp_final - y_seg

                delta = sp_final - seg["sp_inicial"]
                if delta > 0:
                    ov_observado = max(0.0, 100 * (np.max(y_seg) - sp_final) / delta)
                else:
                    ov_observado = max(0.0, 100 * (np.min(y_seg) - sp_final) / delta)
                overshoot_seguranca = max(overshoot_seguranca, ov_observado)

                if not seg["completo"]:
                    continue

                overshoot, t_acomodacao, t_subida, erro_regime, acomodou = calcular_indices_temporais(
                    y_seg, seg["sp_inicial"], sp_final, e_seg,
                    t_seg, self.tolerancia_rp, retornar_acomodacao=True
                )
                if not acomodou:
                    sem_acomodacao_total += 1
                var_saida, var_controle, cruzamentos = calcular_indices_oscilacao(
                    y_seg, sp_final, u_seg
                )
                iae, ise, itae, itse = calcular_indices_integrais(e_seg, t_seg, self.dt)

                total_indices["IAE"] += iae
                total_indices["ISE"] += ise
                total_indices["ITAE"] += itae
                total_indices["ITSE"] += itse
                total_indices["Overshoot"] += overshoot
                total_indices["Tempo_Acomodacao"] += t_acomodacao
                total_indices["Tempo_Subida"] += t_subida
                total_indices["Erro_Regime"] += erro_regime
                total_indices["Var_Saida"] += var_saida
                total_indices["Var_Controle"] += var_controle
                total_indices["Cruzamentos_SP"] += cruzamentos

            y_ensaio_acumulado += y_abs
            u_ensaio_acumulado += u_abs

        divisor = num_repeticoes * len(segmentos_completos)
        resultado_medio = {k: v / divisor for k, v in total_indices.items()}
        resultado_medio["Overshoot_Seguranca"] = overshoot_seguranca
        resultado_medio["Segmentos_Completos"] = len(segmentos_completos)
        resultado_medio["Segmentos_Parciais"] = sum(not seg["completo"] for seg in segmentos_efetivos)
        resultado_medio["status_simulacao"] = "ok"
        resultado_medio["Segmentos_Sem_Acomodacao"] = sem_acomodacao_total // num_repeticoes

        y_medio = y_ensaio_acumulado / num_repeticoes
        u_medio = u_ensaio_acumulado / num_repeticoes

        resultado_medio["t_ensaio"] = self.t_ensaio[:idx_parada]
        resultado_medio["y_ensaio"] = y_medio[:idx_parada]
        resultado_medio["u_ensaio"] = u_medio[:idx_parada]
        resultado_medio["sp_ensaio"] = self.sp_ensaio[:idx_parada]

        y_avaliado = y_medio[:idx_parada]
        u_avaliado = u_medio[:idx_parada]
        resultado_medio["Esforco_Maximo"] = np.max(np.abs(u_avaliado))
        resultado_medio["PV_Max"] = np.max(y_avaliado)
        resultado_medio["PV_Min"] = np.min(y_avaliado)
        resultado_medio["MV_Max"] = np.max(u_avaliado)
        resultado_medio["MV_Min"] = np.min(u_avaliado)

        return resultado_medio
