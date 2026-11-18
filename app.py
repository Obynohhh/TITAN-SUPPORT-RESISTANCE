"""
EURUSD & GBPUSD Hybrid Levels App
Imports original hybrid calculation and event scanner.
Does not reimplement any mathematics.
"""

from flask import Flask, render_template_string, request, jsonify
from datetime import datetime
import json

# Import original functions — no reimplementation
from HYBRID_LEVELS_CODE import (
    build_hybrid_levels,
    get_near_far,
    qualified_edges,
    jenkins_sqrt_levels,
)
from EVENTS_SCANNER import scan_events

app = Flask(__name__)

# In-memory store for current session inputs (replace with real data feed in production)
current_inputs = {
    "GBPUSD": {
        "current_price": 1.2635,
        "atr": 68,
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
        "atr": 52,
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


def compute_pair(pair: str) -> dict:
    """Call original hybrid + scanner functions. No math reimplementation."""
    inp = current_inputs[pair]

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
        "pair": pair,
        "inputs": inp,
        "levels": levels,
        "near_level": near,
        "far_level": far,
        "nearer_side": nearer_side,
        "edges": edges,
        "scan": scan,
        "calculated_at": datetime.utcnow().isoformat() + "Z",
    }


DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Hybrid Levels App</title>
<style>
  :root {
    --bg: #0f1419; --card: #1a2332; --border: #2d3a4f;
    --text: #e8eef4; --muted: #8b9bb4; --accent: #3b82f6;
    --green: #10b981; --red: #ef4444; --yellow: #f59e0b; --orange: #f97316;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
         background: var(--bg); color: var(--text); line-height: 1.5; }
  .header { background: linear-gradient(135deg, #1a2332, #0f172a);
            border-bottom: 1px solid var(--border); padding: 20px 32px;
            display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 16px; }
  .header h1 { font-size: 22px; }
  .header h1 span { color: var(--accent); }
  .container { max-width: 1200px; margin: 0 auto; padding: 24px; }
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); gap: 20px; }
  .card { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 20px; }
  .card h2 { font-size: 14px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 16px; }
  .level-row { display: flex; justify-content: space-between; padding: 14px 16px;
               background: rgba(255,255,255,0.03); border-radius: 8px; margin-bottom: 8px; }
  .level-row.res { border-left: 3px solid var(--red); }
  .level-row.sup { border-left: 3px solid var(--green); }
  .level-value { font-size: 20px; font-weight: 600; font-family: monospace; }
  .res .level-value { color: var(--red); }
  .sup .level-value { color: var(--green); }
  .badge { display: inline-block; padding: 4px 12px; border-radius: 16px; font-size: 12px; font-weight: 600; }
  .badge.expected { background: rgba(59,130,246,0.2); color: var(--accent); }
  .badge.active { background: rgba(16,185,129,0.2); color: var(--green); }
  .badge.inactive { background: rgba(139,155,180,0.2); color: var(--muted); }
  .badge.confirmed { background: rgba(249,115,22,0.2); color: var(--orange); }
  .event { padding: 12px; background: rgba(255,255,255,0.03); border-radius: 8px; margin-bottom: 8px; }
  .event-name { font-weight: 600; }
  .event-note { font-size: 13px; color: var(--muted); }
  .action { padding: 10px 14px; background: rgba(59,130,246,0.1); border-left: 3px solid var(--accent);
            border-radius: 6px; margin-bottom: 8px; font-size: 14px; }
  .pair-select { background: #0d1117; border: 1px solid var(--border); color: var(--text);
                 padding: 8px 14px; border-radius: 8px; font-size: 14px; }
  .section { margin-top: 28px; }
  .section h3 { font-size: 16px; margin-bottom: 12px; }
  input[type="number"] { background: #0d1117; border: 1px solid var(--border); color: var(--text);
                         padding: 6px 10px; border-radius: 6px; width: 100px; }
  .input-row { display: flex; gap: 12px; align-items: center; margin-bottom: 8px; font-size: 13px; }
  button { background: var(--accent); color: white; border: none; padding: 8px 16px;
           border-radius: 6px; cursor: pointer; font-weight: 600; }
  button:hover { opacity: 0.9; }
  .footer { text-align: center; padding: 32px; color: var(--muted); font-size: 12px;
            border-top: 1px solid var(--border); margin-top: 32px; }
</style>
</head>
<body>
<header class="header">
  <h1>Hybrid Levels <span>App</span></h1>
  <div>
    <select class="pair-select" id="pairSelect" onchange="loadPair()">
      <option value="GBPUSD">GBPUSD</option>
      <option value="EURUSD">EURUSD</option>
    </select>
  </div>
</header>

