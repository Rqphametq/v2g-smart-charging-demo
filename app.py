import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

from simulator import generate_fleet_data, get_entsoe_prices
from optimizer import optimize_smart_charging_v2g

st.set_page_config(page_title="Smart Charging & V2G Hub", layout="wide", page_icon="⚡")

# --- INITIALISATION DE L'ÉTAT POUR LE README ---
if "show_readme" not in st.session_state:
    st.session_state.show_readme = False

def toggle_readme():
    st.session_state.show_readme = not st.session_state.show_readme

# --- CACHE ---
@st.cache_data
def load_market_data(api_key):
    """Met en cache la courbe de prix pour éviter qu'elle ne soit regénérée à chaque clic"""
    # Fixer la graine aléatoire dans simulator.py ou ici garantit la stabilité du profil de secours
    np.random.seed(42)
    return get_entsoe_prices(api_key if api_key else None)

# --- BASELINE ---
def simulate_asap_baseline(fleet_df, price_df):
    """Calcule le coût ASAP et traque le pic de puissance global."""
    asap_cost = 0
    efficiency = 0.92
    site_power_kw = np.zeros(48)
    
    for _, row in fleet_df.iterrows():
        soc = row['soc_arrival']
        target = row['soc_target']
        cap = row['capacity_kwh']
        p_max = row['p_max_kw']
        
        # Charge ininterrompue dès le retour au dépôt
        for t in range(int(row['arrival_hour']), int(row['departure_hour'])):
            if soc < target:
                power_needed = min(p_max, ((target - soc) * cap) / efficiency)
                asap_cost += power_needed * price_df.loc[t, 'price_eur_kwh']
                site_power_kw[t] += power_needed
                soc += (power_needed * efficiency) / cap
                
    # On retourne la facture ET le pic de puissance maximal atteint
    return asap_cost, np.max(site_power_kw)

# --- SIDEBAR ---
st.sidebar.title("🎛️ Configuration")
st.sidebar.subheader("🔌 Flotte & Bornes")
num_vehicles = st.sidebar.slider("Nombre de véhicules", min_value=10, max_value=30, value=20, step=1)
idle_pct = st.sidebar.radio("Part de la flotte au dépôt (%)", options=[0, 5, 10, 15], index=1, horizontal=True)
battery_cap = st.sidebar.radio("Capacité Batterie (kWh)", options=[40, 50, 75, 100], index=1, horizontal=True)
p_borne = st.sidebar.radio("Puissance Borne (kW)", options=[7.4, 11.0, 22.0], index=1, horizontal=True)

st.sidebar.subheader("🏢 Infrastructure")
p_site_max = st.sidebar.slider("Raccordement Enedis (kVA)", min_value=100, max_value=300, value=200, step=10)

use_solar = st.sidebar.checkbox("Intégrer des ombrières solaires", value=False)
pv_peak_kw = st.sidebar.slider("Puissance crête solaire (kWc)", min_value=10, max_value=100, value=40, step=10) if use_solar else 0

st.sidebar.subheader("🌐 Données de Marché")
entsoe_key = st.sidebar.text_input("Clé API ENTSO-E (Optionnelle)", type="password")

# Génération / Récupération des données
fleet_df = generate_fleet_data(num_vehicles, battery_cap, p_borne, idle_pct=idle_pct)
price_df = load_market_data(entsoe_key)
from simulator import generate_solar_profile
pv_profile = generate_solar_profile(pv_peak_kw)

# --- CALCULS ---
asap_cost, max_asap_power = simulate_asap_baseline(fleet_df, price_df)
results_df, opt_cost = optimize_smart_charging_v2g(fleet_df, price_df, pv_profile, p_site_max_kw=p_site_max)

