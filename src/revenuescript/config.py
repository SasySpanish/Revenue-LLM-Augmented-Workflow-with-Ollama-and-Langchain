# config.py
# Configurazione ticker e metadati per l'analisi automotive europea

TICKERS = {
    "VOW3.DE":      {"name": "Volkswagen Group",  "country": "DE", "segment": "mass-market"},
    "STLAM.MI":     {"name": "Stellantis",         "country": "IT", "segment": "mass-market"},
    "MBG.DE":       {"name": "Mercedes-Benz",      "country": "DE", "segment": "premium"},
    "BMW.DE":       {"name": "BMW Group",           "country": "DE", "segment": "premium"},
    "RNO.PA":       {"name": "Renault Group",       "country": "FR", "segment": "mass-market"},
    "P911.DE":      {"name": "Porsche AG",          "country": "DE", "segment": "premium"},
    "VOLCAR-B.ST":  {"name": "Volvo Cars",          "country": "SE", "segment": "premium"},
    "TKA.DE":       {"name": "TRATON Group",        "country": "DE", "segment": "commercial"},
    "IVG.MI":       {"name": "Iveco Group",         "country": "IT", "segment": "commercial"},
}

# Anni da analizzare (annuale)
YEARS = 4

# Valuta di riferimento per le note (i dati rimangono nella valuta originale)
CURRENCY_NOTE = "I dati sono nella valuta originale del bilancio (EUR/SEK)"

# ---------------------------------------------------------------------------
# SOGLIE CRITICHE PER INDICATORE
#
# Ogni entry contiene:
#   "fixed"     → soglia fissa standard di riferimento settoriale
#   "direction" → "above_good"  = valori SOPRA la soglia sono positivi
#                 "below_good"  = valori SOTTO la soglia sono positivi
#   "label"     → etichetta breve mostrata nel grafico
#   "note"      → spiegazione per il README
# ---------------------------------------------------------------------------
THRESHOLDS = {
    "EBIT Margin (%)": {
        "fixed":     5.0,
        "direction": "above_good",
        "label":     "Soglia min. 5%",
        "note": (
            "Nel settore automotive un EBIT Margin superiore al 5% è considerato "
            "la soglia minima di salute operativa. Sotto questa soglia il core "
            "business fatica a generare redditività sufficiente a coprire capex e "
            "oneri finanziari tipici del settore."
        ),
    },
    "ROE (%)": {
        "fixed":     10.0,
        "direction": "above_good",
        "label":     "Soglia min. 10%",
        "note": (
            "Un ROE del 10% è comunemente usato come benchmark minimo per "
            "remunerare adeguatamente il capitale proprio degli azionisti. "
            "Valori inferiori indicano che l'azienda non genera valore per chi "
            "ha investito nel capitale."
        ),
    },
    "ROI / ROCE (%)": {
        "fixed":     8.0,
        "direction": "above_good",
        "label":     "Soglia min. 8%",
        "note": (
            "Il ROCE (Return on Capital Employed) dovrebbe superare il costo "
            "medio del capitale (WACC), stimato intorno al 7-9% per un OEM "
            "automobilistico europeo. Sotto l'8% l'azienda distrugge valore "
            "economico rispetto al capitale investito."
        ),
    },
    "Net Margin (%)": {
        "fixed":     3.0,
        "direction": "above_good",
        "label":     "Soglia min. 3%",
        "note": (
            "Nel settore automotive i margini netti sono strutturalmente compressi. "
            "Una soglia del 3% rappresenta il livello minimo al di sopra del quale "
            "si considera che l'azienda stia generando profitto netto in modo "
            "sostenibile dopo tasse e oneri finanziari."
        ),
    },
    "Debt/Equity": {
        "fixed":     2.0,
        "direction": "below_good",
        "label":     "Soglia max. 2x",
        "note": (
            "Un rapporto Debt/Equity superiore a 2 segnala una leva finanziaria "
            "elevata. Nel settore automotive, dove i cicli di investimento sono "
            "pesanti, valori oltre questa soglia aumentano significativamente il "
            "rischio di insolvenza in fasi di contrazione dei ricavi."
        ),
    },
    "Current Ratio": {
        "fixed":     1.0,
        "direction": "above_good",
        "label":     "Soglia min. 1x",
        "note": (
            "Un Current Ratio inferiore a 1 significa che le passività a breve "
            "termine superano le attività correnti: l'azienda potrebbe non essere "
            "in grado di far fronte agli impegni finanziari nel breve periodo "
            "senza ricorrere a nuovi finanziamenti."
        ),
    },
}

