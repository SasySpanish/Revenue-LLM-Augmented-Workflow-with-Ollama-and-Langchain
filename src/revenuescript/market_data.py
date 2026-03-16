# market_data.py
# Estrae dati di mercato (multipli di valutazione) da yfinance .info

import pandas as pd
from config import TICKERS


# Mapping campi yfinance → etichetta leggibile automotive
MARKET_FIELDS = {
    "marketCap":          "Market Cap (M)",
    "trailingPE":         "P/E (Trailing)",
    "forwardPE":          "P/E (Forward)",
    "priceToBook":        "Price/Book (P/B)",
    "enterpriseValue":    "Enterprise Value (M)",
    "enterpriseToEbitda": "EV/EBITDA",
    "enterpriseToRevenue":"EV/Revenue",
    "trailingEps":        "EPS (Trailing)",
    "dividendYield":      "Dividend Yield (%)",
    "beta":               "Beta",
}


def fetch_market_data(all_raw: dict) -> pd.DataFrame:
    """
    Estrae i multipli di mercato dall'oggetto .info già scaricato.
    Input:  all_raw = { symbol: { 'info': {...}, ... } }
    Output: DataFrame con aziende come righe e multipli come colonne
    """
    rows = []

    for symbol, raw in all_raw.items():
        info = raw.get("info", {})
        if not info:
            continue

        try:
            name = TICKERS[symbol]["name"]
        except KeyError:
            name = all_raw[symbol].get("info", {}).get("longName") or symbol
        row = {"Company": name, "Ticker": symbol}

        for yf_key, label in MARKET_FIELDS.items():
            val = info.get(yf_key)

            # Converti in milioni dove applicabile
            if yf_key in ("marketCap", "enterpriseValue") and val is not None:
                val = val / 1e6

            # Converti dividend yield in percentuale
            if yf_key == "dividendYield" and val is not None:
                val = val * 100

            row[label] = round(val, 2) if val is not None else float("nan")

        rows.append(row)

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows).set_index("Company")
    return df


def print_market_table(market_df: pd.DataFrame):
    """Stampa a terminale i multipli di mercato."""
    if market_df.empty:
        print("Nessun dato di mercato disponibile.")
        return

    print("\n" + "=" * 80)
    print("MULTIPLI DI MERCATO — AUTOMOTIVE EUROPEO")
    print("=" * 80)
    cols = [c for c in market_df.columns if c != "Ticker"]
    print(market_df[cols].to_string())
    print("=" * 80)
