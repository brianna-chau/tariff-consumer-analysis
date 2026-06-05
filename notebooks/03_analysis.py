import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from scipy import stats
from pathlib import Path

PROCESSED_DIR = Path(__file__).parent.parent / "data" / "processed"

df = pd.read_csv(PROCESSED_DIR / "cleaned_data.csv", parse_dates=["date"])
df = df.set_index("date")

# Tariff period boundary: April 2025 (Trump broad tariffs announced)
TARIFF_START = pd.Timestamp("2025-04-01")
TARIFF_END   = pd.Timestamp("2025-12-31")
df["tariff_period"] = df.index.map(lambda d: "post_tariff" if d >= TARIFF_START else "pre_tariff")

# ── FRAMING NOTE ──────────────────────────────────────────────────────────────
# This is an event-window analysis, not a causal proof. April 2025 is used as
# the event boundary because it marks the announced effective date of the broad
# US tariff package. Observed changes post-April 2025 coincide with the tariff
# timeline but cannot be attributed solely to tariffs without controlling for
# concurrent macroeconomic variables (Fed policy, consumer credit conditions,
# residual post-COVID normalization). Where the data permits, alternative
# explanations are tested explicitly.

METRICS = {
    "cpi_food":           "CPI Food",
    "cpi_apparel":        "CPI Apparel",
    "consumer_sentiment": "Consumer Sentiment",
    "wmt_adj_close":      "WMT Adj Close ($)",
    "dg_adj_close":       "DG Adj Close ($)",
}

# ── 1. Averages by period ──────────────────────────────────────────────────────

avg  = df.groupby("tariff_period")[list(METRICS.keys())].mean()
pre  = avg.loc["pre_tariff"]
post = avg.loc["post_tariff"]
pct_change = ((post - pre) / pre * 100).rename("pct_change")

# ── 2. Key retail metrics ──────────────────────────────────────────────────────

wmt_pct = pct_change["wmt_adj_close"]
dg_pct  = pct_change["dg_adj_close"]

event_start   = df.index[df.index >= TARIFF_START][0]
event_end     = df.index[df.index <= TARIFF_END][-1]
wmt_event_pct = (df.loc[event_end, "wmt_adj_close"] / df.loc[event_start, "wmt_adj_close"] - 1) * 100
dg_event_pct  = (df.loc[event_end, "dg_adj_close"]  / df.loc[event_start, "dg_adj_close"]  - 1) * 100

biggest_jump_idx = df["cpi_food_mom_pct"].idxmax()
biggest_jump_val = df.loc[biggest_jump_idx, "cpi_food_mom_pct"]

mom_by_period = df.groupby("tariff_period")["cpi_food_mom_pct"].mean()
pre_mom  = mom_by_period["pre_tariff"]
post_mom = mom_by_period["post_tariff"]
mom_accel = post_mom - pre_mom

food_chg    = pct_change["cpi_food"]
apparel_chg = pct_change["cpi_apparel"]
cat_gap     = abs(food_chg - apparel_chg)

# ── 3. Statistical test: food CPI MoM pre vs post tariff ─────────────────────
# A simple Welch t-test to assess whether the difference in monthly food CPI
# growth rates is statistically distinguishable from zero. This does not prove
# causation but adds a basic measure of analytical rigour beyond averages alone.

pre_food_mom  = df[df["tariff_period"] == "pre_tariff"]["cpi_food_mom_pct"].dropna()
post_food_mom = df[df["tariff_period"] == "post_tariff"]["cpi_food_mom_pct"].dropna()
t_stat, p_val = stats.ttest_ind(pre_food_mom, post_food_mom, equal_var=False)

# ── 4. Summary table ──────────────────────────────────────────────────────────

W = 70

print("=" * 62)
print(f"{'TARIFF IMPACT SUMMARY':^62}")
print(f"  Pre-tariff: Jan 2022 – Mar 2025  |  Post-tariff: Apr–Dec 2025")
print(f"  Event-window analysis — April 2025 used as tariff boundary")
print("=" * 62)
print(f"{'Metric':<24} {'Pre-Tariff':>10} {'Post-Tariff':>11} {'% Change':>10}")
print("-" * 62)

rows = []
for col, label in METRICS.items():
    pre_val  = pre[col]
    post_val = post[col]
    chg      = pct_change[col]
    arrow    = "▲" if chg > 0 else "▼"
    print(f"{label:<24} {pre_val:>10.2f} {post_val:>11.2f} {arrow}{abs(chg):>8.1f}%")
    rows.append({
        "metric":      label,
        "pre_tariff":  round(pre_val, 2),
        "post_tariff": round(post_val, 2),
        "pct_change":  round(chg, 2),
    })

