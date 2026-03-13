import math
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# -----------------------------
# Config
# -----------------------------
st.set_page_config(page_title="Guardian Verifier", layout="wide")

# -----------------------------
# Data Load
# -----------------------------
@st.cache_data
def load_all():
    try:
        scn = pd.read_csv("guardian_scenarios.csv")
        eff = pd.read_csv("module_effects.csv")
        upg = pd.read_csv("upgrade_candidates.csv")
        price = pd.read_csv("market_prices.csv")
        presets = pd.read_csv("presets.csv")
    except FileNotFoundError:
        scn = pd.read_csv("data/guardian_scenarios.csv")
        eff = pd.read_csv("data/module_effects.csv")
        upg = pd.read_csv("data/upgrade_candidates.csv")
        price = pd.read_csv("data/market_prices.csv")
        presets = pd.read_csv("data/presets.csv")
    return scn, eff, upg, price, presets

df_scn, df_eff, df_upg, df_price, df_presets = load_all()
prices = {r["item_id"]: float(r["price_gold"]) for _, r in df_price.iterrows()}

# -----------------------------
# Helpers
# -----------------------------
def get_effect(df_eff_, module, level):
    row = df_eff_[(df_eff_["module"] == module) & (df_eff_["level"] == level)]
    if row.empty:
        raise ValueError(f"Missing effect: {module} level {level}")
    return row.iloc[0]

def calc_epi(params, support_buff=False):
    dps_m = 1.0
    ehp_m = 1.0
    u_add = 0.0
    
    for m in ["enhance", "gems", "engrave", "ark", "elixir"]:
        row = get_effect(df_eff, m, params[m])
        dps_m *= row["dps_mult"]
        ehp_m *= row["ehp_mult"]
        u_add += row["uptime_add"]
    
    # 서포터 버프 적용 (공격력 증가 + 피해 증폭 등을 고려하여 딜량 약 2배로 계산)
    if support_buff:
        dps_m *= 2.0 
    
    base_epi = dps_m * 1000
    final_epi = base_epi * (1 + u_add) * (ehp_m ** 0.2)
    return {
        "epi": final_epi,
        "dps_m": dps_m,
        "ehp_m": ehp_m,
        "u_add": u_add
    }

def simulate_cr(epi, boss_hp, time_limit, req_epi):
    k = 0.005 
    x = epi - req_epi
    cr10 = 1 / (1 + math.exp(-k * x))
    x5 = epi - (req_epi * 1.4)
    cr5 = 1 / (1 + math.exp(-k * x5))
    return cr10, cr5

# -----------------------------
# Sidebar
# -----------------------------
st.sidebar.title("Character Settings")
sel_scenario = st.sidebar.selectbox("Target Guardian", df_scn["name"].unique())
df_target_scn = df_scn[df_scn["name"] == sel_scenario]
sel_lv = st.sidebar.selectbox("Level / Difficulty", df_target_scn["ilv_gate"].unique())

row_scn = df_target_scn[df_target_scn["ilv_gate"] == sel_lv].iloc[0]

st.sidebar.divider()
st.sidebar.subheader("Party Settings")
# [추가] 서포터 버프 스위치
support_on = st.sidebar.toggle("Support Buff (Party Play)", value=False, help="서포터의 공격력 증가 및 피해 증폭 버프를 적용합니다 (약 2배 효율)")

st.sidebar.divider()
st.sidebar.subheader("Growth Modules")
p_enhance = st.sidebar.slider("Enhance Level", 0, 5, 2)
p_gems = st.sidebar.slider("Gems Level", 0, 5, 2)
p_engrave = st.sidebar.slider("Engrave Level", 0, 5, 2)
p_ark = st.sidebar.slider("Ark Passive", 0, 5, 2)
p_elixir = st.sidebar.slider("Elixir", 0, 5, 2)

params = {"enhance": p_enhance, "gems": p_gems, "engrave": p_engrave, "ark": p_ark, "elixir": p_elixir}

