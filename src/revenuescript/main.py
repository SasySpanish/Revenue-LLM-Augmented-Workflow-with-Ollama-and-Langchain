# main.py automotive
# Script principale: scarica dati, calcola indicatori, analisi trend,
# dati di mercato, grafici e export Excel/PDF/HTML

import os
import pandas as pd

from fetcher          import fetch_all
from indicators       import compute_all
from trend_analysis   import build_all_trends, build_cagr_table
from market_data      import fetch_market_data, print_market_table
from visualizer       import generate_all_charts
from trend_dashboard  import generate_trend_dashboard
from config           import TICKERS

OUTPUT_DIR = "output"


def safe_sheet(name: str) -> str:
    for ch in r'/\?*[]:':
        name = name.replace(ch, "-")
    return name[:31]


def build_summary(all_data: dict) -> dict:
    results = {}
    for symbol, raw in all_data.items():
        name = TICKERS[symbol]["name"]
        print(f"  Calcolando indicatori per {name}...")
        df = compute_all(raw)
        if not df.empty:
            results[symbol] = df
        else:
            print(f"  [SKIP] Dati insufficienti per {symbol}")
    return results


def export_to_excel(results: dict, trends: dict,
                    cagr_df: pd.DataFrame, market_df: pd.DataFrame,
                    filepath: str):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with pd.ExcelWriter(filepath, engine="openpyxl") as writer:

        for symbol, df in results.items():
            name = TICKERS[symbol]["name"]
            df.round(2).to_excel(writer, sheet_name=safe_sheet(name))

        comparison_rows = []
        for symbol, df in results.items():
            if df.empty:
                continue
            last_year = df.columns[0]
            row = df[last_year].copy()
            row.name = TICKERS[symbol]["name"]
            comparison_rows.append(row)
        if comparison_rows:
            pd.DataFrame(comparison_rows).round(2).to_excel(
                writer, sheet_name="Confronto (ultimo anno)"
            )

        TREND_EXPORT = [
            "Revenue (M)", "EBIT (M)", "EBITDA (M)",
            "EBIT Margin (%)", "EBITDA Margin (%)",
            "ROE (%)", "ROA (%)", "Debt/Equity",
        ]
        for indicator in TREND_EXPORT:
            if indicator in trends:
                trends[indicator].round(2).to_excel(
                    writer, sheet_name=safe_sheet(indicator)
                )

        if not cagr_df.empty:
            cagr_df.round(2).to_excel(writer, sheet_name="CAGR")

        if not market_df.empty:
            market_df.drop(columns=["Ticker"], errors="ignore").round(2).to_excel(
                writer, sheet_name="Multipli di Mercato"
            )

    print(f"\n  ✅ Excel salvato: {filepath}")


def print_comparison_table(results: dict):
    KEY_INDICATORS = [
        "Revenue (M)", "EBIT Margin (%)", "EBITDA Margin (%)",
        "Net Margin (%)", "ROE (%)", "ROA (%)",
        "ROI / ROCE (%)", "Debt/Equity", "Current Ratio",
    ]
    rows = {}
    for symbol, df in results.items():
        if df.empty:
            continue
        last_year = df.columns[0]
        rows[TICKERS[symbol]["name"]] = df[last_year]
    if not rows:
        print("Nessun dato disponibile.")
        return
    comparison = pd.DataFrame(rows).T
    available = [i for i in KEY_INDICATORS if i in comparison.columns]
    print("\n" + "=" * 80)
    print("CONFRONTO INDICATORI — AUTOMOTIVE EUROPEO (ultimo anno disponibile)")
    print("=" * 80)
    print(comparison[available].round(2).to_string())
    print("=" * 80)


def main():
    print("\n🚗 AUTOMOTIVE EUROPE — Financial Analysis")
    print("=" * 55)

    print("\n[1/6] Download dati da Yahoo Finance...")
    all_data = fetch_all()
    print(f"  ✅ Dati scaricati per {len(all_data)} aziende")

    print("\n[2/6] Calcolo indicatori finanziari...")
    results = build_summary(all_data)
    print(f"  ✅ Indicatori calcolati per {len(results)} aziende")

    print("\n[3/6] Analisi trend multi-anno...")
    trends = build_all_trends(results)
    cagr_df = build_cagr_table(trends)
    print(f"  ✅ Trend calcolati per {len(trends)} indicatori")

    print("\n[4/6] Raccolta dati di mercato...")
    market_df = fetch_market_data(all_data)
    print_market_table(market_df)
    print(f"  ✅ Multipli di mercato pronti per {len(market_df)} aziende")

    print("\n[5/6] Generazione grafici matplotlib (PNG + PDF)...")
    print_comparison_table(results)
    excel_path = os.path.join(OUTPUT_DIR, "excel_analysis.xlsx")
    export_to_excel(results, trends, cagr_df, market_df, excel_path)
    generate_all_charts(results, market_df, trends, cagr_df)

    print("\n[6/6] Generazione dashboard Plotly (HTML)...")
    generate_trend_dashboard(trends)

    print("\n" + "=" * 55)
    print("✅ Analisi completata. Output salvati in /output/")
    print("   - analysis.xlsx")
    print("   - analysis_charts.pdf")
    print("   - charts/*.png  (grafici singoli)")
    print("   - trend_dashboard.html  ← apri nel browser o carica online")


if __name__ == "__main__":
    main()
