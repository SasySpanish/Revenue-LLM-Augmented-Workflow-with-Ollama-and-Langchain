# runner.py  (va in C:/Users/Utente/Desktop/revenuescript/)
# automotive
# Espone run_full_analysis(tickers, names) come funzione unica
# che l'agente può chiamare passando una lista di ticker qualsiasi.
# Riutilizza interamente le funzioni esistenti del progetto.

import os
import tempfile
import pandas as pd

from fetcher        import fetch_raw_data
from indicators     import compute_all
from trend_analysis import build_all_trends, build_cagr_table
from market_data    import fetch_market_data
from visualizer     import generate_all_charts
from trend_dashboard import generate_trend_dashboard


def run_full_analysis(
    tickers: dict,
    output_dir: str = "output_agent",
) -> dict:
    import config as _cfg

    os.makedirs(output_dir, exist_ok=True)
    _patch_output_dir(output_dir)

    # Patch TICKERS per tutta la durata dell'analisi
    _original_tickers = _cfg.TICKERS.copy()
    _cfg.TICKERS = tickers

    errors  = []
    all_raw = {}

    try:
        # 1. Download dati
        print(f"\n[runner] Scaricando dati per {len(tickers)} ticker...")
        for symbol, meta in tickers.items():
            print(f"  {meta['name']} ({symbol})...")
            raw = fetch_raw_data(symbol)
            if raw:
                all_raw[symbol] = raw
            else:
                print(f"  [SKIP] Nessun dato per {symbol}")
                errors.append(symbol)

        # 2. Calcolo indicatori
        print("[runner] Calcolo indicatori...")
        results = {}
        for symbol, raw in all_raw.items():
            df = compute_all(raw)
            if not df.empty:
                results[symbol] = df
            else:
                print(f"  [SKIP] Indicatori vuoti per {symbol}")
                errors.append(symbol)

        if not results:
            return {
                "results": {}, "trends": {}, "cagr": pd.DataFrame(),
                "market": pd.DataFrame(), "output_dir": output_dir,
                "errors": errors,
            }

        # 3. Trend e CAGR
        print("[runner] Analisi trend...")
        trends  = build_all_trends(results)
        cagr_df = build_cagr_table(trends)

        # 4. Dati di mercato
        print("[runner] Dati di mercato...")
        market_df = fetch_market_data(all_raw)

        # 5. Grafici e report
        print("[runner] Generazione output...")
        generate_all_charts(results, market_df, trends, cagr_df)
        generate_trend_dashboard(
            trends,
            output_path=os.path.join(output_dir, "trend_dashboard.html"),
        )

    finally:
        # Ripristina TICKERS originale SEMPRE, anche in caso di errore
        _cfg.TICKERS = _original_tickers

    return {
        "results":    results,
        "trends":     trends,
        "cagr":       cagr_df,
        "market":     market_df,
        "output_dir": output_dir,
        "errors":     errors,
    }

def build_comparison_table(results: dict, tickers: dict) -> pd.DataFrame:
    """
    Ritorna un DataFrame di confronto (aziende × indicatori) per l'ultimo anno.
    Utile per passare i numeri alla LLM per il report discorsivo.
    """
    KEY = [
        "Revenue (M)", "EBIT Margin (%)", "EBITDA Margin (%)",
        "Net Margin (%)", "ROE (%)", "ROA (%)",
        "ROI / ROCE (%)", "Debt/Equity", "Current Ratio",
    ]
    rows = {}
    for symbol, df in results.items():
        if df.empty:
            continue
        last_year = df.columns[0]
        row = df[last_year].copy()
        row.name = tickers[symbol]["name"]
        rows[tickers[symbol]["name"]] = row

    if not rows:
        return pd.DataFrame()

    df_comp = pd.DataFrame(rows).T
    available = [c for c in KEY if c in df_comp.columns]
    return df_comp[available].round(2)


# ---------------------------------------------------------------------------
# HELPER INTERNO
# ---------------------------------------------------------------------------

def _patch_output_dir(output_dir: str):
    """
    Le funzioni visualizer e trend_dashboard usano OUTPUT_DIR come costante.
    La sostituiamo a runtime per rispettare la cartella scelta dall'agente.
    """
    import visualizer     as _vis
    import trend_dashboard as _td
    _vis.OUTPUT_DIR = output_dir
    _td.OUTPUT_DIR  = output_dir
