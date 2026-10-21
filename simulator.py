import pandas as pd
import numpy as np

def get_entsoe_prices(api_key=None):
    if api_key:
        try:
            from entsoe import EntsoePandasClient
            client = EntsoePandasClient(api_key=api_key)
            start = pd.Timestamp.now(tz='Europe/Paris').floor('D')
            end = start + pd.Timedelta(days=2)
            ts = client.query_day_ahead_prices('FR', start=start, end=end)
            prices_eur_kwh = (ts.values / 1000.0)[:48]
            if len(prices_eur_kwh) == 48:
                return pd.DataFrame({"hour": np.arange(48), "price_eur_kwh": prices_eur_kwh})
        except Exception:
            pass

    # Profil simulé assagi (Spread d'environ 8 centimes)
    hours = np.arange(48)
    base_curve = 0.16 + 0.03 * np.sin((hours - 7) * np.pi / 12) + 0.01 * np.sin((hours - 18) * np.pi / 6)
    noise = np.random.normal(0, 0.005, 48) 
    prices = np.clip(base_curve + noise, 0.12, 0.22)
    return pd.DataFrame({"hour": hours, "price_eur_kwh": prices})

def generate_solar_profile(pv_peak_kw=0):
    pv_production = np.zeros(48)
    if pv_peak_kw > 0:
        for day in [0, 1]:
            for h in range(24):
                if 8 <= h <= 18:
                    pv_production[day * 24 + h] = pv_peak_kw * np.sin((h - 8) * np.pi / 10)
    return pv_production

def generate_fleet_data(num_vehicles=20, battery_cap_kwh=75, charger_pmax_kw=11.0, idle_pct=0, seed=42):
    np.random.seed(seed)
    vehicles = []
    
    # Calcul du nombre de véhicules immobilisés au dépôt
    num_idle = int(num_vehicles * (idle_pct / 100.0))
    
    for i in range(num_vehicles):
        is_idle = i < num_idle
        
        if is_idle:
            # Véhicule "Batterie domestique" (Présent de l'heure 0 à 48)
            arrival_time = 0
            departure_time = 48
            soc_arr = np.random.uniform(0.40, 0.80) # Niveau de batterie aléatoire
            soc_tgt = 0.50 # Pas de besoin précis à la fin des 48h
            v_id = f"EV_{i+1:02d} (Fixe)"
        else:
            # Véhicule "Standard" en tournée
            arrival_time = np.random.randint(16, 20)
            departure_time = np.random.randint(6, 10) + 24
            soc_arr = np.random.uniform(0.25, 0.50)
            soc_tgt = np.random.uniform(0.75, 0.85)
            v_id = f"EV_{i+1:02d}"

        vehicles.append({
            "id": v_id,
            "capacity_kwh": float(battery_cap_kwh),
            "p_max_kw": float(charger_pmax_kw),
            "soc_arrival": soc_arr,
            "soc_target": soc_tgt,
            "arrival_hour": arrival_time,
            "departure_hour": departure_time
        })
    return pd.DataFrame(vehicles)