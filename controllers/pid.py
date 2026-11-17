import control as ct

def criar_controlador_pid(Kp, Ki, Kd, Ts):
    P_cont = ct.tf([Kp], [1])
    I_cont = ct.tf([Ki], [1, 0])

    N = 10.0
    Tf = (Kd / (Kp * N)) if abs(Kp) > 0.001 else 0.01
    Tf = max(Tf, 0.001)
    D_cont = ct.tf([Kd, 0], [Tf, 1])

    controlador_cont = P_cont + I_cont + D_cont
    PI_cont = P_cont + I_cont

    controlador_disc = ct.sample_system(controlador_cont, Ts, method='tustin')
    PI_disc = ct.sample_system(PI_cont, Ts, method='tustin')

    return controlador_disc, PI_disc