# report_generator.py  (va in wheelhouse-agent/)
# Tool che riceve i risultati numerici dell'analisi e produce:
# 1. Un report discorsivo generato dalla LLM
# 2. Un file HTML self-contained con testo + grafici embedded
# 3. Un file PDF con il testo del report

# wheelhouse output

import json
import os
import base64
from pathlib import Path
from langchain_core.tools import tool
from langchain_ollama import ChatOllama


# ---------------------------------------------------------------------------
# LLM per la generazione del testo
# ---------------------------------------------------------------------------

def _get_llm():
    return ChatOllama(model="qwen2.5:3b", temperature=0.3)


# ---------------------------------------------------------------------------
# PROMPT PER IL REPORT DISCORSIVO
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a professional financial analyst specialising in 
equity research and corporate finance. You write clear, concise, and insightful 
reports based on financial data. Always structure your analysis with:
- An executive summary
- Company-by-company commentary
- Group comparison and key takeaways
- Risk flags for companies below critical thresholds
Write in English. Be direct and avoid filler phrases."""

def _build_analysis_prompt(summary: dict, group_stats: dict,
                            companies: list) -> str:
    """
    Costruisce il prompt con i dati numerici da passare alla LLM.
    """
    company_names = [c.get("name", c) if isinstance(c, dict) else c
                     for c in companies]

    lines = [
        f"Analyse the following financial data for {len(summary)} companies: "
        f"{', '.join(company_names)}.\n",
        "## Key Financial Indicators (latest available year)\n",
    ]

    for company, indicators in summary.items():
        lines.append(f"### {company}")
        for k, v in indicators.items():
            val = f"{v:.2f}" if v is not None else "N/A"
            lines.append(f"- {k}: {val}")
        lines.append("")

    if group_stats:
        lines.append("## Group Statistics\n")
        if "median" in group_stats:
            lines.append("**Group Medians:**")
            for k, v in group_stats["median"].items():
                lines.append(f"- {k}: {v:.2f}" if isinstance(v, float) else f"- {k}: {v}")
        if "best" in group_stats:
            lines.append("\n**Best performer per indicator:**")
            for k, v in group_stats["best"].items():
                lines.append(f"- {k}: {v}")
        if "worst" in group_stats:
            lines.append("\n**Needs attention per indicator:**")
            for k, v in group_stats["worst"].items():
                lines.append(f"- {k}: {v}")

    lines.append(
        "\nWrite a structured financial report with: "
        "1) Executive Summary, "
        "2) Individual company analysis, "
        "3) Comparative conclusions, "
        "4) Risk flags for companies below sector thresholds "
        "(EBIT Margin < 5%, ROE < 10%, Debt/Equity > 2, Current Ratio < 1)."
    )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# GENERAZIONE TESTO REPORT
# ---------------------------------------------------------------------------

def generate_report_text(summary: dict, group_stats: dict,
                          companies: list) -> str:
    """
    Chiama la LLM e restituisce il testo del report discorsivo.
    """
    print("[report_generator] Generando testo report con LLM...")
    llm    = _get_llm()
    prompt = _build_analysis_prompt(summary, group_stats, companies)

    response = llm.invoke([
        ("system", SYSTEM_PROMPT),
        ("human",  prompt),
    ])

    text = response.content.strip()
    print(f"[report_generator] Testo generato ({len(text)} caratteri)")
    return text


# ---------------------------------------------------------------------------
# EXPORT HTML
# ---------------------------------------------------------------------------

def _encode_image(path: str) -> str | None:
    """Converte un'immagine PNG in base64 per embedding nell'HTML."""
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception:
        return None


def _collect_charts(output_dir: str) -> list[dict]:
    """
    Raccoglie i grafici PNG dalla cartella charts/ e li converte in base64.
    """
    charts_dir = os.path.join(output_dir, "charts")
    if not os.path.exists(charts_dir):
        return []

    charts = []
    for f in sorted(Path(charts_dir).glob("*.png")):
        b64 = _encode_image(str(f))
        if b64:
            label = f.stem.replace("_", " ").replace("bar ", "").title()
            charts.append({"label": label, "data": b64})

    return charts


def generate_html_report(report_text: str, output_dir: str,
                          companies: list, summary: dict) -> str:
    """
    Genera un file HTML self-contained con:
    - Testo del report generato dalla LLM
    - Grafici PNG embedded in base64
    - Link alla dashboard Plotly
    - Tabella riepilogativa degli indicatori
    """
    charts  = _collect_charts(output_dir)
    company_names = [c.get("name", c) if isinstance(c, dict) else c
                     for c in companies]

    # Tabella indicatori
    if summary:
        indicators = list(next(iter(summary.values())).keys())
        table_rows = ""
        for company, vals in summary.items():
            cells = "".join(
                f"<td>{vals.get(ind, 'N/A'):.2f}</td>"
                if isinstance(vals.get(ind), float) else f"<td>N/A</td>"
                for ind in indicators
            )
            table_rows += f"<tr><td><b>{company}</b></td>{cells}</tr>\n"

        table_headers = "".join(f"<th>{i}</th>" for i in indicators)
        table_html = f"""
        <table>
          <thead><tr><th>Company</th>{table_headers}</tr></thead>
          <tbody>{table_rows}</tbody>
        </table>"""
    else:
        table_html = "<p>No data available.</p>"

    # Grafici
    charts_html = ""
    for chart in charts:
        charts_html += f"""
        <div class="chart-card">
          <h3>{chart['label']}</h3>
          <img src="data:image/png;base64,{chart['data']}" alt="{chart['label']}">
        </div>"""

    # Testo report → paragrafi HTML
    report_html = ""
    for line in report_text.split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.startswith("## "):
            report_html += f"<h2>{line[3:]}</h2>\n"
        elif line.startswith("### "):
            report_html += f"<h3>{line[4:]}</h3>\n"
        elif line.startswith("**") and line.endswith("**"):
            report_html += f"<p><strong>{line[2:-2]}</strong></p>\n"
        elif line.startswith("- "):
            report_html += f"<li>{line[2:]}</li>\n"
        else:
            report_html += f"<p>{line}</p>\n"

    dashboard_path = os.path.join(output_dir, "trend_dashboard.html")
    dashboard_link = (
        f'<a href="{dashboard_path}" target="_blank">📊 Open Interactive Dashboard</a>'
        if os.path.exists(dashboard_path) else ""
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Financial Analysis Report</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: 'Segoe UI', Arial, sans-serif;
    background: #f0f4f8;
    color: #1a1a2e;
    line-height: 1.7;
  }}
  header {{
    background: linear-gradient(135deg, #03045e, #0077b6);
    color: white;
    padding: 32px 48px;
  }}
  header h1 {{ font-size: 1.8rem; font-weight: 700; }}
  header p  {{ opacity: 0.8; margin-top: 6px; font-size: 0.95rem; }}
  .container {{ max-width: 1100px; margin: 0 auto; padding: 32px 24px; }}
  .card {{
    background: white; border-radius: 10px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.07);
    padding: 28px 32px; margin-bottom: 28px;
  }}
  h2 {{
    font-size: 1.2rem; color: #03045e;
    border-bottom: 2px solid #0077b6;
    padding-bottom: 6px; margin: 24px 0 12px;
  }}
  h3 {{ font-size: 1rem; color: #0077b6; margin: 16px 0 8px; }}
  p  {{ margin-bottom: 10px; }}
  li {{ margin-left: 20px; margin-bottom: 4px; }}
  table {{
    width: 100%; border-collapse: collapse;
    font-size: 0.82rem; margin-top: 12px;
    overflow-x: auto; display: block;
  }}
  th {{
    background: #03045e; color: white;
    padding: 8px 10px; text-align: left;
    white-space: nowrap;
  }}
  td {{ padding: 7px 10px; border-bottom: 1px solid #e8eef5; }}
  tr:last-child td {{ border-bottom: none; }}
  .charts-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(460px, 1fr));
    gap: 20px;
  }}
  .chart-card {{
    background: white; border-radius: 10px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.07);
    padding: 16px;
  }}
  .chart-card h3 {{
    font-size: 0.9rem; margin-bottom: 10px; color: #03045e;
  }}
  .chart-card img {{ width: 100%; height: auto; border-radius: 6px; }}
  .dashboard-link {{
    display: inline-block;
    background: #0077b6; color: white;
    padding: 10px 20px; border-radius: 6px;
    text-decoration: none; font-weight: 600;
    margin-bottom: 24px;
  }}
  .dashboard-link:hover {{ background: #023e8a; }}
  footer {{
    text-align: center; font-size: 0.78rem;
    color: #888; padding: 20px;
  }}
</style>
</head>
<body>

<header>
  <h1>📊 Financial Analysis Report</h1>
  <p>{' · '.join(company_names)}</p>
</header>

<div class="container">

  {f'<a class="dashboard-link" href="{dashboard_path}" target="_blank">📊 Open Interactive Dashboard</a>' if os.path.exists(dashboard_path) else ''}

  <div class="card">
    <h2>Analyst Commentary</h2>
    {report_html}
  </div>

  <div class="card">
    <h2>Key Indicators — Latest Year</h2>
    {table_html}
  </div>

  <h2 style="margin: 0 0 16px;">Charts</h2>
  <div class="charts-grid">
    {charts_html}
  </div>

</div>

<footer>
  Data source: Yahoo Finance via yfinance · For educational/personal use only ·
  Report generated by sasyspanish's agent'
</footer>

</body>
</html>"""

    html_path = os.path.join(output_dir, "report.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[report_generator] ✅ HTML salvato: {html_path}")
    return html_path


