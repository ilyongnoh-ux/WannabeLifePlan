import streamlit as st
import base64
import requests
import json
import os

# [필수] 구글 앱스 스크립트(GAS) 배포 URL
GAS_URL = "https://script.google.com/macros/s/AKfycbwF9R_qvwl1yhXaXsohYnTOBx1NR0s8tDNfzXL3jy8_WJm96RSiMBxS4tYFQAULSexu/exec"

def _get_base64_image(file_path):
    """(내부용) 이미지를 Base64로 변환하는 함수"""
    try:
        # 파일이 실제로 존재하는지 확인
        if not os.path.exists(file_path):
            # 파일이 없으면 경고 후 종료 (또는 기본 아이콘 사용 로직 추가 가능)
            print(f"⚠️ 경고: '{file_path}' 파일을 찾을 수 없습니다.")
            return None
            
        with open(file_path, "rb") as f:
            data = f.read()
        encoded_string = base64.b64encode(data).decode()
        return f"data:image/png;base64,{encoded_string}"
    except Exception as e:
        print(f"이미지 변환 중 오류 발생: {e}")
        return None

def set_global_page_config(page_title="한국금융투자기술", icon_path="logo.png"):
    """
    모든 페이지에서 공통으로 사용할 페이지 설정 함수
    :param page_title: 페이지 제목 (기본값 설정됨)
    :param icon_path: 아이콘 파일 경로 (기본값: ci.png)
    """
    
    # 1. 아이콘 이미지 로드 및 변환
    icon_data = _get_base64_image(icon_path)
    
    # 이미지가 변환되지 않았으면(파일 없음 등) 기본 이모지 사용
    final_icon = icon_data if icon_data else "💰" 

    # 2. set_page_config 실행
    st.set_page_config(
        page_title=page_title,
        page_icon=final_icon,
        layout="wide",
        initial_sidebar_state="collapsed"
    )

    # 3. (선택사항) 모든 페이지에 공통으로 적용할 CSS가 있다면 여기에 추가 가능
    # st.markdown(...)

def send_data_to_api(app_type, data_list):
    '''API 전송 함수'''
    if "여기에" in GAS_URL:
        return False, "utils.py에 GAS_URL을 입력해주세요."
    try:
        payload = {"type": app_type, "payload": data_list}
        response = requests.post(GAS_URL, data=json.dumps(payload), headers={'Content-Type': 'application/json'})
        if response.status_code == 200: return True, "저장 성공"
        else: return False, f"서버 오류: {response.status_code}"
    except Exception as e: return False, f"전송 실패: {str(e)}"

def set_bg_hack(main_bg):
    '''Home 배경 설정'''
    try:
        main_bg_ext = "jpg"
        st.markdown(
             f"""
             <style>
             .stApp {{
                 background: url(data:image/{main_bg_ext};base64,{base64.b64encode(open(main_bg, "rb").read()).decode()});
                 background-size: cover; background-position: center; background-repeat: no-repeat; background-attachment: fixed;
             }}
             </style>
             """, unsafe_allow_html=True)
    except: pass

def hide_header():
    '''상단 툴바 숨기기'''
    st.markdown("""<style>[data-testid="stHeader"] {visibility: hidden;} #MainMenu {visibility: hidden;} footer {visibility: hidden;} .block-container {padding-top: 0rem !important;}</style>""", unsafe_allow_html=True)

def hide_sidebar():
    '''사이드바 숨기기'''
    st.markdown("""<style>[data-testid="stSidebar"] {display: none;} [data-testid="stSidebarCollapsedControl"] {display: none;}</style>""", unsafe_allow_html=True)

def show_footer():
    '''공통 풋터'''
    st.markdown(
        """
        <style>
        .kfit-footer {
            position: fixed;
            left: 0;
            bottom: 0;
            width: 100%;
            text-align: center;
            padding: 10px 0;
            
            color: rgba(255, 255, 255, 0.85);
            background: linear-gradient(to top, rgba(0,0,0,0.9), rgba(0,0,0,0));
            z-index: 999;
            
            /* [핵심 수정 1] 반응형 폰트 크기: 화면 폭에 따라 폰트가 자동으로 줄어듭니다.
               최소 10px, 권장 3.2vw(화면폭의 3.2%), 최대 0.85rem */
            font-size: clamp(10px, 3.2vw, 0.85rem);
            
            /* [핵심 수정 2] 강제 줄바꿈 방지: <br> 태그 외에는 줄이 바뀌지 않습니다. */
            white-space: nowrap;
            
            /* 혹시라도 글자가 화면을 넘어갈 경우를 대비한 안전장치 */
            overflow: hidden;
            text-overflow: ellipsis;
        }
        </style>
        <div class="kfit-footer">
            본 사이트의 모든 컨텐츠는 저작권법의 보호를 받으므로 무단 전재, 복사, 배포를 금합니다. <br> 
            Copyright © 2025 Korea Financial Investment Technology(KFIT)® All rights reserved.
        </div>
        """,
        unsafe_allow_html=True,
    )


# ==========================================
# [NEW] 공통 상담 신청 폼 컴포넌트
# ==========================================
def render_common_form(app_type, DataModelClass, **simulation_data):
    """
    모든 앱에서 공통으로 사용하는 상담 신청 폼
    :param app_type: "golf", "tax", "life" 등 API 구분값
    :param DataModelClass: models.py에 정의된 데이터 클래스 (GolfData 등)
    :param simulation_data: 각 앱에서 계산된 결과값들 (딕셔너리 형태로 전달)
    """
    st.divider()
    st.markdown("### 📞 맞춤 컨설팅 신청")
    st.caption("상세 리포트와 전문가 피드백을 받아보실 수 있습니다.")

    with st.form(f"{app_type}_common_form"):
        # 공통 입력 필드 (2단 배열)
        c1, c2 = st.columns(2)
        name = c1.text_input("성함", placeholder="예: 홍길동")
        phone = c2.text_input("연락처", placeholder="예: 01062559978")
        
        memo = st.text_area("문의사항 (선택)", placeholder="궁금한 점을 남겨주세요.", height=80)
        st.markdown("""
                <div style="font-size: 14px; color: #9CA3AF; margin-bottom: 5px;">
                🔒 입력하신 정보는 <b>오직 상담 목적으로만 활용</b>되며, 외부로 유출되지 않습니다.
                </div>
                """, unsafe_allow_html=True)
        agree = st.checkbox("개인정보 수집 및 이용에 동의합니다.")
        
        submit_btn = st.form_submit_button("🚀 신청 완료 하기", use_container_width=True)

        if submit_btn:
            if not name or not phone:
                st.warning("⚠️ 성함과 연락처를 입력해주세요.")
            elif not agree:
                st.warning("⚠️ 개인정보 동의가 필요합니다.")
            else:
                # [핵심] 공통 필드(이름,폰,메모) + 시뮬레이션 결과(simulation_data)를 합쳐서 객체 생성
                try:
                    data_obj = DataModelClass(
                        name=name, 
                        phone=phone, 
                        memo=memo, 
                        **simulation_data
                    )
                    
                    with st.spinner('데이터 전송 중...'):
                        res, msg = send_data_to_api(app_type, data_obj.to_payload())
                    
                    if res:
                        st.balloons()
                        st.success(f"✅ {name}님, 신청이 완료되었습니다!")
                    else:
                        st.error(f"❌ 전송 실패: {msg}")
                except Exception as e:

                    st.error(f"데이터 처리 중 오류 발생: {str(e)}")


API_BASE = "https://api.kfit.kr"
