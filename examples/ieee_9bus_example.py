# sim_9bus_dae_fault_fixed.py
import numpy as np
from pycontroldae.core import Module, System, Simulator, at_time, DataProbe

nbus = 9
ngen = 3
gen_buses = [0, 1, 2]

E_mag = [1.10, 1.05, 1.02]
Xd_prime = [0.20, 0.25, 0.30]
H = [3.5, 3.0, 2.8]
D_damp = [0.01, 0.015, 0.012]
Pm = [0.7, 1.0, 0.9]

lines = [
    (0, 3, 0.02, 0.06, 0.0),
    (3, 4, 0.08, 0.24, 0.0),
    (1, 4, 0.06, 0.18, 0.0),
    (1, 5, 0.06, 0.18, 0.0),
    (2, 5, 0.01, 0.03, 0.0),
    (5, 6, 0.05, 0.15, 0.0),
    (6, 7, 0.02, 0.06, 0.0),
    (7, 8, 0.03, 0.09, 0.0),
    (8, 3, 0.04, 0.12, 0.0),
]

S_load = np.zeros(nbus, dtype=complex)
S_load[3] = 0.9 + 0.3j
S_load[4] = 1.0 + 0.35j
S_load[5] = 0.9 + 0.30j
S_load[6] = 0.6 + 0.2j
S_load[7] = 0.4 + 0.15j
S_load[8] = 0.45 + 0.15j

fault_bus = 4
R_fault_initial = 1e6
R_fault_short = 1e-3

t_start = 0.0
t_end = 20.0
dt_out = 1e-3

def build_Ybus(nbus, lines):
    Y = np.zeros((nbus, nbus), dtype=complex)
    for (f, t, r, x, b) in lines:
        z = complex(r, x)
        y = 1.0 / z
        Y[f, t] -= y
        Y[t, f] -= y
        Y[f, f] += y + 1j * b / 2.0
        Y[t, t] += y + 1j * b / 2.0
    return Y

Ybus = build_Ybus(nbus, lines)
Gbus = Ybus.real
Bbus = Ybus.imag

