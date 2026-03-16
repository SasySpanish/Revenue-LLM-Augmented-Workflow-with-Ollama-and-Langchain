# visualizer.py
# Genera grafici matplotlib per ogni indicatore (PNG + PDF riepilogativo)

import os
import math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.backends.backend_pdf import PdfPages
import pandas as pd
import numpy as np

from config import TICKERS, THRESHOLDS

# ---------------------------------------------------------------------------
# PALETTE MONOCROMATICA BLU automotive
# ---------------------------------------------------------------------------

COLORS = [
    "#03045e", "#023e8a", "#0077b6", "#0096c7", "#00b4d8",
    "#48cae4", "#90e0ef", "#ade8f4", "#caf0f8", "#e0f7fa",
]

# Colori soglia
COLOR_FIXED    = "#e63946"   # rosso — soglia fissa standard
COLOR_MEDIAN   = "#f4a261"   # arancio — mediana del gruppo
COLOR_ABOVE    = "#03045e"   # barra "sana"
COLOR_BELOW    = "#90e0ef"   # barra sotto soglia (più chiaro = attenzione)

plt.rcParams.update({
    "font.family":       "DejaVu Sans",
    "font.size":         9,
    "axes.titlesize":    11,
    "axes.titleweight":  "bold",
    "axes.spines.top":   False,
    "axes.spines.right": False,
    "axes.grid":         True,
    "grid.alpha":        0.3,
    "grid.linestyle":    "--",
    "figure.dpi":        150,
})

OUTPUT_DIR = "output"


# ---------------------------------------------------------------------------
# UTILS
# ---------------------------------------------------------------------------

def _clean_name(name: str) -> str:
    replacements = {
        "Volkswagen Group": "VW Group",
        "Mercedes-Benz":    "Mercedes",
        "Renault Group":    "Renault",
        "Volvo Cars":       "Volvo Cars",
        "TRATON Group":     "TRATON",
        "Iveco Group":      "Iveco",
        "Porsche AG":       "Porsche",
        "BMW Group":        "BMW",
        "Stellantis":       "Stellantis",
    }
    return replacements.get(name, name)


def _bar_colors_with_threshold(values: pd.Series, indicator: str,
                                median_val: float) -> list:
    """
    Assegna colore a ogni barra in base alla soglia fissa:
    - direction=above_good: barra scura se sopra soglia, chiara se sotto
    - direction=below_good: barra scura se sotto soglia, chiara se sopra
    Se l'indicatore non ha soglia, usa la palette standard.
    """
    if indicator not in THRESHOLDS:
        return [COLORS[i % len(COLORS)] for i in range(len(values))]

    thresh = THRESHOLDS[indicator]
    fixed  = thresh["fixed"]
    direction = thresh["direction"]
    colors = []
    for val in values:
        if math.isnan(val):
            colors.append("#cccccc")
        elif direction == "above_good":
            colors.append(COLOR_ABOVE if val >= fixed else COLOR_BELOW)
        else:  # below_good
            colors.append(COLOR_ABOVE if val <= fixed else COLOR_BELOW)
    return colors


# ---------------------------------------------------------------------------
# BAR CHART CON SOGLIE
# ---------------------------------------------------------------------------