# -----------------------------
# Logic
# -----------------------------
res = calc_epi(params, support_buff=support_on)
cr10, cr5 = simulate_cr(res["epi"], row_scn["boss_hp"], row_scn["time_limit_sec"], row_scn["required_epi"])
res["cr10"] = cr10
res["cr5"] = cr5

# -----------------------------
# UI - Dashboard
# -----------------------------
st.title(f"Balance Verifier: {sel_scenario} ({sel_lv})")
if support_on:
    st.info("📢 서포터 버프가 적용 중입니다. 파티 플레이 환경의 딜 기대값이 시뮬레이션에 반영됩니다.")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Current EPI", f"{res['epi']:.0f}", delta=f"{(res['epi'] - calc_epi(params, False)['epi']):.0f} (Buff)" if support_on else None)
col2.metric("Required EPI", f"{row_scn['required_epi']}")
col3.metric("Clear Rate (10m)", f"{res['cr10']*100:.1f}%")
col4.metric("Clear Rate (5m)", f"{res['cr5']*100:.1f}%")

st.divider()

# Curves Section
st.subheader("Success Probability Curves")

current_epi = res["epi"]
x_min = max(0, min(current_epi * 0.4, row_scn["required_epi"] * 0.4))
x_max = max(current_epi * 1.6, row_scn["required_epi"] * 1.6)
x_range = np.linspace(x_min, x_max, 100)

curve_data = []
for x in x_range:
    c10, c5 = simulate_cr(x, row_scn["boss_hp"], row_scn["time_limit_sec"], row_scn["required_epi"])
    curve_data.append({"EPI": x, "CR10": c10, "CR5": c5})
df_curve = pd.DataFrame(curve_data)

fig1 = go.Figure()
fig1.add_trace(go.Scatter(x=df_curve["EPI"], y=df_curve["CR10"]*100, name="CR10 (10분)", line=dict(color='royalblue', width=2)))
fig1.add_trace(go.Scatter(x=df_curve["EPI"], y=df_curve["CR5"]*100, name="CR5 (5분)", line=dict(color='firebrick', width=2, dash='dot')))

fig1.add_trace(go.Scatter(
    x=[res["epi"]], y=[res["cr10"]*100], 
    name="내 현재 위치", 
    mode="markers+text",
    text=["Buff ON" if support_on else "Solo"],
    textposition="top center",
    marker=dict(size=18, color='gold' if support_on else 'silver', symbol='diamond', line=dict(width=2, color='black'))
))

fig1.add_hline(y=80, line_dash="dash", line_color="green", annotation_text="안정적 클리어선 (80%)")

fig1.update_layout(
    xaxis_title="종합 전투력 지표 (EPI)", 
    yaxis_title="클리어 확률 (%)",
    hovermode="x unified"
)
st.plotly_chart(fig1, use_container_width=True)

# -----------------------------
# ROI Analysis
# -----------------------------
st.divider()
st.subheader("Next Upgrade Recommendation (ROI Analysis)")
reco_data = []
for m in ["enhance", "gems", "engrave", "ark", "elixir"]:
    curr_lv = params[m]
    if curr_lv < 5:
        try:
            u_row = df_upg[(df_upg["module"] == m) & (df_upg["from_level"] == curr_lv)].iloc[0]
            cost = u_row["gold_cost"]
            eff_curr = get_effect(df_eff, m, curr_lv)["dps_mult"]
            eff_next = get_effect(df_eff, m, curr_lv + 1)["dps_mult"]
            dmg_inc = (eff_next / eff_curr - 1) * 100
            reco_data.append({
                "Module": m.capitalize(), "Target": f"Lv.{curr_lv} → {curr_lv+1}",
                "Gold Cost": f"{cost:,}", "DMG Increase": f"{dmg_inc:.2f}%",
                "Cost per 1%": int(cost / dmg_inc)
            })
        except: continue

if reco_data:
    df_reco = pd.DataFrame(reco_data).sort_values("Cost per 1%")
    st.table(df_reco)