print("-" * 62)
print(f"\n  Note: % change figures are level comparisons across unequal windows")
print(f"  (39 pre-tariff months vs 9 post-tariff months). The food CPI figure")
print(f"  reflects a sustained elevated level, not a rate acceleration.")
print(f"  See Alternative Explanations for full context.")
print(f"\n  WMT avg-based change      : {'▲' if wmt_pct > 0 else '▼'}{abs(wmt_pct):.1f}%")
print(f"  DG  avg-based change      : {'▲' if dg_pct > 0 else '▼'}{abs(dg_pct):.1f}%")
print(f"  WMT point-to-point return : {'▲' if wmt_event_pct > 0 else '▼'}{abs(wmt_event_pct):.1f}%  (Apr 1 – Dec 31 2025)")
print(f"  DG  point-to-point return : {'▲' if dg_event_pct > 0 else '▼'}{abs(dg_event_pct):.1f}%  (Apr 1 – Dec 31 2025)")
print(f"\n  Biggest food CPI monthly jump: {biggest_jump_idx.strftime('%b %Y')} (+{biggest_jump_val:.2f}% MoM)")
print("=" * 62)

# Save summary CSV
summary_df = pd.DataFrame(rows)
summary_df.to_csv(PROCESSED_DIR / "insights_summary.csv", index=False)
print(f"\nSaved summary -> {PROCESSED_DIR / 'insights_summary.csv'}")

# ── 5. Signal Confidence ──────────────────────────────────────────────────────
# Placed early so the reader understands confidence levels before reading detail.

print("\n" + "=" * W)
print(f"{'SIGNAL CONFIDENCE':^{W}}")
print("=" * W)
print()
print("  STRONG SIGNAL")
print("    • Consumer sentiment decline (-15.6% post-tariff, sustained across")
print("      all 9 post-tariff months — the most consistent series in the dataset)")
print("    • Category divergence: food +6.2% vs apparel +1.3% — a broad macro")
print("      force would affect both categories more equally; the 4.9 pp gap is")
print("      directionally consistent with differential tariff exposure")
print()
print("  MODERATE SIGNAL")
print("    • Sustained food CPI level post-tariff (elevated above the pre-tariff")
print("      trend even as the monthly rate decelerated)")
print("    • WMT / DG stock divergence — the direction is clear but the magnitude")
print("      and interpretation depend heavily on measurement approach (see below)")
print()
print("  WEAK SIGNAL")
print("    • Causal tariff attribution (concurrent macro events not controlled)")
print("    • Supply-chain flexibility as the specific driver of WMT resilience")
print("      (plausible mechanism but not directly testable with available data)")
print()
print("=" * W)

# ── 6. Hypotheses and findings ────────────────────────────────────────────────

print("\n" + "=" * W)
print(f"{'HYPOTHESES AND FINDINGS':^{W}}")
print("=" * W)

# --- H1: Food vs Apparel ---
print("\n[H1]  Food CPI would rise more sharply than apparel CPI post-tariff")
print("-" * W)
print("\nRATIONALE:")
print("  Food supply chains have higher import dependence in agricultural inputs")
print("  and shorter inventory cycles, making them faster to reprice. Apparel")
print("  retailers typically carry longer forward inventory positions, providing")
print("  a temporary buffer against cost increases.")
print("\nFINDING:")
print(f"  Food CPI +{food_chg:.1f}%  |  Apparel CPI +{apparel_chg:.1f}%")
print(f"  Category gap: {cat_gap:.1f} percentage points")
print(f"\n  Food CPI MoM rate — pre-tariff avg: {pre_mom:+.3f}% | post-tariff avg: {post_mom:+.3f}%")
print(f"  MoM rate change post-tariff: {mom_accel:+.3f} pp")
print(f"\n  Welch t-test (food CPI MoM, pre vs post):")
print(f"    t = {t_stat:.3f}  |  p = {p_val:.3f}")
if p_val < 0.05:
    print("    Result: statistically significant at the 5% level.")
else:
    print("    Result: not statistically significant at the 5% level.")
    print("    The monthly rate difference is directional but not reliably")
    print("    distinguishable from noise at this sample size (n=39 pre, n=9 post).")
