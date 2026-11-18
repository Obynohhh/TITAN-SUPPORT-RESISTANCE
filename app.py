"""
EURUSD & GBPUSD Hybrid Levels — Streamlit App
Imports original hybrid calculation and event scanner.
Does not reimplement any trading mathematics.
Deployable on Streamlit Cloud.
"""

import streamlit as st
from datetime import datetime

# Import original functions — no reimplementation of mathematics
from HYBRID_LEVELS_CODE import (
    build_hybrid_levels,
    get_near_far,
    qualified_edges,
)
from EVENTS_SCANNER import scan_events

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Hybrid Levels Dashboard",
    page_icon="📊",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Session state for inputs
# ---------------------------------------------------------------------------
if "inputs" not in st.session_state:
    st.session_state.inputs = {
        "GBPUSD": {
            "current_price": 1.2635,
            "atr": 68.0,
            "first_hour_high": 1.2650,
            "first_hour_low": 1.2610,
            "first_hour_open": 1.2625,
            "asia_high": 1.2660,
            "asia_low": 1.2605,
            "prev_day_high": 1.2680,
            "prev_day_low": 1.2590,
            "first_touch_side": None,
            "wick": None,
        },
        "EURUSD": {
            "current_price": 1.0855,
            "atr": 52.0,
            "first_hour_high": 1.0870,
            "first_hour_low": 1.0835,
            "first_hour_open": 1.0845,
            "asia_high": 1.0880,
            "asia_low": 1.0830,
            "prev_day_high": 1.0900,
            "prev_day_low": 1.0820,
            "first_touch_side": None,
            "wick": None,
        },
    }

# ---------------------------------------------------------------------------
# Helper — call original modules only
# ---------------------------------------------------------------------------
def compute(pair: str) -> dict:
    inp = st.session_state.inputs[pair]

    levels = build_hybrid_levels(
        first_hour_high=inp["first_hour_high"],
        first_hour_low=inp["first_hour_low"],
        first_hour_open=inp["first_hour_open"],
        asia_high=inp["asia_high"],
        asia_low=inp["asia_low"],
        prev_day_high=inp["prev_day_high"],
        prev_day_low=inp["prev_day_low"],
        current_price=inp["current_price"],
    )

    near, far, nearer_side = get_near_far(levels, inp["current_price"])

    edges = qualified_edges(atr=inp["atr"], nearer_side=nearer_side)

    scan = scan_events(
        pair=pair,
        current_price=inp["current_price"],
        atr=inp["atr"],
        first_hour_high=inp["first_hour_high"],
        first_hour_low=inp["first_hour_low"],
        first_hour_open=inp["first_hour_open"],
        asia_high=inp["asia_high"],
        asia_low=inp["asia_low"],
        prev_day_high=inp["prev_day_high"],
        prev_day_low=inp["prev_day_low"],
        first_touch_side=inp["first_touch_side"],
        wick=inp["wick"],
    )

    return {
        "levels": levels,
        "near_level": near,
        "far_level": far,
        "nearer_side": nearer_side,
        "edges": edges,
        "scan": scan,
        "inputs": inp,
    }

# ---------------------------------------------------------------------------
# Sidebar — pair + inputs
# ---------------------------------------------------------------------------
st.sidebar.title("Settings")
pair = st.sidebar.selectbox("Pair", ["GBPUSD", "EURUSD"])

st.sidebar.markdown("---")
st.sidebar.subheader("Market Inputs")

inp = st.session_state.inputs[pair]

inp["current_price"] = st.sidebar.number_input(
    "Current Price", value=inp["current_price"], format="%.4f", step=0.0001
)
inp["atr"] = st.sidebar.number_input("ATR(14) pips", value=float(inp["atr"]), step=1.0)

st.sidebar.markdown("---")
st.sidebar.subheader("First-Touch Confirmation")

touch_options = ["None", "sup", "res"]
touch_idx = 0 if inp["first_touch_side"] is None else touch_options.index(inp["first_touch_side"])
touch_sel = st.sidebar.selectbox("First Touch Side", touch_options, index=touch_idx)
inp["first_touch_side"] = None if touch_sel == "None" else touch_sel

wick_options = ["None", "0", "1"]
wick_idx = 0 if inp["wick"] is None else wick_options.index(str(inp["wick"]))
wick_sel = st.sidebar.selectbox("Wick", wick_options, index=wick_idx)
inp["wick"] = None if wick_sel == "None" else int(wick_sel)

st.session_state.inputs[pair] = inp

# ---------------------------------------------------------------------------
# Main dashboard
# ---------------------------------------------------------------------------
st.title(f"Hybrid Levels Dashboard — {pair}")
st.caption("Non-repainting levels • Original calculation functions • 10pm Spain / 07:00")

result = compute(pair)

# ----- Calculated Levels -----
st.subheader("Calculated Levels")
col1, col2 = st.columns(2)
with col1:
    st.metric("Nearest Support", f"{result['near_level']:.4f}" if result["near_level"] else "—")
with col2:
    st.metric("Nearest Resistance", f"{result['far_level']:.4f}" if result["far_level"] else "—")

st.info(f"Nearer side: **{result['nearer_side'] or '—'}**")

# ----- Expected Edges -----
st.subheader("Expected Edges")
for ev in result["scan"].get("active_events", []):
    status = ev.get("status", "")
    if status == "ACTIVE":
        st.success(f"**{ev['name']}** — {ev['note']} ({ev['rate']})")
    elif status == "EXPECTED":
        st.info(f"**{ev['name']}** — {ev['note']} ({ev['rate']})")
    else:
        st.warning(f"**{ev['name']}** — {ev['note']}")

# ----- Confirmed First-Touch -----
st.subheader("Confirmed First-Touch Events")
if inp["first_touch_side"] and inp["wick"] is not None:
    st.success(
        f"**CONFIRMED** — First touch {inp['first_touch_side'].upper()} "
        f"with Wick = {inp['wick']}"
    )
else:
    st.info("No first-touch confirmed yet. Set First Touch Side and Wick in the sidebar.")

# ----- Actions -----
st.subheader("Actions")
actions = result["scan"].get("actions", [])
if actions:
    for a in actions:
        st.write(f"- {a}")
else:
    st.caption("No actions at this time.")

# ----- Footer -----
st.markdown("---")
st.caption(
    f"Calculated at {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC • "
    "Uses original HYBRID_LEVELS_CODE and EVENTS_SCANNER modules • "
    "Past results do not guarantee future performance."
)
