import control as ct

def criar_planta_primeira_ordem(K, tau, num_pade, den_pade):
    return ct.tf([K], [tau, 1]) * ct.tf(num_pade, den_pade)