class NineBusDAE(Module):
    def __init__(self, name="ninebus"):
        super().__init__(name)

        # differential states: delta, omega for each generator
        for i in range(ngen):
            self.add_state(f"delta{i+1}", float(0.0))
        for i in range(ngen):
            self.add_state(f"omega{i+1}", float(0.0))

        # --- IMPORTANT: use add_state for algebraic variables (Vr, Vi) ---
        for k in range(nbus):
            self.add_state(f"Vr{k+1}", float(1.0))
            self.add_state(f"Vi{k+1}", float(0.0))

        # params: Ybus entries
        for i in range(nbus):
            for j in range(nbus):
                self.add_param(f"G{i+1}{j+1}", float(Gbus[i, j]))
                self.add_param(f"B{i+1}{j+1}", float(Bbus[i, j]))

        # load params
        for k in range(nbus):
            self.add_param(f"P_load{k+1}", float(S_load[k].real))
            self.add_param(f"Q_load{k+1}", float(S_load[k].imag))

        # generator params
        for i in range(ngen):
            self.add_param(f"E{i+1}", float(E_mag[i]))
            self.add_param(f"Xd_p{i+1}", float(Xd_prime[i]))
            self.add_param(f"H{i+1}", float(H[i]))
            self.add_param(f"D{i+1}", float(D_damp[i]))
            self.add_param(f"Pm{i+1}", float(Pm[i]))
            # keep gen_buses in python side (we already have gen_buses list)

        # fault param
        self.add_param("R_fault", float(R_fault_initial))
        self.add_param("fault_bus", int(fault_bus)+1)

        # ---- swing equations: D(delta)=omega ; D(omega)= (Pm - Pe - D*omega)/(2H)
        for i in range(ngen):
            self.add_equation(f"D(delta{i+1}) ~ omega{i+1}")

        for i in range(ngen):
            bus = gen_buses[i] + 1  # 1-based
            # Pe from generator current as function of terminal Vr/Vi and internal E∠δ
            swing_eq = (
                f"D(omega{i+1}) ~ ( Pm{i+1} - ("
                f" Vr{bus} * ((E{i+1}*sin(delta{i+1}) - Vi{bus}) / Xd_p{i+1})"
                f" + Vi{bus} * (-(E{i+1}*cos(delta{i+1}) - Vr{bus}) / Xd_p{i+1})"
                f") - D{i+1}*omega{i+1} ) / (2.0 * H{i+1})"
            )
            self.add_equation(swing_eq)

        # ---- nodal algebraic equations (real & imag)
        for k in range(1, nbus+1):
            lhs_real_terms = []
            lhs_imag_terms = []
            for j in range(1, nbus+1):
                lhs_real_terms.append(f"G{k}{j}*Vr{j} - B{k}{j}*Vi{j}")
                lhs_imag_terms.append(f"G{k}{j}*Vi{j} + B{k}{j}*Vr{j}")
            lhs_real = " + ".join(lhs_real_terms)
            lhs_imag = " + ".join(lhs_imag_terms)

            # generator injection at this bus
            igen_real_terms = []
            igen_imag_terms = []
            for gi in range(ngen):
                gbus = gen_buses[gi] + 1
                if gbus == k:
                    igen_real_terms.append(f"(E{gi+1}*sin(delta{gi+1}) - Vi{gbus}) / Xd_p{gi+1}")
                    igen_imag_terms.append(f"-(E{gi+1}*cos(delta{gi+1}) - Vr{gbus}) / Xd_p{gi+1}")
            igen_real = " + ".join(igen_real_terms) if igen_real_terms else "0.0"
            igen_imag = " + ".join(igen_imag_terms) if igen_imag_terms else "0.0"

            Pk = f"P_load{k}"
            Qk = f"Q_load{k}"
            den = f"(Vr{k}*Vr{k} + Vi{k}*Vi{k})"
            iload_real = f"(({Pk})*Vr{k} + ({Qk})*Vi{k}) / {den}"
            iload_imag = f"-(({Pk})*Vi{k} + ({Qk})*Vr{k}) / {den}"

            gf = "(1.0 / R_fault)"
            ifault_real = f"{gf} * Vr{k}"
            ifault_imag = f"{gf} * Vi{k}"

            rhs_real = f"({igen_real}) - ({iload_real}) - ({ifault_real})"
            rhs_imag = f"({igen_imag}) - ({iload_imag}) - ({ifault_imag})"

            eq_real = f"{lhs_real} - ({rhs_real}) ~ 0.0"
            eq_imag = f"{lhs_imag} - ({rhs_imag}) ~ 0.0"

            self.add_equation(eq_real)
            self.add_equation(eq_imag)

# ---- build system and simulate ----
system = System("nine_bus_system")
nb_module = NineBusDAE("ninebus")
system.add_module(nb_module)

def fault_close_cb(integrator):
    print("[event] Fault close at t =", getattr(integrator, "t", "unknown"))
    return { "ninebus.R_fault": float(R_fault_short) }

def fault_clear_cb(integrator):
    print("[event] Fault clear at t =", getattr(integrator, "t", "unknown"))
    return { "ninebus.R_fault": float(R_fault_initial) }

system.add_event(at_time(15.0, fault_close_cb))
system.add_event(at_time(15.1, fault_clear_cb))

probe_vars = []
probe_names = []
for i in range(ngen):
    probe_vars += [f"ninebus.delta{i+1}", f"ninebus.omega{i+1}"]
    probe_names += [f"delta{i+1}", f"omega{i+1}"]
for k in range(1, nbus+1):
    probe_vars += [f"ninebus.Vr{k}", f"ninebus.Vi{k}"]
    probe_names += [f"Vr{k}", f"Vi{k}"]

probe = DataProbe(variables=probe_vars, names=probe_names, description="gen states + bus voltages")

system.compile()
sim = Simulator(system)
print("Start simulation 0->20 s; fault at 15.0s lasting 0.1s...")

res = sim.run(t_span=(t_start, t_end), dt=dt_out, probes=probe, solver="Rodas5")

df = res.to_dataframe(include_probes=True)
df.to_csv("9bus_dae_fault_result_fixed.csv", index=False)
print("Saved results to 9bus_dae_fault_result_fixed.csv")
