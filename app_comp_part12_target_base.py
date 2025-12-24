# app_comp_part12.py
import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib

from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# 만약 Part2에서 더 이상 comp_core를 쓰지 않는다면, 아래 import는 있어도 되고 없어도 됩니다.
from comp_core_target_base import simulate_all

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from pathlib import Path
import matplotlib
from matplotlib import font_manager as fm

# 페이지 레이아웃
st.set_page_config(layout="wide", page_title="부동산 법인 급여·인센티브 시뮬레이터")

# # 한글 폰트 (윈도우 기준, 맑은고딕 가정)
# matplotlib.rcParams["font.family"] = "Malgun Gothic"
# matplotlib.rcParams["axes.unicode_minus"] = False

from pathlib import Path
import matplotlib
from matplotlib import font_manager as fm

def setup_korean_matplotlib_font():
    """
    Streamlit Cloud(리눅스)에서도 한글이 깨지지 않도록:
    1) repo에 포함된 폰트 파일(ttf/otf)을 우선 등록해서 사용
    2) 없으면 시스템 폰트 중 한글 폰트를 탐색
    """
    base = Path(__file__).resolve().parent

    # 1) repo에 포함된 폰트 우선 (루트 또는 fonts/ 폴더)
    font_candidates = [
        base / "NanumGothic.ttf",
        base / "fonts" / "NanumGothic.ttf",
        base / "NotoSansKR-Regular.otf",
        base / "fonts" / "NotoSansKR-Regular.otf",
    ]

    for fp in font_candidates:
        if fp.exists():
            # (중요) 폰트 캐시가 꼬였을 때를 대비해 fontlist 캐시 제거
            try:
                cache_dir = Path(matplotlib.get_cachedir())
                for f in cache_dir.glob("fontlist-v*.json"):
                    try:
                        f.unlink()
                    except Exception:
                        pass
            except Exception:
                pass

            # 폰트 등록 + 적용
            fm.fontManager.addfont(str(fp))
            font_name = fm.FontProperties(fname=str(fp)).get_name()

            # font.family를 sans-serif로 두고, sans-serif 후보 1순위로 지정하면 안정적
            matplotlib.rcParams["font.family"] = "sans-serif"
            matplotlib.rcParams["font.sans-serif"] = [font_name]
            matplotlib.rcParams["axes.unicode_minus"] = False
            return font_name

    # 2) repo에 폰트가 없다면 시스템 폰트에서 탐색(있을 수도/없을 수도)
    prefer_names = ["Noto Sans CJK KR", "Noto Sans KR", "NanumGothic", "Malgun Gothic"]
    installed = {f.name for f in fm.fontManager.ttflist}
    for name in prefer_names:
        if name in installed:
            matplotlib.rcParams["font.family"] = "sans-serif"
            matplotlib.rcParams["font.sans-serif"] = [name]
            matplotlib.rcParams["axes.unicode_minus"] = False
            return name

    # 실패 시 fallback (이 경우 한글 깨질 수 있음)
    matplotlib.rcParams["axes.unicode_minus"] = False
    return None

KOR_FONT_USED = setup_korean_matplotlib_font()
# 디버그용: 폰트 적용 여부 확인(원하면 남겨두세요)
# st.caption(f"Matplotlib Korean font: {KOR_FONT_USED}")


