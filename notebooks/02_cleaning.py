import pandas as pd
from pathlib import Path

RAW_DIR = Path(__file__).parent.parent / "data" / "raw"
PROCESSED_DIR = Path(__file__).parent.parent / "data" / "processed"

# --- Load raw data ---

fred_files = {
    "cpi_food": RAW_DIR / "cpi_food.csv",
    "cpi_apparel": RAW_DIR / "cpi_apparel.csv",
    "consumer_sentiment": RAW_DIR / "consumer_sentiment.csv",
}

stock_files = {
    "wmt": RAW_DIR / "stocks_wmt.csv",
    "dg": RAW_DIR / "stocks_dg.csv",
}

fred_dfs = {}
for name, path in fred_files.items():
    df = pd.read_csv(path, parse_dates=["date"])
    df = df.rename(columns={"value": name})
    df = df.set_index("date")
    fred_dfs[name] = df

stock_dfs = {}
for ticker, path in stock_files.items():
    df = pd.read_csv(path, parse_dates=["date"])
    df = df[["date", "adjusted close", "volume"]].copy()
    df = df.rename(columns={
        "adjusted close": f"{ticker}_adj_close",
        "volume": f"{ticker}_volume",
    })
    # Alpha Vantage dates land on month-end; normalize to month-start to align with FRED
    df["date"] = df["date"].values.astype("datetime64[M]")
    df = df.set_index("date")
    stock_dfs[ticker] = df

# --- Merge into one master frame on a clean monthly index ---

master = pd.concat(list(fred_dfs.values()) + list(stock_dfs.values()), axis=1)
master.index.name = "date"
master = master.sort_index()

print("=== Raw merged shape:", master.shape)
print("Nulls before cleaning:")
print(master.isnull().sum().to_string())

# --- Null check: identify which rows have missing CPI values ---
null_rows = master[master[["cpi_food", "cpi_apparel"]].isnull().any(axis=1)]
if not null_rows.empty:
    print(f"\nRows with null CPI values:\n{null_rows[['cpi_food', 'cpi_apparel']]}")

# Forward-fill the trailing CPI nulls (latest month not yet published by BLS)
master[["cpi_food", "cpi_apparel"]] = master[["cpi_food", "cpi_apparel"]].ffill()

print("\nNulls after cleaning:")
print(master.isnull().sum().to_string())

# --- Derived columns ---

# Month-over-month % change for each CPI series
master["cpi_food_mom_pct"] = master["cpi_food"].pct_change() * 100
master["cpi_apparel_mom_pct"] = master["cpi_apparel"].pct_change() * 100

# Year-over-year % change (12-month lag)
master["cpi_food_yoy_pct"] = master["cpi_food"].pct_change(12) * 100
master["cpi_apparel_yoy_pct"] = master["cpi_apparel"].pct_change(12) * 100

# Stock: month-over-month % change in adjusted close
master["wmt_mom_pct"] = master["wmt_adj_close"].pct_change() * 100
master["dg_mom_pct"] = master["dg_adj_close"].pct_change() * 100

# --- Save ---

out_path = PROCESSED_DIR / "cleaned_data.csv"
master.reset_index().to_csv(out_path, index=False)
print(f"\nSaved master cleaned dataset -> {out_path}")
print(f"Shape: {master.shape[0]} rows x {master.shape[1]} columns")
print(f"Date range: {master.index.min().date()} to {master.index.max().date()}")
print(f"\nColumns: {list(master.columns)}")
