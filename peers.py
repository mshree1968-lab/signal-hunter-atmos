"""Archetype-aware peer selection. Replaces the AUM-only rule (Improvement Kit P2)."""

SCALE = {
    "bank": "advances", "nbfc": "aum", "hfc": "aum",
    "life": "ape", "general": "gwp", "amc": "aum",
    "exchange": "revenue", "holding": "cons_assets",
    "government_lender": "advances", "card_specialty": "advances",
}


def pick_peers(company, candidates, archetype, band=(0.25, 4.0), n=3):
    """Same archetype, same fiscal calendar, size within band of the archetype's scale metric.
    Falls back to the closest n by that metric and flags the substitution."""
    key = SCALE[archetype]
    if key not in company or not company[key]:
        raise ValueError(f"missing scale metric '{key}' for archetype '{archetype}'")
    base = float(company[key])
    inside = [
        c for c in candidates
        if c.get("fiscal_end") == company.get("fiscal_end")
        and c.get(key) and band[0] * base <= float(c[key]) <= band[1] * base
    ]
    if len(inside) >= 2:
        return inside[:n], "in-band", key
    closest = sorted(
        [c for c in candidates if c.get(key)],
        key=lambda c: abs(float(c[key]) / base - 1.0))[:n]
    return closest, "out-of-band: trends only", key
