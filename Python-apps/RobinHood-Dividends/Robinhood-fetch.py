import csv
import json
import os
import yfinance as yf

# pip install yfinance
# (Run the above install a second time in a row, if you get an error)

# Update with your actual Robinhood CSV filename
ROBINHOOD_CSV_PATH = "robinhood_export.csv"
CACHE_FILE_PATH = "dividends_cache.json"


def get_unique_tickers(csv_path):
  tickers = set()
  if not os.path.exists(csv_path):
    print(
        f"Error: '{csv_path}' not found. Place your Robinhood CSV in this"
        " directory."
    )
    return []

  with open(csv_path, mode="r", encoding="utf-8-sig") as f:
    reader = csv.reader(f)
    headers = [
        h.strip().replace('"', "").replace("'", "").lower()
        for h in next(reader, [])
    ]

    try:
      inst_idx = (
          headers.index("instrument")
          if "instrument" in headers
          else headers.index("symbol")
      )
    except ValueError:
      print("Could not locate Instrument/Symbol column in CSV.")
      return []

    for row in reader:
      if len(row) > inst_idx:
        ticker = row[inst_idx].strip().upper()
        if (
            ticker
            and ticker != "UNDEFINED"
            and not ticker.isdigit()
            and len(ticker) <= 5
        ):
          tickers.add(ticker)

  return sorted(list(tickers))


def main():
  tickers = get_unique_tickers(ROBINHOOD_CSV_PATH)
  if not tickers:
    print("No tickers found to fetch.")
    return

  print(
      f"Found {len(tickers)} unique symbols. Fetching real dividend rates via"
      " yfinance..."
  )

  cache = {}
  for ticker in tickers:
    try:
      tk = yf.Ticker(ticker)
      info = tk.info
      # Extract official dividend rate or trailing annual dividend rate
      div_rate = info.get("dividendRate") or info.get(
          "trailingAnnualDividendRate", 0.0
      )
      if div_rate is None:
        div_rate = 0.0

      cache[ticker] = round(float(div_rate), 6)
      print(f"  [{ticker}] Annual Dividend: ${cache[ticker]:.6f}")
    except Exception as e:
      print(f"  [{ticker}] Error fetching data: {e}")
      cache[ticker] = 0.0

  with open(CACHE_FILE_PATH, "w", encoding="utf-8") as f:
    json.dump(cache, f, indent=4)

  print(
      f"\nDone! Saved accurate dividend rates for {len(cache)} symbols to"
      f" '{CACHE_FILE_PATH}'."
  )


if __name__ == "__main__":
  main()