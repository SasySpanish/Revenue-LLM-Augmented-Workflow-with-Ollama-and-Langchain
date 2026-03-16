# trend_analysis.py
# Analisi trend multi-anno per ogni indicatore e azienda automotive

import pandas as pd
from config import TICKERS


def build_trend_table(results: dict, indicator: str) -> pd.DataFrame:
    rows = {}
    for symbol, df in results.items():
        if df.empty or indicator not in df.index:
            continue

        # Legge il nome dal dizionario results stesso se disponibile,
        # altrimenti fallback a config.TICKERS, altrimenti usa il simbolo
        try:
            from config import TICKERS as _T
            name = _T[symbol]["name"]
        except KeyError:
            name = symbol  # fallback: usa il ticker come nome

        series = df.loc[indicator]
        series.index = [_parse_year(c) for c in series.index]
        rows[name] = series

    if not rows:
        return pd.DataFrame()

    trend_df = pd.DataFrame(rows).T
    trend_df = trend_df[sorted(trend_df.columns)]
    return trend_df


def build_all_trends(results: dict) -> dict:
    """
    Costruisce le tabelle trend per tutti gli indicatori disponibili.
    Output: { indicator_name: DataFrame(aziende x anni) }
    """
    if not results:
        return {}

    # Prendi la lista indicatori dal primo ticker con dati
    sample_df = next(iter(results.values()))
    all_indicators = sample_df.index.tolist()

    trends = {}
    for indicator in all_indicators:
        df = build_trend_table(results, indicator)
        if not df.empty:
            trends[indicator] = df

    return trends


def compute_cagr(series: pd.Series) -> float:
    """
    Calcola il CAGR (Compound Annual Growth Rate) di una serie temporale.
    Ritorna NaN se i dati sono insufficienti o il valore iniziale è <= 0.
    """
    clean = series.dropna()
    if len(clean) < 2:
        return float("nan")
    start, end = clean.iloc[0], clean.iloc[-1]
    n = len(clean) - 1
    if start <= 0 or end <= 0:
        return float("nan")
    return round(((end / start) ** (1 / n) - 1) * 100, 2)


def build_cagr_table(trends: dict, indicators: list = None) -> pd.DataFrame:
    """
    Costruisce una tabella con il CAGR per ogni azienda e indicatore.
    Utile per capire chi è cresciuto di più nel tempo.
    """
    if indicators is None:
        indicators = [
            "Revenue (M)",
            "EBIT (M)",
            "EBITDA (M)",
            "Net Income (M)",
            "EBIT Margin (%)",
            "ROE (%)",
        ]

    cagr_data = {}
    for indicator in indicators:
        if indicator not in trends:
            continue
        df = trends[indicator]
        cagr_data[indicator] = df.apply(compute_cagr, axis=1)

    if not cagr_data:
        return pd.DataFrame()

    return pd.DataFrame(cagr_data)


def print_trend_summary(trends: dict, indicator: str):
    """Stampa la tabella trend per un indicatore specifico."""
    if indicator not in trends:
        print(f"Indicatore '{indicator}' non disponibile.")
        return

    df = trends[indicator]
    print(f"\n{'='*70}")
    print(f"TREND: {indicator}")
    print("="*70)
    print(df.round(2).to_string())


# ---------------------------------------------------------------------------
# HELPER
# ---------------------------------------------------------------------------

def _parse_year(col) -> int:
    """Estrae l'anno da un oggetto Timestamp o stringa."""
    try:
        if hasattr(col, "year"):
            return col.year
        return int(str(col)[:4])
    except Exception:
        return col
