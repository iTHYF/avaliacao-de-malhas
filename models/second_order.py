import control as ct

def criar_planta_segunda_ordem(K, tau, zeta, num_pade, den_pade):
    return ct.tf([K], [tau**2, 2 * zeta * tau, 1]) * ct.tf(num_pade, den_pade)