# ---------------------------------------------------------------------------
# EXPORT PDF
# ---------------------------------------------------------------------------

def generate_pdf_report(report_text: str, output_dir: str,
                        companies: list) -> str:
    """
    Genera un PDF con il testo del report usando matplotlib
    (nessuna dipendenza esterna aggiuntiva).
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages

    company_names = [c.get("name", c) if isinstance(c, dict) else c
                     for c in companies]

    pdf_path = os.path.join(output_dir, "report.pdf")

    with PdfPages(pdf_path) as pdf:

        # Pagina titolo
        fig, ax = plt.subplots(figsize=(11, 8.5))
        ax.axis("off")
        ax.text(0.5, 0.70, "Financial Analysis Report",
                ha="center", va="center",
                fontsize=26, fontweight="bold", color="#03045e",
                transform=ax.transAxes)
        ax.text(0.5, 0.58, " · ".join(company_names),
                ha="center", va="center",
                fontsize=13, color="#0077b6",
                transform=ax.transAxes)
        ax.text(0.5, 0.44,
                "Data source: Yahoo Finance via yfinance\n"
                "Generated by sasyspanish",
                ha="center", va="center",
                fontsize=10, color="#888",
                transform=ax.transAxes)
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

        # Pagine testo — split per pagina
        lines      = report_text.split("\n")
        page_lines = []
        chars_per_page = 3000

        current = []
        current_len = 0
        for line in lines:
            current.append(line)
            current_len += len(line)
            if current_len >= chars_per_page:
                page_lines.append("\n".join(current))
                current = []
                current_len = 0
        if current:
            page_lines.append("\n".join(current))

        for page_text in page_lines:
            fig, ax = plt.subplots(figsize=(11, 8.5))
            ax.axis("off")
            ax.text(
                0.05, 0.95, page_text,
                ha="left", va="top",
                fontsize=8.5,
                family="monospace",
                transform=ax.transAxes,
                wrap=True,
            )
            pdf.savefig(fig, bbox_inches="tight")
            plt.close(fig)

    print(f"[report_generator] ✅ PDF salvato: {pdf_path}")
    return pdf_path


# ---------------------------------------------------------------------------
# TOOL PER L'AGENTE
# ---------------------------------------------------------------------------

@tool
def generate_report_tool(analysis_output: str) -> str:
    """
    Genera il report finale dell'analisi finanziaria.

    Input: stringa JSON prodotta da run_analysis_tool, contenente
           'summary', 'group_stats', 'companies' e 'output_dir'.

    Produce tre file nella cartella di output:
    - report.html  → report completo con testo + grafici embedded
    - report.pdf   → versione PDF del testo discorsivo
    - (dashboard HTML già generata dal tool precedente)

    Restituisce i path dei file generati.
    """
    try:
        data = json.loads(analysis_output)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Input JSON non valido: {e}"})

    if data.get("status") != "success":
        return json.dumps({"error": "L'analisi non è andata a buon fine.", "detail": data})

    summary     = data.get("summary", {})
    group_stats = data.get("group_stats", {})
    companies   = data.get("companies", [])
    output_dir  = data.get("output_dir", "output_agent")

    if not summary:
        return json.dumps({"error": "Nessun dato numerico disponibile per il report."})

    # 1. Genera testo con LLM
    report_text = generate_report_text(summary, group_stats, companies)

    # 2. HTML
    html_path = generate_html_report(
        report_text, output_dir, companies, summary
    )

    # 3. PDF
    pdf_path = generate_pdf_report(report_text, output_dir, companies)

    return json.dumps({
        "status":      "success",
        "report_text": report_text[:500] + "...",  # preview
        "files": {
            "html":      html_path,
            "pdf":       pdf_path,
            "dashboard": os.path.join(output_dir, "trend_dashboard.html"),
        },
    }, ensure_ascii=False)