def plot_bar_comparison(df_last: pd.DataFrame, indicator: str,
                        ax: plt.Axes = None, save_path: str = None):
    """
    Bar chart orizzontale con:
    - linea rossa = soglia fissa standard
    - linea arancione = mediana del gruppo
    - colore barra = verde scuro (OK) / azzurro chiaro (attenzione)
    """
    series = df_last[indicator].dropna().sort_values(ascending=True)
    if series.empty:
        return

    has_threshold = indicator in THRESHOLDS
    median_val = series.median()

    standalone = ax is None
    if standalone:
        fig, ax = plt.subplots(figsize=(9, 5))

    short_names = [_clean_name(c) for c in series.index]
    bar_colors  = _bar_colors_with_threshold(series.values, indicator, median_val)

    bars = ax.barh(short_names, series.values,
                   color=bar_colors, edgecolor="white", linewidth=0.5)

    # Etichette valore
    for bar, val in zip(bars, series.values):
        ax.text(
            val + abs(series.values).max() * 0.01 if val >= 0
            else val - abs(series.values).max() * 0.01,
            bar.get_y() + bar.get_height() / 2,
            f"{val:.1f}",
            va="center",
            ha="left" if val >= 0 else "right",
            fontsize=7.5,
        )

    # Linea soglia fissa
    legend_patches = []
    if has_threshold:
        fixed = THRESHOLDS[indicator]["fixed"]
        label = THRESHOLDS[indicator]["label"]
        ax.axvline(fixed, color=COLOR_FIXED, linewidth=1.8,
                   linestyle="--", zorder=5, label=label)
        legend_patches.append(
            mpatches.Patch(color=COLOR_FIXED, label=f"Soglia fissa: {fixed}")
        )

    # Linea mediana gruppo
    ax.axvline(median_val, color=COLOR_MEDIAN, linewidth=1.4,
               linestyle=":", zorder=4)
    legend_patches.append(
        mpatches.Patch(color=COLOR_MEDIAN,
                       label=f"Mediana gruppo: {median_val:.1f}")
    )

    if legend_patches:
        ax.legend(handles=legend_patches, fontsize=7.5,
                  loc="lower right", framealpha=0.8)

    ax.set_title(indicator)
    ax.set_xlabel(indicator)
    ax.axvline(0, color="black", linewidth=0.7)

    if standalone:
        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, bbox_inches="tight")
            plt.close(fig)


# ---------------------------------------------------------------------------
# LINE CHART TREND (matplotlib — usato solo nel PDF)
# ---------------------------------------------------------------------------

def plot_trend_lines(trend_df: pd.DataFrame, indicator: str,
                     ax: plt.Axes = None, save_path: str = None):
    if trend_df.empty:
        return

    standalone = ax is None
    if standalone:
        fig, ax = plt.subplots(figsize=(9, 5))

    for i, company in enumerate(trend_df.index.tolist()):
        values = trend_df.loc[company]
        ax.plot(
            trend_df.columns.tolist(), values,
            marker="o", markersize=5, linewidth=2,
            color=COLORS[i % len(COLORS)],
            label=_clean_name(company),
        )

    # Soglie anche nei trend
    if indicator in THRESHOLDS:
        fixed = THRESHOLDS[indicator]["fixed"]
        ax.axhline(fixed, color=COLOR_FIXED, linewidth=1.6,
                   linestyle="--", label=THRESHOLDS[indicator]["label"])

    ax.set_title(f"Trend — {indicator}")
    ax.set_xlabel("Anno")
    ax.set_ylabel(indicator)
    ax.set_xticks(trend_df.columns.tolist())
    ax.legend(fontsize=7.5, loc="best", framealpha=0.7)

    if standalone:
        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, bbox_inches="tight")
            plt.close(fig)


# ---------------------------------------------------------------------------
# HEATMAP CAGR
# ---------------------------------------------------------------------------

def plot_cagr_heatmap(cagr_df: pd.DataFrame,
                      ax: plt.Axes = None, save_path: str = None):
    if cagr_df.empty:
        return

    standalone = ax is None
    if standalone:
        fig, ax = plt.subplots(figsize=(10, 5))

    short_index = [_clean_name(c) for c in cagr_df.index]
    data = cagr_df.values.astype(float)
    valid = data[~np.isnan(data)]
    vmax  = max(abs(valid).max(), 1) if len(valid) else 1

    im = ax.imshow(data, cmap="RdYlGn", aspect="auto",
                   vmin=-vmax, vmax=vmax)

    ax.set_xticks(range(len(cagr_df.columns)))
    ax.set_xticklabels(cagr_df.columns, rotation=25, ha="right", fontsize=8)
    ax.set_yticks(range(len(cagr_df.index)))
    ax.set_yticklabels(short_index, fontsize=8)

    for i in range(len(cagr_df.index)):
        for j in range(len(cagr_df.columns)):
            val = data[i, j]
            if not math.isnan(val):
                ax.text(j, i, f"{val:.1f}%",
                        ha="center", va="center", fontsize=7.5,
                        color="black" if abs(val) < vmax * 0.6 else "white")

    plt.colorbar(im, ax=ax, label="CAGR (%)", shrink=0.8)
    ax.set_title("CAGR per Azienda e Indicatore")

    if standalone:
        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, bbox_inches="tight")
            plt.close(fig)


