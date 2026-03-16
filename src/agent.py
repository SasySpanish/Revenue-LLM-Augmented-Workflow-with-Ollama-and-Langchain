# agent.py  (va in wheelhouse-agent/)
# Agente principale: riceve un prompt in linguaggio naturale,
# decide autonomamente quali tool chiamare e in quale ordine,
# e produce i report finali. output

import sys
import os

# ---------------------------------------------------------------------------
# PATH — permette di importare i moduli di wheelhouse
# ---------------------------------------------------------------------------

WHEELHOUSE_PATH = r"C:/Users/Utente/Desktop/revenuescript"
if WHEELHOUSE_PATH not in sys.path:
    sys.path.insert(0, WHEELHOUSE_PATH)

# ---------------------------------------------------------------------------
# IMPORT
# ---------------------------------------------------------------------------

from langchain_ollama import ChatOllama
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate
from langchain.agents import create_agent

from ticker_resolver  import ticker_resolver_tool, validate_custom_tickers_tool
from tool_analysis    import run_analysis_tool
from report_generator import generate_report_tool


# ---------------------------------------------------------------------------
# SYSTEM PROMPT DELL'AGENTE
# ---------------------------------------------------------------------------

AGENT_SYSTEM_PROMPT = """You are a financial analysis agent. Your job is to:
1. Understand what companies or sectors the user wants to analyse
2. Resolve company names to valid stock tickers
3. Run the full financial analysis
4. Generate a complete report with charts and commentary

## Tools available
- ticker_resolver_tool: use when the user describes companies or sectors 
  in natural language (e.g. "European banks", "top automotive OEMs")
- validate_custom_tickers_tool: use when the user provides explicit ticker 
  symbols (e.g. "BMW.DE, AAPL, UCG.MI")
- run_analysis_tool: ALWAYS call this after resolving tickers. 
  Pass the full JSON output from the resolver tool as input.
- generate_report_tool: ALWAYS call this last. 
  Pass the full JSON output from run_analysis_tool as input.

## Rules
- Always validate tickers before running the analysis
- Always run the analysis before generating the report
- If a ticker is not found, inform the user and ask for clarification
- Never skip the report generation step
- Respond in the same language the user used

## Workflow
ticker_resolver_tool OR validate_custom_tickers_tool
    → run_analysis_tool
        → generate_report_tool
            → tell the user where the files are saved
"""


# ---------------------------------------------------------------------------
# SETUP AGENTE
# ---------------------------------------------------------------------------

def build_agent():
    llm = ChatOllama(
        model="qwen2.5:3b",
        temperature=0,
        num_ctx=8192,
    )

    tools = [
        ticker_resolver_tool,
        validate_custom_tickers_tool,
        run_analysis_tool,
        generate_report_tool,
    ]

    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=AGENT_SYSTEM_PROMPT,
    )
    return agent

# ---------------------------------------------------------------------------
# INTERFACCIA A TERMINALE
# ---------------------------------------------------------------------------

def run_interactive():
    print("\n" + "=" * 60)
    print("  WHEELHOUSE AGENT — Financial Analysis")
    print("=" * 60)
    print("  Modello : qwen2.5:3b via Ollama")
    print("  Output  : output_agent/")
    print("=" * 60)
    print("\nEsempi di prompt:")
    print("  → Analyse the top European automotive OEMs")
    print("  → Compare BMW.DE and MBG.DE")
    print("  → Analyse Apple, Microsoft and Nvidia")
    print("\nDigita 'exit' per uscire.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nUscita.")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit", "q"):
            print("Uscita.")
            break

        print("\n[agent] Elaborazione in corso...\n")

        try:
            run_pipeline(user_input)
        except Exception as e:
            print(f"\n[agent] Errore: {e}\n")
            import traceback
            traceback.print_exc()

        print("-" * 60)


def run_pipeline(user_input: str):
    """
    Pipeline esplicita: resolver → analisi → report.
    Il flusso è gestito in Python, non delegato al modello.
    """
    import json

    # Step 1 — Risolvi ticker
    print("[1/3] Risoluzione ticker...")

    # Prova prima il resolver testuale
    resolver_result = ticker_resolver_tool.invoke({"query": user_input})
    data = json.loads(resolver_result)

    # Se non trova nulla prova a trattare l'input come lista di ticker diretti
    if not data.get("tickers"):
        print("  Nessun preset trovato, provo come ticker diretti...")
        resolver_result = validate_custom_tickers_tool.invoke(
            {"ticker_list": user_input}
        )
        data = json.loads(resolver_result)

    tickers = data.get("tickers") or data.get("valid", [])
    if not tickers:
        print(f"\n[agent] Nessun ticker trovato per: '{user_input}'")
        print("  Prova con ticker espliciti, es: BMW.DE, MBG.DE, UCG.MI\n")
        return

    print(f"  Ticker risolti: {tickers}")

    # Step 2 — Analisi
    print("\n[2/3] Avvio analisi finanziaria...")
    analysis_result = run_analysis_tool.invoke(
        {"resolver_output": resolver_result}
    )
    analysis_data = json.loads(analysis_result)

    if analysis_data.get("status") != "success":
        print(f"\n[agent] Analisi fallita: {analysis_data.get('error')}\n")
        return

    output_dir = analysis_data.get("output_dir")
    print(f"  Analisi completata. Output in: {output_dir}")

    # Step 3 — Report
    print("\n[3/3] Generazione report...")
    report_result = generate_report_tool.invoke(
        {"analysis_output": analysis_result}
    )
    report_data = json.loads(report_result)

    if report_data.get("status") != "success":
        print(f"\n[agent] Report fallito: {report_data.get('error')}\n")
        return

    files = report_data.get("files", {})
    print("\n✅ Report completato!")
    print(f"   HTML      : {files.get('html')}")
    print(f"   PDF       : {files.get('pdf')}")
    print(f"   Dashboard : {files.get('dashboard')}")
    print()

# ---------------------------------------------------------------------------
# SINGLE SHOT — per uso programmatico
# ---------------------------------------------------------------------------

def run_once(prompt: str) -> dict:
    agent  = build_agent()
    result = agent.invoke({"messages": [("human", prompt)]})
    return result


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Se viene passato un argomento da riga di comando usalo come prompt
    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
        print(f"\n[agent] Prompt: {prompt}\n")
        result = run_once(prompt)
        messages = result.get("messages", [])
        if messages:
            print(f"\nAgent: {messages[-1].content}\n")
    else:
        # Altrimenti avvia il loop interattivo
        run_interactive()