import numpy as np

def calcular_indices_temporais(y, setpoint, e, t, tolerancia_rp):
    overshoot = max(0.0, ((np.max(y) - setpoint) / abs(setpoint)) * 100.0) if setpoint != 0 else max(0.0, np.max(y) * 100.0)

    band = tolerancia_rp * abs(setpoint)
    idx_fora_banda = np.where(np.abs(e) > band)[0]
    t_acomodacao = t[idx_fora_banda[-1]] if len(idx_fora_banda) > 0 else t[-1]

    try:
        t10 = t[np.where(y >= 0.1 * setpoint)[0][0]]
        t90 = t[np.where(y >= 0.9 * setpoint)[0][0]]
        t_subida = t90 - t10
    except IndexError:
        t_subida = t[-1]
        
    desvio_media_saida = np.abs(setpoint - np.mean(y))
    
    return overshoot, t_acomodacao, t_subida, desvio_media_saida