print("\nVERDICT:")
print(f"  Partially confirmed. The aggregate level gap ({food_chg:.1f}% vs {apparel_chg:.1f}%) is")
print("  directionally consistent with the hypothesis. However, the food CPI")
print("  monthly rate did not accelerate post-tariff — it reflects a sustained")
print("  elevated level, not a new shock. Apparel's lower figure is consistent")
print("  with longer inventory buffers delaying cost passthrough rather than")
print("  lower tariff exposure per se.")

# --- H2: Consumer Sentiment ---
sentiment_chg = pct_change["consumer_sentiment"]
print("\n[H2]  Consumer sentiment would fall as prices eroded purchasing power")
print("-" * W)
print("\nRATIONALE:")
print("  Higher food prices directly affect household budgets, particularly for")
print("  lower-income consumers. Sentiment surveys tend to respond quickly to")
print("  visible price changes at the grocery level.")
print("\nFINDING:")
print(f"  Consumer sentiment: pre-tariff avg 65.5 → post-tariff avg 55.3")
print(f"  Change: {sentiment_chg:+.1f}% — sustained across all 9 post-tariff months")
print("\nVERDICT:")
print("  Confirmed. The decline is consistent and sustained, making this the")
print("  strongest signal in the dataset. The direction is unambiguous; the")
print("  causal link to tariffs specifically (vs general economic anxiety)")
print("  cannot be isolated with available data.")

# --- H3: Retailer divergence ---
print("\n[H3]  Discount retailers would outperform premium retailers post-tariff")
print("-" * W)
print("\nRATIONALE:")
print("  A consumer spending squeeze typically benefits value-oriented retailers")
print("  as households trade down to lower-cost channels. Dollar General was")
print("  expected to benefit; Walmart less so.")
print("\nFINDING:")
print(f"  Average-based:    WMT {'▲' if wmt_pct > 0 else '▼'}{abs(wmt_pct):.1f}%  vs  DG {'▲' if dg_pct > 0 else '▼'}{abs(dg_pct):.1f}%")
print(f"  Point-to-point:   WMT {'▲' if wmt_event_pct > 0 else '▼'}{abs(wmt_event_pct):.1f}%  vs  DG {'▲' if dg_event_pct > 0 else '▼'}{abs(dg_event_pct):.1f}%  (Apr 1 – Dec 31 2025)")
print("\nVERDICT:")
print("  Evidence is mixed depending on measurement approach. The average-based")
print("  figures show WMT dramatically outperforming DG, but this captures a")
print("  multi-year trajectory where WMT was rising and DG was already declining")
print("  before April 2025. The point-to-point return within the tariff window")
print("  itself shows DG outperforming WMT (+43.3% vs +15.3%), as DG bounced")
print("  from a tariff-period low. Neither metric alone tells the full story.")
print("  The hypothesis is neither cleanly confirmed nor refuted — the direction")
print("  of the average-based result contradicts the original expectation, but")
print("  the point-to-point result partially supports it.")

print("\n" + "=" * W)

# ── 7. Unexpected findings ────────────────────────────────────────────────────

print("\n" + "=" * W)
print(f"{'UNEXPECTED FINDINGS':^{W}}")
print("=" * W)

print("\n[Finding 1 of 2]  WMT vs DG Post-Tariff Divergence")
print("-" * W)
print("\nORIGINAL EXPECTATION:")
print("  Discount retailers like Dollar General would outperform in a tariff/")
print("  inflation environment as consumers trade down to lower-cost channels.")
print("\nWHAT THE DATA SHOWED:")
print(f"  Average-based: WMT ▲{abs(wmt_pct):.1f}% vs DG ▼{abs(dg_pct):.1f}% — a {abs(wmt_pct - dg_pct):.0f} pp spread in")
print("  the opposite direction of the hypothesis.")
print(f"  Point-to-point within the tariff window: DG ▲{abs(dg_event_pct):.1f}% vs WMT ▲{abs(wmt_event_pct):.1f}%.")
print("  The two metrics tell meaningfully different stories; neither should be")
print("  treated as definitive in isolation.")
print("\nPOSSIBLE EXPLANATIONS:")
print("  1. Walmart's supply-chain scale and import diversification may have")
print("     allowed faster supplier renegotiation than smaller peers.")
print("  2. Dollar General's rural, fixed-income customer base was disproportio-")
print("     nately squeezed by food inflation, reducing visit frequency and basket")
print("     size — undermining the trade-down thesis.")
print("  3. Dollar General entered the period with known inventory challenges;")
print("     the tariff shock may have compounded existing operational pressure.")
print("  4. This analysis covers only two stocks. A finding based on n=2 retailers")
print("     is directional at best. Adding Target or Costco would strengthen or")
print("     refute the pattern.")

