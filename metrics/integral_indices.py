import numpy as np

def calcular_indices_integrais(e, t, dt):
    iae = np.sum(np.abs(e)) * dt
    ise = np.sum(e**2) * dt
    itae = np.sum(t * np.abs(e)) * dt
    itse = np.sum(t * (e**2)) * dt
    
    return iae, ise, itae, itse