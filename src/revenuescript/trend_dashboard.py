# trend_dashboard.py
# Genera una dashboard HTML interattiva con Plotly:
# - dropdown per selezionare l'indicatore
# - una linea per ogni azienda, trend multi-anno
# - soglia fissa e mediana del gruppo come linee di riferimento
# - visualizzabile online (tutto self-contained in un unico file HTML)

import os
import json
import pandas as pd

from config import TICKERS, THRESHOLDS

OUTPUT_DIR = "output"

# Palette monocromatica blu (stessa di visualizer.py)
PLOTLY_COLORS = [
    "#03045e", "#023e8a", "#0077b6", "#0096c7", "#00b4d8",
    "#48cae4", "#90e0ef", "#ade8f4", "#caf0f8", "#e0f7fa",
]

# Indicatori da includere nella dashboard
DASHBOARD_INDICATORS = [
    "Revenue (M)",
    "EBIT (M)",
    "EBITDA (M)",
    "Net Income (M)",
    "EBIT Margin (%)",
    "EBITDA Margin (%)",
    "Net Margin (%)",
    "ROE (%)",
    "ROA (%)",
    "ROI / ROCE (%)",
    "Debt/Equity",
    "Current Ratio",
    "Interest Coverage",
]


def _clean_name(name: str) -> str:
    replacements = {
        "Volkswagen Group": "VW Group",
        "Mercedes-Benz":    "Mercedes",
        "Renault Group":    "Renault",
        "TRATON Group":     "TRATON",
        "Iveco Group":      "Iveco",
        "Porsche AG":       "Porsche",
        "BMW Group":        "BMW",
    }
    return replacements.get(name, name)


def _build_traces(trends: dict) -> dict:
    """
    Costruisce i dati JSON per ogni indicatore:
    {
      "EBIT Margin (%)": {
        "companies": [ {name, x, y, color}, ... ],
        "fixed":     5.0  | null,
        "direction": "above_good" | "below_good" | null,
        "label":     "Soglia min. 5%" | null,
      },
      ...
    }
    """
    data = {}
    companies_global = []

    # Raccoglie tutti i nomi azienda
    for indicator in DASHBOARD_INDICATORS:
        if indicator in trends:
            for company in trends[indicator].index:
                if company not in companies_global:
                    companies_global.append(company)

    for indicator in DASHBOARD_INDICATORS:
        if indicator not in trends:
            continue

        df = trends[indicator]
        companies_data = []

        for i, company in enumerate(df.index):
            series = df.loc[company]
            years  = [int(y) for y in series.index.tolist()]
            values = [None if pd.isna(v) else round(float(v), 2)
                      for v in series.values]

            color_idx = companies_global.index(company) if company in companies_global else i
            companies_data.append({
                "name":  _clean_name(company),
                "full":  company,
                "x":     years,
                "y":     values,
                "color": PLOTLY_COLORS[color_idx % len(PLOTLY_COLORS)],
            })

        # Mediana del gruppo (ultimo anno disponibile)
        last_col = df.columns[-1]
        group_median = round(float(df[last_col].median(skipna=True)), 2)

        thresh = THRESHOLDS.get(indicator)
        data[indicator] = {
            "companies": companies_data,
            "median":    group_median,
            "fixed":     thresh["fixed"]     if thresh else None,
            "direction": thresh["direction"] if thresh else None,
            "label":     thresh["label"]     if thresh else None,
            "note":      thresh["note"]      if thresh else None,
        }

    return data, companies_global


