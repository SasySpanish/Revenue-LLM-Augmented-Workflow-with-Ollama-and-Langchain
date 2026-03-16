# ticker_resolver.py
# Tool che converte una descrizione testuale in ticker validi su yfinance.
# Strategia ibrida: la LLM suggerisce i ticker, yfinance li valida.

import yfinance as yf
from langchain_core.tools import tool

# wheelhouse
# ---------------------------------------------------------------------------
# KNOWLEDGE BASE — ticker noti per settore
# Usata come fallback/suggerimento per la LLM
# ---------------------------------------------------------------------------

KNOWN_TICKERS = {
    # Automotive europeo
    "volkswagen": "VOW3.DE", "vw": "VOW3.DE",
    "stellantis": "STLAM.MI", "fiat": "STLAM.MI",
    "mercedes": "MBG.DE", "mercedes-benz": "MBG.DE",
    "bmw": "BMW.DE",
    "renault": "RNO.PA",
    "porsche": "P911.DE",
    "volvo cars": "VOLCAR-B.ST",
    "traton": "TKA.DE",
    "iveco": "IVG.MI",
    "ferrari": "RACE.MI",
    # Banche europee
    "unicredit": "UCG.MI",
    "intesa": "ISP.MI", "intesa sanpaolo": "ISP.MI",
    "bnp": "BNP.PA", "bnp paribas": "BNP.PA",
    "santander": "SAN.MC",
    "deutsche bank": "DBK.DE",
    "hsbc": "HSBA.L",
    "barclays": "BARC.L",
    "societe generale": "GLE.PA",
    "ing": "INGA.AS",
    # Tech US
    "apple": "AAPL", "microsoft": "MSFT",
    "google": "GOOGL", "alphabet": "GOOGL",
    "amazon": "AMZN", "meta": "META",
    "nvidia": "NVDA", "tesla": "TSLA",
    # Energia
    "eni": "ENI.MI", "shell": "SHEL.L",
    "bp": "BP.L", "totalenergies": "TTE.PA",
    "exxon": "XOM", "chevron": "CVX",
}

# Settori predefiniti pronti all'uso
SECTOR_PRESETS = {
    "automotive europeo": {
        "VOW3.DE":     {"name": "Volkswagen Group",  "country": "DE", "segment": "mass-market"},
        "STLAM.MI":    {"name": "Stellantis",         "country": "IT", "segment": "mass-market"},
        "MBG.DE":      {"name": "Mercedes-Benz",      "country": "DE", "segment": "premium"},
        "BMW.DE":      {"name": "BMW Group",           "country": "DE", "segment": "premium"},
        "RNO.PA":      {"name": "Renault Group",       "country": "FR", "segment": "mass-market"},
        "P911.DE":     {"name": "Porsche AG",          "country": "DE", "segment": "premium"},
        "VOLCAR-B.ST": {"name": "Volvo Cars",          "country": "SE", "segment": "premium"},
        "TKA.DE":      {"name": "TRATON Group",        "country": "DE", "segment": "commercial"},
        "IVG.MI":      {"name": "Iveco Group",         "country": "IT", "segment": "commercial"},
    },
    "banche europee": {
        "UCG.MI":  {"name": "UniCredit",        "country": "IT", "segment": "banking"},
        "ISP.MI":  {"name": "Intesa Sanpaolo",  "country": "IT", "segment": "banking"},
        "BNP.PA":  {"name": "BNP Paribas",      "country": "FR", "segment": "banking"},
        "SAN.MC":  {"name": "Santander",         "country": "ES", "segment": "banking"},
        "DBK.DE":  {"name": "Deutsche Bank",    "country": "DE", "segment": "banking"},
        "HSBA.L":  {"name": "HSBC",             "country": "GB", "segment": "banking"},
        "BARC.L":  {"name": "Barclays",         "country": "GB", "segment": "banking"},
        "GLE.PA":  {"name": "Societe Generale", "country": "FR", "segment": "banking"},
        "INGA.AS": {"name": "ING Group",        "country": "NL", "segment": "banking"},
    },
    "big tech us": {
        "AAPL":  {"name": "Apple",     "country": "US", "segment": "tech"},
        "MSFT":  {"name": "Microsoft", "country": "US", "segment": "tech"},
        "GOOGL": {"name": "Alphabet",  "country": "US", "segment": "tech"},
        "AMZN":  {"name": "Amazon",   "country": "US", "segment": "tech"},
        "META":  {"name": "Meta",     "country": "US", "segment": "tech"},
        "NVDA":  {"name": "Nvidia",   "country": "US", "segment": "tech"},
    },
}


