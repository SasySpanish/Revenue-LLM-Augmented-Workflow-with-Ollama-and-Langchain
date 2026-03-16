# fetcher.py
# Scarica i dati finanziari grezzi da Yahoo Finance tramite yfinance

import yfinance as yf
import pandas as pd
from config import TICKERS, YEARS


def fetch_raw_data(ticker_symbol: str) -> dict:
    """
    Scarica income statement, balance sheet e cashflow per un ticker.
    Ritorna un dizionario con i tre DataFrame annuali.
    """
    ticker = yf.Ticker(ticker_symbol)

    try:
        income_stmt  = ticker.income_stmt          # conto economico annuale
        balance_sheet = ticker.balance_sheet       # stato patrimoniale annuale
        cashflow      = ticker.cashflow            # rendiconto finanziario annuale
        info          = ticker.info                # metriche e metadata
    except Exception as e:
        print(f"[ERRORE] Impossibile scaricare dati per {ticker_symbol}: {e}")
        return {}

    # Tronca agli ultimi N anni disponibili
    def trim(df):
        if df is not None and not df.empty:
            return df.iloc[:, :YEARS]
        return pd.DataFrame()

    return {
        "income_stmt":   trim(income_stmt),
        "balance_sheet": trim(balance_sheet),
        "cashflow":      trim(cashflow),
        "info":          info,
    }


def fetch_all() -> dict:
    """
    Scarica i dati per tutti i ticker definiti in config.py.
    Ritorna un dizionario { ticker_symbol: { raw_data } }
    """
    all_data = {}
    for symbol, meta in TICKERS.items():
        print(f"  Scaricando {meta['name']} ({symbol})...")
        raw = fetch_raw_data(symbol)
        if raw:
            all_data[symbol] = raw
        else:
            print(f"  [SKIP] Nessun dato per {symbol}")
    return all_data


def print_available_fields(ticker_symbol: str):
    """
    Utility: stampa tutti i campi disponibili per un ticker.
    Utile per debug o per esplorare nuovi indicatori.
    """
    ticker = yf.Ticker(ticker_symbol)
    print(f"\n=== CAMPI DISPONIBILI PER {ticker_symbol} ===")

    for label, df in [
        ("INCOME STATEMENT", ticker.income_stmt),
        ("BALANCE SHEET",    ticker.balance_sheet),
        ("CASH FLOW",        ticker.cashflow),
    ]:
        print(f"\n--- {label} ---")
        if df is not None and not df.empty:
            for field in df.index.tolist():
                print(f"  {field}")
        else:
            print("  (nessun dato)")

    print("\n--- INFO (chiavi principali) ---")
    info = ticker.info
    keys_of_interest = [
        "returnOnEquity", "returnOnAssets", "debtToEquity",
        "currentRatio", "quickRatio", "grossMargins",
        "operatingMargins", "profitMargins", "ebitdaMargins",
        "revenueGrowth", "earningsGrowth", "totalRevenue",
        "marketCap", "enterpriseValue", "trailingEps",
    ]
    for k in keys_of_interest:
        print(f"  {k}: {info.get(k, 'N/A')}")


if __name__ == "__main__":
    # Test rapido: esplora i campi disponibili per Volkswagen
    print_available_fields("VOW3.DE")
