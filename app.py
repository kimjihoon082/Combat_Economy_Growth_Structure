import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import math

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
            df_growth[col] = pd.to_numeric(df_growth[col].apply(clean_val), errors='coerce')
            if col in ['Final_Crit_Dmg', 'Base_Crit_Rate']:
                df_growth[col] = df_growth[col].apply(lambda x: x/100 if x > 5 else x)

    df_const['Value'] = pd.to_numeric(df_const['Value'].apply(clean_val), errors='coerce')
    const_dict = dict(zip(df_const['ConstantName'], df_const['Value'].values))
    return const_dict, df_growth, df_monster

const, df_growth, df_monster = load_all_data()
CRIT_RATE_TARGET = float(const.get('Crit_Rate_Max', 0.8))

# ---------------------------------------------------------
# 2. 사이드바: 시뮬레이션 컨트롤러 (초기화 로직 포함)
# ---------------------------------------------------------
st.sidebar.header("🕹️ Player Growth Simulator")
selected_lv = st.sidebar.slider("캐릭터 레벨 (Level)", 1, 100, 1)
ref = df_growth[df_growth['Level'] == selected_lv].iloc[0]
mon = df_monster[df_monster['Monster_Lv'] == selected_lv].iloc[0]

st.sidebar.divider()
st.sidebar.subheader("⚔️ 장비 및 강화 세팅")

# [핵심 보정] key에 selected_lv를 넣어 레벨 변경 시 모든 슬라이더 초기화
base_atk = int(ref['Atk'])
user_atk = st.sidebar.slider(
    "현재 공격력 (Attack)", 
    base_atk, base_atk * 10, base_atk, 
    key=f"atk_{selected_lv}", # 레벨 변경 시 리셋
    help=f"기본 공격력 {base_atk:,}의 최대 10배까지 시뮬레이션"
)

reward_gap = max(0, int(ref['Req_Acc'] - ref['Acc']))
bonus_acc = 0
if reward_gap > 0:
    bonus_acc = st.sidebar.slider("장비 추가 명중 (Bonus Acc)", 0, reward_gap, 0, key=f"acc_{selected_lv}")
else:
    st.sidebar.info("✅ 기본 명중이 충분한 구간입니다.")

user_crit_rate = st.sidebar.slider("치명타 확률 (%)", 0, int(CRIT_RATE_TARGET * 100), 0, key=f"cr_{selected_lv}") / 100
user_crit_dmg = st.sidebar.slider("치명타 피해 (%)", 150, 300, 150, key=f"cd_{selected_lv}") / 100

# [디자인 보정] 가이드 박스 폰트 크기 위계 조정
st.sidebar.divider()
st.sidebar.markdown(f"""
<div style="background-color: #31333F; padding: 20px; border-radius: 12px; border: 1px solid #464855;">
    <p style="color: #FFFFFF; font-size: 1.2em; font-weight: 700; margin-bottom: 15px; border-left: 4px solid #FF4B4B; padding-left: 10px;">
        🎯 레벨 {selected_lv} 설계 목표
    </p>
    <div style="color: #FFFFFF; font-size: 1.1em; line-height: 1.8; margin-left: 14px;">
        치명타 확률: <b>{int(CRIT_RATE_TARGET*100)}%</b><br>
        치명타 피해: <b>{int(ref['Final_Crit_Dmg']*100)}%</b>
    </div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 3. 전투 연산 로직 (HTK 포함)
# ---------------------------------------------------------
def simulate_combat(atk, acc_total, crit_r, crit_d, lv):
    m = df_monster[df_monster['Monster_Lv'] == lv].iloc[0]
    hit_rate = min(1.0, acc_total / m['Evasion_Rating']) if m['Evasion_Rating'] > 0 else 1.0
    crit_mult = 1 + (crit_r * (crit_d - 1))
    e_dmg = atk * hit_rate * crit_mult
    
    # HTK (Hits to Kill) 계산
    htk = math.ceil(m['HP'] / e_dmg) if e_dmg > 0 else 0
    return e_dmg, int(hit_rate * 100), htk

cur_dmg, cur_hit, cur_htk = simulate_combat(user_atk, (ref['Acc'] + bonus_acc), user_crit_rate, user_crit_dmg, selected_lv)

# ---------------------------------------------------------
# 4. 메인 대시보드
# ---------------------------------------------------------
st.title("⚔️ Combat Balance Simulator")

c1, c2, c3, c4 = st.columns(4) # HTK를 위해 4열로 확장
with c1:
    diff = round((cur_dmg / ref['E_Dmg_Ref'] - 1) * 100, 1)
    st.metric("기대 대미지 (E.Dmg)", f"{int(cur_dmg):,}", f"{diff}% vs 설계표준")
with c2:
    st.metric("현재 명중률", f"{cur_hit}%", f"{cur_hit-100}%" if cur_hit < 100 else "MAX")
with c3:
    st.metric("목표 처치 타수 (HTK)", f"{cur_htk} hits", help="몬스터 체력을 기대 대미지로 나눈 값")
with c4:
    st.metric("표준 전투력 (Ref.CP)", f"{int(ref['CP_Ref']):,}")

# 차트 시각화
fig = go.Figure()
fig.add_trace(go.Scatter(x=df_growth['Level'], y=df_growth['E_Dmg_Ref'], name="설계 표준 (Target)", line=dict(color='lightgray', dash='dot')))
fig.add_trace(go.Scatter(x=[selected_lv], y=[cur_dmg], mode='markers', marker=dict(size=18, color='red', symbol='star'), name="현재 세팅"))
fig.update_layout(xaxis_title="Character Level", yaxis_title="Effective Damage", template="plotly_white", height=450)
st.plotly_chart(fig, use_container_width=True)

st.info(f"**Designer's Insight**: {mon['Name']}(Lv.{selected_lv}) 상대 시뮬레이션. 몬스터 체력: {int(mon['HP']):,} / 요구 명중: {int(ref['Req_Acc'])}")