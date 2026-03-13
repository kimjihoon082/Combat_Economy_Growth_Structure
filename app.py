import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# ---------------------------------------------------------
# 1. 페이지 설정 및 데이터 로드
# ---------------------------------------------------------
st.set_page_config(page_title="RPG Combat Balance Simulator", layout="wide")

@st.cache_data
def load_all_data():
    def clean_val(x):
        if isinstance(x, str): return x.replace(',', '').replace('%', '').strip()
        return x

    # CSV 로드
    df_const = pd.read_csv("constants.csv")
    df_growth = pd.read_csv("player_growth.csv")
    df_monster = pd.read_csv("monster_db.csv")

    # 수치 데이터 클리닝
    numeric_cols = ['E_Dmg_Ref', 'EHP_Ref', 'CP_Ref', 'Final_Crit_Dmg', 'Base_Crit_Rate', 'Atk', 'Def', 'HP', 'Acc', 'Req_Acc']
    for col in numeric_cols:
        if col in df_growth.columns:
            df_growth[col] = df_growth[col].apply(clean_val).astype(float)
            if col in ['Final_Crit_Dmg', 'Base_Crit_Rate']:
                # 150(%) -> 1.5 변환 로직
                df_growth[col] = df_growth[col].apply(lambda x: x/100 if x > 5 else x)

    df_const['Value'] = df_const['Value'].apply(clean_val).astype(float)
    const_dict = dict(zip(df_const['ConstantName'], df_const['Value']))

    return const_dict, df_growth, df_monster

const, df_growth, df_monster = load_all_data()
K_VALUE = const.get('Defense_K', 2000.0)
CRIT_MAX = const.get('Crit_Rate_Max', 0.8)

# ---------------------------------------------------------
# 2. 사이드바: 유저 세팅
# ---------------------------------------------------------
st.sidebar.header("🕹️ Player Farming Simulator")
selected_lv = st.sidebar.slider("레벨 선택 (Level)", 1, 100, 1)
ref = df_growth[df_growth['Level'] == selected_lv].iloc[0]

st.sidebar.divider()
st.sidebar.subheader("💎 장비 및 강화 세팅")

# [보정] 공격력 조절 단위를 레벨 표준의 10%로 설정
atk_step = max(1, int(ref['Atk'] * 0.1))
user_atk = st.sidebar.number_input("현재 공격력 (Attack)", value=int(ref['Atk']), step=atk_step)

# [보정] 명중 슬라이더 - 에러 방지 및 범위 제한
reward_gap = max(0, int(ref['Req_Acc'] - ref['Acc']))

if reward_gap > 0:
    bonus_acc = st.sidebar.slider(
        "장비 추가 명중 (Bonus Acc)", 
        0, reward_gap, 0, 
        help=f"이 레벨의 요구 명중은 {int(ref['Req_Acc'])}입니다. (기본 명중: {int(ref['Acc'])})"
    )
else:
    # Gap이 0인 경우 슬라이더를 표시하지 않아 에러를 방지함
    st.sidebar.info("✅ 현재 레벨은 추가 명중이 필요 없습니다.")
    bonus_acc = 0

# 치명타 설정
user_crit_rate = st.sidebar.slider("치명타 확률 (%)", 0.0, float(CRIT_MAX * 100), float(ref['Base_Crit_Rate'] * 100)) / 100
user_crit_dmg = st.sidebar.slider("치명타 피해량 (%)", 150.0, 300.0, float(ref['Final_Crit_Dmg'] * 100)) / 100

# ---------------------------------------------------------
# 3. 핵심 전투 연산 (Excel 수식과 100% 동기화)
# ---------------------------------------------------------
def run_simulation(atk, def_val, acc_total, crit_rate, crit_dmg, lv):
    m = df_monster[df_monster['Monster_Lv'] == lv].iloc[0]
    
    # 플레이어 DR(방어율) 계산: 엑셀의 Damage 수식을 재현
    p_dr = def_val / (def_val + K_VALUE)
    damage_base = atk * (1 - p_dr)
    
    # 명중률 계산
    hit_rate = min(1.0, acc_total / m['Evasion_Rating']) if m['Evasion_Rating'] > 0 else 1.0
    
    # 치명타 기댓값
    crit_mult = 1 + (crit_rate * (crit_dmg - 1))
    
    # 최종 기대 대미지
    e_dmg = damage_base * hit_rate * crit_mult
    return e_dmg, round(hit_rate * 100, 1)

current_e_dmg, current_hit_p = run_simulation(
    user_atk, ref['Def'], (ref['Acc'] + bonus_acc), user_crit_rate, user_crit_dmg, selected_lv
)

# ---------------------------------------------------------
# 4. 결과 대시보드
# ---------------------------------------------------------
st.title("⚔️ Combat Economy Balance Simulator")

m1, m2, m3 = st.columns(3)
with m1:
    diff_dmg = round((current_e_dmg / ref['E_Dmg_Ref'] - 1) * 100, 1)
    st.metric("기대 대미지 (E.Dmg)", f"{current_e_dmg:,.1f}", f"{diff_dmg}% vs 설계표준")

with m2:
    hit_delta = current_hit_p - 100
    st.metric("현재 명중률 (Hit Rate)", f"{current_hit_p}%", f"{hit_delta}%" if hit_delta < 0 else "MAX")

with m3:
    st.metric("표준 전투력 (Planned CP)", f"{int(ref['CP_Ref']):,}")

# 시각화 차트
st.divider()
fig = go.Figure()
fig.add_trace(go.Scatter(x=df_growth['Level'], y=df_growth['E_Dmg_Ref'], name="설계 표준 (Planned)", line=dict(color='lightgray', dash='dot')))
fig.add_trace(go.Scatter(x=[selected_lv], y=[current_e_dmg], mode='markers', marker=dict(size=18, color='red', symbol='star'), name="현재 세팅"))
fig.update_layout(xaxis_title="Character Level", yaxis_title="E.Dmg (기대 대미지)", template="plotly_white", height=450)
st.plotly_chart(fig, use_container_width=True)

# 기획자 통찰 (Designer's Insight)
status_msg = "✅ 설계된 표준 대미지에 도달했습니다." if diff_dmg >= -0.5 else "⚠️ 장비 파밍을 통해 보상 공간을 채워야 합니다."
st.info(f"**Designer's Insight**: {status_msg} (목표 명중: {int(ref['Req_Acc'])} / 현재 명중: {int(ref['Acc'] + bonus_acc)})")