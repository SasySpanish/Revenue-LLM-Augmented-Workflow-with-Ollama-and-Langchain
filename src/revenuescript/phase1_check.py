# phase1_check.py  (va in C:/Users/Utente/Desktop/revenuescript/)
#
# Script di verifica Fase 1.
# Esegui con:  python phase1_check.py
# Controlla:
#   1. Import delle funzioni wheelhouse
#   2. runner.run_full_analysis() con 2 ticker di test
#   3. Connessione Ollama + risposta base di qwen2.5:3b
#   4. Tool use minimo con LangChain + Ollama

import sys
import importlib

SEP = "=" * 55


# ---------------------------------------------------------------------------
# CHECK 1 — Import moduli wheelhouse
# ---------------------------------------------------------------------------
print(f"\n{SEP}")
print("CHECK 1 — Import moduli wheelhouse")
print(SEP)

modules = [
    "config", "fetcher", "indicators",
    "market_data", "trend_analysis",
    "trend_dashboard", "visualizer", "runner",
]
for mod in modules:
    try:
        importlib.import_module(mod)
        print(f"  ✅ {mod}")
    except Exception as e:
        print(f"  ❌ {mod}: {e}")


# ---------------------------------------------------------------------------
# CHECK 2 — runner.run_full_analysis() con 2 ticker
# ---------------------------------------------------------------------------
print(f"\n{SEP}")
print("CHECK 2 — runner.run_full_analysis() (2 ticker di test)")
print(SEP)

try:
    from runner import run_full_analysis, build_comparison_table

    TEST_TICKERS = {
        "BMW.DE":   {"name": "BMW Group",   "country": "DE", "segment": "premium"},
        "MBG.DE":   {"name": "Mercedes-Benz","country": "DE", "segment": "premium"},
    }

    result = run_full_analysis(TEST_TICKERS, output_dir="output_check")

    print(f"  Ticker analizzati : {len(result['results'])}")
    print(f"  Indicatori trend  : {len(result['trends'])}")
    print(f"  Errori            : {result['errors']}")

    comp = build_comparison_table(result["results"], TEST_TICKERS)
    if not comp.empty:
        print("\n  Tabella confronto (ultime 3 colonne):")
        print(comp.iloc[:, :3].to_string())
        print("  ✅ runner OK")
    else:
        print("  ⚠️  Tabella confronto vuota — controlla i dati")

except Exception as e:
    print(f"  ❌ runner fallito: {e}")
    import traceback; traceback.print_exc()


# ---------------------------------------------------------------------------
# CHECK 3 — Connessione Ollama
# ---------------------------------------------------------------------------
print(f"\n{SEP}")
print("CHECK 3 — Connessione Ollama (qwen2.5:3b)")
print(SEP)

try:
    from langchain_ollama import ChatOllama

    llm = ChatOllama(model="qwen2.5:3b", temperature=0)
    response = llm.invoke("Reply with exactly: OLLAMA_OK")
    text = response.content.strip()
    print(f"  Risposta: {text}")
    if "OLLAMA_OK" in text:
        print("  ✅ Ollama risponde correttamente")
    else:
        print("  ⚠️  Ollama risponde ma output inatteso — modello caricato?")
except Exception as e:
    print(f"  ❌ Ollama non raggiungibile: {e}")
    print("     → Assicurati che Ollama sia in esecuzione (ollama serve)")


# ---------------------------------------------------------------------------
# CHECK 4 — Tool use LangGraph + Ollama
# ---------------------------------------------------------------------------
print(f"\n{SEP}")
print("CHECK 4 — Tool use LangGraph + Ollama")
print(SEP)

try:
    from langchain_ollama import ChatOllama
    from langchain_core.tools import tool
    from langgraph.prebuilt import create_react_agent

    @tool
    def dummy_tool(query: str) -> str:
        """Test tool: restituisce sempre TOOL_OK."""
        return "TOOL_OK"

    llm   = ChatOllama(model="qwen2.5:3b", temperature=0)
    agent = create_react_agent(llm, tools=[dummy_tool])

    result = agent.invoke({
        "messages": [
            ("human", "Call the dummy_tool with query='test' and return its output.")
        ]
    })

    # L'ultimo messaggio è la risposta finale dell'agente
    answer = result["messages"][-1].content
    print(f"  Risposta agente: {answer}")

    if "TOOL_OK" in answer:
        print("  ✅ Tool use funziona")
    else:
        print("  ⚠️  Il modello non ha chiamato il tool")
        print("     → Normale su modelli piccoli, si gestisce in Fase 3")

except Exception as e:
    print(f"  ❌ Tool use fallito: {e}")
    import traceback; traceback.print_exc()

# ---------------------------------------------------------------------------
# RIEPILOGO
# ---------------------------------------------------------------------------
print(f"\n{SEP}")
print("FASE 1 completata — controlla eventuali ❌ o ⚠️ sopra")
print("Se tutti i check sono ✅ sei pronto per la Fase 2.")
print(SEP)
