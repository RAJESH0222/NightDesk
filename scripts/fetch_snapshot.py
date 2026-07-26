# scripts/fetch_snapshot.py
# ======================================================================
# NIGHT DESK data fetcher - runs on GitHub Actions cron, writes
# data/snapshot.json which the static Netlify frontend reads.
#
# DATA SOURCES - free tier, personal use only:
#   * yfinance  -> Yahoo Finance UNOFFICIAL endpoints. No SLA, no
#                  contract. Can break or rate-limit WITHOUT warning.
#                  Keep request volume low (the sleeps are deliberate).
#   * Finnhub   -> free tier, 60 calls/min, company-news endpoint.
#                  (Alpha Vantage news free tier = 25 requests/DAY -
#                   too tight for near-real-time monitoring, avoided.)
#
# Modes:
#   --mode intraday  every 15-20 min in market hours: prices + 24h news
#   --mode daily     once a day: trailing-30d news-mention counts
# ======================================================================
import argparse, json, os, pathlib, time
import datetime as dt

import requests
import yfinance  # UNOFFICIAL Yahoo Finance wrapper - may break anytime

WATCHLIST = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "SBIN.NS",
    "TATAMOTORS.NS", "ADANIENT.NS", "500325.BO", "532174.BO",
    "AAPL", "NVDA", "MSFT", "TSLA", "AMD", "PLTR", "LUNR", "RGTI", "BBAI",
    "DATAPATTNS.NS", "PRICOLLTD.NS", "GRAVITA.NS", "GOKEX.NS", "AMBER.NS",
    "7203.T", "9988.HK", "SAP.DE", "RIO.L",
]
KEY = os.environ.get("FINNHUB_KEY", "")
OUT = pathlib.Path("data") / "snapshot.json"


def quote_row(sym):
    t = yfinance.Ticker(sym)
    info = t.info or {}
    hist = t.history(period="3mo", interval="1d")
    time.sleep(0.8)  # be gentle - unofficial API, we are a guest
    return {
        "sym": sym,
        "name": info.get("longName") or sym,
        "exch": info.get("exchange") or "?",
        "currency": info.get("currency") or "?",
        "price": info.get("regularMarketPrice"),
        "prev_close": info.get("previousClose"),
        "volume": info.get("regularMarketVolume"),
        "market_cap": info.get("marketCap"),
        "avg_vol_30d": int(hist["Volume"].tail(30).mean()) if len(hist) else 0,
        "spark": [round(float(v), 4) for v in hist["Close"].tail(40)],
    }


def company_news(sym, days):
    if not KEY:
        return []
    to_ = int(time.time())
    r = requests.get(
        "https://finnhub.io/api/v1/company-news",
        params={"symbol": sym, "from": to_ - days * 86400, "to": to_, "token": KEY},
        timeout=15,
    )
    time.sleep(1.1)  # free tier caps at 60 calls/min - stay well under
    items = r.json() if r.ok else []
    return [
        {"headline": n.get("headline"), "source": n.get("source"),
         "ts": n.get("datetime"), "url": n.get("url")}
        for n in items[:8]
    ]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["intraday", "daily"], default="intraday")
    args = ap.parse_args()

    prev = {}
    if OUT.exists():
        prev = json.loads(OUT.read_text())

    quotes = [quote_row(s) for s in WATCHLIST]

    if args.mode == "intraday":
        keep = {p["sym"]: p for p in prev.get("quotes", [])}
        for q in quotes:
            q["news_24h"] = company_news(q["sym"], 1)
            # 30d mention counts are owned by the daily job - carry forward
            q["news_mentions_30d"] = keep.get(q["sym"], {}).get("news_mentions_30d", 0)
    else:
        for q in quotes:
            q["news_mentions_30d"] = len(company_news(q["sym"], 30))

    payload = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source": "yfinance (UNOFFICIAL) + finnhub (free tier)",
        "quotes": quotes,
    }
    OUT.parent.mkdir(exist_ok=True)
    tmp = OUT.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload))  # write aside, then swap
    tmp.replace(OUT)
    print("wrote", OUT, len(quotes), "quotes")


if __name__ == "__main__":
    main()
