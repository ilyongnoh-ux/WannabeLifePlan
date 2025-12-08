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
    page_icon="⛳", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# CSS 스타일링
st.markdown("""
    <style>
    /* 스코어카드 박스 디자인 강화 */
    .metric-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        background: white;
        border-radius: 15px;
        padding: 20px;
        box-shadow: 0 10px 20px rgba(0,0,0,0.08);
        transition: transform 0.3s ease;
        border: 1px solid #f0f0f0;
        height: 160px;
    }
    .metric-container:hover {
        transform: translateY(-5px);
    }
    
    .metric-icon { font-size: 3rem; margin-bottom: 10px; }
    
    .metric-label {
        font-size: 1rem;
        color: #888;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .metric-value {
        font-size: 2rem;
        font-weight: 800;
        color: #333;
    }
    
    .val-safe { color: #2E8B57; }
    .val-warn { color: #FF8C00; }
    .val-danger { color: #E53935; }
    .val-blue { color: #1E88E5; }
    .val-purple { color: #8E24AA; }

    /* 사이드바 타이틀 */
    .sidebar-container { text-align: center; margin-bottom: 20px; width: 100%; }
    .sidebar-title {
        font-size: clamp(1.4rem, 6vw, 2.2rem);
        font-weight: 900;
        color: #2E8B57; 
        line-height: 1.2;
        white-space: nowrap;
        overflow: hidden;
    }
    .sidebar-subtitle { font-size: 13px; color: #666; margin-top: 5px; white-space: nowrap; }

    /* 부동산 카드 */
    .prop-card-sell { background-color: #e8f5e9; border-left: 5px solid #2e7d32; padding: 10px; border-radius: 5px; margin-bottom: 8px; font-size: 13px; }
    .prop-card-inherit { background-color: #e3f2fd; border-left: 5px solid #1565c0; padding: 10px; border-radius: 5px; margin-bottom: 8px; font-size: 13px; }
    .prop-title { font-weight: bold; font-size: 14px; }

    /* 메인 풋터 */
    .main-footer { margin-top: 50px; padding: 20px; border-top: 1px solid #eee; text-align: center; color: #888; font-size: 13px; }
    </style>
""", unsafe_allow_html=True)

if 'properties' not in st.session_state:
    st.session_state.properties = []