<div class="container">
  <div class="grid">
    <div class="card">
      <h2>Calculated Levels</h2>
      <div id="levelsBox"></div>
    </div>
    <div class="card">
      <h2>Expected Edges</h2>
      <div id="edgesBox"></div>
    </div>
  </div>

  <div class="section">
    <h3>Confirmed First-Touch Events</h3>
    <div class="card" id="confirmedBox"></div>
  </div>

  <div class="section">
    <h3>Actions</h3>
    <div class="card" id="actionsBox"></div>
  </div>

  <div class="section">
    <h3>Update Inputs</h3>
    <div class="card">
      <div class="input-row">ATR: <input type="number" id="inpAtr" step="1"></div>
      <div class="input-row">Price: <input type="number" id="inpPrice" step="0.0001"></div>
      <div class="input-row">First Touch: 
        <select id="inpTouch">
          <option value="">None</option>
          <option value="sup">Support</option>
          <option value="res">Resistance</option>
        </select>
      </div>
      <div class="input-row">Wick: 
        <select id="inpWick">
          <option value="">None</option>
          <option value="0">0 (closed through)</option>
          <option value="1">1 (wicked)</option>
        </select>
      </div>
      <button onclick="updateInputs()">Recalculate</button>
    </div>
  </div>
</div>

<footer class="footer">
  Hybrid Levels App • Uses original calculation functions • Non-repainting
</footer>

<script>
let currentPair = 'GBPUSD';

function loadPair() {
  currentPair = document.getElementById('pairSelect').value;
  fetch('/api/compute/' + currentPair)
    .then(r => r.json())
    .then(render);
}

function render(data) {
  // Calculated Levels
  const levelsHtml = `
    <div class="level-row res">
      <span>Nearest Resistance</span>
      <span class="level-value">${data.far_level ? data.far_level.toFixed(4) : '—'}</span>
    </div>
    <div class="level-row sup">
      <span>Nearest Support</span>
      <span class="level-value">${data.near_level ? data.near_level.toFixed(4) : '—'}</span>
    </div>
    <div style="margin-top:10px;font-size:13px;color:var(--muted);">
      Nearer side: <strong>${data.nearer_side || '—'}</strong>
    </div>
  `;
  document.getElementById('levelsBox').innerHTML = levelsHtml;

  // Expected Edges
  let edgesHtml = '';
  (data.scan.active_events || []).forEach(ev => {
    const cls = ev.status === 'ACTIVE' ? 'active' : ev.status === 'EXPECTED' ? 'expected' : 'inactive';
    edgesHtml += `
      <div class="event">
        <span class="badge ${cls}">${ev.status}</span>
        <span class="event-name"> ${ev.name}</span>
        <div class="event-note">${ev.note} (${ev.rate})</div>
      </div>
    `;
  });
  document.getElementById('edgesBox').innerHTML = edgesHtml || '<div style="color:var(--muted)">No edges</div>';

  // Confirmed First-Touch
  const touch = data.inputs.first_touch_side;
  const wick = data.inputs.wick;
  let confirmedHtml = '';
  if (touch && wick !== null && wick !== '') {
    confirmedHtml = `
      <div class="event">
        <span class="badge confirmed">CONFIRMED</span>
        <span class="event-name"> First touch ${touch.toUpperCase()}</span>
        <div class="event-note">Wick = ${wick}</div>
      </div>
    `;
  } else {
    confirmedHtml = '<div style="color:var(--muted)">No first-touch confirmed yet</div>';
  }
  document.getElementById('confirmedBox').innerHTML = confirmedHtml;

  // Actions
  let actionsHtml = '';
  (data.scan.actions || []).forEach(a => {
    actionsHtml += `<div class="action">${a}</div>`;
  });
  document.getElementById('actionsBox').innerHTML = actionsHtml || '<div style="color:var(--muted)">No actions</div>';

  // Populate inputs
  document.getElementById('inpAtr').value = data.inputs.atr;
  document.getElementById('inpPrice').value = data.inputs.current_price;
  document.getElementById('inpTouch').value = data.inputs.first_touch_side || '';
  document.getElementById('inpWick').value = data.inputs.wick !== null ? data.inputs.wick : '';
}

function updateInputs() {
  const payload = {
    atr: parseFloat(document.getElementById('inpAtr').value),
    current_price: parseFloat(document.getElementById('inpPrice').value),
    first_touch_side: document.getElementById('inpTouch').value || null,
    wick: document.getElementById('inpWick').value === '' ? null : parseInt(document.getElementById('inpWick').value),
  };
  fetch('/api/update/' + currentPair, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(payload),
  })
  .then(r => r.json())
  .then(render);
}

loadPair();
</script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(DASHBOARD_HTML)


@app.route("/api/compute/<pair>")
def api_compute(pair):
    if pair not in current_inputs:
        return jsonify({"error": "Unknown pair"}), 404
    return jsonify(compute_pair(pair))


@app.route("/api/update/<pair>", methods=["POST"])
def api_update(pair):
    if pair not in current_inputs:
        return jsonify({"error": "Unknown pair"}), 404
    data = request.get_json() or {}
    for key in ("atr", "current_price", "first_touch_side", "wick"):
        if key in data:
            current_inputs[pair][key] = data[key]
    return jsonify(compute_pair(pair))


if __name__ == "__main__":
    print("Starting Hybrid Levels App on http://127.0.0.1:5000")
    print("Place HYBRID_LEVELS_CODE.py and EVENTS_SCANNER.py in the same directory.")
    app.run(debug=True, port=5000)
