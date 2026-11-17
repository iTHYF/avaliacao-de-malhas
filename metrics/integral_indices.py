import numpy as np

def calcular_indices_integrais(e, t, dt):
    t_relativo = t - t[0]
    
    iae = np.sum(np.abs(e)) * dt
    ise = np.sum(e**2) * dt
    itae = np.sum(t_relativo * np.abs(e)) * dt
    itse = np.sum(t_relativo * (e**2)) * dt
    
    return iae, ise, itae, itse