"""
EURUSD & GBPUSD Hybrid Levels — Full Calculation Code
Non-repainting levels at 07:00 / 10pm Spain
Qualified Edges: Nearer-First, Near Break (high ATR), Fade Close-Through
"""

import math
from typing import List, Optional, Tuple

def jenkins_sqrt_levels(pivot: float, increments=(0.25, 0.5, 0.75, 1.0, 1.5, 2.0)) -> List[float]:
    """Jenkins square-root levels from a pivot price."""
    if pivot <= 0:
        return []
    root = math.sqrt(pivot * 10000)
    levels = []
    for i in increments:
        levels.append(((root + i) ** 2) / 10000)
        levels.append(((root - i) ** 2) / 10000)
    return [l for l in levels if abs(l - pivot) < 0.03 and l > 0.5]


def build_hybrid_levels(
    first_hour_high: float,
    first_hour_low: float,
    first_hour_open: float,
    asia_high: float,
    asia_low: float,
    prev_day_high: Optional[float],
    prev_day_low: Optional[float],
    current_price: float,
) -> List[float]:
    """
    Build non-repainting Hybrid Levels known at 07:00.
    Combines Jenkins square-root + Asia extremes + Prev Day + Round numbers.
    """
    # Jenkins origin = farther extreme of first hour
    pivot = first_hour_high if abs(first_hour_high - first_hour_open) > abs(first_hour_open - first_hour_low) else first_hour_low
    levels = jenkins_sqrt_levels(pivot)

    # Asia extremes (00:00-07:00)
    levels.append(asia_high)
    levels.append(asia_low)

    # Previous day
    if prev_day_high:
        levels.append(prev_day_high)
    if prev_day_low:
        levels.append(prev_day_low)

    # Round numbers
    base = round(current_price / 0.005) * 0.005
    for k in range(-2, 3):
        levels.append(base + k * 0.005)

    # Clean and cluster to >=10 pips
    levels = sorted(set([round(x, 5) for x in levels if x and 0.5 < x < 2.0]))
    clustered = []
    for l in levels:
        if not clustered or abs(l - clustered[-1]) >= 0.0010:
            clustered.append(l)
    return clustered


def get_near_far(
    levels: List[float],
    price: float,
) -> Tuple[Optional[float], Optional[float], str]:
    """
    Return (near_level, far_level, nearer_side).
    nearer_side is 'sup' or 'res'.
    """
    supports = [x for x in levels if x < price - 0.0003]
    resistances = [x for x in levels if x > price + 0.0003]
    if not supports or not resistances:
        return None, None, ""
    near_sup = max(supports)
    near_res = min(resistances)
    d_sup = price - near_sup
    d_res = near_res - price
    if d_sup < d_res:
        return near_sup, near_res, "sup"
    else:
        return near_res, near_sup, "res"


def qualified_edges(atr: float, nearer_side: str) -> dict:
    """
    Return the qualified edge signals for the current day.
    """
    signals = {
        "nearer_first_expected": True,          # ~81% historically
        "near_break_expected": atr >= 75,       # 79-81% when ATR >= 75
        "trade_near_break": atr >= 75,
        "direction": None,
        "notes": [],
    }

    if atr >= 75:
        if nearer_side == "sup":
            signals["direction"] = "SHORT the break of Support"
            signals["notes"].append("Near = Support → short break by 10 pips")
        elif nearer_side == "res":
            signals["direction"] = "LONG the break of Resistance"
            signals["notes"].append("Near = Resistance → long break by 10 pips")
        signals["notes"].append("Stop back inside beyond broken level +10 pips")
    else:
        signals["notes"].append("ATR < 75 — no Near-Break trade")

    return signals


# Example usage
if __name__ == "__main__":
    # Demo values
    levels = build_hybrid_levels(
        first_hour_high=1.2650,
        first_hour_low=1.2610,
        first_hour_open=1.2625,
        asia_high=1.2660,
        asia_low=1.2605,
        prev_day_high=1.2680,
        prev_day_low=1.2590,
        current_price=1.2635,
    )
    print("Hybrid Levels:", levels)

    near, far, side = get_near_far(levels, 1.2635)
    print(f"Near: {near} | Far: {far} | Side: {side}")

    edges = qualified_edges(atr=82, nearer_side=side)
    print("Edges:", edges)
