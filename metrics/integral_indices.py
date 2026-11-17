import numpy as np

def calcular_indices_integrais(e, t, dt):
    # O tempo deve ser relativo ao instante do degrau para ITAE e ITSE.
    # Como 't' agora começa em 300s (ou o t_estab que for escolhido), 
    # subtraímos t[0] para que a contagem do peso inicie em zero.
    t_relativo = t - t[0]
    
    iae = np.sum(np.abs(e)) * dt
    ise = np.sum(e**2) * dt
    itae = np.sum(t_relativo * np.abs(e)) * dt
    itse = np.sum(t_relativo * (e**2)) * dt
    
    return iae, ise, itae, itse