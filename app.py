import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# ---------------------------------------------------------
# 1. 환경 설정 및 데이터 로드
# ---------------------------------------------------------
st.set_page_config(page_title="RPG Balance Simulator v1.0", layout="wide")

@st.cache_data
def load_all_data():
    def clean_val(x):
        if isinstance(x, str): return x.replace(',', '').replace('%', '').strip()
        return x

    df_const = pd.read_csv("constants.csv")
    df_growth = pd.read_csv("player_growth.csv")
    df_monster = pd.read_csv("monster_db.csv")

    numeric_cols = ['E_Dmg_Ref', 'EHP_Ref', 'CP_Ref', 'Final_Crit_Dmg', 'Base_Crit_Rate', 'Atk', 'Def', 'HP', 'Acc', 'Req_Acc']
    for col in numeric_cols:
        if col in df_growth.columns:
            df_growth[col] = df_growth[col].apply(clean_val).astype(float)
            if col in ['Final_Crit_Dmg', 'Base_Crit_Rate']:
                df_growth[col] = df_growth[col].apply(lambda x: x/100 if x > 5 else x)

    df_const['Value'] = df_const['Value'].apply(clean_val).astype(float)
    const_dict = dict(zip(df_const['ConstantName'], df_const['Value'].values))
    return const_dict, df_growth, df_monster

const, df_growth, df_monster = load_all_data()
K_VALUE = const.get('Defense_K', 2000.0)

# ---------------------------------------------------------
# 2. 사이드바: 시뮬레이션 컨트롤러
# ---------------------------------------------------------
st.sidebar.header("🕹️ Player Growth Simulator")
selected_lv = st.sidebar.slider("캐릭터 레벨 (Level)", 1, 100, 1)
ref = df_growth[df_growth['Level'] == selected_lv].iloc[0]

st.sidebar.divider()
st.sidebar.subheader("⚔️ 장비 및 강화 세팅")

# [개선] 공격력을 숫자가 아닌 '강화율' 슬라이더로 조절 (직관성 강화)
atk_boost = st.sidebar.slider("공격력 강화 효율 (%)", -50, 100, 0, step=5)
current_atk = ref['Atk'] * (1 + atk_boost/100)

# [개선] 명중 보상 공간 슬라이더
reward_gap = max(0, int(ref['Req_Acc'] - ref['Acc']))
bonus_acc = 0
if reward_gap > 0:
    bonus_acc = st.sidebar.slider("장비 추가 명중 (Bonus Acc)", 0, reward_gap, 0)
else:
    st.sidebar.info("✅ 기본 명중이 충분한 구간입니다.")

# [개선] 치명타 확률 및 피해량 (목표 수치를 가이드로 제시)
user_crit_rate = st.sidebar.slider("치명타 확률 (%)", 0.0, 80.0, 0.0) / 100
user_crit_dmg = st.sidebar.slider("치명타 피해량 (%)", 150.0, 300.0, 150.0) / 100

st.sidebar.caption(f"💡 설계 표준 목표: 치피 {int(ref['Final_Crit_Dmg']*100)}% / 치확 {int(ref['Base_Crit_Rate']*100)}%")

# ---------------------------------------------------------
# 3. 전투 연산 로직
# ---------------------------------------------------------
def simulate_combat(atk, def_val, acc_total, crit_r, crit_d, lv):
    m = df_monster[df_monster['Monster_Lv'] == lv].iloc[0]
    p_dr = def_val / (def_val + K_VALUE)
    damage_base = atk * (1 - p_dr)
    hit_rate = min(1.0, acc_total / m['Evasion_Rating']) if m['Evasion_Rating'] > 0 else 1.0
    crit_mult = 1 + (crit_r * (crit_d - 1))
    return damage_base * hit_rate * crit_mult, round(hit_rate * 100, 1)

cur_dmg, cur_hit = simulate_combat(current_atk, ref['Def'], (ref['Acc'] + bonus_acc), user_crit_rate, user_crit_dmg, selected_lv)

# ---------------------------------------------------------
# 4. 메인 대시보드
# ---------------------------------------------------------
st.title("⚔️ Combat Balance Simulator")

c1, c2, c3 = st.columns(3)
with c1:
    diff = round((cur_dmg / ref['E_Dmg_Ref'] - 1) * 100, 1)
    st.metric("기대 대미지 (E.Dmg)", f"{cur_dmg:,.1f}", f"{diff}% vs 설계표준")
with c2:
    st.metric("현재 명중률", f"{cur_hit}%", f"{cur_hit-100}%" if cur_hit < 100 else "MAX")
with c3:
    st.metric("표준 전투력 (Ref.CP)", f"{int(ref['CP_Ref']):,}")

# 차트 시각화
fig = go.Figure()
fig.add_trace(go.Scatter(x=df_growth['Level'], y=df_growth['E_Dmg_Ref'], name="설계 표준 (Target)", line=dict(color='lightgray', dash='dot')))
fig.add_trace(go.Scatter(x=[selected_lv], y=[cur_dmg], mode='markers', marker=dict(size=20, color='red', symbol='star'), name="현재 세팅"))
fig.update_layout(xaxis_title="Level", yaxis_title="Effective Damage", template="plotly_white", height=450)
st.plotly_chart(fig, use_container_width=True)

# 기획자 메모
st.info(f"**Designer's Insight**: 현재 공격력 {int(current_atk):,} (기본 대비 {atk_boost}%). 명중 {int(ref['Acc']+bonus_acc)} / 요구 {int(ref['Req_Acc'])}")