def generate_trend_dashboard(trends: dict, output_path: str = None):
    """
    Genera il file HTML self-contained con la dashboard Plotly.
    """
    if output_path is None:
        output_path = os.path.join(OUTPUT_DIR, "trend_dashboard.html")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    trace_data, companies = _build_traces(trends)
    indicators_list = list(trace_data.keys())

    if not indicators_list:
        print("  [SKIP] Nessun dato disponibile per la dashboard.")
        return

    data_json      = json.dumps(trace_data,      ensure_ascii=False)
    indicators_json = json.dumps(indicators_list, ensure_ascii=False)
    companies_json  = json.dumps(
        [_clean_name(c) for c in companies], ensure_ascii=False
    )

    html = f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Automotive Europe — Trend Dashboard</title>
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: 'Segoe UI', Arial, sans-serif;
    background: #f0f4f8;
    color: #1a1a2e;
  }}
  header {{
    background: linear-gradient(135deg, #03045e, #0077b6);
    color: white;
    padding: 28px 40px 20px;
  }}
  header h1 {{ font-size: 1.7rem; font-weight: 700; letter-spacing: 0.5px; }}
  header p  {{ font-size: 0.9rem; opacity: 0.8; margin-top: 4px; }}
  .container {{ max-width: 1100px; margin: 0 auto; padding: 28px 24px; }}
  .controls {{
    display: flex; align-items: center; gap: 16px;
    background: white; border-radius: 10px;
    padding: 16px 20px; margin-bottom: 20px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.07);
    flex-wrap: wrap;
  }}
  .controls label {{ font-weight: 600; font-size: 0.9rem; color: #03045e; }}
  select {{
    padding: 8px 14px; border-radius: 6px;
    border: 1.5px solid #0077b6; font-size: 0.95rem;
    color: #03045e; background: #f8fbff; cursor: pointer;
    min-width: 220px;
  }}
  select:focus {{ outline: none; border-color: #023e8a; }}
  .chart-card {{
    background: white; border-radius: 10px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.07);
    padding: 20px; margin-bottom: 20px;
  }}
  #plotly-chart {{ width: 100%; height: 480px; }}
  .threshold-box {{
    background: #f8fbff; border-left: 4px solid #0077b6;
    border-radius: 6px; padding: 14px 18px;
    margin-bottom: 20px; font-size: 0.88rem; line-height: 1.6;
  }}
  .threshold-box h3 {{
    font-size: 0.95rem; color: #03045e;
    margin-bottom: 6px; font-weight: 700;
  }}
  .threshold-box .badges {{
    display: flex; gap: 10px; margin-bottom: 8px; flex-wrap: wrap;
  }}
  .badge {{
    display: inline-block; padding: 3px 10px;
    border-radius: 20px; font-size: 0.8rem; font-weight: 600;
  }}
  .badge-fixed  {{ background: #fde8ea; color: #c0392b; }}
  .badge-median {{ background: #fef3e2; color: #d35400; }}
  .badge-none   {{ background: #e8f4fd; color: #0077b6; }}
  .status-table {{
    width: 100%; border-collapse: collapse; font-size: 0.87rem;
    margin-top: 16px;
  }}
  .status-table th {{
    background: #03045e; color: white;
    padding: 8px 12px; text-align: left; font-weight: 600;
  }}
  .status-table td {{ padding: 7px 12px; border-bottom: 1px solid #e8eef5; }}
  .status-table tr:last-child td {{ border-bottom: none; }}
  .ok   {{ color: #1a7a4a; font-weight: 600; }}
  .warn {{ color: #c0392b; font-weight: 600; }}
  .na   {{ color: #aaa; }}
  footer {{
    text-align: center; font-size: 0.78rem; color: #888;
    padding: 20px; margin-top: 10px;
  }}
</style>
</head>
<body>

<header>
  <h1>🚗 Automotive Europe — Trend Dashboard</h1>
  <p>VW Group · Stellantis · Mercedes-Benz · BMW · Renault · Porsche AG · Volvo Cars · TRATON · Iveco</p>
</header>

<div class="container">

  <div class="controls">
    <label for="indicator-select">Indicatore:</label>
    <select id="indicator-select" onchange="updateChart()">
    </select>
  </div>

  <div class="chart-card">
    <div id="plotly-chart"></div>
  </div>

  <div class="threshold-box" id="threshold-box"></div>

  <div class="chart-card">
    <table class="status-table" id="status-table">
      <thead>
        <tr>
          <th>Azienda</th>
          <th>Ultimo anno</th>
          <th>Soglia fissa</th>
          <th>vs Mediana gruppo</th>
          <th>Stato</th>
        </tr>
      </thead>
      <tbody id="status-tbody"></tbody>
    </table>
  </div>

</div>

<footer>
  Dati: Yahoo Finance via yfinance · Solo uso educativo/personale
</footer>

<script>
const DATA       = {data_json};
const INDICATORS = {indicators_json};
const COMPANIES  = {companies_json};

// Popola il dropdown
const sel = document.getElementById('indicator-select');
INDICATORS.forEach(ind => {{
  const opt = document.createElement('option');
  opt.value = ind;
  opt.textContent = ind;
  sel.appendChild(opt);
}});

function updateChart() {{
  const indicator = sel.value;
  const entry     = DATA[indicator];
  if (!entry) return;

  const traces = [];

  // Trace per ogni azienda
  entry.companies.forEach(co => {{
    traces.push({{
      type: 'scatter',
      mode: 'lines+markers',
      name: co.name,
      x: co.x,
      y: co.y,
      line:   {{ color: co.color, width: 2.5 }},
      marker: {{ color: co.color, size: 7 }},
      connectgaps: false,
      hovertemplate: '<b>' + co.name + '</b><br>Anno: %{{x}}<br>Valore: %{{y:.2f}}<extra></extra>',
    }});
  }});

  // Linea soglia fissa
  if (entry.fixed !== null) {{
    const xMin = Math.min(...entry.companies.flatMap(c => c.x));
    const xMax = Math.max(...entry.companies.flatMap(c => c.x));
    traces.push({{
      type: 'scatter', mode: 'lines',
      name: entry.label || 'Soglia fissa',
      x: [xMin, xMax],
      y: [entry.fixed, entry.fixed],
      line: {{ color: '#e63946', width: 2, dash: 'dash' }},
      hovertemplate: 'Soglia fissa: ' + entry.fixed + '<extra></extra>',
    }});
  }}

  // Linea mediana gruppo (tratteggiata arancione)
  {{
    const xMin = Math.min(...entry.companies.flatMap(c => c.x));
    const xMax = Math.max(...entry.companies.flatMap(c => c.x));
    traces.push({{
      type: 'scatter', mode: 'lines',
      name: 'Mediana gruppo: ' + entry.median,
      x: [xMin, xMax],
      y: [entry.median, entry.median],
      line: {{ color: '#f4a261', width: 1.8, dash: 'dot' }},
      hovertemplate: 'Mediana: ' + entry.median + '<extra></extra>',
    }});
  }}

  const layout = {{
    margin: {{ t: 40, r: 20, b: 60, l: 60 }},
    xaxis: {{
      title: 'Anno',
      tickmode: 'array',
      tickvals: [...new Set(entry.companies.flatMap(c => c.x))].sort(),
      tickformat: 'd',
      gridcolor: '#e8eef5',
    }},
    yaxis: {{
      title: indicator,
      gridcolor: '#e8eef5',
      zeroline: true,
      zerolinecolor: '#ccc',
    }},
    legend: {{
      orientation: 'h', x: 0, y: -0.22,
      font: {{ size: 11 }},
    }},
    plot_bgcolor:  'white',
    paper_bgcolor: 'white',
    hovermode: 'x unified',
    font: {{ family: 'Segoe UI, Arial', size: 12 }},
  }};

  Plotly.newPlot('plotly-chart', traces, layout, {{
    responsive: true, displayModeBar: true,
    modeBarButtonsToRemove: ['lasso2d','select2d'],
  }});

  updateThresholdBox(entry, indicator);
  updateStatusTable(entry, indicator);
}}

function updateThresholdBox(entry, indicator) {{
  const box = document.getElementById('threshold-box');
  let html = `<h3>📊 ${{indicator}}</h3><div class="badges">`;

  if (entry.fixed !== null) {{
    const dir = entry.direction === 'above_good'
      ? '≥ ' + entry.fixed + ' = positivo'
      : '≤ ' + entry.fixed + ' = positivo';
    html += `<span class="badge badge-fixed">Soglia fissa: ${{entry.fixed}} (${{dir}})</span>`;
  }} else {{
    html += `<span class="badge badge-none">Nessuna soglia fissa per questo indicatore</span>`;
  }}

  html += `<span class="badge badge-median">Mediana gruppo: ${{entry.median}}</span>`;
  html += `</div>`;

  if (entry.note) {{
    html += `<p>${{entry.note}}</p>`;
  }}

  box.innerHTML = html;
}}

function updateStatusTable(entry, indicator) {{
  const tbody = document.getElementById('status-tbody');
  tbody.innerHTML = '';

  // Prendi l'ultimo anno per ogni azienda
  entry.companies.forEach(co => {{
    const validPairs = co.x.map((yr, i) => [yr, co.y[i]])
                           .filter(p => p[1] !== null && p[1] !== undefined);
    if (!validPairs.length) return;

    validPairs.sort((a,b) => b[0] - a[0]);
    const [lastYear, lastVal] = validPairs[0];

    // Stato vs soglia fissa
    let statoFixed = '<span class="na">N/A</span>';
    let isOk = null;
    if (entry.fixed !== null) {{
      if (entry.direction === 'above_good') {{
        isOk = lastVal >= entry.fixed;
      }} else {{
        isOk = lastVal <= entry.fixed;
      }}
      const op = entry.direction === 'above_good'
        ? (lastVal >= entry.fixed ? '≥' : '<')
        : (lastVal <= entry.fixed ? '≤' : '>');
      statoFixed = `${{lastVal.toFixed(2)}} ${{op}} ${{entry.fixed}}`;
    }}

    // Stato vs mediana
    const vsMedian = lastVal - entry.median;
    const vsMedianStr = (vsMedian >= 0 ? '+' : '') + vsMedian.toFixed(2);

    // Icona stato
    let statoIcon = '<span class="na">—</span>';
    if (isOk === true)  statoIcon = '<span class="ok">✅ OK</span>';
    if (isOk === false) statoIcon = '<span class="warn">⚠️ Attenzione</span>';

    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><b>${{co.name}}</b></td>
      <td>${{lastVal.toFixed(2)}} <small style="color:#888">(${{lastYear}})</small></td>
      <td>${{statoFixed}}</td>
      <td>${{vsMedianStr}}</td>
      <td>${{statoIcon}}</td>
    `;
    tbody.appendChild(tr);
  }});
}}

// Inizializza con il primo indicatore
updateChart();
</script>
</body>
</html>
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"  ✅ Dashboard HTML salvata: {output_path}")
    return output_path