# ---------------------------------------------------------------------------
# BUBBLE CHART MULTIPLI DI MERCATO
# ---------------------------------------------------------------------------

def plot_market_multiples(market_df: pd.DataFrame,
                          ax: plt.Axes = None, save_path: str = None):
    needed = ["EV/EBITDA", "P/E (Trailing)", "Market Cap (M)"]
    if market_df.empty or not all(c in market_df.columns for c in needed):
        return

    df = market_df[needed].dropna()
    if df.empty:
        return

    standalone = ax is None
    if standalone:
        fig, ax = plt.subplots(figsize=(9, 6))

    sizes = (df["Market Cap (M)"] / df["Market Cap (M)"].max()) * 2000 + 100

    for i, (company, row) in enumerate(df.iterrows()):
        ax.scatter(
            row["EV/EBITDA"], row["P/E (Trailing)"],
            s=sizes[company], color=COLORS[i % len(COLORS)],
            alpha=0.80, edgecolors="white", linewidth=0.8, zorder=3,
        )
        ax.annotate(
            _clean_name(company),
            (row["EV/EBITDA"], row["P/E (Trailing)"]),
            textcoords="offset points", xytext=(8, 4), fontsize=8,
        )

    ax.axhline(df["P/E (Trailing)"].median(), color="#aaa",
               linestyle="--", linewidth=0.8, label="Mediana P/E")
    ax.axvline(df["EV/EBITDA"].median(), color="#aaa",
               linestyle=":",  linewidth=0.8, label="Mediana EV/EBITDA")
    ax.set_xlabel("EV / EBITDA")
    ax.set_ylabel("P/E (Trailing)")
    ax.set_title("Multipli di Mercato\n(dimensione bolla = Market Cap)")
    ax.legend(fontsize=7.5)

    if standalone:
        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, bbox_inches="tight")
            plt.close(fig)


def plot_market_bars(market_df: pd.DataFrame, save_dir: str):
    multiples = {
        "P/E (Trailing)":   "P/E Ratio (Trailing 12M)",
        "EV/EBITDA":        "EV / EBITDA",
        "Price/Book (P/B)": "Price / Book Value",
        "Market Cap (M)":   "Market Capitalisation (M — valuta locale)",
    }
    for col, title in multiples.items():
        if col not in market_df.columns:
            continue
        series = market_df[col].dropna().sort_values(ascending=True)
        if series.empty:
            continue

        fig, ax = plt.subplots(figsize=(9, 4.5))
        short_names = [_clean_name(c) for c in series.index]
        colors = [COLORS[i % len(COLORS)] for i in range(len(series))]

        bars = ax.barh(short_names, series.values,
                       color=colors, edgecolor="white", linewidth=0.5)
        for bar, val in zip(bars, series.values):
            ax.text(
                val + abs(val) * 0.01,
                bar.get_y() + bar.get_height() / 2,
                f"{val:.1f}x" if col != "Market Cap (M)" else f"{val:,.0f}M",
                va="center", ha="left", fontsize=8,
            )
        ax.set_title(title)
        ax.axvline(0, color="black", linewidth=0.7)
        plt.tight_layout()

        safe = col.replace("/", "_").replace(" ", "_").replace("(","").replace(")","")
        path = os.path.join(save_dir, f"market_{safe}.png")
        plt.savefig(path, bbox_inches="tight")
        plt.close(fig)
        print(f"    {path}")


# ---------------------------------------------------------------------------
# EXPORT PRINCIPALE
# ---------------------------------------------------------------------------

