import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ==============================================================================
# 0. 설정 및 CSS
# ==============================================================================
st.set_page_config(
    page_title="Wannabe Life Plan", 
    page_icon="K", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# CSS 스타일링
st.markdown("""
    <style>
    :root {
        --kfit-bg: #111315;
        --kfit-panel: rgba(24, 26, 28, 0.92);
        --kfit-panel-border: #2a2d30;
        --kfit-text: #f1f5f9;
        --kfit-muted: #9ca3af;
    }

    .stApp {
        background: radial-gradient(1200px 600px at 20% 10%, rgba(255,255,255,0.06), transparent 60%),
                    radial-gradient(900px 500px at 80% 15%, rgba(255,255,255,0.05), transparent 55%),
                    linear-gradient(180deg, #0e0f11 0%, #111315 100%);
        color: var(--kfit-text);
    }

    body {
        background: var(--kfit-bg);
        color: var(--kfit-text);
    }

    /* [1] 타이틀 반응형 & 다크모드 자동 대응 */
    .responsive-title {
        font-size: clamp(1.5rem, 5vw, 2.5rem); 
        font-weight: 900;
        color: var(--kfit-text); 
        white-space: nowrap; 
        text-align: left;
        margin-bottom: 20px;
    }

    /* [2] 스코어카드 박스 디자인 (제목 강조형) */
    .metric-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        background: var(--kfit-panel); 
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.35);
        border: 1px solid var(--kfit-panel-border);
        height: 140px; /* 높이 약간 조정 */
    }
    
    /* 제목 스타일: 이모티콘+텍스트 한 줄, 크고 진하게 */
    .metric-label {
        font-size: 1.2rem; /* 글자 키움 */
        color: #e5e7eb; /* 진한 회색/검정으로 잘 보이게 */
        font-weight: 800; /* 굵게 강조 */
        margin-bottom: 10px;
        letter-spacing: -0.5px;
        white-space: nowrap;
    }
    
    .metric-value {
        font-size: 2.2rem; /* 숫자 더 크게 */
        font-weight: 900;
        color: var(--kfit-text); 
        line-height: 1;
    }
    
    .val-safe { color: #9ae6b4 !important; }
    .val-warn { color: #fbd38d !important; }
    .val-danger { color: #fca5a5 !important; }
    .val-blue { color: #c7d2fe !important; }
    .val-purple { color: #d8b4fe !important; }

    /* 부동산 목록 가독성 해결 (흰 카드 위 검은 글씨 강제) */
    .prop-card-sell { 
        background-color: rgba(34, 197, 94, 0.12) !important; 
        border-left: 5px solid #22c55e; 
        padding: 10px; 
        border-radius: 5px; 
        margin-bottom: 8px; 
    }
    .prop-card-inherit { 
        background-color: rgba(59, 130, 246, 0.12) !important; 
        border-left: 5px solid #3b82f6; 
        padding: 10px; 
        border-radius: 5px; 
        margin-bottom: 8px; 
    }
    
    .prop-card-sell div, .prop-card-inherit div, .prop-title {
        color: #e5e7eb !important;
        font-family: sans-serif;
    }
    
    .prop-title { font-weight: bold; font-size: 14px; }
    
    /* 사이드바 */
    .sidebar-title {
        font-size: 1.8rem;
        font-weight: 900;
        color: #e5e7eb; 
        text-align: center;
    }
    .sidebar-subtitle { font-size: 13px; color: var(--kfit-muted); text-align: center; margin-bottom: 20px; }
    
    /* 풋터 */
    .main-footer { margin-top: 50px; padding: 20px; border-top: 1px solid #2a2d30; text-align: center; color: var(--kfit-muted); font-size: 13px; }

    /* 버튼 톤온톤 */
    .stButton > button, .stFormSubmitButton > button {
        background: #2a2d30;
        color: #f3f4f6;
        border-radius: 999px;
        border: 1px solid #3a3d41;
        padding: 0.5rem 1.1rem;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.06);
    }
    .stButton > button:hover, .stFormSubmitButton > button:hover {
        background: #31353a;
        border-color: #4b5563;
    }

    [data-testid="stSidebar"] > div:first-child {
        background: rgba(17, 19, 21, 0.98);
        border-right: 1px solid #2a2d30;
    }

    .stTextInput input,
    .stNumberInput input,
    .stTextArea textarea,
    .stSelectbox div[data-baseweb="select"] > div {
        background-color: #1b1d20 !important;
        color: #f1f5f9 !important;
        border: 1px solid #2a2d30 !important;
        border-radius: 10px !important;
    }

    .stSelectbox svg {
        fill: #9ca3af !important;
    }

    .stMarkdown, .stMarkdown p,
    .stTextInput label, .stNumberInput label,
    .stSelectbox label, .stSlider label,
    .stTextArea label, .stCheckbox label,
    .stCaption {
        color: #e5e7eb !important;
    }
    </style>
""", unsafe_allow_html=True)

if 'properties' not in st.session_state:
    st.session_state.properties = []

def get_google_sheet_client():
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        if "service_account" in st.secrets:
            creds_dict = dict(st.secrets["service_account"])
        elif "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
        else:
            return None
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        return gspread.authorize(creds)
    except Exception:
        return None

def save_data_to_gsheet(data_dict):
    client = get_google_sheet_client()
    if not client: return False, "구글 시트 연결 실패 (Secrets 설정 확인)"
    try:
        sheet = client.open("WannabeLifePlan").sheet1
        if not sheet.get_all_values():
            sheet.append_row(list(data_dict.keys()) + ["타임스탬프"])
        sheet.append_row(list(data_dict.values()) + [str(datetime.now())])
        return True, "저장 성공"
    except Exception as e:
        return False, f"저장 오류: {str(e)}"

# ==============================================================================
# 1. 로직 엔진
# ==============================================================================
class WannabeEngine:
    def __init__(self, current_age, retire_age, death_age):
        self.current_age = current_age
        self.retire_age = retire_age
        self.death_age = death_age
        self.period = death_age - current_age + 1

    def run_simulation(self, liquid_billions, monthly_save, monthly_spend, 
                        inflation, return_rate, properties_list, annual_hobby_cost):
        liquid = liquid_billions * 100000000
        annual_save = monthly_save * 12 * 10000
        base_annual_spend = (monthly_spend * 12 * 10000) + annual_hobby_cost
        
        ages = []
        liquid_history = []     
        real_estate_history = [] 
        
        props = [p.copy() for p in properties_list] 
        current_liquid = liquid
        shortfall_age = None
        
        for i in range(self.period):
            age = self.current_age + i
            ages.append(age)
            current_liquid = current_liquid * (1 + return_rate)
            
            if age < self.retire_age:
                current_liquid += annual_save
            else:
                this_year_spend = base_annual_spend * ((1 + inflation) ** i)
                current_liquid -= this_year_spend
                
            current_re_net_val = 0
            for p in props:
                if p.get('is_sold', False): continue 
                years = age - self.current_age
                gross_val = (p['current_val'] * 100000000) * ((1 + inflation) ** years)
                loan_amt = p.get('loan', 0) * 100000000
                net_equity = max(0, gross_val - loan_amt)
                
                if p['strategy'] == '매각 (Sell)' and age == p['sell_age']:
                    purchase_val = p['purchase_price'] * 100000000
                    capital_gain = gross_val - purchase_val
                    tax = capital_gain * 0.25 if capital_gain > 0 else 0
                    cash_in_hand = gross_val - loan_amt - tax
                    current_liquid += cash_in_hand 
                    p['is_sold'] = True
                    net_equity = 0 
                current_re_net_val += net_equity
            
            if current_liquid < 0 and shortfall_age is None:
                shortfall_age = age
            
            liquid_history.append(current_liquid / 100000000)
            real_estate_history.append(current_re_net_val / 100000000)
            
        return ages, liquid_history, real_estate_history, shortfall_age

    def calculate_score(self, shortfall_age):
        if shortfall_age is None: return 100, "완벽 (Perfect)"
        gap = self.death_age - shortfall_age
        if gap <= 0: return 90, "안정 (Stable)"
        elif gap <= 5: return 70, "주의 (Caution)"
        elif gap <= 10: return 50, "위험 (Danger)"
        else: return 30, "심각 (Critical)"

# ==============================================================================
# 2. 사이드바 UI
# ==============================================================================
with st.sidebar:
    st.markdown("""
        <div class="sidebar-container">
            <div class="sidebar-title">Wannabe Life</div>
            <div class="sidebar-subtitle">Professional Asset Simulator</div>
        </div>
    """, unsafe_allow_html=True)
    
    with st.expander("1. 기본 정보 (Profile)", expanded=True):
        c1, c2 = st.columns(2)
        age_curr = c1.number_input("현재 나이", 30, 80, 50)
        age_retire = c2.number_input("은퇴 목표", 50, 90, 65)
        age_death = st.number_input("기대 수명", 80, 120, 95)

    with st.expander("2. 금융 자산 (Finance)", expanded=True):
        c1, c2 = st.columns(2)
        liquid_asset = c1.number_input("유동자산(억)", 0.0, 100.0, 3.0)
        monthly_save = c2.number_input("월 저축(만원)", 0, 10000, 300)
        return_rate_int = st.slider("투자 수익률(%)", 0, 15, 4, step=1)
        return_rate = return_rate_int / 100

    with st.expander("3. 부동산 자산 (Real Estate)", expanded=True):
        with st.form("prop_form", clear_on_submit=True):
            r1_c1, r1_c2 = st.columns(2)
            p_name = r1_c1.text_input("자산명 (예: 반포아파트)")
            p_curr = r1_c2.number_input("현재가(억)", 0, 300, 10)
            r2_c1, r2_c2 = st.columns(2)
            p_buy = r2_c1.number_input("매입가(억)", 0, 300, 5)
            p_loan = r2_c2.number_input("대출금(억)", 0, 200, 0)
            r3_c1, r3_c2 = st.columns(2)
            p_strat = r3_c1.radio("계획", ["매각", "상속"])
            p_sell_default = max(age_curr, 75)
            p_sell_default = min(p_sell_default, 100)
            p_sell = r3_c2.slider("시기(세)", age_curr, 100, p_sell_default)
            
            st.write("")
            b1, b2, b3 = st.columns([1, 2, 1])
            with b2:
                btn_submitted = st.form_submit_button("자산 추가", use_container_width=True)
            
            if btn_submitted:
                strat_code = "매각 (Sell)" if "매각" in p_strat else "상속 (Inherit)"
                st.session_state.properties.append({
                    "name": p_name, "current_val": p_curr, "loan": p_loan,
                    "purchase_price": p_buy, "strategy": strat_code, 
                    "sell_age": p_sell, "is_sold": False
                })
                st.rerun()

        if st.session_state.properties:
            st.markdown("---")
            for i, p in enumerate(st.session_state.properties):
                desc = f"매각 ({p['sell_age']}세)" if "매각" in p['strategy'] else "상속"
                css_class = "prop-card-sell" if "매각" in p['strategy'] else "prop-card-inherit"
                net = p['current_val'] - p['loan']
                
                col_info, col_del = st.columns([8, 2])
                with col_info:
                    st.markdown(f"""
                        <div class="{css_class}">
                            <div class="prop-title">{p['name']}</div>
                            <div>순가치 {net}억 (대출 {p['loan']}억)</div>
                            <div>{desc}</div>
                        </div>
                    """, unsafe_allow_html=True)
                with col_del:
                    st.write("") 
                    if st.button("X", key=f"del_{i}"):
                        st.session_state.properties.pop(i)
                        st.rerun()

    with st.expander("4. 라이프스타일 (Lifestyle)", expanded=True):
        monthly_spend = st.number_input("은퇴 월 생활비(만원)", 0, 5000, 300)
        c1, c2 = st.columns(2)
        golf_freq = c1.selectbox("골프 라운딩", ["안 함", "월 1회", "월 2회", "월 4회", "VIP"])
        c1.caption("회당 40만원")
        travel_freq = c2.selectbox("해외 여행", ["안 함", "연 1회", "연 2회", "분기별"])
        c2.caption("회당 400만원")
        inflation = st.select_slider("물가상승률", ["안정(2%)", "보통(3.5%)", "심각(5%)"], value="보통(3.5%)")

# ==============================================================================
# 3. 메인 화면
# ==============================================================================
golf_map = {"안 함":0, "월 1회":12, "월 2회":24, "월 4회":48, "VIP":100}
travel_map = {"안 함":0, "연 1회":1, "연 2회":2, "분기별":4}
annual_hobby_cost = (golf_map[golf_freq] * 400000) + (travel_map[travel_freq] * 4000000)
inf_val = {"안정(2%)":0.02, "보통(3.5%)":0.035, "심각(5%)":0.05}[inflation]

engine = WannabeEngine(age_curr, age_retire, age_death)
ages, liq_norm, re_norm, ob_norm = engine.run_simulation(liquid_asset, monthly_save, monthly_spend, inf_val, return_rate, st.session_state.properties, annual_hobby_cost)
score, grade = engine.calculate_score(ob_norm)

# 타이틀
st.markdown('<div class="responsive-title">은퇴 준비 종합 진단</div>', unsafe_allow_html=True)

# 스코어카드 (이모티콘 + 텍스트 한 줄로 변경)
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(f"""
        <div class="metric-container">
            <div class="metric-label">은퇴 준비 점수</div>
            <div class="metric-value val-blue">{score}점</div>
        </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown(f"""
        <div class="metric-container">
            <div class="metric-label">진단 등급</div>
            <div class="metric-value val-purple">{grade.split('(')[0]}</div>
        </div>
    """, unsafe_allow_html=True)

with c3:
    if ob_norm:
        val_text = f"{ob_norm}세"
        color_class = "val-danger"
    else:
        val_text = "Safe"
        color_class = "val-safe"
    st.markdown(f"""
        <div class="metric-container">
            <div class="metric-label">현금 고갈 시점</div>
            <div class="metric-value {color_class}">{val_text}</div>
        </div>
    """, unsafe_allow_html=True)

st.write("") 

# 그래프
st.subheader("자산별 생애 궤적")
fig = go.Figure()

fig.add_trace(go.Scatter(
    x=ages, y=liq_norm, name='현금 자산', 
    line=dict(color='#2e7d32', width=4), mode='lines',
    hovertemplate='<b>%{x}세</b><br>현금: %{y:.1f}억<extra></extra>'
))

fig.add_trace(go.Scatter(
    x=ages, y=re_norm, name='부동산(순자산)', 
    line=dict(color='#8d6e63', width=3, dash='dash'), 
    fill='tozeroy', fillcolor='rgba(141, 110, 99, 0.1)',
    hovertemplate='<b>%{x}세</b><br>부동산: %{y:.1f}억<extra></extra>'
))

fig.add_shape(type="line", x0=age_curr, y0=0, x1=age_death, y1=0, line=dict(color="red", width=1))

for p in st.session_state.properties:
    if "매각" in p['strategy'] and p['sell_age'] <= age_death:
        idx = p['sell_age'] - age_curr
        if 0 <= idx < len(liq_norm):
            fig.add_annotation(x=p['sell_age'], y=liq_norm[idx], 
                               text=f"{p['name']}", showarrow=True, arrowhead=2, ay=-30, 
                               font=dict(color="#2e7d32", size=10))

fig.update_layout(
    template="plotly_dark", 
    height=400, 
    margin=dict(l=20, r=20, t=50, b=50), 
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
    dragmode=False, 
    xaxis=dict(fixedrange=True), 
    yaxis=dict(fixedrange=True),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)"
)
st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False, 'scrollZoom': False})

st.divider()

# --- 하단 섹션 ---
col_expert, col_form = st.columns([1, 1])

with col_expert:
    st.subheader("심층 분석 의견")
    
    # [1] 유동성
    with st.expander("1. 유동성 및 현금 흐름", expanded=True):
        if score >= 90:
            st.success("**'골든 포트폴리오' 달성**")
            st.write("은퇴 후에도 자산이 증식되는 이상적인 구조입니다. 이제는 '자산 증식'보다 '인출 전략'과 '상속 플랜'에 집중하여 효율성을 높이십시오.")
        elif score >= 70:
            st.info("**구매력 보존 주의**")
            st.write(f"현금 흐름은 양호하나 인플레이션 장기화 시 구매력이 저하될 수 있습니다. 배당주나 리츠 등 **현금 창출형 자산**으로 포트폴리오를 다변화하세요.")
        elif score >= 50:
            st.warning(f"**{ob_norm}세 전후 '소득 절벽'**")
            st.write(f"{ob_norm}세 경 자산 고갈 위험이 있습니다. **주택연금** 활용을 적극 검토하고, 고정 지출을 20% 이상 줄이는 **구조조정**이 시급합니다.")
        else:
            st.error(f"**즉각적인 유동성 확보 필요**")
            st.write(f"은퇴 직후 유동성 위기가 우려됩니다. 부동산 **다운사이징**을 통해 현금을 확보하거나, 재취업 등 **제2의 소득원**을 반드시 마련해야 합니다.")

    # [2] 부동산 (상속세 경고 포함)
    with st.expander("2. 부동산 및 부채 리스크", expanded=True):
        inherit_props = [p for p in st.session_state.properties if "상속" in p['strategy']]
        if inherit_props:
            inherit_val = sum([p['current_val'] for p in inherit_props])
            st.error(f"**[치명적 위험] '부동산 상속' 경고**")
            st.markdown(f"""
                <div style='background-color: rgba(239, 68, 68, 0.12); padding: 10px; border-radius: 8px; color: #fecaca; border: 1px solid rgba(239, 68, 68, 0.25);'>
                    <b>현재 {inherit_val}억 원 상당의 부동산을 상속할 계획입니다.</b><br><br>
                    대한민국의 상속세율은 <b>최대 50%</b>입니다. 
                    자녀가 충분한 현금이 없다면, 세금을 내기 위해 
                    <b>물려주신 집을 급매(헐값)하거나 물납</b>해야 하는 비극이 발생합니다.<br><br>
                    <b>즉시 '상속세 재원 마련(종신보험)' 또는 '사전 증여' 컨설팅이 필수적입니다.</b>
                </div>
            """, unsafe_allow_html=True)
            st.divider()

        net_re = sum([max(0, p['current_val'] - p['loan']) for p in st.session_state.properties])
        total_asset = liquid_asset + net_re
        ratio = net_re / total_asset if total_asset > 0 else 0
        
        loans = sum([p['loan'] for p in st.session_state.properties])
        if loans > 0:
            st.write(f"**부채 관리:** 총 대출 {loans}억 원의 이자 부담을 우선적으로 제거하십시오.")

        if ratio > 0.8:
            st.warning(f"**부동산 편중 ({ratio*100:.0f}%)**")
            st.write("'Asset Rich, Cash Poor' 유형입니다. 유동성 위기 방지를 위해 부동산 비중을 60% 이하로 낮추는 **전략적 매각**이 필요합니다.")
        elif ratio > 0.5:
            st.info(f"**균형 잡힌 자산 ({ratio*100:.0f}%)**")
            st.write("비교적 이상적인 비중입니다. 금융 자산 내에서 채권, 해외 ETF 등 **글로벌 자산 배분**을 통해 안정성을 강화하십시오.")
        else:
            st.success(f"**풍부한 유동성 ({ratio*100:.0f}%)**")
            st.write("현금 비중이 높아 위기에 강하지만, 인플레이션에는 취약할 수 있습니다. **우량 실물 자산** 비중 확대를 고려해 보세요.")

    # [3] 변동성
    with st.expander("3. 변동성 대응 및 투자 전략", expanded=True):
        if return_rate_int < 3:
            st.write("보수적인 운용 중입니다. 물가 상승을 방어하기 위해 **투자형 연금** 비중을 조금 더 늘리는 것을 권장합니다.")
        elif return_rate_int > 7:
            st.write("공격적인 목표 수익률입니다. 시장 하락 시 손실을 줄이기 위해 **분할 매수**와 **자산 배분(Rebalancing)** 원칙을 철저히 지키십시오.")
        else:
            st.write("적절한 중위험·중수익 전략입니다. 은퇴 시점이 다가올수록 변동성을 줄이는 **TDF(Target Date Fund)** 형태의 운용이 유리합니다.")

with col_form:
    st.subheader("상담 신청")
    with st.form("save_form"):
        u_name = st.text_input("성함")
        u_phone = st.text_input("연락처")
        u_memo = st.text_area("문의사항", height=100)
        agree = st.checkbox("개인정보 수집 및 이용 동의")
        
        submit_btn = st.form_submit_button("무료 리포트 받기", use_container_width=True)
        
        if submit_btn:
            if not agree:
                st.warning("동의가 필요합니다.")
            elif u_name and u_phone:
                props_str = ""
                if st.session_state.properties:
                    p_details = []
                    for p in st.session_state.properties:
                        detail = f"[{p['name']}:{p['current_val']}억(대출{p['loan']})/{p['strategy']}"
                        if "매각" in p['strategy']: detail += f"({p['sell_age']}세)"
                        detail += "]"
                        p_details.append(detail)
                    props_str = ", ".join(p_details)
                else: props_str = "없음"

                expert_summary = ""
                if score >= 90: expert_summary = "안정/상속플랜"
                elif score >= 50: expert_summary = "주의/주택연금"
                else: expert_summary = "위험/구조조정"

                data = {
                    "이름": u_name, "연락처": u_phone,
                    "현재나이": age_curr, "은퇴나이": age_retire, "기대수명": age_death,
                    "유동자산(억)": liquid_asset, "월저축(만)": monthly_save, "수익률(%)": return_rate_int,
                    "부동산목록": props_str,
                    "생활비(만)": monthly_spend, "골프": golf_freq, "여행": travel_freq, "물가": inflation,
                    "점수": score, "고갈시점": f"{ob_norm}세" if ob_norm else "유지",
                    "전문가진단": expert_summary,
                    "최종잔액": liq_norm[-1], "문의": u_memo
                }
                res, msg = save_data_to_gsheet(data)
                if res: st.balloons(); st.success("신청 완료되었습니다.")
                else: st.error(f"{msg}")
            else: 
                st.warning("정보를 입력해주세요.")

st.markdown("""<div class="main-footer"><b>한국금융투자기술 (Korea Financial Investment Technology)</b> | CEO: 노일용 | 문의: 010-6255-9978 <br> Copyright © 2025 Wannabe Life Solution. All rights reserved.</div>""", unsafe_allow_html=True)
