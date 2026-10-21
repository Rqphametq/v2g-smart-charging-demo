import pandas as pd
from ortools.linear_solver import pywraplp

def optimize_smart_charging_v2g(fleet_df, price_df, pv_profile_kw, p_site_max_kw=150.0, dt=1.0):
    solver = pywraplp.Solver.CreateSolver('SCIP')
    if not solver:
        return None, None

    horizon = 48
    efficiency = 0.92
    deg_penalty = 0.02
    soc_min_v2g = 0.20

    P_charge = {}
    P_discharge = {}
    is_charging = {}
    soc = {}

    for v in fleet_df['id']:
        p_max = fleet_df.loc[fleet_df['id'] == v, 'p_max_kw'].values[0]
        for t in range(horizon):
            P_charge[v, t] = solver.NumVar(0, p_max, f'Pc_{v}_{t}')
            P_discharge[v, t] = solver.NumVar(0, p_max, f'Pd_{v}_{t}')
            is_charging[v, t] = solver.IntVar(0, 1, f'ic_{v}_{t}')
            soc[v, t] = solver.NumVar(0, 1.0, f'soc_{v}_{t}')
        soc[v, horizon] = solver.NumVar(0, 1.0, f'soc_{v}_{horizon}')

    P_import = {}
    P_export = {}
    for t in range(horizon):
        P_import[t] = solver.NumVar(0, p_site_max_kw, f'P_imp_{t}')
        P_export[t] = solver.NumVar(0, p_site_max_kw, f'P_exp_{t}')

    for _, row in fleet_df.iterrows():
        v = row['id']
        cap = row['capacity_kwh']
        arr = int(row['arrival_hour'])
        dep = int(row['departure_hour'])
        p_max = row['p_max_kw']

        solver.Add(soc[v, arr] == row['soc_arrival'])
        solver.Add(soc[v, dep] >= row['soc_target'])

        for t in range(horizon):
            solver.Add(P_charge[v, t] <= p_max * is_charging[v, t])
            solver.Add(P_discharge[v, t] <= p_max * (1 - is_charging[v, t]))

            if t < arr or t >= dep:
                solver.Add(P_charge[v, t] == 0)
                solver.Add(P_discharge[v, t] == 0)
            else:
                safe_limit = min(soc_min_v2g, row['soc_arrival'])
                solver.Add(soc[v, t] >= safe_limit)

            solver.Add(soc[v, t+1] == soc[v, t] + (P_charge[v, t] * efficiency - P_discharge[v, t] / efficiency) * dt / cap)

    for t in range(horizon):
        net_ev_power = solver.Sum(P_charge[v, t] - P_discharge[v, t] for v in fleet_df['id'])
        solver.Add(P_import[t] - P_export[t] == net_ev_power - pv_profile_kw[t])

    objective = solver.Objective()
    for t in range(horizon):
        price = price_df.loc[t, 'price_eur_kwh']
        objective.SetCoefficient(P_import[t], price * dt)
        objective.SetCoefficient(P_export[t], -price * dt)
        for v in fleet_df['id']:
            objective.SetCoefficient(P_discharge[v, t], deg_penalty * dt)

    objective.SetMinimization()
    status = solver.Solve()

    if status == pywraplp.Solver.OPTIMAL:
        results = []
        for t in range(horizon):
            for v in fleet_df['id']:
                results.append({
                    'hour': t,
                    'id': v,
                    'charge_kw': P_charge[v, t].solution_value(),
                    'discharge_kw': P_discharge[v, t].solution_value(),
                    'soc': soc[v, t].solution_value()
                })
        return pd.DataFrame(results), objective.Value()
    return None, None