def generate_all_charts(results: dict, market_df: pd.DataFrame,
                        trends: dict, cagr_df: pd.DataFrame):
    charts_dir = os.path.join(OUTPUT_DIR, "charts")
    os.makedirs(charts_dir, exist_ok=True)

    # Costruisci df confronto ultimo anno
    comparison_rows = []
    for symbol, df in results.items():
        if df.empty:
            continue
        last_year = df.columns[0]
        row = df[last_year].copy()
        try:
            row.name = TICKERS[symbol]["name"]
        except KeyError:
            row.name = symbol
        comparison_rows.append(row)
    df_last = pd.DataFrame(comparison_rows) if comparison_rows else pd.DataFrame()

    BAR_INDICATORS = [
        "Revenue (M)", "EBIT (M)", "EBITDA (M)", "Net Income (M)",
        "Gross Margin (%)", "EBIT Margin (%)", "EBITDA Margin (%)", "Net Margin (%)",
        "ROE (%)", "ROA (%)", "ROI / ROCE (%)",
        "Current Ratio", "Quick Ratio", "Debt/Equity", "Interest Coverage",
    ]
    TREND_INDICATORS = [
        "Revenue (M)", "EBIT Margin (%)", "EBITDA Margin (%)",
        "ROE (%)", "Net Margin (%)", "Debt/Equity",
    ]

    all_figures = []

    # 1. Bar chart con soglie
    print("\n  Generando bar chart confronto (con soglie)...")
    for indicator in BAR_INDICATORS:
        if df_last.empty or indicator not in df_last.columns:
            continue
        fig, ax = plt.subplots(figsize=(9, 5))
        plot_bar_comparison(df_last, indicator, ax=ax)
        plt.tight_layout()
        safe = (indicator.replace("/", "_").replace(" ", "_")
                         .replace("(%)", "pct").replace("(M)", "M"))
        path = os.path.join(charts_dir, f"bar_{safe}.png")
        plt.savefig(path, bbox_inches="tight")
        all_figures.append(fig)
        print(f"    {path}")

    # 2. Trend line chart (matplotlib, solo per PDF)
    print("\n  Generando trend line chart (per PDF)...")
    for indicator in TREND_INDICATORS:
        if indicator not in trends:
            continue
        fig, ax = plt.subplots(figsize=(9, 5))
        plot_trend_lines(trends[indicator], indicator, ax=ax)
        plt.tight_layout()
        safe = (indicator.replace("/", "_").replace(" ", "_")
                         .replace("(%)", "pct").replace("(M)", "M"))
        path = os.path.join(charts_dir, f"trend_{safe}.png")
        plt.savefig(path, bbox_inches="tight")
        all_figures.append(fig)
        print(f"    {path}")

    # 3. Heatmap CAGR
    print("\n  Generando heatmap CAGR...")
    if not cagr_df.empty:
        fig, ax = plt.subplots(figsize=(11, 5))
        plot_cagr_heatmap(cagr_df, ax=ax)
        plt.tight_layout()
        path = os.path.join(charts_dir, "cagr_heatmap.png")
        plt.savefig(path, bbox_inches="tight")
        all_figures.append(fig)
        print(f"    {path}")

    # 4. Multipli di mercato
    if not market_df.empty:
        print("\n  Generando grafici multipli di mercato...")
        fig, ax = plt.subplots(figsize=(9, 6))
        plot_market_multiples(market_df, ax=ax)
        plt.tight_layout()
        path = os.path.join(charts_dir, "market_bubble.png")
        plt.savefig(path, bbox_inches="tight")
        all_figures.append(fig)
        print(f"    {path}")
        plot_market_bars(market_df, charts_dir)

    # 5. PDF riepilogativo
    pdf_path = os.path.join(OUTPUT_DIR, "automotive_analysis_charts.pdf")
    print(f"\n  Generando PDF riepilogativo: {pdf_path}")
    with PdfPages(pdf_path) as pdf:
        fig_title, ax_t = plt.subplots(figsize=(11, 4))
        ax_t.axis("off")
        ax_t.text(0.5, 0.65, "Automotive Europe",
                  ha="center", va="center", fontsize=28, fontweight="bold",
                  color="#03045e")
        ax_t.text(0.5, 0.42, "Analisi Comparativa Indicatori Finanziari",
                  ha="center", va="center", fontsize=16, color="#0077b6")
        ax_t.text(0.5, 0.22,
                  "VW Group · Stellantis · Mercedes-Benz · BMW · Renault\n"
                  "Porsche AG · Volvo Cars · TRATON · Iveco",
                  ha="center", va="center", fontsize=10, color="#555")
        pdf.savefig(fig_title, bbox_inches="tight")
        plt.close(fig_title)
        for fig in all_figures:
            pdf.savefig(fig, bbox_inches="tight")
            plt.close(fig)

    print(f"  ✅ PDF salvato: {pdf_path}")
    print(f"  ✅ PNG salvati in: {charts_dir}/")
