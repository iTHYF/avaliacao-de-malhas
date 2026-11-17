import control as ct

def obter_atraso_discreto(atraso, Ts):
    d = int(atraso / Ts)
    numerador = [1]
    denominador = [1] + [0] * d
    return ct.tf(numerador, denominador, Ts)