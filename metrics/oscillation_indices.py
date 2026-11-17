import numpy as np


def calcular_indices_oscilacao(y, setpoint, u_unit):
    sinais = np.sign(y - setpoint)
    sinais = sinais[sinais != 0] 
    cruzamentos = np.count_nonzero(np.diff(sinais) != 0)
    var_saida = np.var(y)
    var_controle = np.var(u_unit)

    return var_saida, var_controle, cruzamentos