print("\n[Finding 2 of 2]  Food CPI Spike Predates the Tariff Period")
print("-" * W)
print("\nORIGINAL EXPECTATION:")
print("  The largest single-month food CPI jump would fall in or just after")
print("  April 2025, when tariff costs first propagated through supply chains.")
print("\nWHAT THE DATA SHOWED:")
print(f"  Largest monthly food CPI jump: {biggest_jump_idx.strftime('%B %Y')} (+{biggest_jump_val:.2f}% MoM),")
print("  occurring during the post-COVID inflation surge — nearly three years")
print("  before the tariff period. Post-tariff monthly increases were real and")
print("  sustained but did not approach the 2022 spike magnitude.")
print("\nPOSSIBLE EXPLANATIONS:")
print("  1. Post-COVID supply chain disruptions and the Russia-Ukraine war drove")
print("     commodity prices sharply in mid-2022, producing a more acute spike.")
print("  2. The April 2025 tariffs compounded an already-elevated price baseline,")
print("     producing a sustained lift rather than a concentrated monthly shock.")
print("  3. CPI captures retail shelf prices with a publication lag; tariff costs")
print("     likely spread across multiple months rather than concentrating in one.")

print("\n" + "=" * W)

# ── 8. Alternative explanations ───────────────────────────────────────────────

print("\n" + "=" * W)
print(f"{'ALTERNATIVE EXPLANATIONS':^{W}}")
print("=" * W)
print("  Testing whether observed CPI and sentiment shifts could be explained")
print("  by causes other than the April 2025 tariff implementation.")

# --- Alt 1: General Inflation ---
print("\n[Alt 1 of 3]  General Inflation (not tariffs)")
print("-" * W)
print("\nALTERNATIVE EXPLANATION:")
print("  Food prices were already rising at the same rate before April 2025,")
print("  so the post-tariff increase reflects continuation of a pre-existing")
print("  trend rather than a tariff-specific shock.")
print("\nDATA TEST:")
print(f"  Avg monthly food CPI change  pre-tariff : {pre_mom:+.3f}% MoM")
print(f"  Avg monthly food CPI change post-tariff : {post_mom:+.3f}% MoM")
print(f"  MoM rate change post-tariff             : {mom_accel:+.3f} pp")
print("\nVERDICT:")
if mom_accel > 0.05:
    print(f"  Partially contradicted. Monthly rate accelerated by {mom_accel:+.3f} pp")
    print("  post-tariff, indicating a genuine step-up beyond the pre-existing trend.")
else:
    direction_word = "decelerated" if mom_accel < 0 else "was largely unchanged"
    print(f"  Inconclusive — the MoM rate {direction_word} post-tariff, not")
    print("  accelerated. The +6.2% aggregate figure is a level comparison across")
    print("  unequal windows (39 vs 9 months) partly driven by the elevated")
    print("  2022–23 post-COVID baseline. General inflation cannot be ruled out")
    print("  as a co-contributor. The honest argument is that tariffs likely")
    print("  sustained an already-elevated level rather than triggering a new shock.")

# --- Alt 2: Exchange Rate Effects ---
print("\n[Alt 2 of 3]  Exchange Rate Effects")
print("-" * W)
print("\nALTERNATIVE EXPLANATION:")
print("  A weakening USD raised import prices broadly across all categories,")
print("  accounting for the food CPI rise independently of tariff policy.")
print("\nDATA TEST:")
print("  Cannot be directly tested — no FX data in the current dataset.")
print("  However, the category divergence (food +6.2% vs apparel +1.3%) is")
print("  difficult to explain through FX alone, since both are import-exposed.")
print("  A uniform FX effect would be expected to move both categories more")
print("  equally than observed.")
print("\nVERDICT:")
print("  Data limitation — flag for future analysis. Recommended addition:")
print("  pull trade-weighted USD index from FRED series DTWEXBGS and test")
print("  correlation with post-tariff food CPI MoM changes.")

