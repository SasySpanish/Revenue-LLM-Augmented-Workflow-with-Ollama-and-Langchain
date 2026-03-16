# indicators.py automotive
# Calcolo di tutti gli indicatori finanziari dal conto economico e stato patrimoniale

import pandas as pd


# ---------------------------------------------------------------------------
# HELPER
# ---------------------------------------------------------------------------

def _get(df: pd.DataFrame, *keys) -> pd.Series:
    """
    Cerca la prima chiave trovata nel DataFrame (case-insensitive).
    Ritorna una Serie di NaN se nessuna chiave è trovata.
    """
    for key in keys:
        for idx in df.index:
            if str(idx).lower() == key.lower():
                return df.loc[idx]
    return pd.Series([float("nan")] * len(df.columns), index=df.columns)


def safe_div(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    """Divisione sicura che evita divisioni per zero."""
    return numerator.div(denominator.replace(0, float("nan")))


# ---------------------------------------------------------------------------
# INDICATORI DI REDDITIVITA'
# ---------------------------------------------------------------------------

def calc_ebit(income: pd.DataFrame) -> pd.Series:
    """
    EBIT = Operating Income
    Misura il reddito operativo prima di interessi e tasse.
    """
    return _get(income, "Operating Income", "EBIT", "Ebit")


def calc_ebitda(income: pd.DataFrame, cashflow: pd.DataFrame) -> pd.Series:
    """
    EBITDA = EBIT + Depreciation & Amortization
    Approssima il flusso di cassa operativo lordo.
    """
    ebit = calc_ebit(income)
    # D&A può stare nel cashflow o nel conto economico
    da = _get(cashflow,
              "Depreciation And Amortization",
              "Depreciation Amortization Depletion",
              "Depreciation")
    # Alcuni ticker espongono D&A nel conto economico
    if da.isna().all():
        da = _get(income,
                  "Reconciled Depreciation",
                  "Depreciation And Amortization In Income Statement")
    return ebit + da.abs()


def calc_net_income(income: pd.DataFrame) -> pd.Series:
    """Net Income (utile netto)."""
    return _get(income, "Net Income", "Net Income Common Stockholders")


def calc_gross_profit(income: pd.DataFrame) -> pd.Series:
    """Gross Profit (utile lordo)."""
    return _get(income, "Gross Profit")


def calc_revenue(income: pd.DataFrame) -> pd.Series:
    """Ricavi totali."""
    return _get(income, "Total Revenue", "Revenue")


# ---------------------------------------------------------------------------
# INDICATORI DI MARGINE
# ---------------------------------------------------------------------------

def calc_gross_margin(income: pd.DataFrame) -> pd.Series:
    """Gross Margin = Gross Profit / Revenue (%)"""
    return safe_div(calc_gross_profit(income), calc_revenue(income)) * 100


def calc_ebit_margin(income: pd.DataFrame) -> pd.Series:
    """EBIT Margin = EBIT / Revenue (%)"""
    return safe_div(calc_ebit(income), calc_revenue(income)) * 100


def calc_ebitda_margin(income: pd.DataFrame, cashflow: pd.DataFrame) -> pd.Series:
    """EBITDA Margin = EBITDA / Revenue (%)"""
    return safe_div(calc_ebitda(income, cashflow), calc_revenue(income)) * 100


def calc_net_margin(income: pd.DataFrame) -> pd.Series:
    """Net Margin = Net Income / Revenue (%)"""
    return safe_div(calc_net_income(income), calc_revenue(income)) * 100


# ---------------------------------------------------------------------------
# INDICATORI DI RENDIMENTO
# ---------------------------------------------------------------------------

def calc_roe(income: pd.DataFrame, balance: pd.DataFrame) -> pd.Series:
    """
    ROE = Net Income / Stockholders' Equity (%)
    Misura il rendimento sul capitale proprio.
    """
    equity = _get(balance,
                  "Stockholders Equity",
                  "Total Equity Gross Minority Interest",
                  "Common Stock Equity")
    return safe_div(calc_net_income(income), equity) * 100


def calc_roa(income: pd.DataFrame, balance: pd.DataFrame) -> pd.Series:
    """
    ROA = Net Income / Total Assets (%)
    Misura l'efficienza nell'uso degli asset totali.
    """
    assets = _get(balance, "Total Assets")
    return safe_div(calc_net_income(income), assets) * 100


def calc_roi(income: pd.DataFrame, balance: pd.DataFrame) -> pd.Series:
    """
    ROI = EBIT / (Total Assets - Current Liabilities) (%)
    Misura il rendimento sul capitale investito operativo.
    """
    ebit = calc_ebit(income)
    assets = _get(balance, "Total Assets")
    curr_liab = _get(balance, "Current Liabilities", "Total Current Liabilities Net Minority Interest")
    invested_capital = assets - curr_liab
    return safe_div(ebit, invested_capital) * 100


def calc_roce(income: pd.DataFrame, balance: pd.DataFrame) -> pd.Series:
    """
    ROCE = EBIT / Capital Employed (%)
    Capital Employed = Total Assets - Current Liabilities
    Simile al ROI, enfatizza il capitale impiegato a lungo termine.
    """
    return calc_roi(income, balance)  # stessa formula


# ---------------------------------------------------------------------------
# INDICATORI DI LIQUIDITA'
# ---------------------------------------------------------------------------

def calc_current_ratio(balance: pd.DataFrame) -> pd.Series:
    """
    Current Ratio = Current Assets / Current Liabilities
    Misura la capacità di coprire debiti a breve con attivi a breve.
    Valore ideale > 1.
    """
    curr_assets = _get(balance, "Current Assets", "Total Current Assets")
    curr_liab   = _get(balance, "Current Liabilities", "Total Current Liabilities Net Minority Interest")
    return safe_div(curr_assets, curr_liab)


def calc_quick_ratio(balance: pd.DataFrame) -> pd.Series:
    """
    Quick Ratio = (Current Assets - Inventory) / Current Liabilities
    Versione più conservativa del Current Ratio (esclude magazzino).
    """
    curr_assets = _get(balance, "Current Assets", "Total Current Assets")
    inventory   = _get(balance, "Inventory")
    curr_liab   = _get(balance, "Current Liabilities", "Total Current Liabilities Net Minority Interest")
    return safe_div(curr_assets - inventory, curr_liab)


# ---------------------------------------------------------------------------
# INDICATORI DI STRUTTURA FINANZIARIA / LEVA
# ---------------------------------------------------------------------------

def calc_debt_to_equity(balance: pd.DataFrame) -> pd.Series:
    """
    Debt/Equity = Total Debt / Stockholders' Equity
    Misura il grado di leva finanziaria.
    """
    total_debt = _get(balance, "Total Debt", "Long Term Debt And Capital Lease Obligation")
    equity     = _get(balance, "Stockholders Equity",
                      "Total Equity Gross Minority Interest",
                      "Common Stock Equity")
    return safe_div(total_debt, equity)


def calc_net_debt(balance: pd.DataFrame) -> pd.Series:
    """
    Net Debt = Total Debt - Cash & Equivalents
    Misura l'indebitamento netto effettivo.
    """
    total_debt = _get(balance, "Total Debt")
    cash       = _get(balance, "Cash And Cash Equivalents",
                      "Cash Cash Equivalents And Short Term Investments")
    return total_debt - cash


def calc_interest_coverage(income: pd.DataFrame) -> pd.Series:
    """
    Interest Coverage = EBIT / Interest Expense
    Misura quante volte l'EBIT copre gli oneri finanziari.
    Valori > 3 sono considerati sani.
    """
    ebit     = calc_ebit(income)
    interest = _get(income, "Interest Expense",
                    "Interest Expense Non Operating").abs()
    return safe_div(ebit, interest)


# ---------------------------------------------------------------------------
# CALCOLO COMPLETO PER UN TICKER
# ---------------------------------------------------------------------------

def compute_all(raw_data: dict) -> pd.DataFrame:
    """
    Calcola tutti gli indicatori per un singolo ticker.
    Input: dizionario con 'income_stmt', 'balance_sheet', 'cashflow'
    Output: DataFrame con indicatori come righe e anni come colonne
    """
    income  = raw_data.get("income_stmt",   pd.DataFrame())
    balance = raw_data.get("balance_sheet", pd.DataFrame())
    cf      = raw_data.get("cashflow",      pd.DataFrame())

    if income.empty or balance.empty:
        return pd.DataFrame()

    indicators = {
        # --- Redditività assoluta ---
        "Revenue (M)":        calc_revenue(income) / 1e6,
        "Gross Profit (M)":   calc_gross_profit(income) / 1e6,
        "EBIT (M)":           calc_ebit(income) / 1e6,
        "EBITDA (M)":         calc_ebitda(income, cf) / 1e6,
        "Net Income (M)":     calc_net_income(income) / 1e6,
        "Net Debt (M)":       calc_net_debt(balance) / 1e6,

        # --- Margini (%) ---
        "Gross Margin (%)":   calc_gross_margin(income),
        "EBIT Margin (%)":    calc_ebit_margin(income),
        "EBITDA Margin (%)":  calc_ebitda_margin(income, cf),
        "Net Margin (%)":     calc_net_margin(income),

        # --- Rendimento (%) ---
        "ROE (%)":            calc_roe(income, balance),
        "ROA (%)":            calc_roa(income, balance),
        "ROI / ROCE (%)":     calc_roi(income, balance),

        # --- Liquidità ---
        "Current Ratio":      calc_current_ratio(balance),
        "Quick Ratio":        calc_quick_ratio(balance),

        # --- Leva finanziaria ---
        "Debt/Equity":        calc_debt_to_equity(balance),
        "Interest Coverage":  calc_interest_coverage(income),
    }

    return pd.DataFrame(indicators).T
