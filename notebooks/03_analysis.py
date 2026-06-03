import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path

PROCESSED_DIR = Path(__file__).parent.parent / "data" / "processed"

df = pd.read_csv(PROCESSED_DIR / "cleaned_data.csv", parse_dates=["date"])
df = df.set_index("date")

# Tariff period boundary: April 2025 (Trump broad tariffs announced)
TARIFF_START = pd.Timestamp("2025-04-01")
df["tariff_period"] = df.index.map(lambda d: "post_tariff" if d >= TARIFF_START else "pre_tariff")

METRICS = {
    "cpi_food":           "cpi_food",
    "cpi_apparel":        "cpi_apparel",
    "consumer_sentiment": "consumer_sentiment",
    "wmt_adj_close":      "wmt_adj_close",
    "dg_adj_close":       "dg_adj_close",
}

# ── 1. Averages by period ──────────────────────────────────────────────────────

avg = df.groupby("tariff_period")[list(METRICS.values())].mean()
pre  = avg.loc["pre_tariff"]
post = avg.loc["post_tariff"]

# ── 2. % change pre → post ────────────────────────────────────────────────────

pct_change = ((post - pre) / pre * 100).rename("pct_change")

# ── 3. Which retailer performed better post-tariff? ───────────────────────────

wmt_pct = pct_change["wmt_adj_close"]
dg_pct  = pct_change["dg_adj_close"]
better_retailer = "WMT" if wmt_pct > dg_pct else "DG"

# ── 4. Month with biggest single-month food CPI jump ─────────────────────────

biggest_jump_idx = df["cpi_food_mom_pct"].idxmax()
biggest_jump_val = df.loc[biggest_jump_idx, "cpi_food_mom_pct"]

# ── 5. Print summary ──────────────────────────────────────────────────────────

DISPLAY = {
    "cpi_food":           "CPI Food",
    "cpi_apparel":        "CPI Apparel",
    "consumer_sentiment": "Consumer Sentiment",
    "wmt_adj_close":      "WMT Adj Close ($)",
    "dg_adj_close":       "DG Adj Close ($)",
}

print("=" * 62)
print(f"{'TARIFF IMPACT SUMMARY':^62}")
print(f"  Pre-tariff: Jan 2022 – Mar 2025  |  Post-tariff: Apr–Dec 2025")
print("=" * 62)
print(f"{'Metric':<24} {'Pre-Tariff':>10} {'Post-Tariff':>11} {'% Change':>10}")
print("-" * 62)

rows = []
for col, label in DISPLAY.items():
    pre_val  = pre[col]
    post_val = post[col]
    chg      = pct_change[col]
    arrow    = "▲" if chg > 0 else "▼"
    print(f"{label:<24} {pre_val:>10.2f} {post_val:>11.2f} {arrow}{abs(chg):>8.1f}%")
    rows.append({
        "metric":       label,
        "pre_tariff":   round(pre_val, 2),
        "post_tariff":  round(post_val, 2),
        "pct_change":   round(chg, 2),
    })

print("-" * 62)
print(f"\nBetter post-tariff retailer : {better_retailer}")
print(f"  WMT avg change            : {'▲' if wmt_pct > 0 else '▼'}{abs(wmt_pct):.1f}%")
print(f"  DG  avg change            : {'▲' if dg_pct > 0 else '▼'}{abs(dg_pct):.1f}%")
print(f"\nBiggest food CPI monthly jump: {biggest_jump_idx.strftime('%b %Y')} "
      f"(+{biggest_jump_val:.2f}%)")
print("=" * 62)

# ── 6. Save summary CSV ───────────────────────────────────────────────────────

summary_df = pd.DataFrame(rows)
summary_df.to_csv(PROCESSED_DIR / "insights_summary.csv", index=False)
print(f"\nSaved summary -> {PROCESSED_DIR / 'insights_summary.csv'}")

# ── 7. Visualization: WMT vs DG over time ────────────────────────────────────

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
fig.suptitle("WMT vs DG Stock Performance\nPre- vs Post-Tariff (April 2025)",
             fontsize=13, fontweight="bold")

# Normalize to 100 at start for apples-to-apples comparison
wmt_norm = df["wmt_adj_close"] / df["wmt_adj_close"].iloc[0] * 100
dg_norm  = df["dg_adj_close"]  / df["dg_adj_close"].iloc[0]  * 100

# Top panel: normalized performance
ax1.plot(df.index, wmt_norm, color="#0057e7", linewidth=2, label="WMT (indexed)")
ax1.plot(df.index, dg_norm,  color="#d62728", linewidth=2, label="DG (indexed)")
ax1.axvline(TARIFF_START, color="black", linestyle="--", linewidth=1.2, label="Tariff start (Apr 2025)")
ax1.axvspan(TARIFF_START, df.index[-1], alpha=0.06, color="orange", label="Post-tariff period")
ax1.set_ylabel("Indexed Price (Jan 2022 = 100)", fontsize=9)
ax1.set_title("Relative Performance (both indexed to 100 at Jan 2022)", fontsize=10, loc="left")
ax1.legend(fontsize=9)
ax1.grid(axis="y", linestyle="--", alpha=0.4)
ax1.spines[["top", "right"]].set_visible(False)

# Bottom panel: actual adjusted close prices
ax2.plot(df.index, df["wmt_adj_close"], color="#0057e7", linewidth=2, label="WMT adj close")
ax2.plot(df.index, df["dg_adj_close"],  color="#d62728", linewidth=2, label="DG adj close")
ax2.axvline(TARIFF_START, color="black", linestyle="--", linewidth=1.2)
ax2.axvspan(TARIFF_START, df.index[-1], alpha=0.06, color="orange")
ax2.set_ylabel("Adjusted Close Price ($)", fontsize=9)
ax2.set_title("Actual Adjusted Close Prices", fontsize=10, loc="left")
ax2.legend(fontsize=9)
ax2.grid(axis="y", linestyle="--", alpha=0.4)
ax2.spines[["top", "right"]].set_visible(False)

ax2.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 4, 7, 10]))
ax2.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha="right")

plt.tight_layout()

out_path = PROCESSED_DIR / "retailer_comparison.png"
plt.savefig(out_path, dpi=150, bbox_inches="tight")
print(f"Saved chart -> {out_path}")
plt.show()