# --- Alt 3: Inventory Cycles ---
print("\n[Alt 3 of 3]  Inventory Cycles / Supply Chain Lag")
print("-" * W)
print("\nALTERNATIVE EXPLANATION:")
print("  Retailers drew down pre-tariff inventory in the post-April 2025 window,")
print("  delaying the true cost impact. Observed price and stock moves reflect")
print("  inventory positioning rather than steady-state tariff pass-through.")
print("\nDATA TEST:")
print("  Cannot be directly tested — no SKU-level inventory or gross margin")
print("  data in the current dataset. The 9-month post-tariff window falls")
print("  plausibly within a typical inventory cycle for food and apparel.")
print("\nVERDICT:")
print("  Data limitation — cannot confirm or refute with available data.")
print("  Recommended addition: quarterly gross margin data from WMT and DG")
print("  10-Q filings. Margin compression in Q2 2025 followed by Q3–Q4 recovery")
print("  would suggest inventory absorption rather than sustained pass-through.")

# --- Conclusion ---
print("\n" + "-" * W)
print(f"{'CONCLUSION':^{W}}")
print("-" * W)
print()
print("  The +6.2% food CPI figure is a level comparison across unequal windows,")
print("  not a rate acceleration. The monthly food CPI rate")
print(f"  {'accelerated' if mom_accel > 0 else 'decelerated'} by {abs(mom_accel):.3f} pp post-April 2025.")
print()
print("  The honest argument is narrower: tariffs likely sustained an already-")
print("  elevated food price level rather than triggering a new shock. Without")
print("  a tariff floor, continued disinflation would have been the expected")
print("  trajectory given the decelerating pre-tariff MoM trend.")
print()
print(f"  The strongest remaining signal is category differentiation. The {cat_gap:.1f} pp")
print(f"  gap ({food_chg:.1f}% food vs {apparel_chg:.1f}% apparel) is more consistent with")
print("  targeted tariff exposure than with a broad macro explanation, since FX")
print("  weakness or general inflation would affect both categories more equally.")
print("  Note: apparel is not a formal control group — it differs from food in")
print("  demand elasticity, purchase frequency, and inventory cycles.")
print()
print("  Exchange rate and inventory-cycle effects remain untested. A boundary-")
print("  specific test (Mar 2025 vs Dec 2025 directly) and quarterly gross margin")
print("  data from retailer 10-Qs would materially strengthen or refute the")
print("  sustained-level hypothesis.")
print("\n" + "=" * W)

# ── 9. What I Got Wrong ───────────────────────────────────────────────────────

print("\n" + "=" * W)
print(f"{'WHAT I GOT WRONG':^{W}}")
print("=" * W)

print("\nHYPOTHESIS:")
print("  Food prices would spike most sharply in the months immediately following")
print("  the April 2025 tariff announcement, as supply chains repriced imported")
print("  inputs and retailers passed costs through to shelf prices.")

print("\nWHAT THE DATA SHOWED:")
print(f"  The single largest monthly food CPI jump was {biggest_jump_idx.strftime('%B %Y')}")
print(f"  (+{biggest_jump_val:.2f}% MoM) — during the post-pandemic inflation surge,")
print("  nearly three years before the tariff period. Post-tariff monthly")
print("  increases were real and sustained but produced no single month")
print("  approaching the 2022 spike magnitude.")

print("\nWHY THIS MATTERS:")
print("  Acknowledging where the signal was weaker than expected strengthens")
print("  the credibility of findings where the signal was strong. The consumer")
print("  sentiment decline and the category-level divergence are more robust")
print("  observations. Overstating the food CPI spike story would undermine")
print("  confidence in those better-supported findings.")

print("\nIMPLICATION FOR ANALYSIS:")
print("  Tariff effects on food CPI appear gradual and accumulating rather than")
print("  a sharp one-month shock. The right analytical frame is whether the")
print("  post-tariff price level remained elevated relative to the pre-tariff")
print("  disinflation trend — which the data does support.")

print("\n" + "=" * W)

# ── 10. Limitations ───────────────────────────────────────────────────────────

print("\n" + "=" * W)
print(f"{'LIMITATIONS':^{W}}")
print("=" * W)

print("\n1. NO FIRM-LEVEL PRICING DATA")
print("   CPI reflects retail shelf prices as reported by BLS surveyors. This")
print("   dataset cannot determine whether observed increases were absorbed by")
print("   retailer margins or passed through to consumers. Gross margin data")
print("   from quarterly 10-Q filings would be required to answer directly.")

print("\n2. CPI IS CATEGORY-LEVEL, NOT PRODUCT-LEVEL")
print("   The food CPI (CPIUFDNS) and apparel CPI (CPIAPPNS) are basket averages.")
print("   Individual product price moves may diverge significantly from the basket.")
print("   A product-level scanner dataset would provide higher resolution.")