def get_google_sheet_client():
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds_dict = dict(st.secrets["service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        return gspread.authorize(creds)
    except Exception:
        return None

def save_data_to_gsheet(data_dict):
    client = get_google_sheet_client()
    if not client: return False, "구글 시트 설정 필요"
    try:
        sheet = client.open("WannabeLifePlan").sheet1
        if not sheet.get_all_values():
            sheet.append_row(list(data_dict.keys()) + ["Timestamp"])
        sheet.append_row(list(data_dict.values()) + [str(datetime.now())])
        return True, "저장 성공"
    except Exception as e:
        return False, str(e)

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
            
            # 유동자산 운용
            current_liquid = current_liquid * (1 + return_rate)
            
            if age < self.retire_age:
                current_liquid += annual_save
            else:
                this_year_spend = base_annual_spend * ((1 + inflation) ** i)
                current_liquid -= this_year_spend
                
            # 부동산 가치 평가
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
            <div class="sidebar-title">⛳ Wannabe Life</div>
            <div class="sidebar-subtitle">Professional Asset Simulator</div>
        </div>
    """, unsafe_allow_html=True)
    
    # 1. 기본 정보
    with st.expander("1. 기본 정보 (Profile)", expanded=True):
        c1, c2 = st.columns(2)
        age_curr = c1.number_input("현재 나이", 30, 80, 50)
        age_retire = c2.number_input("은퇴 목표", 50, 90, 65)
        age_death = st.number_input("기대 수명", 80, 120, 95)

    # 2. 금융 자산
    with st.expander("2. 금융 자산 (Finance)", expanded=True):
        c1, c2 = st.columns(2)
        liquid_asset = c1.number_input("유동자산(억)", 0.0, 100.0, 3.0)
        monthly_save = c2.number_input("월 저축(만원)", 0, 10000, 300)
        return_rate_int = st.slider("투자 수익률(%)", 0, 15, 4, step=1)
        return_rate = return_rate_int / 100

    # 3. 부동산 자산
    with st.expander("3. 부동산 자산 (Real Estate)", expanded=True):
        with st.form("prop_form", clear_on_submit=True):
            r1_c1, r1_c2 = st.columns(2)
            p_name = r1_c1.text_input("자산명 (예: 아파트)")
            p_curr = r1_c2.number_input("현재가(억)", 0, 300, 10, format="%d")

            r2_c1, r2_c2 = st.columns(2)
            p_buy = r2_c1.number_input("매입가(억)", 0, 300, 5, format="%d")
            p_loan = r2_c2.number_input("대출금(억)", 0, 200, 0, format="%d")
            
            r3_c1, r3_c2 = st.columns(2)
            p_strat = r3_c1.radio("활용 계획", ["매각", "상속"], label_visibility="visible")
            p_sell = r3_c2.slider("매각/상속나이", age_curr, 100, 75)
            
            st.write("")
            b1, b2, b3 = st.columns([1, 2, 1])
            with b2:
                btn_submitted = st.form_submit_button("➕ 자산 추가", use_container_width=True)
            
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
            st.write("**📋 보유 자산 목록**")
            for i, p in enumerate(st.session_state.properties):
                desc = f"매각 ({p['sell_age']}세 현금화)" if "매각" in p['strategy'] else f"상속 (현금화 안 함)"
                css_class = "prop-card-sell" if "매각" in p['strategy'] else "prop-card-inherit"
                icon = "💰" if "매각" in p['strategy'] else "🎁"
                net = p['current_val'] - p['loan']
                
                col_info, col_del = st.columns([7, 3])
                with col_info:
                    st.markdown(f"""
                        <div class="{css_class}">
                            <div class="prop-title">{icon} {p['name']}</div>
                            <div>순가치 {net}억 (대출 {p['loan']}억)</div>
                            <div>{desc}</div>
                        </div>
                    """, unsafe_allow_html=True)
                with col_del:
                    st.write("") 
                    if st.button("삭제", key=f"del_{i}"):
                        st.session_state.properties.pop(i)
                        st.rerun()

    # 4. 라이프스타일 (비용 명시 및 로직 수정)
    with st.expander("4. 라이프스타일 (Lifestyle)", expanded=True):
        monthly_spend = st.number_input("은퇴 월 생활비(만원)", 0, 5000, 300)
        c1, c2 = st.columns(2)
        
        # 골프 라운딩 및 비용 캡션
        golf_freq = c1.selectbox("골프 라운딩", ["안 함", "월 1회", "월 2회", "월 4회", "VIP"])
        c1.caption("기준: 회당 40만 원")

        # 해외 여행 및 비용 캡션
        travel_freq = c2.selectbox("해외 여행", ["안 함", "연 1회", "연 2회", "분기별"])
        c2.caption("기준: 회당 400만 원")

        inflation = st.select_slider("물가상승률", ["안정(2%)", "보통(3.5%)", "심각(5%)"], value="보통(3.5%)")

# ==============================================================================
# 3. 메인 화면
# ==============================================================================
golf_map = {"안 함":0, "월 1회":12, "월 2회":24, "월 4회":48, "VIP":100}
travel_map = {"안 함":0, "연 1회":1, "연 2회":2, "분기별":4}

# 비용 로직 수정 (골프 40만, 여행 400만)
annual_hobby_cost = (golf_map[golf_freq] * 400000) + (travel_map[travel_freq] * 4000000)
inf_val = {"안정(2%)":0.02, "보통(3.5%)":0.035, "심각(5%)":0.05}[inflation]

engine = WannabeEngine(age_curr, age_retire, age_death)
ages, liq_norm, re_norm, ob_norm = engine.run_simulation(liquid_asset, monthly_save, monthly_spend, inf_val, return_rate, st.session_state.properties, annual_hobby_cost)
score, grade = engine.calculate_score(ob_norm)

# 상단 스코어카드
st.title("📊 은퇴 준비 종합 진단")

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(f"""
        <div class="metric-container">
            <div class="metric-icon">🎯</div>
            <div class="metric-label">은퇴 준비 점수</div>
            <div class="metric-value val-blue">{score}점</div>
        </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown(f"""
        <div class="metric-container">
            <div class="metric-icon">🏆</div>
            <div class="metric-label">진단 등급</div>
            <div class="metric-value val-purple">{grade.split('(')[0]}</div>
        </div>
    """, unsafe_allow_html=True)

with c3:
    if ob_norm:
        icon = "🚨"
        val_text = f"{ob_norm}세"
        color_class = "val-danger"
    else:
        icon = "⏳"
        val_text = "유지 (Safe)"
        color_class = "val-safe"
        
    st.markdown(f"""
        <div class="metric-container">
            <div class="metric-icon">{icon}</div>
            <div class="metric-label">현금 고갈 시점</div>
            <div class="metric-value {color_class}">{val_text}</div>
        </div>
    """, unsafe_allow_html=True)

st.write("") 
st.write("") 

# 그래프 (툴팁 텍스트 수정 적용)
st.subheader("📈 자산별 생애 궤적 (Trajectory)")
fig = go.Figure()

# 유동자산 Trace (hovertemplate 적용)
fig.add_trace(go.Scatter(
    x=ages, 
    y=liq_norm, 
    name='💵 유동자산 (현금)', 
    line=dict(color='#2e7d32', width=4), 
    mode='lines',
    hovertemplate='<b>%{x}세</b><br>현금: %{y:.1f}억<extra></extra>'
))

# 부동산 Trace (hovertemplate 적용)
fig.add_trace(go.Scatter(
    x=ages, 
    y=re_norm, 
    name='🏠 부동산 (순자산)', 
    line=dict(color='#8d6e63', width=3, dash='dash'), 
    fill='tozeroy', 
    fillcolor='rgba(141, 110, 99, 0.1)',
    hovertemplate='<b>%{x}세</b><br>부동산: %{y:.1f}억<extra></extra>'
))

fig.add_shape(type="line", x0=age_curr, y0=0, x1=age_death, y1=0, line=dict(color="red", width=1))

for p in st.session_state.properties:
    if "매각" in p['strategy'] and p['sell_age'] <= age_death:
        idx = p['sell_age'] - age_curr
        if 0 <= idx < len(liq_norm):
            fig.add_annotation(x=p['sell_age'], y=liq_norm[idx], text=f"↗ {p['name']} 매각", showarrow=True, arrowhead=2, ay=-40, font=dict(color="#2e7d32"))

fig.update_layout(xaxis_title="나이", yaxis_title="자산 (억원)", template="plotly_white", height=450, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
st.plotly_chart(fig, use_container_width=True)
st.info("💡 **그래프 안내:** 갈색 영역은 대출금을 뺀 **순자산** 가치이며, 매각 시 현금(초록색 선)으로 전환됩니다.")
st.divider()

# --- 하단 섹션 ---
col_expert, col_form = st.columns([1, 1])

# [좌측] 심층 분석 (테두리 X)
with col_expert:
    st.subheader("📝 심층 분석 의견")
    
    with st.expander("1. 유동성 분석", expanded=True):
        if ob_norm:
            st.error(f"⚠️ {ob_norm}세에 현금이 고갈됩니다.")
            st.write("솔루션: 주택연금, 즉시연금 등 현금 흐름 창출 전략이 시급합니다.")
        else:
            st.success("✅ 평생 현금 흐름이 안정적입니다.")
            st.write("솔루션: 증여 및 절세 플랜을 통해 자산 효율을 높이세요.")
            
    with st.expander("2. 부동산 및 대출 리스크", expanded=True):
        loans = sum([p['loan'] for p in st.session_state.properties])
        if loans > 0: st.write(f"- 총 대출금: **{loans}억 원**")
        
        net_re = sum([max(0, p['current_val'] - p['loan']) for p in st.session_state.properties])
        ratio = net_re / (liquid_asset + net_re) if (liquid_asset + net_re) > 0 else 0
        if ratio > 0.7: st.warning(f"⚠️ 부동산 비중 {ratio*100:.0f}% (높음)")
        else: st.info(f"✅ 부동산 비중 {ratio*100:.0f}% (적정)")

    with st.expander("3. 변동성 대응", expanded=True):
        st.write("외부 경제 충격에도 자산이 유지될 확률이 높습니다.")

# [우측] 상담 신청 (테두리 X, 높이 120)
with col_form:
    st.subheader("📞 상담 신청")
    
    with st.form("save_form"):
        u_name = st.text_input("성함")
        u_phone = st.text_input("연락처")
        u_memo = st.text_area("문의사항", height=120) 
        
        agree = st.checkbox("개인정보 수집 및 이용에 동의합니다.")
        
        st.write("")
        submit_btn = st.form_submit_button("무료 리포트 받기", use_container_width=True)
        
        if submit_btn:
            if not agree:
                st.warning("⚠️ 개인정보 수집 및 이용에 동의해주세요.")
            elif u_name and u_phone:
                data = {"Name": u_name, "Phone": u_phone, "Score": score, "Liquid_End": liq_norm[-1], "Memo": u_memo}
                res, msg = save_data_to_gsheet(data)
                if res: st.balloons(); st.success("✅ 신청 완료! 리포트를 곧 보내드리겠습니다.")
                else: st.error(f"⚠️ {msg}")
            else: 
                st.warning("⚠️ 성함과 연락처를 입력해주세요.")

# 풋터
st.markdown("""<div class="main-footer"><b>한국금융투자기술 (Korea Financial Investment Technology)</b> | CEO: 노일용 | 문의: 010-6255-9978 <br> Copyright © 2025 Wannabe Life Solution. All rights reserved.</div>""", unsafe_allow_html=True)