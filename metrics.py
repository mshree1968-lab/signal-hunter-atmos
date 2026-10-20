"""Lender metric formulas (patch P1). Every function returns (value, formula).
Pure functions, no I/O, no AI. ValueError = DATA-CHECK-FAILED."""


def _pos(x, name):
    if x is None or x <= 0:
        raise ValueError(f"{name} must be positive, got {x}")
    return float(x)


def growth_pct(closing, opening):
    return (closing - opening) / _pos(opening, "opening") * 100, "(closing - opening) / opening * 100"


def stage3_pct(stage3, gross_loans):
    return stage3 / _pos(gross_loans, "gross_loans") * 100, "stage3 / gross_loans * 100"


def stage2_pct(stage2, gross_loans):
    return stage2 / _pos(gross_loans, "gross_loans") * 100, "stage2 / gross_loans * 100"


def write_off_rate(writeoffs, opening_stage3):
    return writeoffs / _pos(opening_stage3, "opening_stage3") * 100, "writeoffs / opening_stage3 * 100"


def adjusted_gnpa(gnpa, writeoffs, loans):
    l = _pos(loans, "loans")
    return (gnpa + writeoffs) / (l + writeoffs) * 100, "(gnpa + writeoffs) / (loans + writeoffs) * 100"


def provision_coverage(stage3_provisions, stage3_gross):
    return (stage3_provisions / _pos(stage3_gross, "stage3_gross") * 100,
            "stage3_provisions / stage3_gross * 100")


def credit_cost(impairment, average_loans, annualise=1.0):
    return (impairment * annualise / _pos(average_loans, "average_loans") * 100,
            f"impairment * {annualise} / average_loans * 100")


def cost_of_funds(interest_expense, average_borrowings, annualise=1.0):
    return (interest_expense * annualise / _pos(average_borrowings, "average_borrowings") * 100,
            f"interest_expense * {annualise} / average_borrowings * 100")


def share_pct(part, total):
    return part / _pos(total, "total") * 100, "part / total * 100"


def vnb_margin(vnb, ape):
    return vnb / _pos(ape, "ape") * 100, "vnb / ape * 100"


def solvency(available, required, minimum=1.5):
    return available / _pos(required, "required"), f"available / required (min {minimum})"


def loss_ratio(claims, net_earned_premium):
    return claims / _pos(net_earned_premium, "nep") * 100, "claims / nep * 100"


def transaction_yield(charges, turnover):
    return charges / _pos(turnover, "turnover") * 10000, "charges / turnover * 10000 (bps)"


def amc_yield(revenue, average_aum):
    return revenue / _pos(average_aum, "average_aum") * 10000, "revenue / average_aum * 10000 (bps)"


def rupee_delta(old_num, old_den, new_num, new_den):
    """G14: never report a ratio move without the underlying amount move."""
    return {"num_delta": new_num - old_num, "den_delta": new_den - old_den,
            "ratio_old": old_num / _pos(old_den, "old_den"),
            "ratio_new": new_num / _pos(new_den, "new_den")}
