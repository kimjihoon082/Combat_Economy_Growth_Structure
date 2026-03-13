import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# ---------------------------------------------------------
# 1. 페이지 설정 및 환경 구성
# ---------------------------------------------------------
st.set_page_config(page_title="RPG Combat Balance Simulator", layout="wide")

@st.cache_data
def load_all_data():
    # 수치 클리닝 함수: 콤마(,)와 % 제거
    def clean_val(x):
        if isinstance(x, str):
            return x.replace(',', '').replace('%', '').strip()
        return x

    # 파일 로드 (루트 디렉토리 기준)
    try:
        df_const = pd.read_csv("constants.csv")
        df_growth = pd.read_csv("player_growth.csv")
        df_monster = pd.read_csv("monster_db.csv")
    except FileNotFoundError as e:
        st.error(f"파일을 찾을 수 없습니다: {e}")
        st.stop()

    # 데이터 전처리
    # player_growth 클리닝
    target_cols = ['E_Dmg_Ref', 'EHP_Ref', 'CP_Ref', 'Final_Crit_Dmg']
    for col in target_cols:
        if col in df_growth.columns:
            df_growth[col] = df_growth[col].apply(clean_val).astype(float)
            # 퍼센트 단위였던 데이터는 소수점으로 변환
            if col == 'Final_Crit_Dmg':
                df_growth[col] = df_growth[col] / 100

    # constants 클리닝 및 딕셔너리화
    df_const['Value'] = df_const['Value'].apply(clean_val).astype(float)
    const_dict = dict(zip(df_const['ConstantName'], df_const['Value']))

    return const_dict, df_growth, df_monster

# 데이터 불러오기
const, df_growth, df_monster = load_all_data()

# 전역 상수 추출
K_VALUE = const.get('Defense_K', 2000.0)

# ---------------------------------------------------------
# 2. 사이드바: 유저 세팅 및 보너스 스탯
# ---------------------------------------------------------
st.sidebar.header("🕹️ Player Setting")
selected_lv = st.sidebar.slider("레벨 선택 (Level)", 1, 100, 1)

# 해당 레벨의 표준 데이터(Reference) 추출
ref = df_growth[df_growth['Level'] == selected_lv].iloc[0]

st.sidebar.divider()
st.sidebar.subheader("💎 보너스/장비 스탯 설정")
# 지훈 님의 의도: 기본 150% ~ 최대 300% (슬라이더 기본값은 해당 레벨의 설계값)
user_crit_dmg = st.sidebar.slider("치명타 피해량 (%)", 150.0, 300.0, float(ref['Final_Crit_Dmg'] * 100)) / 100
user_crit_rate = st.sidebar.slider("치명타 확률 (%)", 0.0, 80.0, float(ref['Base_Crit_Rate'] * 100)) / 100
user_atk = st.sidebar.number_input("현재 공격력 (Attack)", value=int(ref['Atk']))

# ---------------------------------------------------------
# 3. 핵심 전투 연산 로직 (Excel 수식 이식)
# ---------------------------------------------------------
def run_simulation(atk, crit_rate, crit_dmg, lv):
    # 몬스터 데이터 가져오기
    m = df_monster[df_monster['Monster_Lv'] == lv].iloc[0]
    
    # [1] 명중률 계산
    # Acc / Evasion (최대 1.0)
    hit_rate = min(1.0, ref['Acc'] / m['Evasion_Rating']) if m['Evasion_Rating'] > 0 else 1.0
    
    # [2] 방어율 계산 (몬스터 방어력 적용)
    # 현재 시뮬레이션에서는 몬스터 방어력(Def)을 0으로 설계했으나 로직은 포함
    m_dr = m['Def'] / (m['Def'] + K_VALUE)
    
    # [3] 치명타 기댓값 (Crit Multiplier)
    # 1 + (확률 * (피해량 - 1))
    crit_mult = 1 + (crit_rate * (crit_dmg - 1))
    
    # [4] 실질 기대 대미지 (E.Dmg)
    # Atk * (1 - 몬스터방어율) * 명중률 * 치명타보정
    e_dmg = atk * (1 - m_dr) * hit_rate * crit_mult
    
    return round(e_dmg, 2), round(hit_rate * 100, 1)

current_e_dmg, current_hit_p = run_simulation(user_atk, user_crit_rate, user_crit_dmg, selected_lv)

# ---------------------------------------------------------
# 4. 메인 대시보드 출력
# ---------------------------------------------------------
st.title("⚔️ Combat Economy Balance Simulator")
st.markdown(f"**Level {selected_lv}** 구간의 전투 효율 및 성장 지표를 분석합니다.")

# 주요 지표 Metric
m1, m2, m3 = st.columns(3)
with m1:
    diff_dmg = round((current_e_dmg / ref['E_Dmg_Ref'] - 1) * 100, 1)
    st.metric("실질 화력 기댓값 (E.Dmg)", f"{current_e_dmg:,.1f}", f"{diff_dmg}% vs 설계표준")
with m2:
    st.metric("현재 명중률 (Hit Rate)", f"{current_hit_p}%")
with m3:
    st.metric("표준 전투력 (Planned CP)", f"{int(ref['CP_Ref']):,}")

# 시각화: 성장 곡선 비교
st.divider()
st.subheader("📈 화력 성장 곡선: 설계 표준 vs 현재 세팅")

fig = go.Figure()
# 표준 성장 곡선 (Reference)
fig.add_trace(go.Scatter(
    x=df_growth['Level'], 
    y=df_growth['E_Dmg_Ref'], 
    name="설계 표준 (Planned)",
    line=dict(color='rgba(150, 150, 150, 0.5)', dash='dot')
))
# 현재 유저 위치
fig.add_trace(go.Scatter(
    x=[selected_lv], 
    y=[current_e_dmg], 
    mode='markers+text',
    marker=dict(size=15, color='red', symbol='diamond'),
    name="현재 유저 세팅",
    text=[f"Lv.{selected_lv}"],
    textposition="top center"
))

fig.update_layout(
    xaxis_title="Character Level",
    yaxis_title="Effective Damage (E.Dmg)",
    hovermode="x unified",
    template="plotly_white"
)
st.plotly_chart(fig, use_container_width=True)

# 기획자 코멘트
with st.expander("📝 Designer's Insight"):
    st.write(f"""
    - **방어 상수(K)**: 현재 시스템의 방어 상수는 **{K_VALUE}**로 설정되어 인플레이션을 제어하고 있습니다.
    - **치명타 스케일링**: Lv.{selected_lv}의 목표 치명타 피해량은 **{int(ref['Final_Crit_Dmg']*100)}%**입니다. 
    - **보상 공간(Reward Space)**: 현재 레벨의 요구 명중치는 **{ref['Req_Acc']}**이며, 기본 명중({ref['Acc']})과의 간극을 장비 파밍으로 채우는 구간입니다.
    """)