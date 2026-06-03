import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path

RAW_DIR = Path(__file__).parent.parent / "data" / "raw"

food = pd.read_csv(RAW_DIR / "cpi_food.csv", parse_dates=["date"])
apparel = pd.read_csv(RAW_DIR / "cpi_apparel.csv", parse_dates=["date"])
sentiment = pd.read_csv(RAW_DIR / "consumer_sentiment.csv", parse_dates=["date"])

fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=True)
fig.suptitle("U.S. Consumer Indicators (Jan 2022 – Dec 2025)", fontsize=14, fontweight="bold", y=0.98)

datasets = [
    (axes[0], food,      "CPI: Food (CPIUFDNS)",      "#d62728", "Index (1982-84=100)"),
    (axes[1], apparel,   "CPI: Apparel (CPIAPPNS)",   "#1f77b4", "Index (1982-84=100)"),
    (axes[2], sentiment, "Consumer Sentiment (UMCSENT)", "#2ca02c", "Index"),
]

for ax, df, title, color, ylabel in datasets:
    ax.plot(df["date"], df["value"], color=color, linewidth=1.8)
    ax.fill_between(df["date"], df["value"], alpha=0.1, color=color)
    ax.set_title(title, fontsize=11, loc="left")
    ax.set_ylabel(ylabel, fontsize=9)
    ax.grid(axis="y", linestyle="--", alpha=0.5)
    ax.spines[["top", "right"]].set_visible(False)

axes[2].xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 7]))
axes[2].xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
plt.setp(axes[2].xaxis.get_majorticklabels(), rotation=45, ha="right")

plt.tight_layout()

out_path = Path(__file__).parent.parent / "data" / "processed" / "consumer_indicators.png"
plt.savefig(out_path, dpi=150, bbox_inches="tight")
print(f"Chart saved -> {out_path}")
plt.show()
