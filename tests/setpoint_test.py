import numpy as np

def gerar_sp_desvio(t_ensaio, sentido_teste, t_estab, amp_degrau, int_testes):
    sp_desvio = np.zeros_like(t_ensaio)

    if sentido_teste == 1:
        step_times = [t_estab]
        step_amplitudes = [amp_degrau]
    elif sentido_teste == 2:
        step_times = [t_estab]
        step_amplitudes = [-amp_degrau]
    else:
        step_times = [
            t_estab,
            t_estab + int_testes,
            t_estab + (2 * int_testes),
            t_estab + (3 * int_testes)
        ]
        step_amplitudes = [amp_degrau, -amp_degrau, -amp_degrau, amp_degrau]

    for step_time, step_amplitude in zip(step_times, step_amplitudes):
        sp_desvio[t_ensaio >= step_time] += step_amplitude

    return sp_desvio