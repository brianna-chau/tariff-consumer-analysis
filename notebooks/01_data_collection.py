import os
import time
from pathlib import Path
from dotenv import load_dotenv
from fredapi import Fred
import pandas as pd
import requests

load_dotenv()

fred = Fred(api_key=os.getenv("FRED_API_KEY"))

START = "2022-01-01"
END = "2025-12-31"
RAW_DIR = Path(__file__).parent.parent / "data" / "raw"

series = {
    "cpi_food": "CPIUFDNS",
    "cpi_apparel": "CPIAPPNS",
    "consumer_sentiment": "UMCSENT",
}

for filename, series_id in series.items():
    data = fred.get_series(series_id, observation_start=START, observation_end=END)
    df = data.reset_index()
    df.columns = ["date", "value"]
    out_path = RAW_DIR / f"{filename}.csv"
    df.to_csv(out_path, index=False)
    print(f"Saved {series_id} -> {out_path}")
    time.sleep(1)

# --- Alpha Vantage: monthly stock data ---

AV_KEY = os.getenv("ALPHAVANTAGE_API_KEY")
AV_URL = "https://www.alphavantage.co/query"

stocks = {"stocks_wmt": "WMT", "stocks_dg": "DG"}

for filename, ticker in stocks.items():
    resp = requests.get(AV_URL, params={
        "function": "TIME_SERIES_MONTHLY_ADJUSTED",
        "symbol": ticker,
        "apikey": AV_KEY,
    })
    resp.raise_for_status()
    payload = resp.json()

    if "Monthly Adjusted Time Series" not in payload:
        raise ValueError(f"Unexpected response for {ticker}: {payload}")

    records = [
        {"date": date, **values}
        for date, values in payload["Monthly Adjusted Time Series"].items()
    ]
    df = pd.DataFrame(records)
    df.columns = [c.split(". ", 1)[-1] for c in df.columns]  # strip "1. ", "2. " prefixes
    df["date"] = pd.to_datetime(df["date"])
    df = df[(df["date"] >= START) & (df["date"] <= END)].sort_values("date").reset_index(drop=True)

    out_path = RAW_DIR / f"{filename}.csv"
    df.to_csv(out_path, index=False)
    print(f"Saved {ticker} -> {out_path}")
    time.sleep(12)  # Alpha Vantage free tier: 5 requests/min
