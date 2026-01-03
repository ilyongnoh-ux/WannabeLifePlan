import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from utils import send_data_to_api, render_common_form
from models import LifeData
import json 

def app(input_col):
    # ==============================================================================
    # 0. 설정 및 CSS
    # ==============================================================================
    st.markdown("""
        <style>
        /* 메인 타이틀 색상을 Primary Color로 통일 (다크모드 대응) */
        .responsive-title { 
            font-size: clamp(1.5rem, 5vw, 2.5rem); 
            font-weight: 900; 
            color: var(--primary-color);
            white-space: nowrap; 
            text-align: center; 
            margin-bottom: 20px; 
        }
        .metric-container { 
            display: flex; 
            flex-direction: column; 
            align-items: center; 
            justify-content: center; 
            background: white; 
            border-radius: 15px; 
            padding: 20px; 
            box-shadow: 0 5px 15px rgba(0,0,0,0.08); 
            border: 1px solid #e0e0e0; 
            height: 140px; 
        }
        .metric-label { 
            font-size: 1.2rem; 
            color: #333333; 
            font-weight: 800; 
            margin-bottom: 10px; 
            letter-spacing: -0.5px; 
            white-space: nowrap; 
        }
        .metric-value { 
            font-size: 2.2rem; 
            font-weight: 900; 
            color: #000000; 
            line-height: 1; 
        }
        .val-safe { color: #2E8B57 !important; }
        .val-warn { color: #FF8C00 !important; }
        .val-danger { color: #E53935 !important; }
        .val-blue { color: #1E88E5 !important; }
        .val-purple { color: #8E24AA !important; }
        
        /* 자산 카드 스타일 */
        .prop-card-sell { 
            background-color: #e8f5e9 !important; 
            border-left: 5px solid #2e7d32; 
            padding: 10px; 
            border-radius: 5px; 
            margin-bottom: 8px; 
        }
        .prop-card-inherit { 
            background-color: #e3f2fd !important; 
            border-left: 5px solid #1565c0; 
            padding: 10px; 
            border-radius: 5px; 
            margin-bottom: 8px; 
        }
        .prop-card-sell div, 
        .prop-card-inherit div, 
        .prop-title { 
            color: #000000 !important; 
            font-family: sans-serif; 
        }
        .prop-title { 
            font-weight: bold; 
            font-size: 14px; 
        }
        
        /* Client Info 타이틀도 Primary Color로 통일 */
        .sidebar-title { 
            font-size: 2rem; 
            font-weight: 900; 
            color: var(--primary-color); 
            text-align: center; 
        } 
        .sidebar-subtitle { 
            font-size: 12px; 
            color: #666; 
            text-align: center; 
            margin-bottom: 20px; 
        }
        </style>
    """, unsafe_allow_html=True)

    if 'properties' not in st.session_state:
        st.session_state.properties = []

    # ==============================================================================
    # 1. 로직 엔진
    # ==============================================================================
    class WannabeEngine:
        def __init__(self, current_age, retire_age, death_age):
            self.current_age = current_age
            self.retire_age = retire_age
            self.death_age = death_age
            self.period = death_age - current_age + 1

        def run_simulation(
            self, liquid_billions, monthly_save, monthly_spend,
            inflation, return_rate, properties_list, annual_hobby_cost
        ):
            liquid = liquid_billions * 100000000
            annual_save = monthly_save * 12 * 10000
            base_annual_spend = (monthly_spend * 12 * 10000) + annual_hobby_cost

            ages, liquid_history, real_estate_history = [], [], []
            props = [p.copy() for p in properties_list]
            current_liquid = liquid
            shortfall_age = None
            
            for i in range(self.period):
                age = self.current_age + i
                ages.append(age)

                # 1) 수익 반영
                current_liquid = current_liquid * (1 + return_rate)

                # 2) 저축/지출 반영
                if age < self.retire_age:
                    current_liquid += annual_save
                else:
                    current_liquid -= base_annual_spend * ((1 + inflation) ** i)
                
                # 3) 부동산 평가 + 매각 처리
                current_re_net_val = 0
                for p in props:
                    if p.get('is_sold', False):
                        continue

                    years = age - self.current_age
                    gross_val = (p['current_val'] * 100000000) * ((1 + inflation) ** years)
                    loan_amt = p.get('loan', 0) * 100000000
                    net_equity = max(0, gross_val - loan_amt)
                    
                    if p['strategy'] == '매각 (Sell)' and age == p['sell_age']:
                        purchase_val = p['purchase_price'] * 100000000
                        capital_gain = gross_val - purchase_val
                        tax = capital_gain * 0.25 if capital_gain > 0 else 0
                        current_liquid += (gross_val - loan_amt - tax)
                        p['is_sold'] = True
                        net_equity = 0

                    current_re_net_val += net_equity
                
                if current_liquid < 0 and shortfall_age is None:
                    shortfall_age = age

                liquid_history.append(current_liquid / 100000000)
                real_estate_history.append(current_re_net_val / 100000000)

            return ages, liquid_history, real_estate_history, shortfall_age

        def calculate_score(self, shortfall_age):
            if shortfall_age is None:
                return 100, "완벽 (Perfect)"

            gap = self.death_age - shortfall_age
            if gap <= 0:
                return 90, "안정 (Stable)"
            elif gap <= 5:
                return 70, "주의 (Caution)"
            elif gap <= 10:
                return 50, "위험 (Danger)"
            else:
                return 30, "심각 (Critical)"

    # ==============================================================================
    # 2. [왼쪽 프레임] 입력 UI
    # ==============================================================================
    with input_col:
        # Client Info 타이틀
        st.markdown("""
            <div class="sidebar-container">
                <h3 class="sidebar-title">🧮 Client Info</h3> 
            </div>
        """, unsafe_allow_html=True)
        st.write("")
        
        # 2-1. 기본 정보
        with st.expander("1. 기본 정보 (Profile)", expanded=False): 
            c1, c2 = st.columns(2)
            age_curr = c1.number_input("현재 나이", 30, 80, 50)
            age_retire = c2.number_input("은퇴 목표", 50, 90, 65)
            age_death = st.number_input("기대 수명", 80, 120, 95)

        # 2-2. 금융 자산
        with st.expander("2. 금융 자산 (Finance)", expanded=False): 
            c1, c2 = st.columns(2)
            liquid_asset = c1.number_input("유동자산(억)", 0.0, 100.0, 3.0, step=0.1)
            monthly_save = c2.number_input("월 저축(만원)", 0, 10000, 300, step=10)
            return_rate_int = st.slider("투자 수익률(%)", 0, 15, 4, step=1)
            return_rate = return_rate_int / 100

        # 2-3. 부동산 자산
        with st.expander("3. 부동산 자산 (Real Estate)", expanded=False):

            # ▶ 자산 입력 폼
            # - Streamlit의 st.form은 submit 시점에만 값이 확정되며,
            #   submit 이후 st.rerun()이 호출되면 화면이 다시 그려집니다.
            # - 따라서 "등록된 자산 목록"은 submit 여부와 무관하게 항상 렌더링되도록
            #   form 바깥(=expander 영역)에 배치해야 합니다. (특허 명세서 대비: UI/상태 일관성 핵심)
            with st.form("prop_form", clear_on_submit=True):
                r1_c1, r1_c2 = st.columns(2)
                p_name = r1_c1.text_input("자산명", placeholder="예: 아파트")
                p_curr = r1_c2.number_input("현재가(억)", 0, 300, 10)

                r2_c1, r2_c2 = st.columns(2)
                p_buy = r2_c1.number_input("매입가(억)", 0, 300, 5)
                p_loan = r2_c2.number_input("대출금(억)", 0, 200, 0)

                r3_c1, r3_c2 = st.columns(2)
                p_strat = r3_c1.radio("계획", ["매각", "상속"])
                p_sell = r3_c2.slider("시기(세)", age_curr, 100, 75)

                st.write("")
                b1, b2, b3 = st.columns([1, 2, 1])
                with b2:
                    btn_submitted = st.form_submit_button("➕ 자산 추가", use_container_width=True)

                # ✅ 버튼 아래에 에러 메시지 위치 (form 내부: UX 일관성)
                warning_placeholder = st.empty()

                if btn_submitted:
                    # 입력 검증: 자산명이 비어 있으면 저장하지 않음
                    if not p_name or p_name.strip() == "":
                        warning_placeholder.error("⚠️ 자산명칭을 입력해주세요.")
                    else:
                        strat_code = "매각 (Sell)" if "매각" in p_strat else "상속 (Inherit)"

                        # 상태 저장: session_state.properties에 누적 (앱 전체에서 동일 참조)
                        st.session_state.properties.append({
                            "name": p_name.strip(),
                            "current_val": p_curr,
                            "loan": p_loan,
                            "purchase_price": p_buy,
                            "strategy": strat_code,
                            "sell_age": p_sell,
                            "is_sold": False
                        })

                        # 경고 제거 후 즉시 화면 갱신
                        warning_placeholder.empty()
                        st.rerun()

            # ▶ 자산 목록
            # - [버그 원인] 기존 코드는 자산 목록 렌더링 코드가 form submit 분기 안쪽에 잘못 들여쓰기 되어
            #   '추가' 버튼을 눌렀을 때만 목록이 갱신/표시되는 구조였습니다.
            # - 또한 submit 시 st.rerun()이 실행되면 그 아래 코드가 실행되지 않으므로,
            #   목록이 화면에 나타나지 않는 증상이 반복될 수 있습니다.
            # - [해결] 목록 렌더링을 form 바깥으로 이동하여, session_state의 현재 상태를 항상 반영합니다.
            if st.session_state.properties:
                st.markdown("---")
                st.markdown("**📋 등록된 자산 목록**")

                for i, p in enumerate(st.session_state.properties):
                    # 텍스트 구성
                    desc = "상속" if "상속" in p["strategy"] else f"매각 ({p['sell_age']}세)"
                    css_class = "prop-card-sell" if "매각" in p["strategy"] else "prop-card-inherit"
                    icon = "💰" if "매각" in p["strategy"] else "🎁"
                    net = p["current_val"] - p["loan"]

                    # 한 줄에: [카드 전체 텍스트] | [삭제 버튼]
                    col_info, col_btn = st.columns([9, 1])

                    # 왼쪽: 색깔 카드 + 한 줄 요약
                    with col_info:
                        st.markdown(
                            f"""
                            <div class="{css_class}">
                                <div class="prop-title">{icon} {p['name']}</div>
                                <div>순자산가치 {net}억 (대출 {p['loan']}억) {desc}</div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                    # 오른쪽: 삭제 버튼만
                    with col_btn:
                        st.write("")  # 살짝 위 여백
                        if st.button("X", key=f"del_{i}"):
                            # 삭제 후 즉시 rerun하여 화면/상태 동기화
                            st.session_state.properties.pop(i)
                            st.rerun()
        # 2-4. 라이프스타일
        with st.expander("4. 라이프스타일 (Lifestyle)", expanded=False):
            monthly_spend = st.number_input("은퇴 월 생활비(만원)", 0, 5000, 300)
            c1, c2 = st.columns(2)
            golf_freq = c1.selectbox("골프 라운딩", ["안 함", "월 1회", "월 2회", "월 4회", "VIP"])
            c1.caption("회당 40만원")
            travel_freq = c2.selectbox("해외 여행", ["안 함", "연 1회", "연 2회", "분기별"])
            c2.caption("회당 400만원")
            inflation = st.select_slider("물가상승률", ["안정(2%)", "보통(3.5%)", "심각(5%)"], value="보통(3.5%)")

    # ==============================================================================
    # 3. [오른쪽 프레임] 메인 화면
    # ==============================================================================
    golf_map = {"안 함": 0, "월 1회": 12, "월 2회": 24, "월 4회": 48, "VIP": 100}
    travel_map = {"안 함": 0, "연 1회": 1, "연 2회": 2, "분기별": 4}
    annual_hobby_cost = (golf_map[golf_freq] * 400000) + (travel_map[travel_freq] * 4000000)
    inf_val = {"안정(2%)": 0.02, "보통(3.5%)": 0.035, "심각(5%)": 0.05}[inflation]

    engine = WannabeEngine(age_curr, age_retire, age_death)
    ages, liq_norm, re_norm, ob_norm = engine.run_simulation(
        liquid_asset, monthly_save, monthly_spend,
        inf_val, return_rate, st.session_state.properties, annual_hobby_cost
    )
    score, grade = engine.calculate_score(ob_norm)

    st.markdown("""
        <div class="title-container">
            <div class="responsive-title">⛳ Retirement Readiness Checkup</div>
        </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            f"""
            <div class="metric-container">
                <div class="metric-label">🎯 은퇴 준비 점수</div>
                <div class="metric-value val-blue">{score}점</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with c2:
        st.markdown(
            f"""
            <div class="metric-container">
                <div class="metric-label">🏆 진단 등급</div>
                <div class="metric-value val-purple">{grade.split('(')[0]}</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with c3:
        if ob_norm:
            icon = "🚨"
            val_text = f"{ob_norm}세"
            color_class = "val-danger"
        else:
            icon = "⏳"
            val_text = "Safe"
            color_class = "val-safe"

        st.markdown(
            f"""
            <div class="metric-container">
                <div class="metric-label">{icon} 현금 고갈 시점</div>
                <div class="metric-value {color_class}">{val_text}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.write("")
    st.subheader("📈 자산별 생애 궤적")
    
    fig = go.Figure()

    # 1) 부동산(순자산) - hover 텍스트 1, 2줄 담당
    fig.add_trace(go.Scatter(
        x=ages,
        y=re_norm,
        name='부동산(순자산)',
        line=dict(color='#8d6e63', width=3, dash='dash'),
        fill='tozeroy',
        fillcolor='rgba(141, 110, 99, 0.1)',
        hovertemplate="<b>%{x}세</b><br>부동산(순자산): %{y:.1f}억<extra></extra>"
    ))

    # 2) 현금 자산 - hover 텍스트 3줄 담당
    fig.add_trace(go.Scatter(
        x=ages,
        y=liq_norm,
        name='현금 자산',
        line=dict(color='#2e7d32', width=4),
        mode='lines',
        hovertemplate="현금 자산: %{y:.1f}억<extra></extra>"
    ))

    # 기준선 (0억)
    fig.add_shape(
        type="line",
        x0=age_curr, y0=0,
        x1=age_death, y1=0,
        line=dict(color="red", width=1)
    )

    # 부동산 매각 시점 말풍선
    for p in st.session_state.properties:
        if "매각" in p['strategy'] and p['sell_age'] <= age_death:
            idx = p['sell_age'] - age_curr
            if 0 <= idx < len(liq_norm):
                fig.add_annotation(
                    x=p['sell_age'],
                    y=liq_norm[idx],
                    text=f"↗ {p['name']}",
                    showarrow=True,
                    arrowhead=2,
                    ay=-30,
                    font=dict(color="#2e7d32", size=10)
                )

    # hover 시 점선 + unified 박스 (원래 설정 유지했다면 여기에)
    fig.update_layout(
        template="plotly_white",
        height=400,
        margin=dict(l=20, r=20, t=50, b=50),
        legend=dict(
            orientation="h",
            yanchor="bottom", y=1.02,
            xanchor="right", x=1
        ),
        dragmode=False,
        xaxis=dict(
            fixedrange=True,
            title="경과나이 (세)",
            showspikes=True,
            spikemode="across",
            spikethickness=1.5,
            spikedash="dot",
            spikecolor="rgba(120,120,120,0.8)",
        ),
        yaxis=dict(
            fixedrange=True,
            title="금액단위 (억원)",
            showspikes=True,
            spikemode="across",
            spikethickness=1.5,
            spikedash="dot",
            spikecolor="rgba(120,120,120,0.4)",
        ),
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor="rgba(255, 255, 255, 0.9)",
            font_size=12,
            font_color="black",
        ),
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
        config={'displayModeBar': False, 'scrollZoom': False}
    )

    st.info("""
    💡 **그래프 해석 가이드**

    1. **갈색 점선 + 음영** → 부동산 순자산
    2. **초록 실선** → 현금 자산(유동자산)
    3. **빨간 가로선(0억)** → 현금/자산 기준선
    4. 마우스를 올리면
       **64세 → 부동산(순자산) → 현금 자산** 순으로
       한 박스에 정리되어 표시됩니다.
    """)



    # ==============================================================================
    # 4. 심층 분석 및 상담 신청
    # ==============================================================================
    st.subheader("📝 전문가 심층 분석")
    
    with st.expander("1. 현금 흐름 및 자산 수명", expanded=True):
        if score >= 90:
            st.success("✅ **[Excellent] '골든 포트폴리오' 달성: 자산 수명 > 기대 수명**")
            st.markdown("""
            * **진단:** 현재의 소비 수준과 물가 상승을 고려하더라도, 기대 수명까지 자산이 고갈되지 않는 **이상적인 은퇴 구조**입니다.
            * **제언:** 이제는 '자산 증식'보다 '**자산 관리 및 이전**'에 집중해야 할 시기입니다.
                * 금융 자산의 비과세/감면 상품 활용을 통한 세후 수익률 극대화.
                * 자녀 세대로의 부의 이전을 위한 **상속/증여 플랜** 수립.
            """)
        elif score >= 70:
            st.info("⚠️ **[Caution] 구매력 보존 주의: 인플레이션 헤지 필요**")
            st.markdown("""
            * **진단:** 현재는 안정적이나, 장기적인 **인플레이션(물가 상승)** 충격 시 구매력이 서서히 저하될 위험이 있습니다.
            * **제언:** 현금 비중이 너무 높다면 '**실질 마이너스 금리**' 위험에 노출됩니다.
                * 확정 금리형 상품보다는, 물가 상승을 방어할 수 있는 **배당 성장주**나 **리츠(REITs)** 등 현금 창출형 실물 자산 비중을 늘리십시오.
            """)
        elif score >= 50:
            st.warning(f"🚨 **[Warning] 소득 절벽 경고: {ob_norm}세 전후 '소득 절벽'**")
            st.markdown(f"""
            * **진단:** 은퇴 후 {ob_norm}세 시점에 보유 현금이 바닥날 것으로 예측됩니다. 이는 '**장수 리스크(Longevity Risk)**'에 취약한 구조입니다.
            * **제언:** 즉각적인 **구조조정(Restructuring)**이 필요합니다.
                * **주택연금:** 거주 주택을 활용하여 평생 월급을 확보하십시오.
                * **지출 통제:** 고정 지출(보험료, 차량 유지비 등)을 20% 이상 감축하는 다이어트가 시급합니다.
            """)
        else:
            st.error("🆘 **[Critical] 비상 단계: 즉각적인 유동성 확보 필수**")
            st.markdown("""
            * **진단:** 은퇴 직후부터 심각한 유동성 부족에 직면합니다. 현재의 자산 구조로는 노후 생활 유지가 불가능합니다.
            * **제언:** 특단의 조치가 없으면 빈곤한 노후가 예상됩니다.
                * **부동산 다운사이징:** 거주지를 옮겨 현금을 확보하십시오.
                * **제2의 소득:** 재취업이나 창업을 통해 근로 소득 기간을 최소 5년 이상 연장해야 합니다.
            """)

    with st.expander("2. 부동산 리스크 및 상속 세무", expanded=True):
        inherit_props = [p for p in st.session_state.properties if "상속" in p['strategy']]
        if inherit_props:
            inherit_val = sum([p['current_val'] for p in inherit_props])
            st.error("🚨 **[Tax Warning] 부동산 상속 리스크 감지**")
            st.markdown(f"""
            <div style='background-color: #ffebee; padding: 15px; border-radius: 10px; border: 1px solid #ffcdd2;'>
                <strong style='color: #b71c1c; font-size: 1.1em;'>
                    ⚠️ 현재 {inherit_val}억 원 상당의 상속 계획. 상속세 재원(종신보험) 마련이 필수적입니다.
                </strong>
                <ul style='margin-top: 10px; color: #333;'>
                    <li>대한민국의 상속세율은 <b>최대 50%</b>(누진세율)에 달합니다.</li>
                    <li>자녀들이 충분한 <b>현금 재원</b>을 준비하지 못한다면, 세금을 납부하기 위해 물려주신 소중한 부동산을 <b>급매(헐값 처분)</b>하거나 <b>물납</b>해야 하는 상황이 발생합니다.</li>
                    <li>👉 <b>Action Plan:</b> 종신보험을 활용한 상속세 재원 마련 또는 '부담부 증여' 등 사전 증여 컨설팅이 필수적입니다.</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
        
        net_re = sum([max(0, p['current_val'] - p['loan']) for p in st.session_state.properties])
        total_asset = liquid_asset + net_re
        ratio = net_re / total_asset if total_asset > 0 else 0
        
        loans = sum([p['loan'] for p in st.session_state.properties])
        if loans > 0:
            st.markdown(f"📉 **부채 관리:** 현재 보유 부채 **{loans}억 원**은 은퇴 전 반드시 상환하여 고정비 지출을 없애야 합니다.")

        st.markdown("**📊 자산 배분 비율 분석**")
        if ratio > 0.8:
            st.warning(f"**🏠 부동산 과다 보유 (비중 {ratio*100:.0f}%)**")
            st.write("전형적인 '**Asset Rich, Cash Poor**' 유형입니다. 부동산 시장 침체 시 유동성 위기가 발생할 수 있으니, 비중을 60% 이하로 낮추는 전략적 매각이 필요합니다.")
        elif ratio > 0.5:
            st.info(f"⚖️ **균형 잡힌 자산 배분 (비중 {ratio*100:.0f}%)**")
            st.write("안정적인 배분입니다. 글로벌 자산 배분을 강화하세요.")
        else:
            st.success(f"💵 **풍부한 유동성 (비중 {ratio*100:.0f}%)**")
            st.write("위기에 강하지만 인플레이션에 취약할 수 있습니다. 물가 방어용 자산을 일부 편입하는 것도 고려하십시오.")

    with st.expander("3. 변동성 관리 및 투자 전략", expanded=True):
        if return_rate_int < 3:
            st.markdown("**🛡️ 보수적 운용 (Low Risk)**")
            st.write("원금 보존 중심입니다. 다만 물가상승률 + 1~2% 수준의 수익은 확보해야 실질 구매력을 지킬 수 있습니다.")
        elif return_rate_int > 7:
            st.markdown("**🚀 공격적 운용 (High Risk)**")
            st.write("수익률은 높지만 은퇴 직전 폭락장에 매우 취약합니다. 은퇴 5년 전부터는 위험자산 비중을 줄이고 안전자산을 늘리는 전략이 필요합니다.")
        else:
            st.markdown("**⚖️ 중위험·중수익 (Moderate Risk)**")
            st.write("가장 권장되는 구간입니다. TDF 등 은퇴시점 펀드를 활용하여 자동으로 리스크를 줄이는 구조가 적합합니다.")

    # ==============================================================================
    # 4-2. 공통 상담 신청 폼
    # ==============================================================================
    props_str = ", ".join([p['name'] for p in st.session_state.properties]) if st.session_state.properties else "없음"
    re_asset = sum([p['current_val'] for p in st.session_state.properties])
    props_json = json.dumps(st.session_state.properties, ensure_ascii=False)
    inflation_label = inflation

    simulation_data = {
        "age": age_curr,
        "retire_age": age_retire,
        "death_age": age_death,
        "asset": liquid_asset,
        "save": monthly_save,
        "rate_pct": return_rate_int,
        "props_str": props_str,
        "spend": monthly_spend,
        "golf_freq": golf_freq,
        "travel_freq": travel_freq,
        "inflation_pct": inf_val * 100,
        "score": score,
        "grade": grade,
        "shortfall_txt": f"{ob_norm}세" if ob_norm else "Safe",
        "re_asset": re_asset,
        "props_json": props_json,
        "inflation_label": inflation_label
    }

    render_common_form(
        app_type="life",
        DataModelClass=LifeData,
        **simulation_data

    )