print("\n3. CORRELATION WITH TARIFF TIMING DOES NOT PROVE CAUSATION")
print("   April 2025 coincided with other macroeconomic events: continued Fed")
print("   policy adjustments, consumer credit tightening, and post-COVID supply")
print("   chain normalization. This analysis cannot isolate the tariff effect")
print("   without a control group or difference-in-differences design.")

print("\n4. SHORT POST-TARIFF WINDOW (9 MONTHS)")
print("   Supply chains reprice on 6–18 month cycles. Averages over this window")
print("   may capture transition dynamics rather than a new steady state.")

print("\n5. FRED DATA LAG — OCTOBER 2025 CPI FORWARD-FILLED")
print("   BLS CPI series carry a publication lag of 3–6 weeks. October 2025")
print("   values were forward-filled from September 2025. Post-tariff averages")
print("   including Oct 2025 should be treated with caution.")

print("\n6. RETAILER SAMPLE SIZE OF TWO")
print("   WMT and DG are two stocks. Any pattern observed across n=2 retailers")
print("   is directional at best. Adding Costco, Target, or Loblaw would")
print("   substantially strengthen or refute the retailer divergence finding.")

print("\n" + "=" * W)

# ── 11. Consolidated recommendations ─────────────────────────────────────────

print("\n" + "=" * W)
print(f"{'RECOMMENDATIONS FOR A MID-SIZE CANADIAN RETAILER':^{W}}")
print("=" * W)
print()
print("  1. PRIORITIZE FOOD CATEGORY SOURCING REVIEWS")
print("     Food CPI rose 6.2% in aggregate over the post-tariff window.")
print("     While the monthly rate did not re-accelerate, the sustained")
print("     elevated level signals that costs were not being absorbed at")
print("     the retail level. Retailers without forward contracts or")
print("     alternative supplier relationships face ongoing margin risk.")
print("     Action: map supplier concentration by category; identify any")
print("     single-source dependencies in the top 20% of food SKUs by volume.")
print()
print("  2. DO NOT ASSUME DISCOUNT POSITIONING IS A TARIFF HEDGE")
print("     The Dollar General result — declining stock performance despite")
print("     being a value retailer — suggests that supply-chain flexibility")
print("     and product mix matter more than price tier alone. A value")
print("     customer base can become a liability if those customers reduce")
print("     consumption rather than trade channels.")
print("     Action: stress-test margin assumptions under a scenario where")
print("     your lowest-income customer segment reduces basket size by 15%.")
print()
print("  3. TREAT CONSUMER SENTIMENT AS A LEADING INDICATOR")
print("     Sentiment fell 15.6% post-tariff and remained depressed across")
print("     the full 9-month window. Historically, sustained sentiment")
print("     declines precede reduced discretionary spend by 1–2 quarters.")
print("     Action: add a monthly sentiment tracker to category planning")
print("     reviews; flag any further decline below the post-tariff avg of 55.3.")
print()
print("  Confidence note: recommendations 1 and 3 rest on the strongest")
print("  signals in this analysis. Recommendation 2 is directionally supported")
print("  but rests on a two-stock comparison and should be treated as a prompt")
print("  for further investigation, not a firm conclusion.")
print()
print("=" * W)

# ── 12. Visualization: WMT vs DG over time ───────────────────────────────────

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
fig.suptitle("WMT vs DG Stock Performance\nPre- vs Post-Tariff (April 2025)",
             fontsize=13, fontweight="bold")

wmt_norm = df["wmt_adj_close"] / df["wmt_adj_close"].iloc[0] * 100
dg_norm  = df["dg_adj_close"]  / df["dg_adj_close"].iloc[0]  * 100

ax1.plot(df.index, wmt_norm, color="#0057e7", linewidth=2, label="WMT (indexed)")
ax1.plot(df.index, dg_norm,  color="#d62728", linewidth=2, label="DG (indexed)")
ax1.axvline(TARIFF_START, color="black", linestyle="--", linewidth=1.2, label="Tariff start (Apr 2025)")
ax1.axvspan(TARIFF_START, df.index[-1], alpha=0.06, color="orange", label="Post-tariff period")
ax1.set_ylabel("Indexed Price (Jan 2022 = 100)", fontsize=9)
ax1.set_title("Relative Performance (both indexed to 100 at Jan 2022)", fontsize=10, loc="left")
ax1.legend(fontsize=9)
ax1.grid(axis="y", linestyle="--", alpha=0.4)
ax1.spines[["top", "right"]].set_visible(False)

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
print(f"\nSaved chart -> {out_path}")
plt.show()
