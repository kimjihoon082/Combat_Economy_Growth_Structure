# ⚔️ RPG Combat Balance Simulator v1.0
**설계자: 김지훈 (Kim Ji-hoon)**

본 프로젝트는 RPG 게임의 전투 경제 및 성장 구조를 수학적으로 모델링하고 실시간으로 검증하기 위한 인터랙티브 시뮬레이터입니다. Excel로 설계된 밸런스 엔진을 Python(Streamlit) 환경으로 이식하여, 기획자의 의도가 실제 플레이어의 세팅에 따라 어떻게 변동되는지 시각적으로 증명합니다.

> **Live Demo:** [![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://combatbalance2engine.streamlit.app/)

## 🚀 프로젝트 핵심 가치
- **데이터 기반 검증**: 정적인 엑셀 수치를 넘어, 유저의 장비 강화 및 파밍 수준에 따른 전투 효율을 실시간으로 산출합니다.
- **보상 공간(Reward Space) 시각화**: 기획자가 의도한 '성장 허들'과 이를 극복하기 위한 '보상 공간'의 수학적 정당성을 입증합니다.
- **UX 최적화**: 레벨 변경 시 모든 세팅이 해당 레벨의 기본값으로 리셋되는 'Clean Slate' 로직을 통해 시뮬레이션의 정확도를 보장합니다.

## 🛠️ 주요 시뮬레이션 기능
1. **현재 공격력 (Attack)**: 레벨별 기본 공격력의 최대 10배까지 강화 효율 시뮬레이션.
2. **현재 명중 (Acc)**: 몬스터 회피에 대응하는 명중률 100% 달성 여부 확인.
3. **치명타 최적화**: 80% 상한 기반의 치명타 확률과 피해량 스케일링 검증.
4. **전투 지표 산출**:
   - **E.Dmg**: 명중률과 치명타가 결합된 실질 기대 대미지.
   - **HTK (Hits to Kill)**: 대상 몬스터를 처치하기까지 필요한 타수 산출.

## 📂 파일 구성
- `app.py`: 시뮬레이터 메인 로직 및 UI 코드
- `player_growth.csv`: 레벨별 플레이어 표준 성장 데이터
- `monster_db.csv`: 플레이어 화력에 대응하는 몬스터 밸런스 데이터
- `constants.csv`: 방어 상수 K 등 전역 밸런스 설정값
- `requirements.txt`: 배포 환경 구동을 위한 라이브러리 목록