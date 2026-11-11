#!/usr/bin/env python3
"""
Automatic monthly content for the blog (runs inside the GitHub workflow).

Every month it adds, at most once per month:
  1. "Crypto Market Report – <Month Year>"   (live data: CoinGecko — top 10 coins, trending coins, Bitcoin range)
  2. "Gold & Forex Market Report – <Month Year>" (live data: gold via PAXG on CoinGecko, forex via Frankfurter/ECB)
  3. One ready-written evergreen SEO article from data/queue/ (released in order, one per month)

Safe by design:
  - Existing articles are never changed or deleted, so existing URLs (and Google rankings) stay the same.
  - If a data source is down, that report is simply skipped and retried on the next run.
  - No API keys needed.
Run locally:  python tools/monthly_content.py
"""
import json
import re
import statistics
import sys
import time
import urllib.request
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTICLES = ROOT / "data" / "articles"
QUEUE = ROOT / "data" / "queue"
LOG = ROOT / "data" / "content_log.json"
TODAY = date.today()
MONTH = TODAY.strftime("%B %Y")             # e.g. November 2026
MSLUG = TODAY.strftime("%B-%Y").lower()     # e.g. november-2026
YM = TODAY.strftime("%Y-%m")
CG = "https://api.coingecko.com/api/v3"
UA = {"User-Agent": "Mozilla/5.0 (site-monthly-content; +https://github.com)", "Accept": "application/json"}
STABLE = {"usdt", "usdc", "dai", "fdusd", "usde", "usds", "busd", "tusd", "pyusd", "usd1", "susde", "usdd", "usdtb", "bsc-usd",
          "steth", "wsteth", "wbtc", "weth", "weeth", "cbbtc", "wbeth", "reth", "bnsol", "jitosol", "msol", "lbtc", "solvbtc", "buidl", "usdf", "rlusd", "susds", "xaut", "paxg"}


def fetch(url, tries=3):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:  # noqa: BLE001
            print(f"  fetch failed ({i + 1}/{tries}): {url} — {e}")
            time.sleep(6 * (i + 1))
    raise RuntimeError("unavailable: " + url)


def money(v):
    if v is None:
        return "—"
    if v >= 1000:
        return f"${v:,.0f}"
    if v >= 1:
        return f"${v:,.2f}"
    return f"${v:.6f}".rstrip("0")


def pct(v):
    return "—" if v is None else f"{v:+.2f}%"


def move(v):
    if v is None:
        return "was little changed"
    if abs(v) < 0.5:
        return f"was almost flat ({v:+.2f}%)"
    if v > 0:
        return ("jumped " if v >= 10 else "rose ") + f"{v:.2f}%"
    return ("dropped " if v <= -10 else "fell ") + f"{abs(v):.2f}%"


def big(v):
    if v is None:
        return "—"
    for unit, n in (("trillion", 1e12), ("billion", 1e9), ("million", 1e6)):
        if v >= n:
            return f"${v / n:,.2f} {unit}"
    return money(v)


def load_providers():
    b = json.loads((ROOT / "data" / "brokers.json").read_text(encoding="utf-8"))
    e = json.loads((ROOT / "data" / "exchanges.json").read_text(encoding="utf-8"))
    pick = lambda xs: [x for x in xs if x.get("top_pick")] or xs[:3]
    return pick(b), pick(e)


def front(title, desc, kw, cat, slug):
    return f"---\ntitle: {title}\ndescription: {desc}\nkeywords: {kw}\ncategory: {cat}\ndate: {TODAY.isoformat()}\nslug: {slug}\n---\n"


def series_stats(vals):
    return {"start": vals[0], "end": vals[-1], "high": max(vals), "low": min(vals),
            "chg": (vals[-1] / vals[0] - 1) * 100 if vals[0] else None,
            "range": (max(vals) / min(vals) - 1) * 100 if min(vals) else None}