if results_df is not None:
    results_df = results_df.merge(price_df, on='hour')
    
    # Nouveaux KPIs basés sur la puissance
    peak_exceeded = max(0, max_asap_power - p_site_max)
    
    st.title("⚡ Pilotage V2G & Flexibilité de Flotte")
    
    # --- LOGIQUE DU BOUTON README ---
    if not st.session_state.show_readme:
        st.button("📖 Fonctionnement", on_click=toggle_readme)
    
    if st.session_state.show_readme:
        with st.container(border=True):
            col1, col2 = st.columns([0.9, 0.1])
            with col2:
                st.button("❌ Fermer", on_click=toggle_readme, key="close_readme")
            with col1:
                try:
                    with open("README.md", "r", encoding="utf-8") as f:
                        st.markdown(f.read())
                except FileNotFoundError:
                    st.error("Le fichier README.md est introuvable. Assurez-vous qu'il est bien à la racine de votre projet.")
        st.write("") # Petit espace après la fenêtre

    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Facture de Référence (ASAP)", f"{asap_cost:.2f} €")
    c2.metric("Facture Optimisée", f"{opt_cost:.2f} €", f"{opt_cost - asap_cost:.2f} €", delta_color="inverse")
    c3.metric("Pic de Puissance ASAP", f"{max_asap_power:.0f} kW", "Sans pilotage", delta_color="off")
    
    if peak_exceeded > 0:
        c4.metric("Dépassement Enedis Évité", f"{peak_exceeded:.0f} kW", "Pénalités sauvées", delta_color="normal")
    else:
        c4.metric("Dépassement Enedis", "Aucun", "Plafond respecté", delta_color="off")

    st.divider()

    tab1, tab2, tab3 = st.tabs(["📈 Courbe de Charge", "📊 Gantt des Véhicules", "🔋 Trajectoire SoC"])

    with tab1:
        site_agg = results_df.groupby('hour')[['charge_kw', 'discharge_kw']].sum().reset_index()
        site_agg['net_power'] = site_agg['charge_kw'] - site_agg['discharge_kw']
        
        fig1 = make_subplots(specs=[[{"secondary_y": True}]])
        fig1.add_trace(go.Bar(x=site_agg['hour'], y=site_agg['net_power'], name="Puissance Nette EV (kW)", marker_color='#1f77b4'), secondary_y=False)
        fig1.add_trace(go.Scatter(x=site_agg['hour'], y=[p_site_max]*48, name="Plafond Enedis", line=dict(color='red', dash='dash')), secondary_y=False)
        
        if use_solar:
            fig1.add_trace(go.Scatter(x=site_agg['hour'], y=pv_profile, name="Production PV (kW)", line=dict(color='green', dash='dot')), secondary_y=False)
            
        fig1.add_trace(go.Scatter(x=price_df['hour'], y=price_df['price_eur_kwh'], name="Prix Spot (€/kWh)", line=dict(color='orange')), secondary_y=True)

        fig1.update_layout(title="Profil d'appel de puissance du site vs Signal Prix", hovermode="x unified", height=500)
        fig1.update_yaxes(title_text="Puissance (kW)", secondary_y=False)
        fig1.update_yaxes(title_text="Prix (€/kWh)", secondary_y=True)
        st.plotly_chart(fig1, use_container_width=True)

    with tab2:
        def label_status(row):
            ev = fleet_df[fleet_df['id'] == row['id']].iloc[0]
            if row['hour'] < ev['arrival_hour'] or row['hour'] >= ev['departure_hour']: return "En Tournée"
            if row['charge_kw'] > 0.1: return "Charge"
            if row['discharge_kw'] > 0.1: return "V2G (Injection)"
            return "En Attente"

        results_df['status'] = results_df.apply(label_status, axis=1)
        fig2 = px.scatter(results_df, x="hour", y="id", color="status", symbol="status",
                          color_discrete_map={"En Tournée": "lightgrey", "En Attente": "lightblue", "Charge": "green", "V2G (Injection)": "red"})
        fig2.update_traces(marker=dict(size=11))
        st.plotly_chart(fig2, use_container_width=True)

    with tab3:
        selected_ev = st.selectbox("Choisir le véhicule :", fleet_df['id'].unique())
        sub_df = results_df[results_df['id'] == selected_ev]
        fig3 = go.Figure()
        fig3.add_trace(go.Scatter(x=sub_df['hour'], y=sub_df['soc']*100, mode='lines+markers', name="SoC (%)", line=dict(color='darkgreen')))
        fig3.update_layout(title=f"Profil de charge batterie - {selected_ev}", yaxis_title="SoC (%)", yaxis_range=[0, 105], height=450)
        st.plotly_chart(fig3, use_container_width=True)
else:
    st.error("Problème d'optimisation : raccordement insuffisant.")