import control as ct

def obter_pade(T):
    return ct.pade(T, n=2, numdeg=0) if T > 0 else ([1], [1])