# ---------------------------------------------------------------- crypto
def crypto_report():
    slug = f"crypto-market-report-{MSLUG}"
    if (ARTICLES / f"{slug}.md").exists():
        print("crypto report already exists"); return False
    mk = fetch(f"{CG}/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=40&page=1&price_change_percentage=24h,7d,30d")
    coins = [c for c in mk if (c.get("symbol") or "").lower() not in STABLE][:10]
    if len(coins) < 5:
        raise RuntimeError("not enough coin data")
    try:
        trending = [t["item"] for t in fetch(f"{CG}/search/trending").get("coins", [])][:7]
    except RuntimeError:
        trending = []
    btc = series_stats([p[1] for p in fetch(f"{CG}/coins/bitcoin/market_chart?vs_currency=usd&days=30")["prices"]])
    total_cap = sum(c.get("market_cap") or 0 for c in coins)
    c30 = lambda c: c.get("price_change_percentage_30d_in_currency")
    ranked = sorted([c for c in coins if c30(c) is not None], key=c30, reverse=True)
    best, worst = (ranked[0], ranked[-1]) if ranked else (coins[0], coins[-1])
    up = sum(1 for c in coins if (c30(c) or 0) > 0)
    _, exchanges = load_providers()
    ex_links = ", ".join(f"[{x['name']}](/exchanges/{x['slug']}/)" for x in exchanges)
    b = coins[0]
    title = f"Crypto Market Report {MONTH}: Bitcoin Price, Top 10 Coins & Trending Altcoins"
    desc = f"Crypto market report for {MONTH}: Bitcoin near {money(btc['end'])} ({pct(btc['chg'])} in 30 days), the top 10 cryptocurrencies, best and worst performers and the coins trending right now."
    kw = f"crypto market report {MONTH.lower()}, bitcoin price {MONTH.lower()}, crypto news {MONTH.lower()}, trending crypto {MONTH.lower()}, top 10 cryptocurrencies, ethereum price, best crypto exchange"
    rows = "\n".join(f"| {i} | {c['name']} ({c['symbol'].upper()}) | {money(c.get('current_price'))} | {pct(c.get('price_change_percentage_24h_in_currency'))} | {pct(c.get('price_change_percentage_7d_in_currency'))} | {pct(c30(c))} | {big(c.get('market_cap'))} |"
                     for i, c in enumerate(coins, 1))
    trend_rows = "\n".join(f"| {t.get('name')} ({(t.get('symbol') or '').upper()}) | #{t.get('market_cap_rank') or '—'} | {pct(((t.get('data') or {}).get('price_change_percentage_24h') or {}).get('usd'))} |" for t in trending)
    mood = "a strong month for buyers" if up >= 7 else "a weak month, with sellers in control" if up <= 3 else "a mixed month"
    md = front(title, desc, kw, "Market Report", slug) + f"""
Here is our monthly crypto market report for **{MONTH}**, based on live market data at the time of publishing. Over the last 30 days, **{up} of the top 10** cryptocurrencies finished higher — {mood}. Bitcoin {move(btc['chg'])} and is trading near **{money(btc['end'])}**.

> This report is published automatically each month from live market data. Prices move quickly — always check the current price on your exchange before trading.

## Crypto market summary for {MONTH}

- **Bitcoin (BTC):** {money(btc['end'])}, 30-day range {money(btc['low'])} – {money(btc['high'])} ({btc['range']:.1f}% from low to high)
- **Best performer (top 10):** {best['name']} {move(c30(best))}
- **Weakest performer (top 10):** {worst['name']} {move(c30(worst))}
- **Combined market cap of the top 10:** {big(total_cap)}

## Top 10 cryptocurrencies by market cap

| # | Coin | Price | 24h | 7 days | 30 days | Market cap |
|---|---|---|---|---|---|---|
{rows}

*Stablecoins and wrapped tokens are excluded so the list shows real price movers.*

## Bitcoin price this month

Bitcoin started the 30-day period near {money(btc['start'])} and now trades around {money(btc['end'])}, so it {move(btc['chg'])}. The lowest price in the period was {money(btc['low'])} and the highest {money(btc['high'])}. A {btc['range']:.1f}% range means {'volatility was high — futures traders should use smaller position sizes and wider stops' if btc['range'] > 15 else 'volatility was moderate — a good environment for planned, rule-based trades'}.

## Trending coins right now
"""
    if trend_rows:
        md += f"""
These are the coins people are searching for most at the moment, according to CoinGecko's trending list:

| Coin | Market cap rank | 24h change |
|---|---|---|
{trend_rows}

Trending coins often move sharply in both directions. If you trade them, keep positions small and always use a stop loss.
"""
    else:
        md += "\nThe trending list was not available at the time of publishing — check back next month.\n"
    md += f"""
## What this means for traders

1. **Size your positions by risk, not by leverage.** Risk 1–2% of your balance per trade.
2. **Use isolated margin** on futures so one trade cannot drain your whole account.
3. **Watch the 30-day range.** Breaks above {money(btc['high'])} or below {money(btc['low'])} on Bitcoin are levels many traders watch.
4. **Take profits regularly** and move them to your exchange wallet or a hardware wallet.

## Where to trade these coins

Our top-rated exchanges for spot and futures trading are {ex_links}. Compare fees, leverage and licences in our [best crypto exchange](/best-crypto-exchange/) ranking, or get free trade ideas on our [free crypto signals](/free-crypto-signals/) page.

## What was the Bitcoin price in {MONTH}?

At the time of this report Bitcoin traded near {money(btc['end'])}, with a 30-day low of {money(btc['low'])} and a high of {money(btc['high'])}.

## Which crypto performed best in {MONTH}?

Among the top 10 cryptocurrencies by market cap, {best['name']} performed best over 30 days ({pct(c30(best))}), while {worst['name']} was the weakest ({pct(c30(worst))}).

*Data: CoinGecko. This report is for information and education only and is not financial advice.*
"""
    (ARTICLES / f"{slug}.md").write_text(md, encoding="utf-8")
    print("wrote", slug); return True