# 표 CSS
st.markdown(
    """
    <style>
    table {
        font-size: 14px;
        white-space: nowrap;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# # PDF용 한글 폰트 등록 시도
# PDF_FONT_NAME = "NanumGothic"
# try:
#     # 같은 폴더에 NanumGothic.ttf 파일을 두어야 합니다.
#     pdfmetrics.registerFont(TTFont(PDF_FONT_NAME, "NanumGothic.ttf"))
#     PDF_FONT_AVAILABLE = True
# except Exception:
#     # 폰트 미존재 시 기본 Helvetica 사용 (한글 깨질 수 있음)
#     PDF_FONT_AVAILABLE = False
#     PDF_FONT_NAME = "Helvetica"

BASE_DIR = Path(__file__).resolve().parent
PDF_FONT_NAME = "NanumGothic"
try:
    ttf_path = BASE_DIR / "NanumGothic.ttf"
    pdfmetrics.registerFont(TTFont(PDF_FONT_NAME, str(ttf_path)))
    PDF_FONT_AVAILABLE = True
except Exception:
    PDF_FONT_AVAILABLE = False


def generate_pdf(summary_p1, team_p1_df, exec_p1_df, summary_p2):
    """Part1/Part2 요약을 PDF로 저장"""
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)

    width, height = A4
    margin_left = 40
    margin_top = height - 40
    line_height = 14

    def set_font(bold=False, size=11):
        if PDF_FONT_AVAILABLE:
            c.setFont(PDF_FONT_NAME, size)
        else:
            c.setFont("Helvetica-Bold" if bold else "Helvetica", size)

    def draw_title(text):
        nonlocal margin_top
        set_font(bold=True, size=14)
        c.drawString(margin_left, margin_top, text)
        margin_top -= 2 * line_height

    def draw_subtitle(text):
        nonlocal margin_top
        set_font(bold=True, size=11)
        c.drawString(margin_left, margin_top, text)
        margin_top -= line_height

    def draw_text(text):
        nonlocal margin_top
        set_font(bold=False, size=9)
        c.drawString(margin_left, margin_top, text)
        margin_top -= line_height

    def check_page():
        nonlocal margin_top
        if margin_top < 60:
            c.showPage()
            margin_top = height - 40

    # Part1 요약
    draw_title("Part 1 결과 요약 (예상 매출 기준)")
    for _, row in summary_p1.iterrows():
        check_page()
        draw_subtitle(f"[{row['구분']}] {row['항목']}")
        draw_text(f"값: {row['값']}")
        draw_text(f"계산식: {row['계산식']}")
        margin_top -= line_height / 2
        check_page()

    # Part1 팀장·팀원
    check_page()
    draw_title("Part 1 – 팀장·팀원 연봉 상세 (1인 기준)")
    for _, row in team_p1_df.iterrows():
        check_page()
        draw_subtitle(f"{row['구분']}")
        draw_text(f"1인 기본연봉(억, 기본급+인센티브): {row['1인 기본연봉(억)']}")
        draw_text(f"1인 연말보너스(억): {row['1인 연말보너스(억)']}")
        draw_text(f"1인 최종연봉(억): {row['1인 최종연봉(억)']}")
        margin_top -= line_height / 2
        check_page()

    # Part1 임원
    check_page()
    draw_title("Part 1 – 임원 연봉 상세 (1인 기준)")
    for _, row in exec_p1_df.iterrows():
        check_page()
        draw_subtitle(f"{row['임원번호']}")
        draw_text(f"기본연봉(억, 기본급+매매보너스): {row['기본연봉(억)']}")
        draw_text(f"연말보너스(억, 전월세 잔여분): {row['연말보너스(억)']}")
        draw_text(f"최종연봉(억): {row['최종연봉(억)']}")
        margin_top -= line_height / 2
        check_page()

    # Part2 요약
    if summary_p2 is not None and len(summary_p2) > 0:
        check_page()
        draw_title("Part 2 결과 요약 (목표 연봉 기준 역산)")
        cols = summary_p2.columns.tolist()
        has_dual_val = "세금·경비 제외 전(억)" in cols and "세금·경비 제외 후(억)" in cols

        for _, row in summary_p2.iterrows():
            check_page()
            draw_subtitle(f"[{row['구분']}] {row['항목']}")
            if has_dual_val:
                draw_text(
                    f"세전: {row['세금·경비 제외 전(억)']} / "
                    f"세후: {row['세금·경비 제외 후(억)']}"
                )
            else:
                for col in cols:
                    if col not in ("구분", "항목"):
                        draw_text(f"{col}: {row[col]}")
            margin_top -= line_height / 2
            check_page()

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer


def main():
    st.title("부동산 중개 법인 급여·인센티브 시뮬레이터 (Part1 & Part2, 1인 기준)")

    # ---------------- 공통 설정 ----------------
    st.sidebar.header("공통 설정")

    tax_rate = st.sidebar.number_input(
        "법인 세금 비율", min_value=0.0, max_value=1.0, value=0.30, step=0.05
    )
    expense_rate = st.sidebar.number_input(
        "법인 필요경비 비율", min_value=0.0, max_value=1.0, value=0.20, step=0.05
    )

    # 팀장·팀원
    st.sidebar.markdown("---")
    st.sidebar.subheader("팀장·팀원 구조 (전월세 기준)")

    # 인원수는 인센티브/보너스 배분 비율 계산에만 사용 (연봉은 1인 기준)
    n_leaders = st.sidebar.number_input(
        "팀장 인원수", min_value=0, max_value=20, value=2, step=1
    )
    n_members = st.sidebar.number_input(
        "팀원 인원수", min_value=0, max_value=50, value=6, step=1
    )

    leader_base_salary = st.sidebar.number_input(
        "팀장 1인 기본급(억)", min_value=0.0, value=0.7, step=0.1
    )
    member_base_salary = st.sidebar.number_input(
        "팀원 1인 기본급(억)", min_value=0.0, value=0.4, step=0.1
    )

    rent_incentive_rate = st.sidebar.number_input(
        "전월세 인센티브율(세후 전월세 수수료 대비)",
        min_value=0.0, max_value=1.0, value=0.25, step=0.05
    )

    leader_weight = st.sidebar.number_input(
        "인센티브 배분 가중치(팀장)", min_value=0.0, value=2.0, step=0.5
    )
    member_weight = st.sidebar.number_input(
        "인센티브 배분 가중치(팀원)", min_value=0.0, value=1.0, step=0.5
    )

    # 임원
    st.sidebar.markdown("---")
    st.sidebar.subheader("임원 구조 (매매 기준)")

    n_exec = st.sidebar.number_input(
        "임원 인원수", min_value=1, max_value=10, value=1, step=1
    )

    corp_sales_keep_rate = st.sidebar.number_input(
        "세후 매매 수수료 중 법인 몫 비율",
        min_value=0.0, max_value=1.0, value=0.5, step=0.05,
    )

    exec_weights = []
    exec_base_salaries = []
    exec_target_salaries = []

    for i in range(n_exec):
        st.sidebar.markdown(f"임원 {i+1}")
        w = st.sidebar.number_input(
            f" - 배분 가중치 (임원 {i+1})",
            value=1.0, step=0.5, key=f"w_{i}"
        )
        b = st.sidebar.number_input(
            f" - 기본급(억, 임원 {i+1})",
            min_value=0.0, max_value=100.0, value=0.76, step=0.1, key=f"b_{i}"
        )
        t = st.sidebar.number_input(
            f" - 목표 연봉(억, 임원 {i+1})",
            min_value=0.0, max_value=100.0, value=0.985, step=0.1, key=f"t_{i}"
        )
        exec_weights.append(w)
        exec_base_salaries.append(b)
        exec_target_salaries.append(t)

    # 전월세 잔여분 연말 배분 비율
    st.sidebar.markdown("---")
    st.sidebar.subheader("전월세 잔여분 연말 배분 비율")

    rent_corp_share_rate = st.sidebar.number_input(
        "법인 이익 배분 비율(전월세 잔여분)", min_value=0.0, max_value=1.0, value=0.4, step=0.05
    )
    rent_exec_share_rate = st.sidebar.number_input(
        "임원 보너스 배분 비율(전월세 잔여분)", min_value=0.0, max_value=1.0, value=0.3, step=0.05
    )
    rent_leader_share_rate = st.sidebar.number_input(
        "팀장 보너스 배분 비율(전월세 잔여분)", min_value=0.0, max_value=1.0, value=0.15, step=0.05
    )
    rent_member_share_rate = st.sidebar.number_input(
        "팀원 보너스 배분 비율(전월세 잔여분)", min_value=0.0, max_value=1.0, value=0.15, step=0.05
    )

    rent_share_sum = (
        rent_corp_share_rate
        + rent_exec_share_rate
        + rent_leader_share_rate
        + rent_member_share_rate
    )

    if rent_share_sum > 0:
        rent_corp_share_norm = rent_corp_share_rate / rent_share_sum
        rent_exec_share_norm = rent_exec_share_rate / rent_share_sum
        rent_leader_share_norm = rent_leader_share_rate / rent_share_sum
        rent_member_share_norm = rent_member_share_rate / rent_share_sum
    else:
        rent_corp_share_norm = rent_exec_share_norm = 0.0
        rent_leader_share_norm = rent_member_share_norm = 0.0

    if rent_share_sum > 1.0:
        st.sidebar.warning(
            "전월세 잔여분 배분 비율 합이 1을 초과하여, 합이 1이 되도록 자동 정규화했습니다."
        )

    # Part2용 팀장/팀원 목표 연봉
    st.sidebar.markdown("---")
    st.sidebar.subheader("팀장·팀원 목표 연봉 (Part 2에서 사용, 1인 기준)")

    target_leader_salary = st.sidebar.number_input(
        "팀장 1인 목표 연봉(억)", min_value=0.0, value=0.9625, step=0.05
    )
    target_member_salary = st.sidebar.number_input(
        "팀원 1인 목표 연봉(억)", min_value=0.0, value=0.5125, step=0.05
    )

    # ---------------- Part 1: Forward ----------------
    st.header("Part 1 – 예상 매출 기준: 세금·경비 제외 후 연봉/순이익 (1인 기준)")

    st.subheader("1) 예상 매출 입력 (Forward)")

    col_p1_left, col_p1_right = st.columns(2)

    with col_p1_left:
        st.markdown("**전월세 수수료 예상**")
        rent_res_fee = st.number_input(
            "주택 전월세 수수료 수입(억) [Part1]",
            min_value=0.0, value=2.0, step=0.5,
        )
        rent_comm_fee = st.number_input(
            "상가 전월세 수수료 수입(억) [Part1]",
            min_value=0.0, value=4.0, step=0.5,
        )

    with col_p1_right:
        st.markdown("**매매 수수료 예상**")
        sales_res_fee = st.number_input(
            "주택 매매 수수료(억) [Part1]",
            min_value=0.0, value=3.0, step=0.5,
        )
        sales_comm_fee = st.number_input(
            "상가 매매 수수료(억) [Part1]",
            min_value=0.0, value=1.0, step=0.5,
        )
        sales_build_fee = st.number_input(
            "빌딩 매매 수수료(억) [Part1]",
            min_value=0.0, value=1.0, step=0.5,
        )

    # ===== Part1 핵심 수식 =====
    rent_total = rent_res_fee + rent_comm_fee            # 전월세 수수료 합(세전)
    sales_total = sales_res_fee + sales_comm_fee + sales_build_fee  # 매매 수수료 합(세전)
    total_revenue = rent_total + sales_total             # 총매출(세전)

    corp_expense = total_revenue * expense_rate          # 필요경비
    corp_tax = total_revenue * tax_rate                  # 세금

    after_tax_exp = total_revenue - corp_expense - corp_tax  # 세금·경비 제외 매출

    # 전월세/매매를 동일 비율로 세금·경비 차감한다고 가정
    net_factor = 1 - tax_rate - expense_rate
    rent_net = rent_total * net_factor   # 세후 전월세 수수료
    sales_net = sales_total * net_factor # 세후 매매 수수료

    # --- 팀장·팀원 인센티브 (세후 전월세 수수료 기준, 1인 기준 인센티브를 유도) ---
    incentive_pool = rent_net * rent_incentive_rate  # 전월세 세후 수수료 × 인센티브율

    weight_leaders = n_leaders * leader_weight
    weight_members = n_members * member_weight
    total_weight_tm = weight_leaders + weight_members

    if total_weight_tm > 0:
        leader_incentive_total = incentive_pool * (weight_leaders / total_weight_tm) if weight_leaders > 0 else 0.0
        member_incentive_total = incentive_pool * (weight_members / total_weight_tm) if weight_members > 0 else 0.0
    else:
        leader_incentive_total = 0.0
        member_incentive_total = 0.0

    if n_leaders > 0:
        leader_incentive_per = leader_incentive_total / n_leaders
    else:
        leader_incentive_per = 0.0

    if n_members > 0:
        member_incentive_per = member_incentive_total / n_members
    else:
        member_incentive_per = 0.0

    # 전월세 잔여분: 인센티브 지급 후 남는 세후 전월세 수수료
    rent_residual_for_corp = rent_net - incentive_pool  # = rent_net * (1 - rent_incentive_rate)

    # 잔여분 연말 배분
    rent_corp_from_rent = rent_residual_for_corp * rent_corp_share_norm
    rent_exec_bonus_pool = rent_residual_for_corp * rent_exec_share_norm
    rent_leader_bonus_total = rent_residual_for_corp * rent_leader_share_norm
    rent_member_bonus_total = rent_residual_for_corp * rent_member_share_norm

    # 팀장/팀원 1인당 연말 보너스 (전월세 잔여분 기준)
    if n_leaders > 0:
        rent_leader_bonus_per = rent_leader_bonus_total / n_leaders
    else:
        rent_leader_bonus_per = 0.0

    if n_members > 0:
        rent_member_bonus_per = rent_member_bonus_total / n_members
    else:
        rent_member_bonus_per = 0.0

    # --- 팀장·팀원 연봉(기본+인센티브) + 연말보너스 + 최종연봉 (전부 1인 기준) ---
    leader_basic_salary_per = leader_base_salary + leader_incentive_per
    member_basic_salary_per = member_base_salary + member_incentive_per

    leader_final_salary_per = leader_basic_salary_per + rent_leader_bonus_per
    member_final_salary_per = member_basic_salary_per + rent_member_bonus_per

    # "팀장·팀원 최종 연봉 합계(억)" = 1인 팀장 + 1인 팀원 (요청대로 인원수 곱하지 않음)
    team_total_final = leader_final_salary_per + member_final_salary_per

    # --- 임원 연봉: 세후 매매 수수료 기준 (기본 구조, 1인 기준) ---
    exec_sales_bonus_pool = sales_net * (1 - corp_sales_keep_rate)

    sum_exec_w = sum(exec_weights)
    exec_sales_bonus_list = []
    exec_rent_bonus_list = []

    # 매매 보너스
    if sum_exec_w > 0 and exec_sales_bonus_pool > 0:
        for w in exec_weights:
            exec_sales_bonus_list.append(exec_sales_bonus_pool * (w / sum_exec_w) if w > 0 else 0.0)
    else:
        exec_sales_bonus_list = [0.0 for _ in exec_weights]

    # 전월세 잔여분에서 임원 연말보너스
    if sum_exec_w > 0 and rent_exec_bonus_pool > 0:
        for w in exec_weights:
            exec_rent_bonus_list.append(rent_exec_bonus_pool * (w / sum_exec_w) if w > 0 else 0.0)
    else:
        exec_rent_bonus_list = [0.0 for _ in exec_weights]

    exec_basic_salary_list = [b + sb for b, sb in zip(exec_base_salaries, exec_sales_bonus_list)]
    exec_final_salary_list = [base + rb for base, rb in zip(exec_basic_salary_list, exec_rent_bonus_list)]

    # 임원 최종 연봉 합계(억): 모든 임원 1인씩의 최종 연봉 합
    exec_total_final = sum(exec_final_salary_list)

    # --- 최종 정산: 세금·경비 제외 매출 = (팀장1인 + 팀원1인 + 임원전원) 최종연봉 + 법인 순이익 ---
    total_labor_cost = team_total_final + exec_total_final
    corp_profit = after_tax_exp - total_labor_cost  # 음수면 적자

    # ===== Part1 요약표 =====
    st.subheader("2) Part 1 결과 – 예상 매출 기준 연봉 & 법인 손익(세금·경비 제외 기준, 1인 기준)")

    summary_p1 = pd.DataFrame(
        [
            [
                "입력",
                "전월세 수수료 합계(억)",
                f"{rent_total:.2f}",
                f"주택 {rent_res_fee:.2f} + 상가 {rent_comm_fee:.2f}",
            ],
            [
                "입력",
                "매매 수수료 합계(억)",
                f"{sales_total:.2f}",
                f"주택 {sales_res_fee:.2f} + 상가 {sales_comm_fee:.2f} + 빌딩 {sales_build_fee:.2f}",
            ],
            [
                "결과",
                "총매출(억)",
                f"{total_revenue:.2f}",
                f"전월세 {rent_total:.2f} + 매매 {sales_total:.2f}",
            ],
            [
                "결과",
                "법인 필요경비(억)",
                f"{corp_expense:.2f}",
                f"총매출 {total_revenue:.2f} × 필요경비비율 {expense_rate:.2f}",
            ],
            [
                "결과",
                "법인 세금(억)",
                f"{corp_tax:.2f}",
                f"총매출 {total_revenue:.2f} × 세율 {tax_rate:.2f}",
            ],
            [
                "결과",
                "세금·경비 제외 매출(억)",
                f"{after_tax_exp:.2f}",
                "세금·경비 제외 매출 = 총매출 - 필요경비 - 세금",
            ],
            [
                "결과",
                "팀장·팀원 최종 연봉 합계(억, 1인씩)",
                f"{team_total_final:.4f}",
                (
                    "팀장(1인) 최종연봉 + 팀원(1인) 최종연봉 "
                    f"= {leader_final_salary_per:.4f} + {member_final_salary_per:.4f}"
                ),
            ],
            [
                "결과",
                "임원 최종 연봉 합계(억)",
                f"{exec_total_final:.4f}",
                "모든 임원(각 1인) 최종연봉 합계",
            ],
            [
                "결과",
                "법인 최종 순이익(억)",
                f"{corp_profit:.4f}",
                (
                    "법인 이익 = 세금·경비 제외 매출 "
                    f"{after_tax_exp:.2f} - (팀장·팀원 최종연봉 {team_total_final:.4f} "
                    f"+ 임원 최종연봉 {exec_total_final:.4f})"
                ),
            ],
        ],
        columns=["구분", "항목", "값", "계산식"],
    )

    st.table(summary_p1)

    # ===== Part1 상세표 & 그래프 =====
    col_p1_a, col_p1_b = st.columns(2)

    # 팀장·팀원 (1인 기준)
    with col_p1_a:
        st.markdown("### 팀장·팀원 연봉 상세 (Part 1, 1인 기준)")

        team_p1_df = pd.DataFrame(
            [
                [
                    "팀장",
                    leader_basic_salary_per,      # 기본연봉 (기본급+인센티브)
                    rent_leader_bonus_per,        # 연말보너스
                    leader_final_salary_per,      # 최종연봉
                ],
                [
                    "팀원",
                    member_basic_salary_per,
                    rent_member_bonus_per,
                    member_final_salary_per,
                ],
            ],
            columns=[
                "구분",
                "1인 기본연봉(억)",
                "1인 연말보너스(억)",
                "1인 최종연봉(억)",
            ],
        )
        st.table(team_p1_df)

        fig_team, ax_team = plt.subplots(figsize=(5, 3))
        labels = ["팀장", "팀원"]
        base_vals = [leader_basic_salary_per, member_basic_salary_per]
        bonus_vals = [rent_leader_bonus_per, rent_member_bonus_per]
        x = np.arange(len(labels))
        ax_team.bar(x, base_vals, label="기본연봉(기본급+인센티브)", color="#4C72B0")
        ax_team.bar(x, bonus_vals, bottom=base_vals, label="연말보너스(전월세 잔여분)", color="#55A868")
        ax_team.set_xticks(x)
        ax_team.set_xticklabels(labels)
        ax_team.set_ylabel("1인 최종 연봉 (억)")
        ax_team.set_title("팀장·팀원 1인 최종 연봉 구성")
        ax_team.grid(axis="y", linestyle="--", alpha=0.4)
        ax_team.legend()
        fig_team.tight_layout()
        st.pyplot(fig_team)

    # 임원 (1인 기준)
    with col_p1_b:
        st.markdown("### 임원 연봉 상세 (Part 1, 1인 기준)")

        exec_p1_df = pd.DataFrame(
            {
                "임원번호": [f"임원{i+1}" for i in range(n_exec)],
                "기본연봉(억)": exec_basic_salary_list,       # 기본급+매매보너스
                "연말보너스(억)": exec_rent_bonus_list,       # 전월세 잔여분 보너스
                "최종연봉(억)": exec_final_salary_list,
            }
        )
        st.table(exec_p1_df)

        fig_exec, ax_exec = plt.subplots(figsize=(6, 3))
        idx = np.arange(n_exec)
        width = 0.35
        ax_exec.bar(idx, exec_basic_salary_list, width,
                    label="기본연봉(기본급+매매보너스)", color="#4C72B0")
        ax_exec.bar(idx, exec_rent_bonus_list, width,
                    bottom=exec_basic_salary_list,
                    label="연말보너스(전월세 잔여분)", color="#55A868")
        ax_exec.set_xticks(idx)
        ax_exec.set_xticklabels([f"임원{i+1}" for i in range(n_exec)])
        ax_exec.set_ylabel("연봉 (억)")
        ax_exec.set_title("임원별 최종 연봉 구성 (Part 1, 1인 기준)")
        ax_exec.grid(axis="y", linestyle="--", alpha=0.4)
        ax_exec.legend()
        fig_exec.tight_layout()
        st.pyplot(fig_exec)

    # --- 전월세 잔여분 연말 배분 시뮬레이션 (Part 1) ---
    st.markdown("### 전월세 잔여분 연말 배분 시뮬레이션 (Part 1)")

    rent_dist_rows = [
        [
            "전월세 세후 수수료(rent_net)",
            f"{rent_net:.2f}",
            "세금·경비 제외 후 전월세 수수료 합계",
        ],
        [
            "팀장·팀원 인센티브 풀",
            f"{incentive_pool:.2f}",
            f"rent_net × 인센티브율({rent_incentive_rate:.2f})",
        ],
        [
            "전월세 잔여분(법인 수익 재원)",
            f"{rent_residual_for_corp:.2f}",
            "rent_net - 인센티브 풀",
        ],
        [
            "법인 몫(전월세 잔여분)",
            f"{rent_corp_from_rent:.2f}",
            f"잔여분 × 법인 비율 정규화({rent_corp_share_norm:.2f})",
        ],
        [
            "임원 연말 보너스 합계(전월세 잔여분)",
            f"{rent_exec_bonus_pool:.2f}",
            f"잔여분 × 임원 비율 정규화({rent_exec_share_norm:.2f})",
        ],
        [
            "팀장 연말 보너스 합계",
            f"{rent_leader_bonus_total:.2f}",
            f"잔여분 × 팀장 비율 정규화({rent_leader_share_norm:.2f})",
        ],
        [
            "팀원 연말 보너스 합계",
            f"{rent_member_bonus_total:.2f}",
            f"잔여분 × 팀원 비율 정규화({rent_member_share_norm:.2f})",
        ],
        [
            "팀장 1인당 연말 보너스",
            f"{rent_leader_bonus_per:.4f}",
            "팀장 연말 보너스 합계 ÷ 팀장 인원수",
        ],
        [
            "팀원 1인당 연말 보너스",
            f"{rent_member_bonus_per:.4f}",
            "팀원 연말 보너스 합계 ÷ 팀원 인원수",
        ],
    ]

    rent_dist_df = pd.DataFrame(
        rent_dist_rows,
        columns=["구분", "금액(억)", "계산식"],
    )
    st.table(rent_dist_df)

    exec_rent_bonus_df = pd.DataFrame(
        {
            "임원번호": [f"임원{i+1}" for i in range(n_exec)],
            "전월세 잔여분 기준 연말 보너스(억)": exec_rent_bonus_list,
        }
    )
    st.markdown("**임원별 전월세 잔여분 연말 보너스(참고)**")
    st.table(exec_rent_bonus_df)

    # ---------------- Part 2 – 기본은 숨기고, 선택 시 표시 ----------------
    st.markdown("---")
    show_part2 = st.checkbox("Part 2 – 목표 연봉 기준 역산 보기 (1인 기준)", value=False)

    summary_p2 = None  # PDF용

    if show_part2:
        st.header("Part 2 – 목표 연봉 기준 역산 (1인 기준)")

        # ---------- 2-1) 팀장·팀원: 목표 연봉 → 전월세 수수료 목표 ----------
        st.subheader("Part 2-1. 팀장·팀원: 목표 연봉 달성을 위한 전월세 수수료 목표 (세전/세후)")

        required_rent_total = None
        required_rent_net = None
        required_rent_residual = None
        incentive_pool_required = None

        if rent_incentive_rate <= 0 or net_factor <= 0 or (n_leaders + n_members) == 0:
            st.warning("전월세 인센티브율=0, 세후 계수≤0, 또는 팀장·팀원이 0명인 경우 전월세 역산이 불가능합니다.")
        else:
            weight_leaders = n_leaders * leader_weight
            weight_members = n_members * member_weight
            total_weight_tm = weight_leaders + weight_members

            # 팀장 측 요구 인센티브 (1인)
            needed_L = max(0.0, target_leader_salary - leader_base_salary) if n_leaders > 0 else 0.0
            total_need_L = needed_L * n_leaders
            share_L = (weight_leaders / total_weight_tm) if total_weight_tm > 0 and weight_leaders > 0 else 0.0
            if share_L > 0:
                pool_req_L = total_need_L / share_L
            else:
                pool_req_L = np.inf if total_need_L > 0 else 0.0

            # 팀원 측 요구 인센티브 (1인)
            needed_M = max(0.0, target_member_salary - member_base_salary) if n_members > 0 else 0.0
            total_need_M = needed_M * n_members
            share_M = (weight_members / total_weight_tm) if total_weight_tm > 0 and weight_members > 0 else 0.0
            if share_M > 0:
                pool_req_M = total_need_M / share_M
            else:
                pool_req_M = np.inf if total_need_M > 0 else 0.0

            incentive_pool_required = max(pool_req_L, pool_req_M)

            if np.isinf(incentive_pool_required):
                st.warning("가중치가 0인 인원이 목표 연봉을 가져 전월세 인센티브 역산이 불가능합니다.")
            else:
                if incentive_pool_required <= 0:
                    required_rent_net = 0.0
                    required_rent_total = 0.0
                else:
                    required_rent_net = incentive_pool_required / rent_incentive_rate
                    required_rent_total = required_rent_net / net_factor

                required_rent_residual = required_rent_net * (1 - rent_incentive_rate)

        if required_rent_total is not None:
            rent_table = pd.DataFrame(
                [
                    [
                        "팀장·팀원",
                        "전월세 수수료 목표(억)",
                        f"{required_rent_total:.2f}",
                        f"{required_rent_net:.2f}",
                    ]
                ],
                columns=["구분", "항목", "세금·경비 제외 전(억)", "세금·경비 제외 후(억)"],
            )
            st.table(rent_table)

        # ---------- 2-2) 임원: 목표 연봉 → 매매 수수료 목표 ----------
        st.subheader("Part 2-2. 임원: 목표 연봉 달성을 위한 매매 수수료 목표 (세전/세후)")

        required_sales_total = None
        required_sales_net = None

        if (1 - corp_sales_keep_rate) <= 0 or net_factor <= 0:
            st.warning("매매에서 임원 보너스가 발생하지 않도록 설정되어 있어 매매 역산이 불가능합니다.")
        else:
            sum_w = sum(exec_weights)
            pool_reqs = []
            impossible = False

            for w, base, target in zip(exec_weights, exec_base_salaries, exec_target_salaries):
                needed = max(0.0, target - base)
                if needed == 0:
                    pool_reqs.append(0.0)
                else:
                    if sum_w <= 0 or w <= 0:
                        impossible = True
                        break
                    pool_i = needed * sum_w / w
                    pool_reqs.append(pool_i)

            if impossible:
                st.warning("가중치가 0이면서 목표 연봉이 기본급보다 큰 임원이 있어 매매 역산이 불가능합니다.")
            else:
                exec_bonus_pool_required = max(pool_reqs) if pool_reqs else 0.0
                if exec_bonus_pool_required <= 0:
                    required_sales_net = 0.0
                    required_sales_total = 0.0
                else:
                    required_sales_net = exec_bonus_pool_required / (1 - corp_sales_keep_rate)
                    required_sales_total = required_sales_net / net_factor

        if required_sales_total is not None:
            sales_table = pd.DataFrame(
                [
                    [
                        "임원",
                        "매매 수수료 목표(억)",
                        f"{required_sales_total:.2f}",
                        f"{required_sales_net:.2f}",
                    ]
                ],
                columns=["구분", "항목", "세금·경비 제외 전(억)", "세금·경비 제외 후(억)"],
            )
            st.table(sales_table)

        # PDF용 summary_p2 (전월세/매매 수수료 목표만 요약)
        rows_p2 = []
        if required_rent_total is not None:
            rows_p2.append(
                [
                    "팀장·팀원",
                    "전월세 수수료 목표(억)",
                    f"{required_rent_total:.2f}",
                    f"{required_rent_net:.2f}" if required_rent_net is not None else "알 수 없음",
                ]
            )
        if required_sales_total is not None:
            rows_p2.append(
                [
                    "임원",
                    "매매 수수료 목표(억)",
                    f"{required_sales_total:.2f}",
                    f"{required_sales_net:.2f}" if required_sales_net is not None else "알 수 없음",
                ]
            )

        if rows_p2:
            summary_p2 = pd.DataFrame(
                rows_p2,
                columns=["구분", "항목", "세금·경비 제외 전(억)", "세금·경비 제외 후(억)"],
            )
        else:
            summary_p2 = None
    else:
        summary_p2 = None

    # ---------------- PDF 다운로드 ----------------
    st.markdown("---")
    st.subheader("시뮬레이션 결과 PDF 다운로드")

    pdf_buffer = generate_pdf(summary_p1, team_p1_df, exec_p1_df, summary_p2)
    st.download_button(
        label="📄 PDF 파일 다운로드",
        data=pdf_buffer,
        file_name="simulation_result.pdf",
        mime="application/pdf",
    )

    if not PDF_FONT_AVAILABLE:
        st.info(
            "PDF에서 한글이 깨지는 경우, 앱 실행 폴더에 'NanumGothic.ttf' 폰트 파일을 넣고 다시 실행하면 한글이 정상 출력됩니다."
        )

    st.markdown(
        """
    ---
    ⚠️ 주의  
    - 인센티브율, 기본급, 법인 몫 비율 등은 모두 설계용 파라미터입니다.  
    - 전월세 잔여분의 배분 구조(법인/임원/팀장/팀원)는 여기서 설계용으로 시뮬레이션한 값입니다.  
    - 실제 제도 확정 전에는 반드시 세무사·노무사·회계사와 상의해 주세요.  
    """
    )


if __name__ == "__main__":
    main()
