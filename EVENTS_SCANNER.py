"""
EURUSD & GBPUSD Events Scanner
Scans for Qualified Edges: Nearer-First, Near Break (high ATR), Fade Close-Through
"""

import math
from typing import List, Optional, Dict, Any
from datetime import datetime

def jenkins_sqrt_levels(pivot: float, increments=(0.25, 0.5, 0.75, 1.0, 1.5, 2.0)) -> List[float]:
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
    pivot = first_hour_high if abs(first_hour_high - first_hour_open) > abs(first_hour_open - first_hour_low) else first_hour_low
    levels = jenkins_sqrt_levels(pivot)
    levels.extend([asia_high, asia_low])
    if prev_day_high:
        levels.append(prev_day_high)
    if prev_day_low:
        levels.append(prev_day_low)
    base = round(current_price / 0.005) * 0.005
    for k in range(-2, 3):
        levels.append(base + k * 0.005)
    levels = sorted(set([round(x, 5) for x in levels if x and 0.5 < x < 2.0]))
    clustered = []
    for l in levels:
        if not clustered or abs(l - clustered[-1]) >= 0.0010:
            clustered.append(l)
    return clustered


def get_near_far(levels: List[float], price: float):
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


def scan_events(
    pair: str,
    current_price: float,
    atr: float,
    first_hour_high: float,
    first_hour_low: float,
    first_hour_open: float,
    asia_high: float,
    asia_low: float,
    prev_day_high: Optional[float] = None,
    prev_day_low: Optional[float] = None,
    first_touch_side: Optional[str] = None,
    wick: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Scan for qualified events on a pair.
    Returns a dict of active events and recommended actions.
    """
    levels = build_hybrid_levels(
        first_hour_high, first_hour_low, first_hour_open,
        asia_high, asia_low, prev_day_high, prev_day_low, current_price
    )
    near, far, nearer_side = get_near_far(levels, current_price)

    events = {
        "pair": pair,
        "time": datetime.utcnow().isoformat() + "Z",
        "atr": atr,
        "current_price": current_price,
        "near_level": near,
        "far_level": far,
        "nearer_side": nearer_side,
        "active_events": [],
        "actions": [],
    }

    # Event 1: Nearer-First expected
    events["active_events"].append({
        "name": "Nearer-First",
        "status": "EXPECTED",
        "rate": "~81%",
        "note": f"Nearer side ({nearer_side}) expected to be visited first"
    })

    # Event 2: Near Break (high ATR)
    if atr >= 75:
        events["active_events"].append({
            "name": "Near Break",
            "status": "ACTIVE",
            "rate": "79-81%",
            "note": "High ATR — near level expected to break"
        })
        if nearer_side == "sup":
            events["actions"].append("SHORT the break of Support by 10 pips")
        elif nearer_side == "res":
            events["actions"].append("LONG the break of Resistance by 10 pips")
        events["actions"].append("Stop back inside beyond broken level +10 pips")
    else:
        events["active_events"].append({
            "name": "Near Break",
            "status": "INACTIVE",
            "rate": "—",
            "note": "ATR < 75 — no Near-Break trade"
        })

    # Event 3: Fade Close-Through (if first touch info available)
    if first_touch_side and wick is not None:
        if wick == 0:
            events["active_events"].append({
                "name": "Fade Close-Through",
                "status": "ACTIVE",
                "rate": "63-65%",
                "note": "First-touch bar closed through the level"
            })
            if first_touch_side == "res":
                events["actions"].append("FADE: Sell after close-through of Resistance")
            elif first_touch_side == "sup":
                events["actions"].append("FADE: Buy after close-through of Support")
        else:
            events["active_events"].append({
                "name": "Fade Close-Through",
                "status": "SKIP",
                "rate": "47%",
                "note": "Wick = 1 — do not fade"
            })

    # Low ATR filter note
    if atr < 100:
        events["active_events"].append({
            "name": "Low ATR Filter",
            "status": "ACTIVE",
            "rate": "70%",
            "note": "Do not expect both Asia extremes to break"
        })

    return events


# Example
if __name__ == "__main__":
    result = scan_events(
        pair="GBPUSD",
        current_price=1.2635,
        atr=82,
        first_hour_high=1.2650,
        first_hour_low=1.2610,
        first_hour_open=1.2625,
        asia_high=1.2660,
        asia_low=1.2605,
        prev_day_high=1.2680,
        prev_day_low=1.2590,
        first_touch_side="sup",
        wick=0,
    )
    import json
    print(json.dumps(result, indent=2))