# ---------------------------------------------------------------- gold & forex
def fx_series(start, end):
    syms = "EUR,GBP,JPY,CHF,AUD,CAD"
    for url in (f"https://api.frankfurter.dev/v1/{start}..{end}?base=USD&symbols={syms}",
                f"https://api.frankfurter.app/{start}..{end}?from=USD&to={syms}"):
        try:
            return fetch(url, tries=2)["rates"]
        except (RuntimeError, KeyError):
            continue
    raise RuntimeError("forex data unavailable")


def gold_forex_report():
    slug = f"gold-forex-market-report-{MSLUG}"
    if (ARTICLES / f"{slug}.md").exists():
        print("gold/forex report already exists"); return False
    gold = series_stats([p[1] for p in fetch(f"{CG}/coins/pax-gold/market_chart?vs_currency=usd&days=30")["prices"]])
    rates = fx_series((TODAY - timedelta(days=31)).isoformat(), TODAY.isoformat())
    days = sorted(rates)
    if len(days) < 10:
        raise RuntimeError("not enough forex data")
    pairs = {
        "EUR/USD": [1 / rates[d]["EUR"] for d in days], "GBP/USD": [1 / rates[d]["GBP"] for d in days],
        "USD/JPY": [rates[d]["JPY"] for d in days], "USD/CHF": [rates[d]["CHF"] for d in days],
        "AUD/USD": [1 / rates[d]["AUD"] for d in days], "USD/CAD": [rates[d]["CAD"] for d in days],
    }
    st = {k: series_stats(v) for k, v in pairs.items()}
    dec = lambda k: 2 if "JPY" in k else 4
    fmt = lambda k, v: f"{v:.{dec(k)}f}"
    usd_strength = statistics.mean([-st["EUR/USD"]["chg"], -st["GBP/USD"]["chg"], st["USD/JPY"]["chg"], st["USD/CHF"]["chg"], -st["AUD/USD"]["chg"], st["USD/CAD"]["chg"]])
    usd_word = "strengthened" if usd_strength > 0.3 else "weakened" if usd_strength < -0.3 else "was broadly steady"
    brokers, _ = load_providers()
    br_links = ", ".join(f"[{x['name']}](/brokers/{x['slug']}/)" for x in brokers)
    rows = "\n".join(f"| {k} | {fmt(k, s['start'])} | {fmt(k, s['end'])} | {pct(s['chg'])} | {fmt(k, s['low'])} – {fmt(k, s['high'])} |" for k, s in st.items())
    mover = max(st.items(), key=lambda kv: abs(kv[1]["chg"]))
    title = f"Gold & Forex Market Report {MONTH}: XAUUSD Price, EUR/USD, GBP/USD & USD/JPY"
    desc = f"Gold and forex market report for {MONTH}: gold (XAUUSD) near {money(gold['end'])} ({pct(gold['chg'])} in 30 days), plus EUR/USD, GBP/USD, USD/JPY and the US dollar trend."
    kw = f"gold price {MONTH.lower()}, xauusd {MONTH.lower()}, forex market report {MONTH.lower()}, eurusd {MONTH.lower()}, gbpusd, usdjpy, us dollar trend, best forex broker"
    md = front(title, desc, kw, "Market Report", slug) + f"""
Welcome to our gold and forex market report for **{MONTH}**, built from live market data at the time of publishing. Over the last 30 days gold {move(gold['chg'])} to around **{money(gold['end'])} per ounce**, while the US dollar {usd_word} against the major currencies.

> This report is published automatically each month. Forex rates are European Central Bank reference rates; gold is tracked through the PAX Gold (PAXG) token, which follows the price of one troy ounce. Always check live prices on your trading platform.

## Gold (XAUUSD) price this month

| | Price |
|---|---|
| 30 days ago | {money(gold['start'])} |
| Now | {money(gold['end'])} |
| 30-day high | {money(gold['high'])} |
| 30-day low | {money(gold['low'])} |
| Change | {pct(gold['chg'])} |

Gold traded in a {gold['range']:.1f}% range this month. {'That is a wide range — gold traders should reduce lot sizes, as a 0.10 lot moves $10 for every $1 change in price.' if gold['range'] > 6 else 'That is a relatively calm range, which suits trend-following and pullback strategies.'} Many traders watch the 30-day high of {money(gold['high'])} and low of {money(gold['low'])} as key levels.

## Major forex pairs: 30-day performance

| Pair | 30 days ago | Now | Change | 30-day range |
|---|---|---|---|---|
{rows}

The biggest mover among the majors was **{mover[0]}**, which {move(mover[1]['chg'])}.

## US dollar trend

Averaged across the six major pairs, the US dollar {usd_word} this month. {'A stronger dollar usually puts pressure on gold and on EUR/USD and GBP/USD.' if usd_strength > 0.3 else 'A softer dollar usually supports gold and lifts EUR/USD and GBP/USD.' if usd_strength < -0.3 else 'With the dollar steady, pair-specific news and interest-rate expectations drove most of the moves.'}

## What this means for traders

1. **Check the economic calendar.** US CPI, Non-Farm Payrolls and central-bank decisions cause the biggest moves in gold and the dollar.
2. **Risk 1–2% per trade** and always place a stop loss.
3. **Trade the London–New York overlap** (about 13:00–17:00 GMT) for the best liquidity in gold and major pairs.
4. Read our [gold trading guide](/guides/how-to-trade-gold-xauusd/) and [risk management guide](/guides/risk-management-for-traders/).

## Best brokers for gold and forex

Our top-rated brokers for gold and forex are {br_links}. See the full [best forex broker](/best-forex-broker/) ranking, or get free gold and forex trade ideas on our [free forex signals](/free-forex-signals/) page.

## What was the gold price in {MONTH}?

At the time of this report gold traded near {money(gold['end'])} per ounce, with a 30-day range of {money(gold['low'])} to {money(gold['high'])}.

*Data: CoinGecko (PAXG) and Frankfurter (ECB reference rates). This report is for information and education only and is not financial advice.*
"""
    (ARTICLES / f"{slug}.md").write_text(md, encoding="utf-8")
    print("wrote", slug); return True


# ---------------------------------------------------------------- queued evergreen article
def release_queued():
    log = json.loads(LOG.read_text(encoding="utf-8")) if LOG.exists() else {"released": {}}
    if YM in log["released"]:
        print("queued article already released this month:", log["released"][YM]); return False
    for f in sorted(QUEUE.glob("*.md")) if QUEUE.exists() else []:
        slug = re.sub(r"^\d+-", "", f.stem)
        target = ARTICLES / f"{slug}.md"
        if target.exists():          # already published earlier (e.g. after a site update re-added the queue file)
            f.unlink(); continue
        text = re.sub(r"(?m)^date:.*$", f"date: {TODAY.isoformat()}", f.read_text(encoding="utf-8"), count=1)
        target.write_text(text, encoding="utf-8")
        f.unlink()
        log["released"][YM] = slug
        LOG.write_text(json.dumps(log, indent=2), encoding="utf-8")
        print("released", slug); return True
    print("queue is empty"); return False


def main():
    ARTICLES.mkdir(parents=True, exist_ok=True)
    for job in (crypto_report, gold_forex_report, release_queued):
        try:
            job()
        except Exception as e:  # noqa: BLE001 — never break the website build
            print(f"skipped {job.__name__}: {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
