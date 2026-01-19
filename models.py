from dataclasses import dataclass
from typing import List, Any

# ==========================================
# 1. 골프 앱 데이터 모델 (Wannabe_Golf)
# ==========================================
@dataclass
class GolfData:
    # 공통 입력
    name: str          # 상담 폼: "성함"
    phone: str         # 상담 폼: "연락처"

    # 앱 입력값 (Wannabe_Golf.py)
    current_age: int   # "현재 나이"
    retire_age: int    # "은퇴 예정 나이"
    assets: int        # "현재 골프 자금 (만원)" * 10,000 → 원 단위
    saving: int        # "월 추가 저축액 (만원)" * 10,000 → 원 단위
    rounds: int        # "월 라운딩 횟수 (회)"
    cost: int          # "회당 비용 (그늘집 포함)" * 10,000 → 원 단위

    # 시뮬레이션 결과
    bankruptcy_age: int  # 골프 자금 고갈 예상 나이
    result_msg: str      # 화면에 보여주는 요약 결과 메시지

    # 공통 메모
    memo: str = ""          # 상담 폼: "문의사항"

    def to_payload(self) -> List[Any]:
        return [
            self.name, "'"+self.phone,
            self.current_age, self.retire_age,
            self.assets, self.saving,
            self.rounds, self.cost,
            self.bankruptcy_age, self.result_msg,
            self.memo
        ]


# ==========================================
# 2. 세금 앱 데이터 모델 (Wannabe_Tax)
# ==========================================
@dataclass
class TaxData:
    # 공통 입력
    name: str          # 상담 폼: "성함"
    phone: str         # 상담 폼: "연락처"

    # 앱 입력값 (Wannabe_Tax.py)
    real_estate_billions: int  # "🏠 부동산 (단위: 억)"
    financial_billions: int    # "💰 금융/동산 (단위: 억)"
    total_estate_eok: float    # 총 자산(원)을 1억으로 나눈 값

    has_spouse_str: str        # 배우자 유무 문자열 ("있음"/"없음")
    spouse_pct: int            # "배우자 상속 비율 (%)"
    sim_years: int             # "시뮬레이션 기간 (년)"
    inflation_re_pct: float    # "부동산 연 상승률 (%)"
    inflation_fin_pct: float   # "금융자산 연 수익률 (%)"
    calculated_tax_now: float = 0 # 현재사망시 상속세
    calculated_future_tax: float = 0 #2차 상속세 
    calculated_future_cash: float = 0 # 총납부 예상액
    is_liquidity_crisis: str = "" # 진달결과
    shortage_amount: float = 0   #부족한 현금
    # 공통 메모
    memo: str = ""                  # 상담 폼: "문의사항"

    def to_payload(self) -> List[Any]:
        return [
            self.name, "'"+self.phone,
            self.real_estate_billions, self.financial_billions,
            self.total_estate_eok,
            self.has_spouse_str, self.spouse_pct,
            self.sim_years,
            self.inflation_re_pct, self.inflation_fin_pct,
            self.calculated_tax_now,
            self.calculated_future_tax,
            self.calculated_future_cash,
            self.is_liquidity_crisis,
            self.shortage_amount,
            self.memo
        ]

# ==========================================
# 3. 은퇴 앱 데이터 모델 (Wannabe_Life_Plan)
# ==========================================
@dataclass
class LifeData:
    # ── 공통 상담 정보 ─────────────────────────────
    name: str          # 상담 폼: 성함
    phone: str         # 상담 폼: 연락처

    # ── 1. 기본 정보 입력폼 ────────────────────────
    age: int           # 현재 나이 (age_curr)
    retire_age: int    # 은퇴 목표 나이 (age_retire)
    death_age: int     # 기대 수명 (age_death)

    # ── 2. 금융 자산 입력폼 ────────────────────────
    asset: float       # 유동자산(억) number_input
    save: int          # 월 저축(만원) number_input
    rate_pct: int      # 투자 수익률(%) 슬라이더 값 (정수 %)

    # ── 3. 부동산 자산 입력폼 ──────────────────────
    re_asset: float    # 부동산 순자산 합계(억) = ∑ max(현재가-대출, 0)
    props_str: str     # 부동산 이름 요약 (예: "아파트, 상가")
    props_json: str    # 부동산 상세 데이터 전체(JSON 문자열)
                       #  - name, current_val, buy_price, loan,
                       #    strategy, sell_age, is_sold 등

    # ── 4. 라이프스타일 입력폼 ─────────────────────
    spend: int         # 은퇴 월 생활비(만원)
    golf_freq: str     # 골프 라운딩 선택값
    travel_freq: str   # 해외 여행 선택값

    # ── 5. 인플레이션 입력폼 ───────────────────────
    inflation_label: str  # 물가상승률 선택 라벨 ("안정(2%)" 등)
    inflation_pct: float  # 물가상승률 % 값 (2.0 / 3.5 / 5.0 등)

    # ── 6. 시뮬레이션 결과 ────────────────────────
    score: int         # 은퇴 준비 점수
    grade: str         # 등급 ("A" / "B" / "C" 등)
    shortfall_txt: str # 자산 고갈 나이 텍스트 (예: "83세" 또는 "Safe")

    # ── 7. 공통 메모 ───────────────────────────────
    memo: str = ""          # 상담 폼: 문의사항

    def to_payload(self) -> List[Any]:
        """
        구글 시트 컬럼 순서:
        이름 / 연락처 / 현재나이 / 은퇴목표 / 기대수명 /
        유동자산 / 부동산순자산 / 월저축 / 투자수익률(%) /
        부동산요약 / 부동산JSON /
        은퇴월생활비 / 골프 / 여행 /
        물가라벨 / 물가(%) /
        점수 / 등급 / 고갈나이 /
        메모
        """
        return [
            self.name, "'"+self.phone,
            self.age, self.retire_age, self.death_age,
            self.asset, self.re_asset,
            self.save, self.rate_pct,
            self.props_str, self.props_json,
            self.spend, self.golf_freq, self.travel_freq,
            self.inflation_label, self.inflation_pct,
            self.score, self.grade, self.shortfall_txt,
            self.memo
        ]
