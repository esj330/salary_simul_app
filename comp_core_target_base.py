# comp_core.py
import numpy as np
import pandas as pd

def simulate_all(
    # ----- 공통: 세금/경비 -----
    tax_rate=0.30,             # 세금 비율 (매출 기준)
    expense_rate=0.20,         # 경비 비율 (매출 기준)

    # ----- 팀장·팀원 (전월세) -----
    n_leaders=2,
    n_members=6,
    rent_res_fee=2.0,          # 주택 전월세 수수료(억)
    rent_comm_fee=4.0,         # 상가 전월세 수수료(억)
    leader_base_salary=0.7,    # 팀장 1인 기본급(억)
    member_base_salary=0.4,    # 팀원 1인 기본급(억)
    rent_incentive_rate=0.25,  # 전월세 인센티브율(수수료 대비)
    leader_weight=2.0,         # 인센티브 가중치(팀장)
    member_weight=1.0,         # 인센티브 가중치(팀원)

    target_leader_salary=1.0,  # 팀장 1인 목표 연봉(억) - 역산용
    target_member_salary=0.6,  # 팀원 1인 목표 연봉(억) - 역산용

    # ----- 임원 (매매 + 전월세 잔여) -----
    n_exec=5,
    sales_res_fee=3.0,         # 주택 매매 수수료(억)
    sales_comm_fee=1.0,        # 상가 매매 수수료(억)
    sales_build_fee=1.0,       # 빌딩 매매 수수료(억)

    # 회사가 가져가는 비율(법인 몫 비율) — 나머지가 임원 보너스 재원
    corp_sales_keep_rate=0.5,  # 매매 잔여(세금/경비 제외 후) 중 법인 몫 비율
    corp_rent_keep_rate=0.5,   # 전월세 잔여(인센 제외) 중 법인 몫 비율

    exec_weights=None,         # 임원별 가중치(길이 n_exec)
    exec_base_salaries=None,   # 임원별 기본급(억, 길이 n_exec)
    exec_target_salaries=None, # 임원별 목표 연봉(억, 길이 n_exec)
):
    """
    모든 금액 단위: '억 원'.

    임원 인건비 구조:
      1) 매매수수료 S 에 대해:
         - 세금 30%, 경비 20% 차감 → S * (1 - tax_rate - expense_rate)
         - 그 중 corp_sales_keep_rate 만큼은 법인 수익,
           나머지 (1 - corp_sales_keep_rate) 만큼은 임원 보너스 재원.

      2) 전월세 수수료 R 에 대해:
         - 인센티브 풀 = R * rent_incentive_rate (팀장·팀원에게 지급)
         - 전월세 잔여 = R - 인센티브풀
         - 이 잔여 중 corp_rent_keep_rate 만큼은 법인 수익,
           나머지 (1 - corp_rent_keep_rate) 만큼은 임원 보너스 재원.

      3) 임원 보너스 풀 = 매매 기반 보너스 + 전월세 기반 보너스
         → 임원별 가중치 비율로 나눠서 지급.
    """

    # -------------------------
    # 1) 팀장·팀원 (전월세) – 인센티브 및 연봉
    # -------------------------
    rent_total = rent_res_fee + rent_comm_fee

    incentive_pool = rent_total * rent_incentive_rate

    total_weight = n_leaders * leader_weight + n_members * member_weight
    if total_weight > 0:
        unit_incentive = incentive_pool / total_weight
        leader_incentive_per = unit_incentive * leader_weight
        member_incentive_per = unit_incentive * member_weight
    else:
        leader_incentive_per = 0.0
        member_incentive_per = 0.0

    leader_salary_per = leader_base_salary + leader_incentive_per
    member_salary_per = member_base_salary + member_incentive_per

    leader_total_salary = leader_salary_per * n_leaders
    member_total_salary = member_salary_per * n_members

    # 전월세 잔여 (인센티브 지급 후 남는 수수료)
    rent_residual = rent_total - incentive_pool

    # -------------------------
    # 2) 임원 관련 벡터 준비
    # -------------------------
    if exec_weights is None:
        exec_weights = np.ones(n_exec)
    else:
        exec_weights = np.array(exec_weights, dtype=float)
        if len(exec_weights) != n_exec:
            raise ValueError("exec_weights 길이는 n_exec와 같아야 합니다.")

    if exec_base_salaries is None:
        exec_base_salaries = np.zeros(n_exec)
    else:
        exec_base_salaries = np.array(exec_base_salaries, dtype=float)
        if len(exec_base_salaries) != n_exec:
            raise ValueError("exec_base_salaries 길이는 n_exec와 같아야 합니다.")

    if exec_target_salaries is None:
        exec_target_salaries = np.ones(n_exec)  # 임시 기본 1억씩 목표 (추측)
    else:
        exec_target_salaries = np.array(exec_target_salaries, dtype=float)
        if len(exec_target_salaries) != n_exec:
            raise ValueError("exec_target_salaries 길이는 n_exec와 같아야 합니다.")

    if exec_weights.sum() <= 0:
        norm_w = np.ones(n_exec) / n_exec
    else:
        norm_w = exec_weights / exec_weights.sum()

    # -------------------------
    # 3) 매매 – 세금·경비 제외 후 임원 몫/법인 몫
    # -------------------------
    sales_total = sales_res_fee + sales_comm_fee + sales_build_fee

    # 전체 매출 기준 세금·경비
    total_revenue = rent_total + sales_total
    corp_expense = total_revenue * expense_rate
    corp_tax = total_revenue * tax_rate

    # "매매수수료 18억에서 세금 30%와 경비 20%를 제외한 잔여"
    # → sales_total * (1 - tax_rate - expense_rate)
    sales_after_tax_exp = sales_total * (1.0 - tax_rate - expense_rate)

    # 매매 잔여 중, 법인 몫 / 임원 몫
    corp_from_sales = sales_after_tax_exp * corp_sales_keep_rate
    exec_bonus_from_sales = sales_after_tax_exp * (1.0 - corp_sales_keep_rate)

    # 전월세 잔여 중, 법인 몫 / 임원 몫
    corp_from_rent = rent_residual * corp_rent_keep_rate
    exec_bonus_from_rent = rent_residual * (1.0 - corp_rent_keep_rate)

    # 임원 보너스 풀 = 매매 기반 + 전월세 기반
    exec_bonus_pool = exec_bonus_from_sales + exec_bonus_from_rent

    # 임원별 연봉 (기본급 + 보너스)
    exec_salaries = exec_base_salaries + exec_bonus_pool * norm_w
    exec_total_salary = exec_salaries.sum()

    # -------------------------
    # 4) 법인 최종 손익 (참고용)
    # -------------------------
    total_team_salary = leader_total_salary + member_total_salary
    total_staff_salary = total_team_salary + exec_total_salary

    corp_net_profit = total_revenue - corp_expense - corp_tax - total_staff_salary

    # -------------------------
    # 5) 팀장·팀원 목표연봉 기준 전월세 최소 필요액 (역산)
    # -------------------------
    required_rent_total = None
    if rent_incentive_rate > 0 and total_weight > 0:
        reqs = []
        # 각 직급에 대해 필요한 rent_total 계산
        if n_leaders > 0:
            alpha_L = rent_incentive_rate * (leader_weight / total_weight)
            need_L = max(0.0, (target_leader_salary - leader_base_salary) / alpha_L)
            reqs.append(need_L)
        if n_members > 0:
            alpha_M = rent_incentive_rate * (member_weight / total_weight)
            need_M = max(0.0, (target_member_salary - member_base_salary) / alpha_M)
            reqs.append(need_M)
        required_rent_total = max(reqs) if reqs else 0.0
    else:
        required_rent_total = None  # 인센티브율 0이면 역산 불가

    # -------------------------
    # 6) 임원 목표연봉 기준 매매 최소 필요액 (역산)
    # -------------------------
    required_sales_total = None
    # 임원 보너스가 매매와 전월세 잔여에 선형적으로 의존하므로 역산 가능
    # exec_salary_i = base_i + norm_w_i * [ (1 - tax - exp)*(1 - corp_sales_keep)*S + rent_residual*(1 - corp_rent_keep) ]
    a_s = (1.0 - tax_rate - expense_rate) * (1.0 - corp_sales_keep_rate)

    if a_s > 0:
        C = rent_residual * (1.0 - corp_rent_keep_rate)  # 전월세 기반 상수항
        req_candidates = []
        for i in range(n_exec):
            w_i = norm_w[i]
            base_i = exec_base_salaries[i]
            target_i = exec_target_salaries[i]

            if w_i <= 0:
                # 이 임원은 보너스를 못 받는 구조 → 기본급만으로 목표 달성 가능한지 확인
                if target_i > base_i:
                    req_candidates.append(np.inf)
                else:
                    continue
            else:
                # base_i + w_i * (a_s * S + C) >= target_i
                # => a_s * w_i * S >= target_i - base_i - w_i * C
                rhs = target_i - base_i - w_i * C
                S_need = rhs / (a_s * w_i)
                if S_need < 0:
                    S_need = 0.0
                req_candidates.append(S_need)

        if req_candidates:
            required_sales_total = max(req_candidates)
        else:
            required_sales_total = 0.0
    else:
        # a_s == 0 이면 매매에서 임원 보너스가 안 나오는 구조라 역산 불가
        required_sales_total = None

    # -------------------------
    # 결과 정리
    # -------------------------
    return {
        "session2": {
            "rent_res_fee": rent_res_fee,
            "rent_comm_fee": rent_comm_fee,
            "rent_total": rent_total,
            "incentive_pool": incentive_pool,
            "rent_residual": rent_residual,
            "leader_salary_per": leader_salary_per,
            "member_salary_per": member_salary_per,
            "leader_base_salary": leader_base_salary,
            "member_base_salary": member_base_salary,
            "leader_incentive_per": leader_incentive_per,
            "member_incentive_per": member_incentive_per,
            "leader_total_salary": leader_total_salary,
            "member_total_salary": member_total_salary,
            "required_rent_total": required_rent_total,
        },
        "session3": {
            "sales_res_fee": sales_res_fee,
            "sales_comm_fee": sales_comm_fee,
            "sales_build_fee": sales_build_fee,
            "sales_total": sales_total,
            "sales_after_tax_exp": sales_after_tax_exp,
            "exec_bonus_from_sales": exec_bonus_from_sales,
            "exec_bonus_from_rent": exec_bonus_from_rent,
            "exec_bonus_pool": exec_bonus_pool,
            "exec_salaries": exec_salaries,
            "exec_total_salary": exec_total_salary,
            "exec_weights": norm_w,
            "exec_base_salaries": exec_base_salaries,
            "exec_target_salaries": exec_target_salaries,
            "required_sales_total": required_sales_total,
        },
        "session1": {
            "total_revenue": total_revenue,
            "corp_expense": corp_expense,
            "corp_tax": corp_tax,
            "total_team_salary": total_team_salary,
            "total_staff_salary": total_staff_salary,
            "corp_net_profit": corp_net_profit,
            "corp_from_sales": corp_from_sales,
            "corp_from_rent": corp_from_rent,
        },
    }