# ---------------------------------------------------------------------------
# VALIDAZIONE TICKER
# ---------------------------------------------------------------------------

def validate_ticker(symbol: str) -> dict | None:
    """
    Verifica che un ticker esista su yfinance e ritorna i suoi metadati.
    Ritorna None se il ticker non è valido.
    """
    try:
        info = yf.Ticker(symbol).info
        # yfinance ritorna un dict quasi vuoto per ticker inesistenti
        if not info or info.get("regularMarketPrice") is None and info.get("currentPrice") is None and info.get("navPrice") is None:
            # Prova a controllare almeno il nome
            if not info.get("shortName") and not info.get("longName"):
                return None
        return {
            "name":    info.get("longName") or info.get("shortName", symbol),
            "country": info.get("country", "??"),
            "segment": info.get("industry", "unknown"),
        }
    except Exception:
        return None


def resolve_tickers(raw_list: list[str]) -> dict:
    """
    Data una lista di simboli grezzi (es. ["BMW.DE", "AAPL", "pippo"]),
    valida ciascuno su yfinance e ritorna solo quelli validi nel formato
    atteso da runner.run_full_analysis().
    """
    resolved = {}
    for symbol in raw_list:
        symbol = symbol.strip().upper()
        print(f"  Validando {symbol}...")
        meta = validate_ticker(symbol)
        if meta:
            resolved[symbol] = meta
            print(f"    ✅ {meta['name']}")
        else:
            print(f"    ❌ Ticker non valido: {symbol}")
    return resolved


def resolve_from_text(text: str) -> dict:
    """
    Prova a risolvere ticker da testo libero usando la knowledge base.
    Usato come fallback quando la LLM non produce ticker diretti.
    """
    text_lower = text.lower()

    # Controlla se corrisponde a un preset di settore
    for sector_key, preset in SECTOR_PRESETS.items():
        if sector_key in text_lower:
            print(f"  Preset trovato: '{sector_key}'")
            return preset

    # Altrimenti cerca nella knowledge base per nome
    found = {}
    for name, symbol in KNOWN_TICKERS.items():
        if name in text_lower and symbol not in found:
            meta = validate_ticker(symbol)
            if meta:
                found[symbol] = meta

    return found


# ---------------------------------------------------------------------------
# TOOL PER L'AGENTE
# ---------------------------------------------------------------------------

@tool
def ticker_resolver_tool(query: str) -> str:
    """
    Risolve una query testuale in una lista di ticker finanziari validi.

    Usa questo tool quando l'utente descrive aziende o settori in linguaggio
    naturale (es. 'i principali OEM europei', 'le banche italiane',
    'Apple e Microsoft').

    Restituisce una stringa JSON con i ticker validi trovati.
    """
    import json

    print(f"\n[ticker_resolver] Query: '{query}'")

    # 1. Prova match diretto con preset di settore
    result = resolve_from_text(query)
    if result:
        print(f"  Risolti {len(result)} ticker dalla knowledge base")
        # Ritorna solo i simboli come lista — il tool run_analysis
        # costruirà il dizionario completo chiamando validate_ticker
        return json.dumps({
            "tickers": list(result.keys()),
            "names":   {k: v["name"] for k, v in result.items()},
            "source":  "knowledge_base",
        })

    # 2. Se non trova nulla, ritorna istruzioni per la LLM
    return json.dumps({
        "tickers": [],
        "names":   {},
        "source":  "not_found",
        "message": (
            f"Nessun ticker trovato per '{query}'. "
            "Fornisci i simboli di borsa direttamente "
            "(es. 'BMW.DE', 'AAPL', 'UCG.MI')."
        ),
    })


@tool
def validate_custom_tickers_tool(ticker_list: str) -> str:
    """
    Valida una lista di ticker forniti direttamente dall'utente.

    Usa questo tool quando l'utente fornisce simboli di borsa espliciti
    (es. 'BMW.DE, AAPL, UCG.MI').

    Input: stringa con ticker separati da virgola.
    Restituisce: JSON con ticker validi e non validi.
    """
    import json

    raw = [t.strip() for t in ticker_list.split(",") if t.strip()]
    print(f"\n[validate_tickers] Validando: {raw}")

    resolved = resolve_tickers(raw)
    invalid  = [t.upper() for t in raw if t.upper() not in resolved]

    return json.dumps({
        "valid":   list(resolved.keys()),
        "names":   {k: v["name"] for k, v in resolved.items()},
        "invalid": invalid,
    })
