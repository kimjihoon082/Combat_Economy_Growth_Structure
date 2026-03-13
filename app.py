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

    df_const = pd.read_csv("constants.csv")
    df_growth = pd.read_csv("player_growth.csv")
    df_monster = pd.read_csv("monster_db.csv")

    # 수치형 변환 및 클리닝
    for col in ['E_Dmg_Ref', 'EHP_Ref', 'CP_Ref', 'Final_Crit_Dmg', 'Base_Crit_Rate']:
        if col in df_growth.columns:
            df_growth[col] = df_growth[col].apply(clean_val).astype(float)
            if col in ['Final_Crit_Dmg', 'Base_Crit_Rate']: df_growth[col] /= 100

    df_const['Value'] = df_const['Value'].apply(clean_val).astype(float)
    const_dict = dict(zip(df_const['ConstantName'], df_const['Value']))

    return const_dict, df_growth, df_monster

const, df_growth, df_monster = load_all_data()
K_VALUE = const.get('Defense_K', 2000.0)
CRIT_MAX = const.get('Crit_Rate_Max', 0.8)

# ---------------------------------------------------------
# 2. 사이드바: 유저 세팅 (보정된 부분)
# ---------------------------------------------------------
st.sidebar.header("🕹️ Player Growth & Farming")
selected_lv = st.sidebar.slider("레벨 선택 (Level)", 1, 100, 1)
ref = df_growth[df_growth['Level'] == selected_lv].iloc[0]

st.sidebar.divider()
st.sidebar.subheader("💎 장비 및 강화 시뮬레이션")

# [보정 1] 공격력 조절 단위(Step)를 레벨에 맞게 동적 설정
atk_step = max(10, int(ref['Atk'] * 0.05)) 
user_atk = st.sidebar.number_input("현재 공격력 (Attack)", value=int(ref['Atk']), step=atk_step)

# [보정 2] 명중 보상 공간을 채울 수 있는 슬라이더 추가
# 02 시트의 Reward_Space 개념을 직접 컨트롤
reward_space = int(ref['Req_Acc'] - ref['Acc'])
bonus_acc = st.sidebar.slider("추가 명중 (Bonus Acc)", 0, reward_space + 100, 0)

# [보정 3] 치명타 확률 상한 적용
user_crit_rate = st.sidebar.slider("치명타 확률 (%)", 0.0, 100.0, float(ref['Base_Crit_Rate'] * 100)) / 100
user_crit_rate = min(user_crit_rate, CRIT_MAX) # 시스템 상한 80% 적용

user_crit_dmg = st.sidebar.slider("치명타 피해량 (%)", 150.0, 300.0, float(ref['Final_Crit_Dmg'] * 100)) / 100

# ---------------------------------------------------------
# 3. 핵심 전투 연산 로직 (보정된 부분)
# ---------------------------------------------------------
def run_simulation(atk, acc_total, crit_rate, crit_dmg, lv):
    m = df_monster[df_monster['Monster_Lv'] == lv].iloc[0]
    
    # [수정] 유저의 총 명중(기본+보너스)을 몬스터 회피와 비교
    hit_rate = min(1.0, acc_total / m['Evasion_Rating']) if m['Evasion_Rating'] > 0 else 1.0
    
    crit_mult = 1 + (crit_rate * (crit_dmg - 1))
    e_dmg = atk * hit_rate * crit_mult
    
    return round(e_dmg, 2), round(hit_rate * 100, 1)

# 총 명중치 적용
current_e_dmg, current_hit_p = run_simulation(user_atk, (ref['Acc'] + bonus_acc), user_crit_rate, user_crit_dmg, selected_lv)

# ---------------------------------------------------------
# 4. 결과 대시보드
# ---------------------------------------------------------
st.title("⚔️ Combat Economy Balance Simulator")

m1, m2, m3 = st.columns(3)
with m1:
    diff_dmg = round((current_e_dmg / ref['E_Dmg_Ref'] - 1) * 100, 1)
    st.metric("실질 화력 (E.Dmg)", f"{current_e_dmg:,.1f}", f"{diff_dmg}% vs 설계표준")
with m2:
    # 명중률이 100%가 아닐 때 경고 표시
    hit_color = "normal" if current_hit_p >= 100 else "inverse"
    st.metric("현재 명중률 (Hit Rate)", f"{current_hit_p}%", delta=None, delta_color=hit_color)
with m3:
    st.metric("표준 전투력 (Planned CP)", f"{int(ref['CP_Ref']):,}")

# 시각화 차트
st.divider()
fig = go.Figure()
fig.add_trace(go.Scatter(x=df_growth['Level'], y=df_growth['E_Dmg_Ref'], name="설계 표준 (Planned)", line=dict(color='gray', dash='dot')))
fig.add_trace(go.Scatter(x=[selected_lv], y=[current_e_dmg], mode='markers+text', marker=dict(size=18, color='red', symbol='star'), name="현재 유저 세팅", text=[f"Lv.{selected_lv} 결과"], textposition="top center"))

fig.update_layout(xaxis_title="Level", yaxis_title="Effective Damage", template="plotly_white")
st.plotly_chart(fig, use_container_width=True)

# 지훈 님의 '보상 공간' 설계를 강조하는 영역
st.warning(f"💡 **Farming Guide**: 현재 레벨의 요구 명중은 **{ref['Req_Acc']}**입니다. 부족한 명중치 **{reward_space - bonus_acc}**를 장비로 채우지 못하면 화력이 급감합니다.")