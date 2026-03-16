# tool_analysis.py
# Tool che riceve i ticker risolti e lancia l'analisi completa
# tramite runner.run_full_analysis(), restituendo un riepilogo
# dei risultati pronti per essere passati alla LLM per il report.

#wheelhouse

import json
import os
from langchain_core.tools import tool

from runner import run_full_analysis, build_comparison_table
from ticker_resolver import resolve_tickers


# ---------------------------------------------------------------------------
# HELPER
# ---------------------------------------------------------------------------

def _build_tickers_dict(valid_tickers: list, names: dict) -> dict:
    """
    Costruisce il dizionario nel formato atteso da run_full_analysis()
    a partire dalla lista di ticker validi e i nomi restituiti dal resolver.
    """
    from ticker_resolver import validate_ticker

    result = {}
    for symbol in valid_tickers:
        if symbol in names:
            # Nome già noto dalla knowledge base
            result[symbol] = {
                "name":    names[symbol],
                "country": "??",
                "segment": "unknown",
            }
        else:
            # Recupera metadati da yfinance
            meta = validate_ticker(symbol)
            if meta:
                result[symbol] = meta

    return result


def _summarise_results(results: dict, tickers: dict) -> dict:
    """
    Costruisce un dizionario compatto con i valori chiave
    dell'ultimo anno per ogni azienda.
    Usato per passare i dati numerici alla LLM in modo conciso.
    """
    KEY_INDICATORS = [
        "Revenue (M)", "EBIT Margin (%)", "EBITDA Margin (%)",
        "Net Margin (%)", "ROE (%)", "ROA (%)",
        "ROI / ROCE (%)", "Debt/Equity", "Current Ratio",
        "Interest Coverage",
    ]

    summary = {}
    for symbol, df in results.items():
        if df.empty:
            continue
        name      = tickers.get(symbol, {}).get("name", symbol)
        last_year = df.columns[0]
        row       = {}
        for ind in KEY_INDICATORS:
            if ind in df.index:
                val = df.loc[ind, last_year]
                row[ind] = round(float(val), 2) if not _isnan(val) else None
        summary[name] = row

    return summary


def _isnan(val) -> bool:
    try:
        import math
        return math.isnan(float(val))
    except Exception:
        return True


def _make_output_dir(names: dict) -> str:
    """
    Genera un nome cartella output basato sui ticker analizzati.
    """
    slug = "_".join(list(names.values())[:3])
    slug = slug.replace(" ", "")[:40]
    return os.path.join("output_agent", slug)


# ---------------------------------------------------------------------------
# TOOL PER L'AGENTE
# ---------------------------------------------------------------------------

@tool
def run_analysis_tool(resolver_output: str) -> str:
    """
    Esegue l'analisi finanziaria completa sui ticker forniti.

    Input: stringa JSON prodotta da ticker_resolver_tool o
           validate_custom_tickers_tool, contenente i campi
           'valid' (o 'tickers') e 'names'.

    Lancia run_full_analysis(), genera tutti i grafici PNG, il PDF
    e la dashboard HTML interattiva, e restituisce un riepilogo
    JSON con i valori degli indicatori chiave per ogni azienda.
    """
    # --- Parse input ---
    try:
        data = json.loads(resolver_output)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Input JSON non valido: {e}"})

    # Supporta sia il formato di ticker_resolver_tool
    # sia quello di validate_custom_tickers_tool
    valid_tickers = data.get("valid") or data.get("tickers", [])
    names         = data.get("names", {})

    if not valid_tickers:
        return json.dumps({
            "error": "Nessun ticker valido da analizzare.",
            "detail": data.get("message", ""),
        })

    print(f"\n[run_analysis] Avvio analisi per: {valid_tickers}")

    # --- Costruisci dizionario tickers ---
    tickers_dict = _build_tickers_dict(valid_tickers, names)
    if not tickers_dict:
        return json.dumps({"error": "Impossibile costruire il dizionario ticker."})

    # --- Output directory ---
    output_dir = _make_output_dir(names)
    os.makedirs(output_dir, exist_ok=True)
    print(f"[run_analysis] Output in: {output_dir}")

    # --- Esegui analisi ---
    try:
        result = run_full_analysis(tickers_dict, output_dir=output_dir)
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print(f"[run_analysis] ERRORE COMPLETO:\n{tb}")
        return json.dumps({"error": f"Analisi fallita: {e}", "traceback": tb})

    # --- Costruisci riepilogo numerico ---
    summary   = _summarise_results(result["results"], tickers_dict)
    comp_df   = build_comparison_table(result["results"], tickers_dict)
    comp_dict = comp_df.to_dict() if not comp_df.empty else {}

    # --- Statistiche gruppo ---
    # Statistiche gruppo
    group_stats = {}
    if not comp_df.empty:
        # Elimina colonne con tutti NaN prima di calcolare best/worst
        clean_df = comp_df.dropna(axis=1, how="all")
        if not clean_df.empty:
            group_stats = {
                "median": clean_df.median(numeric_only=True).round(2).to_dict(),
                "best":   clean_df.idxmax(numeric_only=True).to_dict(),
                "worst":  clean_df.idxmin(numeric_only=True).to_dict(),
            }

    output = {
        "status":       "success",
        "output_dir":   output_dir,
        "files": {
            "excel":     os.path.join(output_dir, "automotive_analysis.xlsx"),
            "pdf":       os.path.join(output_dir, "automotive_analysis_charts.pdf"),
            "dashboard": os.path.join(output_dir, "trend_dashboard.html"),
        },
        "companies":    list(tickers_dict.values()),
        "summary":      summary,
        "group_stats":  group_stats,
        "errors":       result.get("errors", []),
    }

    print(f"[run_analysis] ✅ Completato. File in: {output_dir}")
    return json.dumps(output, ensure_ascii=False)