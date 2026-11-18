"""
EURUSD & GBPUSD Hybrid Levels — Streamlit App
Live prices from Twelve Data API.
Imports original hybrid calculation and event scanner.
Does not reimplement any trading mathematics.
"""

import streamlit as st
import requests
from datetime import datetime, timedelta
import math

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
# Twelve Data API
# ---------------------------------------------------------------------------
TWELVE_DATA_KEY = st.secrets.get("TWELVE_DATA_API_KEY", "")

def fetch_twelve_data(symbol: str, interval: str = "1h", outputsize: int = 50):
    """Fetch OHLC from Twelve Data. Symbol must be EUR/USD format."""
    if not TWELVE_DATA_KEY:
        st.sidebar.error("TWELVE_DATA_API_KEY not found in secrets")
        return None
    # Twelve Data expects EUR/USD not EURUSD
    td_symbol = symbol[:3] + "/" + symbol[3:] if len(symbol) == 6 else symbol
    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": td_symbol,
        "interval": interval,
        "outputsize": outputsize,
        "apikey": TWELVE_DATA_KEY,
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
        if data.get("status") == "error":
            st.sidebar.error(f"Twelve Data error: {data.get('message', 'unknown')}")
            return None
        return data.get("values", [])
    except Exception as e:
        st.sidebar.error(f"Request failed: {e}")
        return None


def fetch_quote(symbol: str):
    """Fetch current price from Twelve Data."""
    if not TWELVE_DATA_KEY:
        return None
    td_symbol = symbol[:3] + "/" + symbol[3:] if len(symbol) == 6 else symbol
    url = "https://api.twelvedata.com/price"
    params = {"symbol": td_symbol, "apikey": TWELVE_DATA_KEY}
    try:
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
        if data.get("status") == "error":
            st.sidebar.error(f"Quote error: {data.get('message', 'unknown')}")
            return None
        return float(data.get("price", 0)) if data.get("price") else None
    except Exception as e:
        st.sidebar.error(f"Quote request failed: {e}")
        return None


def compute_atr(values, period=14):
    """Simple ATR from Twelve Data OHLC list (most recent first)."""
    if not values or len(values) < period + 1:
        return 80.0
    trs = []
    for i in range(period):
        high = float(values[i]["high"])
        low = float(values[i]["low"])
        prev_close = float(values[i + 1]["close"])
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        trs.append(tr)
    return sum(trs) / len(trs) * 10000  # pips


def extract_session_levels(values):
    """Extract first-hour and Asia extremes from 1H bars (most recent first)."""
    if not values:
        return {}
    # Assume values are ordered newest first
    # First hour of current day ≈ most recent bars before ~07:00
    # Simplified: use last 7 bars for Asia, last 1-2 for first hour
    asia_bars = values[:7] if len(values) >= 7 else values
    first_hour = values[0] if values else None

    asia_high = max(float(b["high"]) for b in asia_bars) if asia_bars else 0
    asia_low = min(float(b["low"]) for b in asia_bars) if asia_bars else 0
    fh_high = float(first_hour["high"]) if first_hour else 0
    fh_low = float(first_hour["low"]) if first_hour else 0
    fh_open = float(first_hour["open"]) if first_hour else 0

    prev_high = float(values[7]["high"]) if len(values) > 7 else None
    prev_low = float(values[7]["low"]) if len(values) > 7 else None

    return {
        "first_hour_high": fh_high,
        "first_hour_low": fh_low,
        "first_hour_open": fh_open,
        "asia_high": asia_high,
        "asia_low": asia_low,
        "prev_day_high": prev_high,
        "prev_day_low": prev_low,
    }


def get_live_inputs(pair: str) -> dict:
    """Fetch live data and build inputs for the original functions."""
    quote = fetch_quote(pair)
    values = fetch_twelve_data(pair, interval="1h", outputsize=30)

    if quote is None:
        st.error(f"Could not fetch live price for {pair}. Check API key and symbol.")
        price = 0.0
    else:
        price = quote

    atr = compute_atr(values) if values else 0.0
    session = extract_session_levels(values) if values else {}

    return {
        "current_price": price,
        "atr": atr,
        "first_hour_high": session.get("first_hour_high", price),
        "first_hour_low": session.get("first_hour_low", price),
        "first_hour_open": session.get("first_hour_open", price),
        "asia_high": session.get("asia_high", price),
        "asia_low": session.get("asia_low", price),
        "prev_day_high": session.get("prev_day_high"),
        "prev_day_low": session.get("prev_day_low"),
        "first_touch_side": None,
        "wick": None,
    }


