"""Archetype modules for Track A. Formulas are fixed here, never invented at run time."""

def _pos(x, name):
    if x is None or x <= 0:
        raise ValueError(f"{name} must be positive, got {x}")
    return float(x)

# ---- Life insurer ----
def ape(single_premium, first_year_regular):
    sp = float(single_premium) if single_premium else 0.0
    fy = float(first_year_regular) if first_year_regular else 0.0
    return 0.1 * sp + 1.0 * fy, "0.1*single_premium + 1.0*first_year_regular"

def vnb_margin(vnb, ape_val):
    return vnb / _pos(ape_val, "ape") * 100, "vnb / ape * 100"

def persistency_change(current, prior):
    return current - prior, "current - prior (pp)"

def solvency_ratio(available, required):
    return available / _pos(required, "required"), "available / required"

# ---- General insurer ----
def loss_ratio(claims_incurred, net_earned_premium):
    return claims_incurred / _pos(net_earned_premium, "nep") * 100, "claims / nep * 100"

def combined_ratio(loss_ratio_val, expense_ratio_val):
    return loss_ratio_val + expense_ratio_val, "loss_ratio + expense_ratio"

def reserve_development(prior_releases, pbt):
    return prior_releases / _pos(pbt, "pbt") * 100, "prior_releases / pbt * 100"

def investment_leverage(investments, net_worth):
    return investments / _pos(net_worth, "net_worth"), "investments / net_worth"

# ---- Exchange ----
def transaction_yield(charges, turnover):
    return charges / _pos(turnover, "turnover") * 10000, "charges / turnover * 10000 (bps)"

def core_income(transaction, listing, data):
    return transaction + listing + data, "transaction + listing + data"

def settlement_guarantee_coverage(sgf, required):
    return sgf / _pos(required, "required") * 100, "sgf / required * 100"

# ---- AMC ----
def amc_yield(revenue, average_aum):
    return revenue / _pos(average_aum, "average_aum") * 10000, "revenue / average_aum * 10000 (bps)"

def net_flows_delta(closing_aum, opening_aum, market_appreciation):
    return closing_aum - opening_aum - market_appreciation, "closing - opening - market_appreciation"

def qaaum_share(qaaum, total_industry):
    return qaaum / _pos(total_industry, "total_industry") * 100, "qaaum / total_industry * 100"

# ---- Universal G14 helper ----
def rupee_delta(old_num, old_den, new_num, new_den):
    return {
        "num_delta": new_num - old_num,
        "den_delta": new_den - old_den,
        "ratio_old": old_num / _pos(old_den, "old_den"),
        "ratio_new": new_num / _pos(new_den, "new_den"),
    }
