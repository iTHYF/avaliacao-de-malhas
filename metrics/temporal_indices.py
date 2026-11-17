import numpy as np

def calcular_indices_temporais(y, sp_inicial, sp_final, e, t, tolerancia_rp, retornar_acomodacao=False):
    delta_sp = sp_final - sp_inicial
    if delta_sp != 0:
        if delta_sp > 0:
            overshoot = max(0.0, ((np.max(y) - sp_final) / delta_sp) * 100.0)
        else:
            overshoot = max(0.0, ((np.min(y) - sp_final) / delta_sp) * 100.0)
    else:
        overshoot = 0.0

    band = tolerancia_rp * abs(sp_final)
    idx_fora_banda = np.where(np.abs(e) > band)[0]
    
    if len(idx_fora_banda) == 0:
        t_acomodacao = 0.0
        acomodou = True
    elif idx_fora_banda[-1] == len(t) - 1:
        t_acomodacao = len(t) * (t[1] - t[0])
        acomodou = False
    else:
        t_acomodacao = t[idx_fora_banda[-1] + 1] - t[0]
        acomodou = True

    try:
        y10 = sp_inicial + 0.1 * delta_sp
        y90 = sp_inicial + 0.9 * delta_sp
        
        if delta_sp > 0:
            idx10 = np.where(y >= y10)[0][0]
            idx90 = np.where(y >= y90)[0][0]
        else:
            idx10 = np.where(y <= y10)[0][0]
            idx90 = np.where(y <= y90)[0][0]
            
        t_subida = t[idx90] - t[idx10]
    except IndexError:
        t_subida = t[-1] - t[0]
        
    tamanho_cauda = max(1, int(len(y) * 0.05))
    y_cauda = np.mean(y[-tamanho_cauda:])
    erro_regime = np.abs(sp_final - y_cauda)
    
    resultado = (overshoot, t_acomodacao, t_subida, erro_regime)
    return resultado + (acomodou,) if retornar_acomodacao else resultado