def compute(pair: str, inputs: dict) -> dict:
    """Call original modules only."""
    levels = build_hybrid_levels(
        first_hour_high=inputs["first_hour_high"],
        first_hour_low=inputs["first_hour_low"],
        first_hour_open=inputs["first_hour_open"],
        asia_high=inputs["asia_high"],
        asia_low=inputs["asia_low"],
        prev_day_high=inputs["prev_day_high"],
        prev_day_low=inputs["prev_day_low"],
        current_price=inputs["current_price"],
    )
    near, far, nearer_side = get_near_far(levels, inputs["current_price"])
    edges = qualified_edges(atr=inputs["atr"], nearer_side=nearer_side)
    scan = scan_events(
        pair=pair,
        current_price=inputs["current_price"],
        atr=inputs["atr"],
        first_hour_high=inputs["first_hour_high"],
        first_hour_low=inputs["first_hour_low"],
        first_hour_open=inputs["first_hour_open"],
        asia_high=inputs["asia_high"],
        asia_low=inputs["asia_low"],
        prev_day_high=inputs["prev_day_high"],
        prev_day_low=inputs["prev_day_low"],
        first_touch_side=inputs["first_touch_side"],
        wick=inputs["wick"],
    )
    return {
        "levels": levels,
        "near_level": near,
        "far_level": far,
        "nearer_side": nearer_side,
        "edges": edges,
        "scan": scan,
        "inputs": inputs,
    }


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
st.sidebar.title("Settings")
pair = st.sidebar.selectbox("Pair", ["GBPUSD", "EURUSD"])

if st.sidebar.button("Refresh Live Data"):
    st.session_state["force_refresh"] = True

st.sidebar.markdown("---")
st.sidebar.caption("Live data from Twelve Data API")
if not TWELVE_DATA_KEY:
    st.sidebar.warning("Add TWELVE_DATA_API_KEY to Streamlit secrets")

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
st.title("Hybrid Levels Dashboard")
st.caption("EURUSD & GBPUSD • Live from Twelve Data • Original calculation functions")

# Fetch live inputs
with st.spinner(f"Fetching {pair} from Twelve Data..."):
    live_inputs = get_live_inputs(pair)

result = compute(pair, live_inputs)

# Display both pairs summary
st.subheader("Both Pairs")
cols = st.columns(2)
for i, p in enumerate(["GBPUSD", "EURUSD"]):
    with cols[i]:
        p_inputs = get_live_inputs(p)
        p_result = compute(p, p_inputs)
        st.metric(
            p,
            f"{p_inputs['current_price']:.4f}",
            delta=f"ATR {p_inputs['atr']:.0f}",
        )
        st.caption(f"Near: {p_result['near_level']:.4f}" if p_result["near_level"] else "—")
        st.caption(f"Far: {p_result['far_level']:.4f}" if p_result["far_level"] else "—")

st.markdown("---")

# Selected pair detail
st.subheader(f"{pair} Detail")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Price", f"{live_inputs['current_price']:.4f}")
with col2:
    st.metric("ATR(14)", f"{live_inputs['atr']:.1f} pips")
with col3:
    st.metric("Nearer Side", result["nearer_side"] or "—")

col1, col2 = st.columns(2)
with col1:
    st.metric("Nearest Support", f"{result['near_level']:.4f}" if result["near_level"] else "—")
with col2:
    st.metric("Nearest Resistance", f"{result['far_level']:.4f}" if result["far_level"] else "—")

# Expected Edges
st.subheader("Expected Edges")
for ev in result["scan"].get("active_events", []):
    status = ev.get("status", "")
    if status == "ACTIVE":
        st.success(f"**{ev['name']}** — {ev['note']} ({ev['rate']})")
    elif status == "EXPECTED":
        st.info(f"**{ev['name']}** — {ev['note']} ({ev['rate']})")
    else:
        st.warning(f"**{ev['name']}** — {ev['note']}")

# Actions
st.subheader("Actions")
actions = result["scan"].get("actions", [])
if actions:
    for a in actions:
        st.write(f"- {a}")
else:
    st.caption("No actions at this time.")

st.markdown("---")
st.caption(
    f"Updated {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC • "
    "Uses original HYBRID_LEVELS_CODE and EVENTS_SCANNER • "
    "Live prices from Twelve Data"
)
