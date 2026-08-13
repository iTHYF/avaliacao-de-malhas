import numpy as np
import control as ct

def calcular_indices_oscilacao(y, setpoint, u_unit, controlador_disc, planta_disc, t_metrica, ruido_amplitude):
    cruzamentos = np.sum(np.diff(np.sign(y - setpoint)) != 0)
    
    ruido_branco = np.random.normal(0, ruido_amplitude, len(t_metrica))
    malha_sensibilidade = ct.feedback(1, controlador_disc * planta_disc)
    
    try:
        _, y_ruido = ct.forced_response(malha_sensibilidade, t_metrica, U=ruido_branco)
        var_atual = np.var(y_ruido)
        var_mvc = np.var(ruido_branco)
        harris_index = var_atual / var_mvc if var_mvc > 0 else 1.0
    except Exception:
        harris_index = 1e6
        
    var_saida = np.var(y)
    var_controle = np.var(u_unit * setpoint)
    
    return var_saida, var_controle, cruzamentos, harris_index