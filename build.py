#!/usr/bin/env python3
"""
Static site builder for the Forex & Crypto broker comparison website.

You normally do NOT need to run this yourself: GitHub runs it automatically
every time you change a file (see .github/workflows/deploy.yml).

To preview on your own computer:   python build.py   then open  _site/index.html
Needs only Python 3.8+ (no extra packages).
"""
import html
import itertools
import json
import os
import re
import shutil
import sys
import urllib.parse
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "_site"
DATA = ROOT / "data"

CFG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
# GitHub Actions passes the real address of your site in SITE_URL.
SITE_URL = (os.environ.get("SITE_URL") or CFG["site_url"]).rstrip("/")
SITE = CFG["site_name"]
YEAR = date.today().year
TODAY = date.today().isoformat()
LAST_REVIEWED = date.today().strftime("%B %Y")  # updates automatically on every rebuild

BROKERS = json.loads((DATA / "brokers.json").read_text(encoding="utf-8"))
EXCHANGES = json.loads((DATA / "exchanges.json").read_text(encoding="utf-8"))
COUNTRIES = json.loads((DATA / "countries.json").read_text(encoding="utf-8"))
ALL = BROKERS + EXCHANGES
THE = {"US", "GB", "AE", "NL", "PH", "BS", "GM", "MV", "KY", "VG", "VI", "TC", "MH", "SB", "FO", "CF", "CD", "CG", "DO", "CZ", "VA", "FK", "CK", "KM", "SC", "MP"}
for _c in COUNTRIES:
    _c["in_name"] = ("the " if _c["code"] in THE else "") + _c["name"]
BY_CODE = {c["code"]: c for c in COUNTRIES}

esc = html.escape
PAGES = []  # (path, priority) for sitemap
SANCTIONED = {"IR", "KP", "SY", "CU"}

# --------------------------------------------------------------------------
# Country-specific legal notes (shown on country pages)
# --------------------------------------------------------------------------
NOTES = {
    "IN": "The Reserve Bank of India (RBI) allows residents to trade forex in INR-based pairs on SEBI-recognised Indian exchanges and publishes an Alert List of unauthorised platforms. Crypto is legal to hold and trade, with 30% tax on gains plus 1% TDS, and exchanges serving Indians register with FIU-IND — Binance, Bybit and KuCoin are registered.",
    "PK": "The State Bank of Pakistan and SECP oversee local financial markets, and many Pakistani traders use internationally regulated brokers. Pakistan created the Pakistan Virtual Assets Regulatory Authority (PVARA) in 2025 to license crypto service providers, so check the latest guidance.",
    "US": "US residents may only trade forex with dealers registered with the CFTC and NFA, and CFDs are not offered to US retail traders.",
    "GB": "UK brokers are authorised by the FCA. Retail forex leverage is capped at 1:30 on major pairs, and the FCA does not allow crypto derivatives to be sold to retail consumers. Exness, HFM and Vantage all hold FCA authorisation.",
    "AU": "ASIC caps retail forex leverage at 1:30 on major pairs. IC Markets, Vantage and AvaTrade hold ASIC licences, and crypto exchanges register with AUSTRAC — Bitunix, BingX and KuCoin are registered.",
    "CA": "Forex and CFD dealers in Canada are registered with CIRO and provincial securities regulators.",
    "SG": "The Monetary Authority of Singapore licenses brokers and crypto service providers.",
    "AE": "Forex brokers are licensed by the Capital Market Authority (onshore), the DFSA (DIFC) or the FSRA (ADGM), and crypto firms in Dubai by VARA. HFM holds a DFSA licence, AvaTrade an FSRA licence, and Binance and Bybit hold VARA licences.",
    "CN": "Mainland China restricts capital outflows and does not permit crypto trading.",
    "JP": "Japan's FSA caps retail forex leverage at 1:25, and crypto exchanges register with the FSA. AvaTrade holds a JFSA licence.",
    "HK": "The SFC licenses forex dealers and virtual-asset trading platforms.",
    "FR": "As an EU country, France applies ESMA's 1:30 leverage cap, and crypto platforms need MiCA authorisation. Binance holds an AMF registration, and Bybit and BingX are MiCA-authorised in the EU.",
    "NL": "The AFM supervises brokers and crypto platforms under MiCA.",
    "ZA": "The FSCA licenses forex brokers — Exness, HFM, Vantage, AvaTrade, Octa and PU Prime all hold FSCA licences for local entities. Crypto assets are financial products, so crypto platforms also need FSCA authorisation.",
    "NG": "Nigeria's Investments and Securities Act 2025 classes digital assets as securities under SEC Nigeria. Nigerian traders widely use internationally regulated brokers and exchanges.",
    "KE": "The Capital Markets Authority licenses online forex brokers — Exness (licence 162) and HFM (licence 155) hold CMA licences.",
    "MY": "The Securities Commission Malaysia regulates brokers and registers digital asset exchanges.",
    "ID": "Forex and commodity futures fall under Bappebti and OJK, which also oversee crypto trading.",
    "TR": "Turkey's Capital Markets Board (SPK) regulates brokers, and a 2024 law requires crypto platforms serving Turkish users to be licensed by the SPK.",
    "PH": "The SEC Philippines and BSP regulate brokers and virtual asset service providers.",
    "IL": "The Israel Securities Authority licenses forex dealers — AvaTrade holds an ISA licence.",
    "NZ": "The FMA licenses derivatives issuers in New Zealand.",
    "RU": "International sanctions affect payments to and from Russia, so check payment methods before you register.",
    "BD": "Bangladesh Bank oversees foreign-exchange rules; understand the remittance rules before funding an overseas account.",
    "SA": "The Capital Market Authority licenses securities firms. Saudi traders usually choose swap-free (Islamic) accounts, offered by Exness, Octa, HFM and others.",
    "EG": "The Central Bank of Egypt oversees foreign-currency transfers and licenses crypto activity.",
    "BH": "The Central Bank of Bahrain licenses crypto-asset firms — Binance holds a CBB licence through Binance Bahrain.",
    "KZ": "The Astana International Financial Centre (AIFC) regulates crypto exchanges through the AFSA; Binance and Bybit hold AFSA licences.",
    "IE": "As an EU member state, Ireland applies ESMA rules, including a 1:30 leverage cap on major pairs. AvaTrade's EU business is regulated by the Central Bank of Ireland.",
    "CY": "Cyprus is home to CySEC, which licenses Exness, IC Markets, HFM, AvaTrade and Octa for their EU business.",
    "AT": "As an EU member state, Austria applies ESMA rules. Its regulator, the FMA, has granted MiCA authorisation to Bybit, BingX and KuCoin for their EU entities.",
    "GE": "The National Bank of Georgia licenses virtual asset service providers — Bybit holds an NBG licence.",
}
EU_NOTE = "As an EU member state, {name} applies ESMA rules: retail forex leverage is capped at 1:30 on major pairs, and crypto-asset service providers need MiCA authorisation — Bybit, BingX and KuCoin are MiCA-authorised for the EU."

TIER_LABEL = {"Top-tier": "Top-tier", "Mid-tier": "National regulator", "Offshore": "International", "Licence": "Licence",
              "Registration": "Registration", "AML registration": "Registration", "Company registration": "Registered company"}

# Category labels used on the "best forex broker" / "best crypto exchange" pillar pages
BEST_FOR = {
    "exness": "Best Forex Broker Overall", "ic-markets": "Best Forex Broker for Scalping & EAs", "hfm": "Best Forex Broker for Copy Trading",
    "vantage": "Best Forex Broker for TradingView", "avatrade": "Best Regulated Forex Broker", "octa": "Best Commission-Free Forex Broker",
    "pu-prime": "Best Forex Broker for Cent Accounts", "roboforex": "Best Forex Broker for High Leverage", "instaforex": "Best Forex Broker for a $1 Deposit", "eightcap": "Best Forex Broker for Funded Challenges",
    "bitunix": "Best Crypto Exchange Overall", "bybit": "Best Licensed Crypto Exchange", "binance": "Best Crypto Exchange for Beginners",
    "bingx": "Best Crypto Exchange for Copy Trading", "mexc": "Best Crypto Exchange for Altcoins & Low Fees", "blofin": "Best Crypto Exchange for Pro Futures",
    "kucoin": "Best Crypto Exchange for Trading Bots", "bitbase": "Best Crypto Exchange for USDC Futures",
}


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def rel(depth):
    return "../" * depth


def link(path, depth):
    path = path.lstrip("/")
    return (rel(depth) + path) or "./"


def is_fx(b):
    return b["type"] == "forex"


def base_of(b):
    return "brokers/" if is_fx(b) else "exchanges/"


def review_path(b):
    return f"{base_of(b)}{b['slug']}/"


def status_for(brand, code):
    if code in brand.get("restricted", []) or code in SANCTIONED:
        return "no"
    if code in brand.get("unclear", []):
        return "check"
    return "yes"


def initials(b):
    return "".join(w[0] for w in b["name"].replace("-", " ").split())[:2].upper()


def logo(b, size=""):
    """Company icon (official site favicon) with an initials fallback."""
    src = f"https://www.google.com/s2/favicons?domain={b['domain']}&sz=128"
    return (f'<span class="logo {size}" style="--brand:{b["color"]}">'
            f'<i aria-hidden="true">{esc(initials(b))}</i>'
            f'<img src="{src}" alt="{esc(b["name"])} logo" loading="lazy" decoding="async" width="64" height="64" onload="if(this.naturalWidth>16)this.parentNode.classList.add(&quot;has-img&quot;)" onerror="this.remove()"></span>')


def visit_buttons(b, small=False, first_only=False):
    cls = "btn " + ("btn-fx" if is_fx(b) else "btn-cx") + (" btn-sm" if small else "")
    links = b["links"][:1] if first_only else b["links"]
    return "".join(
        f'<a class="{cls}" href="{esc(l["url"])}" target="_blank" rel="sponsored nofollow noopener">{esc(l["label"])} <span aria-hidden="true">↗</span></a>'
        for l in links)


def tier_badge(t):
    cls = {"Top-tier": "t1", "Mid-tier": "t2", "Offshore": "t2", "Licence": "t2", "Registration": "t2",
           "AML registration": "t2", "Company registration": "t4"}.get(t, "t2")
    return f'<span class="tier {cls}">{esc(TIER_LABEL.get(t, t))}</span>'


def has_top(b):
    return any(l["tier"] == "Top-tier" for l in b["licences"])


def licence_countries(b):
    seen = []
    for l in b["licences"]:
        c = BY_CODE.get(l["country"])
        if c and c["code"] not in [x["code"] for x in seen]:
            seen.append(c)
    return seen


def safety_level(b):
    tiers = {l["tier"] for l in b["licences"]}
    if "Top-tier" in tiers:
        return "High", "ok"
    if tiers & {"Mid-tier", "Licence"}:
        return "Medium", "warn"
    if tiers & {"AML registration", "Registration", "Offshore"}:
        return "Basic", "warn"
    return "Low", "bad"


def not_served(b):
    return sorted({BY_CODE[c]["name"] for c in b["restricted"] if c in BY_CODE} | {BY_CODE[c]["name"] for c in SANCTIONED})


def jsonld(obj):
    return '<script type="application/ld+json">' + json.dumps(obj, ensure_ascii=False) + "</script>"


def breadcrumb_ld(items):
    return {"@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": n, "item": f"{SITE_URL}/{p}"}
                                for i, (n, p) in enumerate(items)]}


def faq_ld(faqs):
    return {"@context": "https://schema.org", "@type": "FAQPage",
            "mainEntity": [{"@type": "Question", "name": q,
                            "acceptedAnswer": {"@type": "Answer", "text": re.sub("<[^>]+>", "", a)}} for q, a in faqs]}


def faq_html(faqs, title="Frequently asked questions"):
    items = "".join(f"<details><summary>{esc(q)}</summary><div>{a}</div></details>" for q, a in faqs)
    return f'<section class="faq"><h2>{title}</h2>{items}</section>'


def crumbs_html(items, depth):
    parts = []
    for i, (n, p) in enumerate(items):
        parts.append(f'<span aria-current="page">{esc(n)}</span>' if i == len(items) - 1 else f'<a href="{link(p, depth)}">{esc(n)}</a>')
    return '<nav class="crumbs" aria-label="Breadcrumb">' + " › ".join(parts) + "</nav>"


def itemlist_ld(name, items):
    return {"@context": "https://schema.org", "@type": "ItemList", "name": name,
            "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": b["name"], "url": f"{SITE_URL}/{review_path(b)}"}
                                for i, b in enumerate(items)]}


# --------------------------------------------------------------------------
# Page shell
# --------------------------------------------------------------------------
NAV = [("Forex Brokers", "forex-brokers/", "fx"), ("Crypto Exchanges", "crypto-exchanges/", "cx"),
       ("Compare", "compare/", ""), ("Licences", "licences/", ""), ("Countries", "countries/", ""),
       ("Free Signals", "free-signals/", ""), ("Blog", "blog/", "")]


def tg_url(handle):
    h = handle.strip()
    if h.startswith("http"):
        return h
    return "https://t.me/" + h.lstrip("@").replace("t.me/", "").replace("T.me/", "")


def sig_cfg(kind):
    fx = kind == "forex"
    return {
        "channel": tg_url(CFG.get("telegram_forex_signals_url" if fx else "telegram_crypto_signals_url",
                                  "https://t.me/AforexKingOfficial" if fx else "https://t.me/AlicecryptoPro_Official")),
        "admin": CFG.get("telegram_forex_admin" if fx else "telegram_crypto_admin", "AforexKingAdmin" if fx else "AliceSupportTeam").lstrip("@").split("/")[-1],
    }


def admin_msg(kind, name, acct=""):
    fx = kind == "forex"
    msg = f"Hey 👋 I am using your partner {'broker' if fx else 'exchange'} Name:- {name}"
    if acct:
        msg += f"\n{'Account ID' if fx else 'UID'}:- {acct}"
    return msg


def admin_link(kind, name):
    return f"https://t.me/{sig_cfg(kind)['admin']}?text=" + urllib.parse.quote(admin_msg(kind, name))


def admin_box(kind, preset=None):
    """Card: 'Already trading with a partner broker? Message our admin' with a broker picker."""
    fx = kind == "forex"
    items = BROKERS if fx else EXCHANGES
    word = "broker" if fx else "exchange"
    first = preset or items[0]
    opts = "".join(f'<option value="{esc(b["name"])}"{" selected" if b["slug"] == first["slug"] else ""}>{esc(b["name"])}</option>' for b in items)
    return f"""<div class="tg-box {'fx' if fx else 'cx'}" data-kind="{kind}" data-admin="{esc(sig_cfg(kind)['admin'])}">
 <span class="kicker {'fx' if fx else 'cx'}">FOR OUR PARTNER CLIENTS</span>
 <h3>Already trading with one of our partner {word}s?</h3>
 <p>Get our {'forex' if fx else 'crypto'} signals <strong>free</strong>. Choose your {word} and tap the button — Telegram opens a chat with our admin with your message already written.</p>
 <div class="tg-form">
  <label><span>Your {word}</span><select class="tg-broker" aria-label="Your {word}">{opts}</select></label>
  <label><span>{'Account ID' if fx else 'UID'} (optional)</span><input class="tg-id" inputmode="numeric" placeholder="e.g. 12345678"></label>
 </div>
 <p class="tg-preview" aria-live="polite">“{esc(admin_msg(kind, first['name']))}”</p>
 <a class="btn btn-tg tg-go" href="{esc(admin_link(kind, first['name']))}" target="_blank" rel="noopener">✈ Message @{esc(sig_cfg(kind)['admin'])} on Telegram</a>
</div>"""





TICKER_SYMBOLS = [("OANDA:XAUUSD", "Gold"), ("BINANCE:BTCUSDT", "Bitcoin"), ("OANDA:US30USD", "US30"), ("OANDA:NAS100USD", "NAS100"),
                  ("FX:EURUSD", "EUR/USD"), ("FX:GBPUSD", "GBP/USD"), ("BINANCE:ETHUSDT", "Ethereum"), ("OANDA:SPX500USD", "S&P 500"),
                  ("TVC:USOIL", "WTI Oil"), ("OANDA:XAGUSD", "Silver"), ("FX:USDJPY", "USD/JPY"), ("BINANCE:SOLUSDT", "Solana"),
                  ("BINANCE:XRPUSDT", "XRP"), ("OANDA:DE30EUR", "GER40")]
MARKET_BLOCKS = [("OANDA:XAUUSD", "Gold", "XAU/USD", "gold"), ("BINANCE:BTCUSDT", "Bitcoin", "BTC/USDT", "cx"),
                 ("OANDA:US30USD", "US30", "Dow Jones", "fx"), ("OANDA:NAS100USD", "NAS100", "Nasdaq 100", "fx"),
                 ("FX:EURUSD", "EUR/USD", "Euro / Dollar", "fx"), ("BINANCE:ETHUSDT", "Ethereum", "ETH/USDT", "cx"),
                 ("FX:GBPUSD", "GBP/USD", "Pound / Dollar", "fx"), ("OANDA:SPX500USD", "S&P 500", "US500", "fx"),
                 ("TVC:USOIL", "WTI Oil", "Crude oil", "gold"), ("OANDA:XAGUSD", "Silver", "XAG/USD", "gold"),
                 ("FX:USDJPY", "USD/JPY", "Dollar / Yen", "fx"), ("BINANCE:SOLUSDT", "Solana", "SOL/USDT", "cx")]


def ticker_tape():
    cfg = {"symbols": [{"proName": s, "title": t} for s, t in TICKER_SYMBOLS], "showSymbolLogo": True, "isTransparent": True,
           "displayMode": "adaptive", "colorTheme": "dark", "locale": "en"}
    fallback = "".join(f"<span>{esc(t)}</span>" for _, t in TICKER_SYMBOLS[:8])
    return (f'<div class="tape" aria-label="Live market prices"><div class="tradingview-widget-container"><div class="tradingview-widget-container__widget"><div class="tape-fallback">{fallback}</div></div>'
            f'<script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-ticker-tape.js" async>{json.dumps(cfg)}</script></div></div>')


def market_blocks(title=None, depth=0):
    blocks = []
    for sym, name, sub, tone in MARKET_BLOCKS:
        cfg = {"symbol": sym, "width": "100%", "isTransparent": True, "colorTheme": "dark", "locale": "en"}
        blocks.append(f'<div class="mblock {tone}"><div class="mb-head"><b>{esc(name)}</b><small>{esc(sub)}</small></div>'
                      f'<div class="tradingview-widget-container"><div class="tradingview-widget-container__widget"></div><div class="mb-loading">Loading live price…</div>'
                      f'<script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-single-quote.js" async>{json.dumps(cfg)}</script></div></div>')
    head = f'<div class="sec-head"><div><span class="kicker" style="color:#8ab6ff">LIVE MARKETS</span><h2>{title or "Live Market Prices"}</h2></div><span class="live"><i></i> Live prices</span></div>'
    return f'<section class="markets"><div class="wrap section">{head}<div class="mgrid">{"".join(blocks)}</div><p class="tiny mnote">Gold, Bitcoin, US30, NAS100 and the world\'s top markets — real-time quotes powered by TradingView.</p></div></section>'


def short_title(title, limit=65):
    """Search engines show about 60-70 characters. Keep the keyword-rich start, add the brand only if it fits."""
    core = re.sub(r"\s*\|\s*" + re.escape(SITE) + r"\s*$", "", title).strip()
    if len(core) > limit:
        for sep in (" – ", ": ", " - "):
            head = core.split(sep)[0].strip()
            if 20 <= len(head) <= limit and head != core:
                core = head
                break
    if len(core) > limit:
        core = core[:limit].rsplit(" ", 1)[0].rstrip(" ,:–-&")
    full = f"{core} | {SITE}"
    return full if len(full) <= limit else core


def short_desc(text, limit=155):
    """Search engines show about 150-160 characters of the description."""
    d = re.sub(r"\s+", " ", text).strip()
    if len(d) <= limit:
        return d
    cut = d[:limit]
    end = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
    if end >= 70:
        return cut[:end + 1]
    return cut.rsplit(" ", 1)[0].rstrip(" ,:;–-&(") + "…"


def page(path, title, description, body, depth, keywords="", ld=None, priority="0.6", og_type="website", canonical=None, in_sitemap=True,
         noindex=False, theme="", image=None):
    url = f"{SITE_URL}/{path}"
    ld_html = "".join(jsonld(x) for x in (ld or []))
    ga = ""
    if CFG.get("google_analytics_id"):
        gid = esc(CFG["google_analytics_id"])
        ga = (f'<script async src="https://www.googletagmanager.com/gtag/js?id={gid}"></script>'
              f"<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments)}}gtag('js',new Date());gtag('config','{gid}');</script>")
    verify = f'<meta name="google-site-verification" content="{esc(CFG["google_site_verification"])}">' if CFG.get("google_site_verification") else ""
    r = rel(depth)
    og_img = f"{SITE_URL}/{image}" if image else f"{SITE_URL}/assets/og-image.png"
    nav_html = "".join(f'<a class="{c}" href="{link(p, depth)}">{n}</a>' for n, p, c in NAV)
    pop = ["AE", "BR", "DE", "EG", "ID", "IN", "KE", "MX", "NG", "PH", "PK", "TR", "VN", "ZA"]
    doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(short_title(title))}</title>
<meta name="description" content="{esc(short_desc(description))}">
{f'<meta name="keywords" content="{esc(keywords)}">' if keywords else ''}
<meta name="robots" content="{'noindex, follow' if noindex else 'index, follow, max-image-preview:large'}">
<link rel="canonical" href="{esc(f"{SITE_URL}/{canonical}" if canonical is not None else url)}">
<meta property="og:type" content="{og_type}">
<meta property="og:site_name" content="{esc(SITE)}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(short_desc(description, 200))}">
<meta property="og:url" content="{esc(url)}">
<meta property="og:image" content="{og_img}">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#070d1d">
<link rel="icon" href="{r}assets/favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://www.google.com">
<link rel="stylesheet" href="{r}assets/style.css">
{verify}{ga}{ld_html}
</head>
<body class="{theme}">
<a class="skip" href="#main">Skip to content</a>
<div class="riskbar">Trading forex, CFDs and crypto with leverage carries a high risk of losing money. <a href="{link('risk-disclaimer/', depth)}">Risk warning</a></div>
<header class="top">
 <div class="wrap top-in">
  <a class="brand" href="{link('', depth)}"><img src="{r}assets/favicon.svg" alt="" width="32" height="32"> <span>{esc(SITE)}</span></a>
  <button class="menu-btn" aria-label="Menu" aria-expanded="false" onclick="this.setAttribute('aria-expanded',document.body.classList.toggle('nav-open'))">☰</button>
  <nav class="mainnav" aria-label="Main">{nav_html}</nav>
 </div>
</header>
{ticker_tape()}
<main id="main">
{body}
</main>
<footer class="foot">
 <div class="wrap foot-grid">
  <div><p class="brand"><img src="{r}assets/favicon.svg" alt="" width="28" height="28"> {esc(SITE)}</p><p>{esc(CFG['site_tagline'])}. Independent comparisons of forex brokers and crypto exchanges for traders in {len(COUNTRIES)} countries and territories worldwide.</p>
  <p><a class="btn btn-tg" href="{esc(CFG['telegram_url'])}" target="_blank" rel="noopener">Join our Telegram</a></p></div>
  <div><h3>Forex</h3><a href="{link('best-forex-broker/', depth)}">Best forex broker {YEAR}</a><a href="{link('forex-brokers/', depth)}">All forex brokers</a><a href="{link('forex-brokers/compare/', depth)}">Forex comparison table</a>{''.join(f'<a href="{link(review_path(b), depth)}">{esc(b["name"])} review</a>' for b in BROKERS)}<a href="{link('free-forex-signals/', depth)}">Free forex signals</a></div>
  <div><h3>Crypto</h3><a href="{link('best-crypto-exchange/', depth)}">Best crypto exchange {YEAR}</a><a href="{link('crypto-exchanges/', depth)}">All crypto exchanges</a><a href="{link('crypto-exchanges/compare/', depth)}">Crypto comparison table</a>{''.join(f'<a href="{link(review_path(b), depth)}">{esc(b["name"])} review</a>' for b in EXCHANGES)}<a href="{link('free-crypto-signals/', depth)}">Free crypto signals</a></div>
  <div><h3>By country</h3>{''.join(f'<a href="{link("countries/" + BY_CODE[c]["slug"] + "/", depth)}">{esc(BY_CODE[c]["name"])}</a>' for c in pop[:10])}<a href="{link('countries/', depth)}"><strong>All {len(COUNTRIES)} countries →</strong></a></div>
  <div><h3>Company</h3><a href="{link('about/', depth)}">About & methodology</a><a href="{link('licences/', depth)}">Licences & regulation</a><a href="{link('contact/', depth)}">Contact</a><a href="{link('risk-disclaimer/', depth)}">Risk disclaimer</a><a href="{link('privacy-policy/', depth)}">Privacy policy</a><a href="{link('terms/', depth)}">Terms of use</a></div>
 </div>
 <div class="wrap legal"><p><strong>Risk warning:</strong> CFDs, forex and crypto derivatives are complex instruments with a high risk of losing money rapidly due to leverage. Most retail accounts lose money. Nothing on this site is financial advice. Information is checked as of {esc(LAST_REVIEWED)} but can change — always confirm terms, regulation and country availability on the provider's official website. Company names and logos belong to their owners and are used only to identify them.</p>
 <p>© <span class="yr">{YEAR}</span> {esc(SITE)}. All rights reserved.</p></div>
</footer>
<script src="{r}assets/main.js" defer></script>
</body>
</html>
"""
    out = OUT / "index.html" if path == "" else (OUT / path if path.endswith(".html") else OUT / path / "index.html")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(doc, encoding="utf-8")
    if not noindex:
        if in_sitemap:
            PAGES.append((path, priority))


# --------------------------------------------------------------------------
# Reusable blocks
# --------------------------------------------------------------------------
def brand_card(b, rank, depth, country=None):
    review = link(review_path(b), depth)
    badge = ""
    if country:
        st = status_for(b, country["code"])
        badge = (f'<span class="pill ok">✓ Accepts traders from {esc(country["in_name"])}</span>' if st == "yes"
                 else f'<span class="pill warn">Confirm {esc(country["in_name"])} at sign-up</span>')
    top = '<span class="ribbon">★ Top pick</span>' if b.get("top_pick") else ""
    if is_fx(b):
        facts = [("Min deposit", b["min_deposit"]), ("Max leverage", b["max_leverage"]), ("Spreads", b["spreads"]), ("Platforms", b["platforms"])]
    else:
        facts = [("Min deposit", b["min_deposit"]), ("Max leverage", b["max_leverage"]), ("Fees", b["fees"]), ("Markets", b["coins"])]
    facts_html = "".join(f"<div><dt>{k}</dt><dd>{esc(v)}</dd></div>" for k, v in facts)
    pros = "".join(f"<li>{esc(p)}</li>" for p in b["pros"][:3])
    regs = "".join(f'<span class="regchip" title="{esc(l["regulator"])}">{BY_CODE[l["country"]]["flag"] if l["country"] in BY_CODE else ""} {esc(short_reg(l))}</span>' for l in b["licences"][:6])
    return f"""<article class="card brand-card {'fx' if is_fx(b) else 'cx'}" id="{b['slug']}">
 {top}
 <div class="bc-head">
  <span class="rank">#{rank}</span>{logo(b)}
  <div class="bc-name"><h3><a href="{review}">{esc(b['name'])}</a></h3><p class="muted">{esc(b['tagline'])}</p></div>
  <div class="score" title="Our editorial score"><b>{b['score']:.1f}</b><small>/10</small></div>
 </div>
 {badge}
 <dl class="facts">{facts_html}</dl>
 <div class="regs"><span class="regs-label">Regulated / registered:</span>{regs}</div>
 <ul class="ticks">{pros}</ul>
 <div class="bc-cta">{visit_buttons(b)}<a class="btn btn-ghost" href="{review}">Review</a></div>
</article>"""


def short_reg(l):
    r = l["regulator"]
    if "MiCA" in r:
        return "MiCA (" + (BY_CODE[l["country"]]["name"] if l["country"] in BY_CODE else "EU") + ")"
    if r.startswith("Company registration"):
        return "Registered: " + (BY_CODE[l["country"]]["name"] if l["country"] in BY_CODE else "")
    m = re.findall(r"\(([A-Z][A-Za-z.\- ]{1,14})\)", r)
    if m:
        return m[0].replace("FSC BVI", "FSC")
    return r.split(" – ")[0].split(",")[0].split(" (")[0].strip()[:22]


def compare_table(items, depth, country=None):
    fx = is_fx(items[0])
    head = "<th>" + ("Broker" if fx else "Exchange") + "</th><th>Score</th><th>Min deposit</th><th>Max leverage</th><th>" + ("Spreads" if fx else "Trading fees") + "</th><th>Regulation</th>"
    if country:
        head += f"<th>{esc(country['name'])}</th>"
    head += "<th></th>"
    rows = []
    for b in items:
        cell = ""
        if country:
            st = status_for(b, country["code"])
            cell = "<td>" + ('<span class="pill ok">✓ Available</span>' if st == "yes" else '<span class="pill warn">Check at sign-up</span>') + "</td>"
        rows.append(f"<tr><td><a class='tname' href='{link(review_path(b), depth)}'>{logo(b, 'sm')} {esc(b['name'])}</a></td><td><b class='sc'>{b['score']:.1f}</b></td>"
                    f"<td>{esc(b['min_deposit'])}</td><td>{esc(b['max_leverage'])}</td><td>{esc(b['spreads'] if fx else b['fees'])}</td><td>{esc(reg_summary(b))}</td>{cell}"
                    f"<td>{visit_buttons(b, small=True, first_only=True)}</td></tr>")
    return f'<div class="table-wrap"><table class="compare"><thead><tr>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'


def full_matrix(items, depth):
    fx = is_fx(items[0])
    rows = [("Our score", lambda b: f"<b class='sc'>{b['score']:.1f}</b>/10"),
            ("Founded", lambda b: esc(b["founded"])),
            ("Minimum deposit", lambda b: esc(b["min_deposit"])),
            ("Max leverage", lambda b: esc(b["max_leverage"]))]
    if fx:
        rows += [("Spreads & commission", lambda b: esc(b["spreads"])), ("Platforms", lambda b: esc(b["platforms"]))]
    else:
        rows += [("Trading fees", lambda b: esc(b["fees"])), ("Coins / markets", lambda b: esc(b["coins"])),
                 ("Products", lambda b: esc(b["features"])), ("Verification", lambda b: esc(b["kyc"]))]
    rows += [("Copy trading", lambda b: esc(b["copy_trading"])),
             ("Licences / registrations", lambda b: "<br>".join(f"{BY_CODE[l['country']]['flag'] if l['country'] in BY_CODE else ''} {esc(short_reg(l))} {tier_badge(l['tier'])}" for l in b["licences"])),
             ("Regulated in", lambda b: ", ".join(esc(c["name"]) for c in licence_countries(b))),
             ("Available in", lambda b: f"~{available_count(b)} countries"),
             ("Best for", lambda b: esc(b["best_for"])),
             ("", lambda b: visit_buttons(b, small=True))]
    head = "<th class='stick'></th>" + "".join(f"<th><a class='tname col' href='{link(review_path(b), depth)}'>{logo(b, 'sm')} {esc(b['name'])}</a></th>" for b in items)
    body = "".join(f"<tr><th class='stick'>{k}</th>" + "".join(f"<td>{fn(b)}</td>" for b in items) + "</tr>" for k, fn in rows)
    return f'<div class="table-wrap matrix-wrap"><table class="matrix"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def licences_table(b, depth):
    rows = "".join(
        f"<tr><td>{BY_CODE[l['country']]['flag'] if l['country'] in BY_CODE else ''} {esc(BY_CODE[l['country']]['name'] if l['country'] in BY_CODE else l['country'])}</td>"
        f"<td>{esc(l['regulator'])}</td><td>{esc(l['entity'])}</td><td><code>{esc(l['number'])}</code></td><td>{tier_badge(l['tier'])}</td></tr>"
        for l in b["licences"])
    return (f'<div class="table-wrap"><table class="lic"><thead><tr><th>Country</th><th>Regulator / register</th><th>Entity</th><th>Licence no.</th><th>Type</th></tr></thead><tbody>{rows}</tbody></table></div>'
            f'<p class="tiny">You can confirm any licence on the regulator\'s official register.</p>')


def country_search(depth, kind="forex-brokers", placeholder="Search your country…"):
    sel_fx = " selected" if kind == "forex-brokers" else ""
    sel_cx = " selected" if kind == "crypto-exchanges" else ""
    return f"""<form class="csearch" role="search" onsubmit="return false">
 <label for="cq" class="sr">Find your country</label>
 <input id="cq" list="clist" placeholder="{placeholder}" autocomplete="off" data-base="{rel(depth)}">
 <select id="ckind" aria-label="What to compare"><option value="forex-brokers"{sel_fx}>Forex brokers</option><option value="crypto-exchanges"{sel_cx}>Crypto exchanges</option></select>
 <button class="btn btn-gold" id="cgo" type="button">Search</button>
 <datalist id="clist">{''.join(f'<option value="{esc(c["name"])}" data-slug="{c["slug"]}">' for c in COUNTRIES)}</datalist>
</form>"""


def disclosure_box(depth):
    return ""


# --------------------------------------------------------------------------
# Mini markdown for guides
# --------------------------------------------------------------------------
def inline_md(s, depth):
    s = esc(s, quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<!\*)\*(?!\*)(.+?)\*", r"<em>\1</em>", s)

    def _l(m):
        text, url = m.group(1), m.group(2)
        if url.startswith("/"):
            return f'<a href="{link(url, depth)}">{text}</a>'
        return f'<a href="{url}" target="_blank" rel="noopener">{text}</a>'
    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", _l, s)


def md_to_html(md, depth):
    out, buf, lst, toc = [], [], None, []

    def flush():
        nonlocal buf
        if buf:
            out.append("<p>" + inline_md(" ".join(buf), depth) + "</p>")
            buf = []

    def close_list():
        nonlocal lst
        if lst:
            out.append(f"</{lst}>")
            lst = None
    rows = []

    def flush_table():
        nonlocal rows
        if rows:
            cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows if not re.match(r"^\|?\s*:?-{2,}", r.strip())]
            head, rest = cells[0], cells[1:]
            out.append('<div class="table-wrap"><table class="md-table"><thead><tr>' + "".join(f"<th>{inline_md(c, depth)}</th>" for c in head) + "</tr></thead><tbody>"
                       + "".join("<tr>" + "".join(f"<td>{inline_md(c, depth)}</td>" for c in r) + "</tr>" for r in rest) + "</tbody></table></div>")
            rows = []
    for line in md.splitlines():
        t = line.strip()
        if t.startswith("|"):
            flush(); close_list(); rows.append(t); continue
        flush_table()
        if not t:
            flush(); close_list(); continue
        m = re.match(r"^(#{2,3})\s+(.*)", t)
        if m:
            flush(); close_list()
            lvl, text = len(m.group(1)), m.group(2)
            hid = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
            if lvl == 2:
                toc.append((hid, text))
            out.append(f'<h{lvl} id="{hid}">{inline_md(text, depth)}</h{lvl}>')
            continue
        m = re.match(r"^(-|\d+\.)\s+(.*)", t)
        if m:
            flush()
            kind = "ul" if m.group(1) == "-" else "ol"
            if lst != kind:
                close_list(); out.append(f"<{kind}>"); lst = kind
            out.append(f"<li>{inline_md(m.group(2), depth)}</li>")
            continue
        if t.startswith(">"):
            flush(); close_list()
            out.append(f'<div class="callout">{inline_md(t.lstrip("> "), depth)}</div>')
            continue
        close_list()
        buf.append(t)
    flush(); close_list(); flush_table()
    return "\n".join(out), toc


def load_articles():
    arts = []
    for f in sorted((DATA / "articles").glob("*.md")):
        raw = f.read_text(encoding="utf-8")
        meta, body = {}, raw
        if raw.startswith("---"):
            _, head, body = raw.split("---", 2)
            for line in head.strip().splitlines():
                k, _, v = line.partition(":")
                meta[k.strip()] = v.strip()
        meta["slug"] = meta.get("slug") or f.stem
        meta["body"] = body
        img = ROOT / "assets" / "img" / f"{meta['slug']}.jpg"
        meta["image"] = f"assets/img/{meta['slug']}.jpg" if img.exists() else None
        arts.append(meta)
    arts.sort(key=lambda a: a.get("date", ""), reverse=True)
    return arts


ARTICLES = load_articles()


def nice_date(d):
    try:
        return datetime.strptime(d, "%Y-%m-%d").strftime("%d %b %Y")
    except (ValueError, TypeError):
        return d or ""


def cat_slug(c):
    return re.sub(r"[^a-z0-9]+", "-", (c or "guide").lower()).strip("-")


def article_cards(arts, depth, cls="g3"):
    def card(a):
        img = f'<img src="{rel(depth)}{a["image"]}" alt="{esc(a["title"])}" loading="lazy" width="2400" height="1260">' if a["image"] else ""
        return (f'<a class="card art-card" data-cat="{cat_slug(a.get("category"))}" href="{link("guides/" + a["slug"] + "/", depth)}"><div class="thumb">{img}</div><div class="art-body">'
                f'<div class="art-meta"><span class="tag">{esc(a.get("category", "Guide"))}</span><time datetime="{esc(a.get("date", ""))}">{esc(nice_date(a.get("date")))}</time></div>'
                f'<h3>{esc(a["title"])}</h3><p>{esc(a["description"])}</p>'
                f'<span class="more">Read article →</span></div></a>')
    return f'<div class="grid {cls}">' + "".join(card(a) for a in arts) + "</div>"


ORG_LD = {"@context": "https://schema.org", "@type": "Organization", "name": SITE, "url": SITE_URL + "/",
          "logo": SITE_URL + "/assets/og-image.png", "sameAs": [CFG["telegram_url"]]}
SITE_LD = {"@context": "https://schema.org", "@type": "WebSite", "name": SITE, "url": SITE_URL + "/", "description": CFG["site_description"]}


# --------------------------------------------------------------------------
# Home
# --------------------------------------------------------------------------
def build_home():
    d = 0
    popular = ["AE", "AR", "BD", "BR", "CO", "DE", "EG", "ES", "ID", "IN", "IT", "KE", "MA", "MX", "NG", "PH", "PK", "PL", "SA", "TH", "TR", "VN", "ZA", "GH"]
    pop_html = "".join(f'<a class="chip" href="countries/{BY_CODE[c]["slug"]}/">{BY_CODE[c]["flag"]} {esc(BY_CODE[c]["name"])}</a>' for c in popular)
    lic_count = sum(len(b["licences"]) for b in ALL)
    body = f"""
<section class="hero">
 <div class="hero-bg" aria-hidden="true"></div>
 <div class="wrap hero-in">
  <p class="eyebrow"><span class="dot"></span> Updated {esc(LAST_REVIEWED)} · Worldwide · {len(COUNTRIES)} countries</p>
  <h1>Find the Best <span class="g-fx">Forex Broker</span> &amp; <span class="g-cx">Crypto Exchange</span> for Your Country</h1>
  <p class="lead">Licences, minimum deposits, leverage and fees compared side by side — with instant availability checks for every country in the world.</p>
  {country_search(d)}
  <div class="pillar-links"><a class="btn btn-fx" href="best-forex-broker/">Best Forex Broker {YEAR} →</a><a class="btn btn-cx" href="best-crypto-exchange/">Best Crypto Exchange {YEAR} →</a></div>
  <div class="chips">{pop_html}<a class="chip strong" href="countries/">All {len(COUNTRIES)} countries →</a></div>
  <div class="hero-stats">
   <div><b>{len(BROKERS)}</b><span>forex brokers</span></div>
   <div><b>{len(EXCHANGES)}</b><span>crypto exchanges</span></div>
   <div><b>{lic_count}</b><span>licences verified</span></div>
   <div><b>{len(COUNTRIES)}</b><span>country guides</span></div>
  </div>
 </div>
</section>
<section class="split wrap">
 <a class="split-card fx" href="forex-brokers/"><span class="kicker">FOREX · CFDs · GOLD</span><h2>Forex Brokers</h2><p>MT4 / MT5 brokers licensed by the FCA, ASIC, CySEC, DFSA &amp; FSCA. Minimum deposits from $1.</p><span class="logos">{''.join(logo(b, 'sm') for b in BROKERS)}</span><span class="go">Compare forex brokers →</span></a>
 <a class="split-card cx" href="crypto-exchanges/"><span class="kicker">SPOT · FUTURES · COPY TRADING</span><h2>Crypto Exchanges</h2><p>Bitunix, Bybit, Binance, BingX and more — fees, leverage up to 200x, licences and wallets.</p><span class="logos">{''.join(logo(b, 'sm') for b in EXCHANGES)}</span><span class="go">Compare crypto exchanges →</span></a>
</section>
{market_blocks()}
<section class="zone cx-zone">
 <div class="wrap section">
  <div class="sec-head"><div><span class="kicker cx">CRYPTO</span><h2>Best crypto exchanges {YEAR}</h2></div><a href="best-crypto-exchange/">Best crypto exchange guide →</a></div>
  <div class="grid g3">{''.join(brand_card(b, i, d) for i, b in enumerate(EXCHANGES, 1))}</div>
 </div>
</section>
<section class="zone fx-zone">
 <div class="wrap section">
  <div class="sec-head"><div><span class="kicker fx">FOREX</span><h2>Best forex brokers {YEAR}</h2></div><a href="best-forex-broker/">Best forex broker guide →</a></div>
  <div class="grid g3">{''.join(brand_card(b, i, d) for i, b in enumerate(BROKERS, 1))}</div>
 </div>
</section>
<section class="wrap section">
 <div class="sec-head"><div><span class="kicker">TRUST</span><h2>Who regulates them?</h2></div><a href="licences/">All licences →</a></div>
 <div class="grid g4 lic-grid">{''.join(f'<a class="card lic-card" href="{review_path(b)}real-or-fake/">{logo(b)}<b>{esc(b["name"])}</b><span class="pill ok">{len(b["licences"])} licence{"s" if len(b["licences"]) != 1 else ""} / registration{"s" if len(b["licences"]) != 1 else ""}</span><small>{esc(reg_summary(b, 4))}</small></a>' for b in ALL)}</div>
</section>
<section class="band">
 <div class="wrap grid g2">
  <div class="card signal-card fx"><span class="kicker fx">FREE</span><h2>Free Forex Signals</h2><p>XAUUSD gold, US30, NAS100, EURUSD, GBPUSD and more — entry, stop loss and take profit, shared on Telegram with risk-management tips.</p><div class="cta-line"><a class="btn btn-tg" href="{esc(sig_cfg('forex')['channel'])}" target="_blank" rel="noopener">✈ Join free channel</a><a class="btn btn-fx" href="free-forex-signals/">Learn more</a></div><p class="sig-note">Already trading with a partner broker? <a href="{esc(admin_link('forex', BROKERS[0]['name']))}" target="_blank" rel="noopener">Message our admin</a> to get the signals free.</p></div>
  <div class="card signal-card cx"><span class="kicker cx">FREE</span><h2>Free Crypto Signals</h2><p>Bitcoin, Ethereum and altcoin futures setups with clear invalidation levels. Learn position sizing before copying any trade.</p><div class="cta-line"><a class="btn btn-tg" href="{esc(sig_cfg('crypto')['channel'])}" target="_blank" rel="noopener">✈ Join free channel</a><a class="btn btn-cx" href="free-crypto-signals/">Learn more</a></div><p class="sig-note">Already trading with a partner exchange? <a href="{esc(admin_link('crypto', EXCHANGES[0]['name']))}" target="_blank" rel="noopener">Message our admin</a> to get the signals free.</p></div>
 </div>
</section>
<section class="wrap section">
 <div class="sec-head"><div><span class="kicker">BLOG</span><h2>Latest from the blog</h2></div><a href="blog/">All articles →</a></div>
 {article_cards(ARTICLES[:6], d)}
</section>
<section class="wrap section prose">
 <h2>How we choose the best forex broker and best crypto exchange</h2>
 <p>Every provider on {esc(SITE)} is checked against the same criteria: <strong>who licenses it</strong> (with licence numbers), the real minimum deposit, maximum leverage, spreads or trading fees, platforms, copy trading — and <strong>whether it accepts traders from your country</strong>. Our {len(COUNTRIES)} country guides cover every region of the world, from North America and Europe to Africa, the Middle East, Asia and Latin America.</p>
 <p>Read our full rankings of the <a href="best-forex-broker/">best forex broker</a> and the <a href="best-crypto-exchange/">best crypto exchange</a> for {YEAR}, or see our <a href="about/">methodology</a>.</p>
</section>"""
    page("", f"Best Forex Broker & Best Crypto Exchange {YEAR} – Compared by Country | {SITE}", CFG["site_description"], body, d,
         keywords="best forex broker, best crypto exchange, best forex broker " + str(YEAR) + ", best crypto exchange " + str(YEAR) + ", forex brokers by country, crypto exchanges by country, regulated forex broker, best crypto exchange wallet, free forex signals, free crypto signals, Bitunix, Bybit, Binance, BingX, Exness, IC Markets, HFM, AvaTrade",
         ld=[ORG_LD, SITE_LD, itemlist_ld("Best crypto exchanges", EXCHANGES), itemlist_ld("Best forex brokers", BROKERS)], priority="1.0", theme="home")


# --------------------------------------------------------------------------
# Hubs (forex / crypto)
# --------------------------------------------------------------------------
def regions_block(base):
    regions = {}
    for c in COUNTRIES:
        regions.setdefault(c["region"], []).append(c)
    return "".join(
        f'<div class="region"><h3>{esc(r)}</h3><div class="clist">' +
        "".join(f'<a href="{c["slug"]}/">{c["flag"]} {esc(c["name"])}</a>' for c in cs) + "</div></div>"
        for r, cs in sorted(regions.items()))


def build_hub(kind):
    fx = kind == "forex"
    items = BROKERS if fx else EXCHANGES
    path = "forex-brokers/" if fx else "crypto-exchanges/"
    d = 1
    noun = "Forex Brokers" if fx else "Crypto Exchanges"
    pillar = "best-forex-broker/" if fx else "best-crypto-exchange/"
    intro = ("Forex brokers give you access to currency pairs, gold (XAUUSD), indices and other CFDs through MetaTrader 4, MetaTrader 5, cTrader and TradingView. Compare licences, costs, minimum deposits and platforms below."
             if fx else
             "Crypto exchanges let you buy Bitcoin, Ethereum and altcoins and trade perpetual futures with leverage. Compare fees, leverage, coin selection, copy trading and licences below.")
    faqs = ([("Which forex broker has the lowest minimum deposit?", "InstaForex lets you start with just $1, and HFM has a $0 minimum on its Cent, Premium and Zero accounts. Exness and RoboForex start from $10, PU Prime from $20 and Octa from $25."),
             ("Which forex brokers are FCA regulated?", "Exness (FRN 730729), HFM (FRN 801701) and Vantage (OC376560) all have UK entities authorised by the FCA. AvaTrade is regulated by the Central Bank of Ireland, ASIC and Japan's FSA, and IC Markets by ASIC and CySEC."),
             ("Which forex broker is best for scalping and EAs?", "IC Markets is the favourite of scalpers and Expert Advisor traders thanks to raw spreads from 0.0 pips, deep liquidity and cTrader/MT5 support."),
             ("Which forex broker is best for copy trading?", "HFM (HFCOPY), Octa (Octa Copytrading), AvaTrade (AvaSocial, DupliTrade, ZuluTrade), RoboForex (CopyFX) and InstaForex (ForexCopy) all have built-in copy trading.")]
            if fx else
            [("Which crypto exchange is best for futures trading?", "Bitunix is our top pick for crypto futures, with up to 200x leverage, 0.02%/0.06% fees and built-in copy trading. Bybit and Binance offer the deepest liquidity, and BloFin is a strong professional futures platform."),
             ("Which crypto exchanges are licensed?", "Bybit holds a VARA licence in Dubai and MiCA authorisation in the EU; Binance holds licences in Dubai, Abu Dhabi, Bahrain and Kazakhstan; BingX and KuCoin are MiCA-authorised in Austria. Bitunix, BingX and KuCoin are registered with AUSTRAC in Australia."),
             ("Which exchange is best for copy trading?", "BingX is the copy-trading leader, and Bitunix, Bybit, Binance, MEXC, BloFin and KuCoin all offer copy trading too."),
             ("Which exchange has the most coins?", "MEXC lists 2,700+ cryptocurrencies, followed by Bybit with 1,800+ assets and KuCoin and BingX with 1,000+ each.")])
    body = f"""
<section class="pagehead {'fx' if fx else 'cx'}-head"><div class="wrap">
 {crumbs_html([("Home", ""), (noun, path)], d)}
 <span class="kicker">{'FOREX · CFDs · GOLD' if fx else 'CRYPTO · SPOT · FUTURES'}</span>
 <h1>{noun} Compared ({YEAR}): Licences, Fees &amp; Minimum Deposits</h1>
 <p class="lead">{intro}</p>
 {country_search(d, path.strip('/'))}
 <p class="sub-links"><a href="../{pillar}">★ Best {'forex broker' if fx else 'crypto exchange'} {YEAR}</a> · <a href="compare/">Full comparison table</a> · <a href="../licences/">Licences &amp; regulation</a> · <a href="../compare/">Head-to-head comparisons</a></p>
</div></section>
<section class="wrap section">
 {compare_table(items, d)}
 <div class="grid g2">{''.join(brand_card(b, i, d) for i, b in enumerate(items, 1))}</div>
</section>
<section class="wrap section" id="countries">
 <h2>Best {'forex broker' if fx else 'crypto exchange'} in your country</h2>
 <p>Pick your country to see which {noun.lower()} accept traders there, the local regulator and important legal notes.</p>
 {regions_block(path)}
</section>
<section class="wrap section">{faq_html(faqs)}</section>"""
    kw = ("forex brokers, forex brokers " + str(YEAR) + ", compare forex brokers, FCA regulated forex broker, ASIC broker, CySEC broker, low minimum deposit forex broker, ECN broker, MT5 broker, gold trading broker"
          if fx else
          "crypto exchanges, crypto exchanges " + str(YEAR) + ", compare crypto exchanges, crypto futures exchange, low fee crypto exchange, licensed crypto exchange, copy trading crypto, Bitunix, Bybit, Binance, BingX, MEXC, KuCoin, BloFin")
    desc = (f"Compare {len(items)} forex brokers for {YEAR}: {', '.join(b['name'] for b in items)}. FCA/ASIC/CySEC licences, minimum deposits from $1, leverage, spreads and availability worldwide."
            if fx else
            f"Compare {len(items)} crypto exchanges for {YEAR}: {', '.join(b['name'] for b in items)}. Fees, futures leverage, licences, verification and which countries each exchange accepts.")
    page(path, f"{noun} {YEAR}: Compare Licences, {'Spreads' if fx else 'Fees'} & Minimum Deposits | {SITE}", desc, body, d, keywords=kw,
         ld=[itemlist_ld(f"{noun} compared", items), breadcrumb_ld([("Home", ""), (noun, path)]), faq_ld(faqs)], priority="0.9", theme="fx" if fx else "cx")

    cpath = path + "compare/"
    d2 = 2
    body = f"""
<section class="pagehead {'fx' if fx else 'cx'}-head"><div class="wrap">
 {crumbs_html([("Home", ""), (noun, path), ("Comparison table", cpath)], d2)}
 <h1>{noun} Comparison Table {YEAR}</h1>
 <p class="lead">Every quality side by side: licences and licence countries, minimum deposit, leverage, {'spreads, platforms' if fx else 'fees, coins, verification'}, copy trading and availability. Scroll sideways on mobile.</p>
</div></section>
<section class="wrap section">
 {full_matrix(items, d2)}
 <h2>Head-to-head comparisons</h2>
 <div class="clist">{''.join(f'<a href="{link(vs_path(a, b), d2)}">{esc(a["name"])} vs {esc(b["name"])}</a>' for a, b in itertools.combinations(items, 2))}</div>
</section>"""
    page(cpath, f"{noun} Comparison Table {YEAR}: Licences, Fees, Leverage & Deposits | {SITE}",
         f"Side-by-side {noun.lower()} comparison table for {YEAR}: {', '.join(b['name'] for b in items)} — licences, minimum deposit, leverage, {'spreads' if fx else 'fees'}, copy trading and availability.",
         body, d2, keywords=f"{noun.lower()} comparison, compare {noun.lower()}, {noun.lower()} comparison table, " + ", ".join(f"{a['name']} vs {b['name']}" for a, b in list(itertools.combinations(items, 2))[:15]),
         ld=[breadcrumb_ld([("Home", ""), (noun, path), ("Comparison table", cpath)])], priority="0.85", theme="fx" if fx else "cx")


# --------------------------------------------------------------------------
# Brand pages: review, sign-up, real-or-fake
# --------------------------------------------------------------------------
def brand_sidebar(b, d):
    others = [x for x in (BROKERS if is_fx(b) else EXCHANGES) if x["slug"] != b["slug"]]
    rp = review_path(b)
    kind = "forex" if is_fx(b) else "crypto"
    return f"""<aside class="side">
  <div class="card sticky side-cta {'fx' if is_fx(b) else 'cx'}">{logo(b, 'lg')}<h3>{esc(b['name'])}</h3><p class="muted">{esc(b['tagline'])}</p>
  <p><strong>Min deposit:</strong> {esc(b['min_deposit'])}<br><strong>Score:</strong> {b['score']:.1f}/10</p>{visit_buttons(b)}
  <div class="side-sig"><b>Already using {esc(b['name'])}?</b><span>Get our {kind} signals free.</span>
  <a class="btn btn-tg btn-sm" href="{esc(admin_link(kind, b['name']))}" target="_blank" rel="noopener">✈ Message admin</a></div>
  <nav class="brand-nav"><a href="{link(rp, d)}">{esc(b['name'])} review</a><a href="{link(rp + 'sign-up/', d)}">{esc(b['name'])} sign up</a><a href="{link(rp + 'real-or-fake/', d)}">Is {esc(b['name'])} real or fake?</a></nav></div>
  <div class="card"><h3>Compare {esc(b['name'])}</h3><ul class="plain">{''.join(f'<li><a href="{link(vs_path(b, o), d)}">{esc(b["name"])} vs {esc(o["name"])}</a></li>' for o in others)}</ul></div>
 </aside>"""


def vs_path(a, b):
    items = BROKERS if is_fx(a) else EXCHANGES
    order = [x["slug"] for x in items]
    x, y = sorted([a, b], key=lambda z: order.index(z["slug"]))
    return f"compare/{x['slug']}-vs-{y['slug']}/"


def brand_head(b, d, crumbs, h1, lead):
    return f"""<section class="pagehead {'fx' if is_fx(b) else 'cx'}-head"><div class="wrap">
 {crumbs_html(crumbs, d)}
 <div class="review-head">{logo(b, 'xl')}<div><h1>{h1}</h1><p class="lead">{lead}</p></div>
 <div class="score big"><b>{b['score']:.1f}</b><small>/10<br>our score</small></div></div>
 <div class="bc-cta">{visit_buttons(b)}</div>
</div></section>"""


def build_review(b):
    fx = is_fx(b)
    path = review_path(b)
    d = 2
    hub = ("Forex Brokers", "forex-brokers/") if fx else ("Crypto Exchanges", "crypto-exchanges/")
    rows = [("Founded", b["founded"]), ("Minimum deposit", b["min_deposit"] + " — " + b["min_deposit_note"]), ("Max leverage", b["max_leverage"])]
    if fx:
        rows += [("Spreads", b["spreads"]), ("Platforms", b["platforms"])]
    else:
        rows += [("Trading fees", b["fees"]), ("Markets", b["coins"]), ("Products", b["features"]), ("Verification", b["kyc"])]
    rows += [("Copy trading", b["copy_trading"]), ("Regulation", b["regulation"]), ("Best for", b["best_for"])]
    if b.get("ref_code"):
        rows.append(("Referral / invite code", b["ref_code"]))
    table = "".join(f"<tr><th>{esc(k)}</th><td>{esc(v)}</td></tr>" for k, v in rows)
    avail = available_count(b)
    n = b["name"]
    kind = "forex broker" if fx else "crypto exchange"
    faqs = [(f"Is {n} real or fake?", f"{n} is a real, established {kind} operating since {b['founded']}. {esc(b['regulation'])} Always use the official website ({esc(b['domain'])}) to avoid fake copies."),
            (f"What is the {n} minimum deposit?", f"{b['min_deposit']}. {b['min_deposit_note']}"),
            (f"Is {n} regulated?", b["regulation"]),
            (f"What is the maximum leverage at {n}?", b["max_leverage"] + ". Choose leverage that matches your risk plan."),
            (f"Is {n} available in my country?", f"{n} welcomes traders from about {avail} countries and territories. Find your country in our <a href=\"{link('countries/', d)}\">country guides</a> to confirm."),
            (f"How do I sign up for {n}?", f"Use the Visit Site button, register with email or phone, verify your identity and fund your account. See our step-by-step <a href=\"sign-up/\">{esc(n)} sign-up guide</a>.")]
    body = brand_head(b, d, [("Home", ""), hub, (n + " Review", path)], f"{esc(n)} Review {YEAR}", esc(b["tagline"])) + f"""
<section class="wrap section two-col">
 <div class="prose">
  <div class="verdict card"><span class="pill ok">✓ {len(b['licences'])} licence{'s' if len(b['licences']) != 1 else ''} / registration{'s' if len(b['licences']) != 1 else ''}</span> <span class="pill ok">✓ Available in ~{avail} countries</span> <span class="pill">Since {esc(b['founded'])}</span><p>{esc(b['summary'])}</p></div>
  <h2>{esc(n)} key facts</h2><div class="table-wrap"><table class="facts-table">{table}</table></div>
  <div class="card pc"><h3>Why traders choose {esc(n)}</h3><ul class="ticks">{''.join(f'<li>{esc(p)}</li>' for p in b['pros'])}</ul></div>
  <h2 id="licences">{esc(n)} licences &amp; regulation</h2>
  {licences_table(b, d)}
  <h2 id="availability">{esc(n)} country availability</h2>
  <p>{esc(n)} welcomes traders from about <strong>{avail}</strong> countries and territories worldwide. Check your country in our <a href="{link('countries/', d)}">country guides</a>.</p>
  <h2>Related {esc(n)} guides</h2>
  <div class="grid g2"><a class="card mini-link" href="sign-up/"><b>{esc(n)} sign up</b><span>Step-by-step registration{(' with code ' + esc(b['ref_code'])) if b.get('ref_code') else ''}</span></a><a class="card mini-link" href="real-or-fake/"><b>Is {esc(n)} real or fake?</b><span>Licences and how to spot fake copies</span></a></div>
  {faq_html(faqs)}
 </div>
 {brand_sidebar(b, d)}
</section>"""
    kw = f"{n} review, {n} review {YEAR}, is {n} safe, is {n} legit, {n} real or fake, {n} minimum deposit, {n} regulation, {n} licence, {n} leverage, {n} fees, {n} app"
    desc = f"{n} review {YEAR}: licences ({reg_summary(b, 4)}), minimum deposit {b['min_deposit']}, leverage, {'spreads' if fx else 'fees'}, features and how to open an account."
    review_ld = {"@context": "https://schema.org", "@type": "Review",
                 "itemReviewed": {"@type": "Organization", "name": n, "url": f"https://{b['domain']}"},
                 "author": {"@type": "Organization", "name": SITE},
                 "reviewRating": {"@type": "Rating", "ratingValue": b["score"], "bestRating": 10, "worstRating": 0},
                 "datePublished": TODAY, "reviewBody": b["summary"]}
    page(path, f"{n} Review {YEAR}: Licences, Minimum Deposit, Fees & Features | {SITE}", desc, body, d, keywords=kw,
         ld=[review_ld, breadcrumb_ld([("Home", ""), hub, (n + " Review", path)]), faq_ld(faqs)], priority="0.85", og_type="article", theme="fx" if fx else "cx")


def build_signup(b):
    fx = is_fx(b)
    rp = review_path(b)
    path = rp + "sign-up/"
    d = 3
    n = b["name"]
    hub = ("Forex Brokers", "forex-brokers/") if fx else ("Crypto Exchanges", "crypto-exchanges/")
    code = b.get("ref_code")
    code_box = (f'<div class="codebox"><span>Referral / invite code</span><code id="refcode">{esc(code)}</code>'
                f'<button class="btn btn-ghost btn-sm" type="button" onclick="navigator.clipboard&&navigator.clipboard.writeText(\'{esc(code)}\');this.textContent=\'Copied ✓\'">Copy</button>'
                f'<small>Already filled in when you use our Visit Site link.</small></div>') if code else ""
    if fx:
        steps = [("Open the official website", f"Click <strong>Visit Site</strong> to open the official {esc(n)} registration page ({esc(b['domain'])})."
                  + (" Traders in Asia can use the Asia server link; everyone else uses Worldwide." if len(b["links"]) > 1 else "")),
                 ("Register", "Enter your country of residence, email and a strong password."),
                 ("Verify email and phone", "Confirm the code sent to your email and/or phone number."),
                 ("Complete your profile and verification", "Upload a passport, national ID card or driving licence, then proof of address (a bank statement or utility bill under 6 months old). Approval often takes minutes."),
                 ("Choose an account type", f"Minimum deposit: {esc(b['min_deposit'])}. {esc(b['min_deposit_note'])}"),
                 ("Deposit", "Fund with a local bank transfer, card, e-wallet or USDT, depending on your country."),
                 ("Download the platform", f"Install {esc(b['platforms'])}, log in with the server and account number from your personal area, and start on a demo account if you are new.")]
    else:
        steps = [("Open the official website", f"Click <strong>Visit Site</strong> to open the official {esc(n)} sign-up page ({esc(b['domain'])}). Bookmark it for next time."),
                 ("Create your account", "Register with email or phone and a strong, unique password." + (f" The invite code <strong>{esc(code)}</strong> is filled in automatically." if code else "")),
                 ("Turn on security", "Enable app-based 2FA (Google Authenticator), set an anti-phishing code and add a withdrawal whitelist."),
                 ("Verify your identity", esc(b["kyc"])),
                 ("Deposit crypto", "Deposit USDT or another supported coin from a wallet, or buy crypto with P2P or a card partner. Always pick the same network (e.g. TRC20, BEP20) on both sides."),
                 ("Start trading", f"Trade spot or futures — leverage {esc(b['max_leverage'][0].lower() + b['max_leverage'][1:])}. Start with small sizes and always use a stop loss.")]
    steps_html = "".join(f'<li><h3>{esc(t)}</h3><p>{c}</p></li>' for t, c in steps)
    faqs = [(f"How do I sign up for {n}?", f"Open the official {n} website, register with your email or phone, verify your identity and deposit. The whole process usually takes 10–20 minutes."),
            (f"Is {n} sign up free?", f"Yes. Opening an {n} account is completely free."),
            (f"What documents do I need for {n}?", "A valid passport, national ID card or driving licence" + (", plus proof of address." if fx else ". Some regions also ask for proof of address or a selfie check.")),
            (f"Can I open {n} from my country?", f"{n} welcomes traders from about {available_count(b)} countries. Check your country in our <a href=\"{link('countries/', d)}\">country guides</a>."),
            (f"What is the {n} minimum deposit?", f"{b['min_deposit']}. {b['min_deposit_note']}")]
    if code:
        faqs.insert(1, (f"What is the {n} referral code?", f"Our {n} referral / invite code is <strong>{esc(code)}</strong>. It is applied automatically when you register through our Visit Site link."))
    body = brand_head(b, d, [("Home", ""), hub, (n, rp), ("Sign up", path)], f"{esc(n)} Sign Up {YEAR}: How to Open an Account", f"Step-by-step {esc(n)} registration{(' with invite code ' + esc(code)) if code else ''} — verification, deposit and first trade.") + f"""
<section class="wrap section two-col">
 <div class="prose">
  {code_box}
  <h2>How to sign up for {esc(n)} (step by step)</h2>
  <ol class="steps">{steps_html}</ol>
  <div class="callout"><strong>Official domain:</strong> {esc(b['domain'])}. {esc(n)} staff will never ask for your password or 2FA code.</div>
  <h2>{esc(n)} account at a glance</h2>
  <div class="table-wrap"><table class="facts-table"><tr><th>Minimum deposit</th><td>{esc(b['min_deposit'])}</td></tr><tr><th>Max leverage</th><td>{esc(b['max_leverage'])}</td></tr><tr><th>{'Spreads' if fx else 'Fees'}</th><td>{esc(b['spreads'] if fx else b['fees'])}</td></tr><tr><th>Regulation</th><td>{esc(b['regulation'])}</td></tr></table></div>
  <p class="cta-line">{visit_buttons(b)}</p>
  {faq_html(faqs)}
 </div>
 {brand_sidebar(b, d)}
</section>"""
    kw = f"{n} sign up, {n} register, {n} registration, {n} create account, {n} open account, {n} account opening, {n} login, {n} app download" + (f", {n} referral code, {n} invite code, {n} code {code}" if code else "")
    page(path, f"{n} Sign Up {YEAR}: Register & Open an Account{(' (Code ' + code + ')') if code else ''} | {SITE}",
         f"How to sign up for {n} in {YEAR}: step-by-step registration{(', invite code ' + code) if code else ''}, verification documents, minimum deposit {b['min_deposit']} and first trade.",
         body, d, keywords=kw, ld=[breadcrumb_ld([("Home", ""), hub, (n, rp), ("Sign up", path)]), faq_ld(faqs),
                                    {"@context": "https://schema.org", "@type": "HowTo", "name": f"How to sign up for {n}",
                                     "step": [{"@type": "HowToStep", "name": t, "text": re.sub("<[^>]+>", "", c)} for t, c in steps]}],
         priority="0.75", og_type="article", theme="fx" if fx else "cx")


def build_legit(b):
    fx = is_fx(b)
    rp = review_path(b)
    path = rp + "real-or-fake/"
    d = 3
    n = b["name"]
    hub = ("Forex Brokers", "forex-brokers/") if fx else ("Crypto Exchanges", "crypto-exchanges/")
    tops = [l for l in b["licences"] if l["tier"] == "Top-tier"]
    reg_only = all(l["tier"] == "Company registration" for l in b["licences"])
    verdict = (f"<strong>Yes — {esc(n)} is real and legitimate.</strong> It is an established {'forex and CFD broker' if fx else 'cryptocurrency exchange'} operating since {esc(b['founded'])}"
               + (f", regulated by {esc(', '.join(short_reg(l) for l in tops))} among {len(b['licences'])} licences and registrations." if tops else
                  (f", {esc(b['regulation'][0].lower() + b['regulation'][1:])}" if not reg_only else f". {esc(b['regulation'])}")))
    checks = [("Registered company with public terms", True),
              (f"Licensed or registered by {len(b['licences'])} authorit{'ies' if len(b['licences']) != 1 else 'y'}", not reg_only),
              ("Top-tier regulator (FCA, ASIC, CySEC, VARA, MiCA…)", bool(tops)),
              (f"Operating since {b['founded']}", True),
              ("Negative balance protection for retail clients" if fx else "Identity verification protects withdrawals", True),
              ("Copy trading / social features", b["copy_trading"].startswith("Yes")),
              ("Official website: " + b["domain"], True)]
    checks_html = "".join(f'<li class="ok"><span>✓</span>{esc(k)}</li>' for k, v in checks if v)
    fca = next((l for l in b["licences"] if "Financial Conduct Authority" in l["regulator"]), None)
    faqs = [(f"Is {n} legit?", re.sub("<[^>]+>", "", verdict)),
            (f"Is {n} safe to use?", f"{b['regulation']} Protect your account with 2FA and use only the official website, {b['domain']}."),
            (f"How do I spot a fake {n} website?", f"The official domain is {b['domain']}. Fake sites use look-alike spellings, extra words or different endings. Never log in from links sent in Telegram, WhatsApp or ads — use our Visit Site button or type the address yourself."),
            (f"Can I withdraw money from {n}?", f"Yes. Withdrawals are processed to your verified payment methods {'(usually the same method you deposited with)' if fx else 'or crypto addresses'} after identity verification.")]
    if fca:
        faqs.insert(2, (f"Is {n} regulated by the FCA?", f"Yes — {n} has a UK entity, {fca['entity']}, authorised by the FCA ({fca['number']})."))
    body = brand_head(b, d, [("Home", ""), hub, (n, rp), ("Real or fake?", path)], f"Is {esc(n)} Real or Fake? Legit Check {YEAR}", f"{esc(n)}'s licences, track record and how to make sure you are on the official website.") + f"""
<section class="wrap section two-col">
 <div class="prose">
  <div class="verdict card big-verdict ok"><span class="pill ok">✓ Real &amp; legitimate</span><p>{verdict}</p></div>
  <h2>{esc(n)} trust checklist</h2>
  <ul class="checklist">{checks_html}</ul>
  <h2>{esc(n)} licences and licence numbers</h2>
  {licences_table(b, d)}
  <h2>How to verify {esc(n)} yourself</h2>
  <ol><li>Copy a licence number from the table above.</li><li>Search it on the regulator's official register (for example the FCA register, ASIC Connect or the FSCA FSP search).</li><li>Check the company name and website listed on the register match {esc(b['domain'])}.</li></ol>
  <h2>How to avoid fake "{esc(n)}" copies</h2>
  <ul class="ticks"><li>Only register through the official domain {esc(b['domain'])} or our Visit Site button</li><li>Real {esc(n)} support never asks for your password or 2FA code</li><li>Deposit only into your own {esc(n)} account — never to a personal wallet or bank account</li><li>Ignore "account managers" who message you first on social media</li></ul>
  <h2>Why traders trust {esc(n)}</h2>
  <ul class="ticks">{''.join(f'<li>{esc(p)}</li>' for p in b['pros'])}</ul>
  <p class="cta-line">{visit_buttons(b)} <a class="btn btn-ghost" href="../">Read full review</a></p>
  {faq_html(faqs)}
 </div>
 {brand_sidebar(b, d)}
</section>"""
    kw = f"{n} real or fake, is {n} real, is {n} fake, is {n} legit, {n} scam, is {n} a scam, is {n} safe, {n} trusted, {n} licence, {n} regulated, {n} withdrawal"
    page(path, f"Is {n} Real or Fake? Legit Check, Licences & Safety ({YEAR}) | {SITE}",
         f"Is {n} real or fake? {n} is a legitimate {'broker' if fx else 'exchange'} operating since {b['founded']}. See its licences ({reg_summary(b, 3)}), how withdrawals work and how to avoid fake copies.",
         body, d, keywords=kw, ld=[breadcrumb_ld([("Home", ""), hub, (n, rp), ("Real or fake?", path)]), faq_ld(faqs)],
         priority="0.75", og_type="article", theme="fx" if fx else "cx")


# --------------------------------------------------------------------------
# Head-to-head (A vs B) pages
# --------------------------------------------------------------------------
def build_vs(a, b):
    path = vs_path(a, b)
    a, b = sorted([a, b], key=lambda z: [x["slug"] for x in (BROKERS if is_fx(z) else EXCHANGES)].index(z["slug"]))
    d = 2
    fx = is_fx(a)
    winner = a if a["score"] >= b["score"] else b
    rows = [("Our score", lambda x: f"<b class='sc'>{x['score']:.1f}</b>/10"), ("Founded", lambda x: esc(x["founded"])),
            ("Minimum deposit", lambda x: esc(x["min_deposit"])), ("Max leverage", lambda x: esc(x["max_leverage"])),
            ("Spreads" if fx else "Fees", lambda x: esc(x["spreads"] if fx else x["fees"])),
            ("Platforms" if fx else "Coins", lambda x: esc(x["platforms"] if fx else x["coins"])),
            ("Copy trading", lambda x: esc(x["copy_trading"])),
            ("Licences", lambda x: ", ".join(esc(short_reg(l)) for l in x["licences"])),
            ("Available in", lambda x: f"~{available_count(x)} countries"),
            ("Best for", lambda x: esc(x["best_for"])), ("", lambda x: visit_buttons(x, small=True))]
    table = "".join(f"<tr><th>{k}</th><td>{f(a)}</td><td>{f(b)}</td></tr>" for k, f in rows)
    faqs = [(f"Which is better, {a['name']} or {b['name']}?", f"Both are excellent. {winner['name']} scores slightly higher in our rating. Choose {a['name']} for: {a['best_for'].lower()}. Choose {b['name']} for: {b['best_for'].lower()}."),
            (f"Which has the lower minimum deposit, {a['name']} or {b['name']}?", f"{a['name']}: {a['min_deposit']}. {b['name']}: {b['min_deposit']}."),
            (f"How are {a['name']} and {b['name']} regulated?", f"{a['name']}: {a['regulation']} {b['name']}: {b['regulation']}")]
    body = f"""<section class="pagehead {'fx' if fx else 'cx'}-head"><div class="wrap">
 {crumbs_html([("Home", ""), ("Compare", "compare/"), (f"{a['name']} vs {b['name']}", path)], d)}
 <div class="vs-head">{logo(a, 'xl')}<span class="vs">VS</span>{logo(b, 'xl')}</div>
 <h1>{esc(a['name'])} vs {esc(b['name'])} ({YEAR}): Which Is Better?</h1>
 <p class="lead">Licences, {'spreads' if fx else 'fees'}, leverage, minimum deposit and features compared side by side. Our pick: <strong>{esc(winner['name'])}</strong> ({winner['score']:.1f}/10).</p>
</div></section>
<section class="wrap section narrow-wide">
 <div class="table-wrap"><table class="vs-table"><thead><tr><th></th><th><a class="tname" href="{link(review_path(a), d)}">{logo(a, 'sm')} {esc(a['name'])}</a></th><th><a class="tname" href="{link(review_path(b), d)}">{logo(b, 'sm')} {esc(b['name'])}</a></th></tr></thead><tbody>{table}</tbody></table></div>
 <div class="grid g2"><div class="card"><h2>Why choose {esc(a['name'])}</h2><ul class="ticks">{''.join(f'<li>{esc(p)}</li>' for p in a['pros'])}</ul><p>{visit_buttons(a)}</p></div><div class="card"><h2>Why choose {esc(b['name'])}</h2><ul class="ticks">{''.join(f'<li>{esc(p)}</li>' for p in b['pros'])}</ul><p>{visit_buttons(b)}</p></div></div>
 <div class="prose">
 <h2>Verdict</h2>
 <p>{esc(a['summary'])}</p><p>{esc(b['summary'])}</p>
 <p><strong>{esc(winner['name'])}</strong> edges ahead in our rating, but many traders open both accounts and use each for what it does best.</p>
 {faq_html(faqs)}
 </div>
</section>"""
    page(path, f"{a['name']} vs {b['name']} ({YEAR}): Fees, Licences & Leverage Compared | {SITE}",
         f"{a['name']} vs {b['name']}: side-by-side comparison of licences, minimum deposit ({a['min_deposit']} vs {b['min_deposit']}), leverage, {'spreads' if fx else 'fees'} and features. Which is better in {YEAR}?",
         body, d, keywords=f"{a['name']} vs {b['name']}, {b['name']} vs {a['name']}, {a['name']} or {b['name']}, {a['name']} {b['name']} comparison",
         ld=[breadcrumb_ld([("Home", ""), ("Compare", "compare/"), (f"{a['name']} vs {b['name']}", path)]), faq_ld(faqs)], priority="0.7", theme="fx" if fx else "cx")


def build_compare_index():
    d = 1

    def links(items):
        return "".join(f'<a class="card vs-card" href="{link(vs_path(a, b), d)}"><span>{logo(a, "sm")}<b>vs</b>{logo(b, "sm")}</span>{esc(a["name"])} vs {esc(b["name"])}</a>' for a, b in itertools.combinations(items, 2))
    body = f"""<section class="pagehead"><div class="wrap">{crumbs_html([("Home", ""), ("Compare", "compare/")], d)}
<h1>Compare Forex Brokers &amp; Crypto Exchanges</h1><p class="lead">Full comparison tables and head-to-head matchups.</p>
<p><a class="btn btn-fx" href="../forex-brokers/compare/">Forex comparison table</a> <a class="btn btn-cx" href="../crypto-exchanges/compare/">Crypto comparison table</a></p></div></section>
<section class="wrap section"><span class="kicker cx">CRYPTO</span><h2>Crypto exchange head-to-heads</h2><div class="grid g4">{links(EXCHANGES)}</div></section>
<section class="wrap section"><span class="kicker fx">FOREX</span><h2>Forex broker head-to-heads</h2><div class="grid g4">{links(BROKERS)}</div></section>"""
    page("compare/", f"Compare Forex Brokers & Crypto Exchanges ({YEAR}) – Head-to-Head | {SITE}",
         "Head-to-head comparisons: Bitunix vs Binance, BingX vs MEXC, Exness vs IC Markets and more — licences, fees, leverage and minimum deposits.",
         body, d, keywords="broker comparison, exchange comparison, Bitunix vs Binance, Exness vs IC Markets, Binance vs KuCoin",
         ld=[breadcrumb_ld([("Home", ""), ("Compare", "compare/")])], priority="0.8")


def build_licences():
    d = 1

    def block(items, kind):
        rows = ""
        for b in items:
            for i, l in enumerate(b["licences"]):
                first = f'<td rowspan="{len(b["licences"])}"><a class="tname" href="{link(review_path(b), d)}">{logo(b, "sm")} {esc(b["name"])}</a></td>' if i == 0 else ""
                c = BY_CODE.get(l["country"])
                rows += f"<tr>{first}<td>{c['flag'] if c else ''} {esc(c['name'] if c else l['country'])}</td><td>{esc(l['regulator'])}</td><td>{esc(l['entity'])}</td><td><code>{esc(l['number'])}</code></td><td>{tier_badge(l['tier'])}</td></tr>"
        return f'<div class="table-wrap"><table class="lic"><thead><tr><th>{kind}</th><th>Country</th><th>Regulator</th><th>Entity</th><th>Licence no.</th><th>Type</th></tr></thead><tbody>{rows}</tbody></table></div>'
    body = f"""<section class="pagehead"><div class="wrap">{crumbs_html([("Home", ""), ("Licences", "licences/")], d)}
<h1>Broker &amp; Exchange Licences and Regulation ({YEAR})</h1>
<p class="lead">Every licence and registration we verified — FCA, ASIC, CySEC, DFSA, FSCA, VARA, MiCA, AUSTRAC and more — with the entity name, country and licence number.</p></div></section>
<section class="wrap section prose">
 <h2>Types of licences</h2>
 <ul><li>{tier_badge('Top-tier')} Leading regulators such as the FCA (UK), ASIC (Australia), CySEC (EU), Central Bank of Ireland, DFSA and VARA (Dubai), and MiCA authorisation (EU).</li>
 <li>{tier_badge('Mid-tier')} National regulators such as the FSCA (South Africa), CMA (Kenya), CIMA (Cayman) and SCB (Bahamas).</li>
 <li>{tier_badge('Offshore')} International licences such as the FSA (Seychelles), FSC (Mauritius, BVI, Belize), VFSC (Vanuatu) and MISA (Comoros), which allow higher leverage.</li>
 <li>{tier_badge('AML registration')} Registrations such as FinCEN MSB, FINTRAC, AUSTRAC and FIU-IND.</li></ul>
 <div class="callout good">Tip: you can confirm any licence number on the regulator's official online register.</div>
</section>
<section class="wrap section"><span class="kicker fx">FOREX</span><h2>Forex broker licences</h2>{block(BROKERS, "Broker")}</section>
<section class="wrap section"><span class="kicker cx">CRYPTO</span><h2>Crypto exchange licences &amp; registrations</h2>{block(EXCHANGES, "Exchange")}</section>"""
    page("licences/", f"Forex Broker & Crypto Exchange Licences: FCA, ASIC, CySEC, VARA, MiCA ({YEAR}) | {SITE}",
         "Verified licence list: FCA, ASIC, CySEC, DFSA, FSCA, VARA, MiCA and AUSTRAC registrations with licence numbers for " + ", ".join(b["name"] for b in ALL) + ".",
         body, d, keywords="FCA regulated broker, ASIC regulated broker, CySEC broker, regulated crypto exchange, VARA licence, MiCA licence, broker licence number, is my broker regulated",
         ld=[breadcrumb_ld([("Home", ""), ("Licences", "licences/")])], priority="0.85")


# --------------------------------------------------------------------------
# Country pages
# --------------------------------------------------------------------------
def country_note(c):
    return NOTES.get(c["code"]) or (EU_NOTE.format(name=c["name"]) if c["eu"] else "")


def lic_in_country(c, items):
    hits = []
    for b in items:
        for l in b["licences"]:
            if l["country"] == c["code"]:
                hits.append((b, l))
    return hits


def build_country(c, kind):
    fx = kind == "forex"
    items = BROKERS if fx else EXCHANGES
    noun = "Forex Brokers" if fx else "Crypto Exchanges"
    sing = "forex broker" if fx else "crypto exchange"
    base = "forex-brokers/" if fx else "crypto-exchanges/"
    path = f"{base}{c['slug']}/"
    d = 2
    name, title_name = c["in_name"], c["name"]
    reg = c["regulator"] or "the national central bank or securities regulator"
    note = country_note(c)
    shown = [b for b in items if status_for(b, c["code"]) == "yes"] + [b for b in items if status_for(b, c["code"]) == "check"]
    avail = [b for b in shown if status_for(b, c["code"]) == "yes"]
    cur = f"{c['currency_name']} ({c['currency']})" if c["currency"] else "your local currency"
    local_lic = lic_in_country(c, items)
    pillar = "best-forex-broker/" if fx else "best-crypto-exchange/"
    if avail:
        summary = (f"Looking for the best {sing} in {esc(name)}? We compared {len(items)} {noun.lower()} and found <strong>{len(avail)}</strong> that welcome traders from {esc(name)}. "
                   f"Our best {sing} in {esc(name)} is <strong>{esc(avail[0]['name'])}</strong> — {esc(avail[0]['tagline'].lower())}.")
    elif shown:
        summary = f"Looking for the best {sing} in {esc(name)}? The options below may accept traders from {esc(name)} — confirm your country when you register."
    else:
        summary = f"Looking for the best {sing} in {esc(name)}? See our worldwide <a href=\"{link(pillar, d)}\">best {sing} ranking</a> and the local rules below."
    lic_html = ""
    if local_lic:
        lic_html = (f'<div class="callout good"><strong>Licensed / registered in {esc(name)}:</strong> ' +
                    "; ".join(f'{esc(b["name"])} — {esc(l["regulator"])}{(" (" + esc(l["number"]) + ")") if l["number"] != "—" else ""}' for b, l in local_lic) + "</div>")
    same_region = [x for x in COUNTRIES if x["region"] == c["region"] and x["code"] != c["code"]][:24]
    region_links = "".join(f'<a href="../{x["slug"]}/">{x["flag"]} Best {sing} in {esc(x["in_name"])}</a>' for x in same_region)
    other = ("crypto-exchanges/", "crypto exchange") if fx else ("forex-brokers/", "forex broker")
    names = lambda lst: ", ".join(b["name"] for b in lst)
    if fx:
        how = f"""<h2>How to choose the best forex broker in {esc(name)}</h2>
<ol><li><strong>Check the licence.</strong> In {esc(name)} the main financial regulator is {esc(reg)}. See every broker's licences in our <a href="{link('licences/', d)}">licence table</a>.</li>
<li><strong>Match the minimum deposit to your budget.</strong> Start from $1 at InstaForex, $0 at HFM or $10 at Exness.</li>
<li><strong>Deposit in {esc(cur)}.</strong> Local bank transfers, cards, e-wallets and USDT are widely supported.</li>
<li><strong>Pick your platform.</strong> MT4, MT5, cTrader or TradingView.</li>
<li><strong>Plan your risk.</strong> Risk 1–2% of your balance per trade and always use a stop loss.</li></ol>"""
        faqs = [(f"What is the best forex broker in {title_name}?", (f"{avail[0]['name']} is our best forex broker in {name}" + (", followed by " + names(avail[1:4]) + "." if len(avail) > 1 else ".")) if avail else f"See our worldwide best forex broker ranking for options."),
                (f"Which forex brokers accept traders from {title_name}?", (names(shown) + f" accept traders from {name}.") if shown else "See our worldwide ranking."),
                (f"Which forex broker has the lowest minimum deposit in {title_name}?", next((f"{b['name']}, with a minimum deposit of {b['min_deposit']}." for b in sorted(avail, key=lambda b: float(re.sub(r'[^0-9.]', '', b['min_deposit']) or 0))), "See our worldwide best forex broker ranking.")),
                (f"Which regulated forex brokers accept traders from {title_name}?", (names([b for b in avail if has_top(b)]) + " hold top-tier licences such as the FCA, ASIC or CySEC.") if any(has_top(b) for b in avail) else (names(avail) + " are internationally regulated.") if avail else "See our licence page."),
                (f"Is forex trading legal in {title_name}?", (note or f"Forex trading rules in {name} are set by {reg}.") + " This is general information, not legal advice.")]
    else:
        how = f"""<h2>How to choose the best crypto exchange in {esc(name)}</h2>
<ol><li><strong>Check local rules.</strong> Crypto rules in {esc(name)} are set by {esc(reg)}.</li>
<li><strong>Compare fees.</strong> Futures maker fees range from 0% at MEXC to 0.02% at Bitunix, Bybit and Binance.</li>
<li><strong>Funding in {esc(cur)}.</strong> Buy USDT through P2P or a card partner, then trade.</li>
<li><strong>Use the exchange wallet safely.</strong> Enable 2FA, an anti-phishing code and a withdrawal whitelist.</li>
<li><strong>Try copy trading.</strong> BingX, Bitunix and Bybit let you follow experienced traders.</li></ol>"""
        faqs = [(f"What is the best crypto exchange in {title_name}?", (f"{avail[0]['name']} is our best crypto exchange in {name}" + (", followed by " + names(avail[1:4]) + "." if len(avail) > 1 else ".")) if avail else "See our worldwide best crypto exchange ranking."),
                (f"Which crypto exchanges accept users from {title_name}?", (names(shown) + f" accept users from {name}.") if shown else "See our worldwide ranking."),
                (f"What is the best crypto exchange wallet in {title_name}?", (f"{names([b for b in shown if b['slug'] in ('binance', 'bybit', 'bitunix')][:3]) or names(shown[:2])} offer an easy exchange wallet for deposits, storage and trading.") if shown else "See our best crypto exchange wallet guide."),
                (f"How do I buy USDT in {title_name}?", f"Use P2P marketplaces (paying in {cur}), card purchases through a payment partner, or a local exchange, then transfer USDT to your trading exchange on the correct network."),
                (f"Is crypto trading legal in {title_name}?", (note or f"Crypto rules in {name} are overseen by {reg}.") + " This is general information, not legal advice.")]
    note_html = f'<div class="callout"><strong>Local rules in {esc(name)}:</strong> {esc(note)}</div>' if note else ""
    facts = f"""<div class="cfacts">
 <div><span>Region</span><b>{esc(c['region'])}</b></div>
 <div><span>Currency</span><b>{esc(cur)}</b></div>
 <div><span>Regulator</span><b>{esc(reg)}</b></div>
 <div><span>{noun} available</span><b>{len(shown)}</b></div></div>"""
    listing = (f"""{compare_table(shown, d, c)}
 <div class="grid g2">{''.join(brand_card(b, i, d, c) for i, b in enumerate(shown, 1))}</div>""" if shown else
               f'<p>See our <a href="{link(pillar, d)}">worldwide best {sing} ranking</a> for the full list.</p>')
    body = f"""
<section class="pagehead {'fx' if fx else 'cx'}-head"><div class="wrap">
 {crumbs_html([("Home", ""), (noun, base), (title_name, path)], d)}
 <h1>{c['flag']} Best {sing.title()} in {esc(name)} ({YEAR})</h1>
 <p class="lead">{summary}</p>
 {facts}
</div></section>
<section class="wrap section">
 {note_html}{lic_html}
 <h2>{f"Top {len(shown)} {noun.lower()} in {esc(name)}" if shown else f"{noun} for traders in {esc(name)}"}</h2>
 {listing}
</section>
<section class="wrap section prose">
 {how}
 {faq_html(faqs)}
 <p>Also see: <a href="{link(other[0] + c['slug'] + '/', d)}">Best {other[1]} in {esc(name)}</a> · <a href="{link(pillar, d)}">Best {sing} worldwide</a> · <a href="{link('countries/' + c['slug'] + '/', d)}">{esc(title_name)} trading guide</a> · <a href="{link('free-forex-signals/', d)}">Free forex signals</a> · <a href="{link('free-crypto-signals/', d)}">Free crypto signals</a></p>
</section>
<section class="wrap section"><h2>Best {sing} in other {esc(c['region'])} countries</h2><div class="clist">{region_links}<a href="{link(base, d)}#countries"><strong>All countries →</strong></a></div></section>"""
    top_names = ", ".join(b["name"] for b in avail[:4])
    if fx:
        title = f"Best Forex Broker in {name} {YEAR}" + (f" – Top {len(shown)} Regulated Brokers" if shown else "") + f" | {SITE}"
        desc = f"Best forex broker in {name} for {YEAR}: {top_names or 'top regulated brokers'} compared — licences, minimum deposit, leverage and MT4/MT5 for traders in {name}."
        kw = f"best forex broker in {title_name}, best forex broker {title_name}, best forex broker in {title_name} {YEAR}, forex brokers {title_name}, forex trading {title_name}, regulated forex broker {title_name}, low minimum deposit forex broker {title_name}, MT5 broker {title_name}, gold trading {title_name}, forex signals {title_name}"
    else:
        title = f"Best Crypto Exchange in {name} {YEAR}" + (f" – Top {len(shown)} Exchanges & Wallets" if shown else "") + f" | {SITE}"
        desc = f"Best crypto exchange in {name} for {YEAR}: {top_names or 'top exchanges'} compared — fees, futures leverage, wallets and licences for users in {name}."
        kw = f"best crypto exchange in {title_name}, best crypto exchange {title_name}, best crypto exchange in {title_name} {YEAR}, best crypto wallet {title_name}, buy bitcoin {title_name}, buy USDT {title_name}, crypto trading {title_name}, crypto futures {title_name}, crypto signals {title_name}"
    page(path, title, desc, body, d, keywords=kw,
         ld=[itemlist_ld(f"Best {sing} in {title_name}", shown or items), breadcrumb_ld([("Home", ""), (noun, base), (title_name, path)]), faq_ld(faqs)], priority="0.7", theme="fx" if fx else "cx")


def build_country_overview(c):
    path = f"countries/{c['slug']}/"
    d = 2
    name, title_name = c["in_name"], c["name"]
    reg = c["regulator"] or "the national central bank or securities regulator"
    note = country_note(c)
    fxs = [b for b in BROKERS if status_for(b, c["code"]) == "yes"]
    cxs = [b for b in EXCHANGES if status_for(b, c["code"]) == "yes"]

    def mini(b):
        return f'<div class="mini">{logo(b, "sm")}<a href="{link(review_path(b), d)}">{esc(b["name"])}</a><span>{esc(b["min_deposit"])}</span>{visit_buttons(b, small=True, first_only=True)}</div>'
    body = f"""
<section class="pagehead"><div class="wrap">
 {crumbs_html([("Home", ""), ("Countries", "countries/"), (title_name, path)], d)}
 <h1>{c['flag']} Forex &amp; Crypto Trading in {esc(name)} ({YEAR})</h1>
 <p class="lead">Which forex brokers and crypto exchanges accept traders from {esc(name)}, who regulates trading there, and where to start.</p>
</div></section>
<section class="wrap section grid g2">
 <div class="card fx-card"><span class="kicker fx">FOREX</span><h2>Forex brokers in {esc(name)}</h2>{''.join(mini(b) for b in fxs) or '<p>None of the brokers we review accept residents of ' + esc(name) + '.</p>'}
  <a class="more" href="{link('forex-brokers/' + c['slug'] + '/', d)}">Full forex comparison for {esc(name)} →</a></div>
 <div class="card cx-card"><span class="kicker cx">CRYPTO</span><h2>Crypto exchanges in {esc(name)}</h2>{''.join(mini(b) for b in cxs) or '<p>None of the exchanges we review accept residents of ' + esc(name) + '.</p>'}
  <a class="more" href="{link('crypto-exchanges/' + c['slug'] + '/', d)}">Full crypto comparison for {esc(name)} →</a></div>
</section>
<section class="wrap section prose">
 <h2>Trading regulation in {esc(name)}</h2>
 <p>The main financial regulator in {esc(name)} is {esc(reg)}. Local currency: {esc(c['currency_name'] or '—')} {('(' + esc(c['currency']) + ')') if c['currency'] else ''}. Region: {esc(c['region'])}.</p>
 {f'<p>{esc(note)}</p>' if note else ''}
 <p>Signals and education: <a href="{link('free-forex-signals/', d)}">free forex signals</a> · <a href="{link('free-crypto-signals/', d)}">free crypto signals</a> · <a href="{link('blog/', d)}">trading blog</a>.</p>
 {disclosure_box(d)}
</section>"""
    page(path, f"Forex & Crypto Trading in {name} ({YEAR}): Brokers, Exchanges & Rules | {SITE}",
         f"Trading guide for {name}: which forex brokers and crypto exchanges accept residents, the local regulator, currency and legal notes for {YEAR}.",
         body, d, keywords=f"trading in {title_name}, forex {title_name}, crypto {title_name}, best broker {title_name}, best exchange {title_name}",
         ld=[breadcrumb_ld([("Home", ""), ("Countries", "countries/"), (title_name, path)])], priority="0.6")


def build_countries_index():
    d = 1
    regions = {}
    for c in COUNTRIES:
        regions.setdefault(c["region"], []).append(c)
    rows = "".join(
        f'<div class="region"><h2>{esc(r)}</h2><div class="ctable">' + "".join(
            f'<div class="crow" data-name="{esc(c["name"].lower())}"><a class="cname" href="{c["slug"]}/">{c["flag"]} {esc(c["name"])}</a>'
            f'<a class="fxl" href="../forex-brokers/{c["slug"]}/">Forex</a><a class="cxl" href="../crypto-exchanges/{c["slug"]}/">Crypto</a></div>' for c in cs) + "</div></div>"
        for r, cs in sorted(regions.items()))
    body = f"""
<section class="pagehead"><div class="wrap">
 {crumbs_html([("Home", ""), ("Countries", "countries/")], d)}
 <h1>Forex Brokers &amp; Crypto Exchanges in Every Country</h1>
 <p class="lead">{len(COUNTRIES)} country and territory guides across every continent. Find out which providers accept traders where you live.</p>
 <input class="filter" id="cfilter" placeholder="Filter countries…" aria-label="Filter countries">
</div></section>
<section class="wrap section" id="countries">{rows}</section>"""
    page("countries/", f"Forex Brokers & Crypto Exchanges in {len(COUNTRIES)} Countries – Country Guides {YEAR} | {SITE}",
         f"Country-by-country guides for {len(COUNTRIES)} countries worldwide: which forex brokers and crypto exchanges accept residents, local regulators and legal notes.",
         body, d, keywords="forex brokers by country, crypto exchanges by country, best forex broker in my country, best crypto exchange by country",
         ld=[breadcrumb_ld([("Home", ""), ("Countries", "countries/")])], priority="0.8")


# --------------------------------------------------------------------------
# Signals
# --------------------------------------------------------------------------
def build_signals(kind):
    d = 1
    fx = kind == "forex"
    path = "free-forex-signals/" if fx else "free-crypto-signals/"
    sc = sig_cfg(kind)
    if fx:
        h1 = f"Free Forex Signals {YEAR} – XAUUSD Gold, US30, NAS100 & More"
        pairs = "XAUUSD (gold), US30, NAS100, EURUSD, GBPUSD and USDJPY"
        partners = BROKERS
        ex = ("BUY XAUUSD (example)", "Entry: 2,350.00 – 2,348.00", "Stop loss: 2,340.00", "TP1: 2,358.00 · TP2: 2,366.00")
    else:
        h1 = f"Free Crypto Signals {YEAR} – Bitcoin, Ethereum & Altcoin Futures"
        pairs = "BTCUSDT, ETHUSDT, SOLUSDT and selected altcoin perpetual futures"
        partners = EXCHANGES
        ex = ("LONG BTCUSDT (example)", "Entry: 64,800 – 64,500", "Stop loss: 63,900", "TP1: 65,700 · TP2: 66,600 · Leverage: max 5x")
    word = "broker" if fx else "exchange"
    faqs = [("Are the signals really free?", f"Yes. Join our public Telegram channel for free signals. If you trade with one of our partner {word}s, message our admin @{sc['admin']} to get our signals free."),
            (f"I already use one of your partner {word}s — how do I get the signals?", f"Choose your {word} in the box on this page and tap the button. Telegram opens a chat with @{sc['admin']} with your message already written — just press send."),
            ("How much should I risk per signal?", "Many professional traders risk 1–2% of their account per trade. Always use the stop loss."),
            ("Which " + word + " should I use?", f"Our top picks are {', '.join(p['name'] for p in partners if p.get('top_pick'))}. Any of our partner {word}s works with the signals.")]
    body = f"""
<section class="pagehead {'fx' if fx else 'cx'}-head"><div class="wrap">
 {crumbs_html([("Home", ""), ("Free Signals", "free-signals/"), (h1.split(' –')[0], path)], d)}
 <h1>{esc(h1)}</h1>
 <p class="lead">Join our free Telegram channel for {esc(pairs)} trade ideas — each with an entry zone, stop loss and take-profit targets — plus risk-management education.</p>
 <div class="cta-line"><a class="btn btn-tg big" href="{esc(sc['channel'])}" target="_blank" rel="noopener">✈ Join the free {'forex' if fx else 'crypto'} signals channel</a></div>
</div></section>
{market_blocks("Markets we trade", d)}
<section class="wrap section two-col">
 <div class="prose">
  {admin_box(kind)}
  <h2>What a signal looks like</h2>
  <div class="signal-demo {'fx' if fx else 'cx'}"><b>{esc(ex[0])}</b><span>{esc(ex[1])}</span><span>{esc(ex[2])}</span><span>{esc(ex[3])}</span><small>Illustration only — not a live trade recommendation.</small></div>
  <h2>How to use trading signals safely</h2>
  <ol><li><strong>Calculate your position size first</strong> so a stop-loss hit costs no more than 1–2% of your balance.</li>
  <li><strong>Always set the stop loss</strong> as soon as you open the trade.</li>
  <li><strong>Take partial profits</strong> at TP1 and move your stop to break-even if the signal says so.</li>
  <li><strong>Skip late entries</strong> if price has already moved far beyond the entry zone.</li>
  <li><strong>{'Watch news events.' if fx else 'Keep leverage low.'}</strong> {'Spreads widen around NFP, CPI and central bank decisions.' if fx else 'With 100x leverage, a 1% move against you wipes out your margin.'}</li></ol>
  {faq_html(faqs)}
 </div>
 <aside class="side"><div class="card sticky"><h3>Trade our signals with</h3>{''.join(f'<div class="mini">{logo(p, "sm")}<b>{esc(p["name"])}</b>{visit_buttons(p, small=True, first_only=True)}</div>' for p in partners)}
 <a class="btn btn-tg" style="width:100%;margin-top:12px" href="{esc(sc['channel'])}" target="_blank" rel="noopener">✈ Join free channel</a></div></aside>
</section>"""
    kw = ("free forex signals, forex signals telegram, gold signals, XAUUSD signals, US30 signals, NAS100 signals, free gold signals, best forex signals, forex signals today" if fx
          else "free crypto signals, crypto signals telegram, bitcoin signals, crypto futures signals, free bitcoin signals, best crypto signals, BTC signals today")
    page(path, f"{h1} | {SITE}", f"Free {'forex' if fx else 'crypto'} signals on Telegram: {pairs} with entry, stop loss and take profit. Partner clients get our signals free.",
         body, d, keywords=kw, ld=[breadcrumb_ld([("Home", ""), ("Free Signals", "free-signals/"), (h1.split(' –')[0], path)]), faq_ld(faqs)], priority="0.9", theme="fx" if fx else "cx")


def build_signals_hub():
    d = 1
    fxc, cxc = sig_cfg("forex"), sig_cfg("crypto")
    body = f"""<section class="pagehead"><div class="wrap">{crumbs_html([("Home", ""), ("Free Signals", "free-signals/")], d)}
<h1>Free Trading Signals {YEAR} – Forex &amp; Crypto</h1><p class="lead">Transparent trade ideas with entry, stop loss and targets — shared free on Telegram.</p></div></section>
<section class="wrap section grid g2">
 <div class="card signal-card fx"><span class="kicker fx">FOREX</span><h2>Free Forex Signals</h2><p>Gold (XAUUSD), US30, NAS100, EURUSD, GBPUSD and more.</p><div class="cta-line"><a class="btn btn-tg" href="{esc(fxc['channel'])}" target="_blank" rel="noopener">✈ Join channel</a><a class="btn btn-fx" href="../free-forex-signals/">Details →</a></div></div>
 <div class="card signal-card cx"><span class="kicker cx">CRYPTO</span><h2>Free Crypto Signals</h2><p>BTC, ETH and altcoin perpetual futures setups.</p><div class="cta-line"><a class="btn btn-tg" href="{esc(cxc['channel'])}" target="_blank" rel="noopener">✈ Join channel</a><a class="btn btn-cx" href="../free-crypto-signals/">Details →</a></div></div>
</section>
<section class="wrap section grid g2">{admin_box("forex")}{admin_box("crypto")}</section>"""
    page("free-signals/", f"Free Forex & Crypto Signals ({YEAR}) – Telegram | {SITE}", "Free forex and crypto trading signals on Telegram: gold, US30, NAS100, forex pairs, Bitcoin and altcoin futures with entry, stop loss and take profit.",
         body, d, keywords="free trading signals, free forex signals, free crypto signals, telegram signals", ld=[breadcrumb_ld([("Home", ""), ("Free Signals", "free-signals/")])], priority="0.8")


# --------------------------------------------------------------------------
# Guides
# --------------------------------------------------------------------------
BLOG_TITLE = f"{SITE} Blog"


def build_guides():
    d = 1
    cats = []
    for x in ARTICLES:
        c = x.get("category", "Guide")
        if c not in cats:
            cats.append(c)
    chips = '<button class="chip-f on" type="button" data-f="all">All articles</button>' + "".join(f'<button class="chip-f" type="button" data-f="{cat_slug(c)}">{esc(c)}</button>' for c in cats)
    body = f"""<section class="pagehead blog-head"><div class="wrap">{crumbs_html([("Home", ""), ("Blog", "blog/")], d)}
<span class="kicker">THE {esc(SITE.upper())} BLOG</span>
<h1>Forex &amp; Crypto Trading Blog {YEAR}: Guides, Market Reports &amp; Broker Tips</h1>
<p class="lead">Monthly gold, forex and crypto market reports, step-by-step how-to guides and beginner education — {len(ARTICLES)} articles and counting, with new articles published automatically every month.</p></div></section>
<section class="wrap section">
 <div class="featured">{article_cards(ARTICLES[:1], d, "g1")}</div>
 <div class="filters" aria-label="Filter articles">{chips}</div>
 <div id="blog-list">{article_cards(ARTICLES, d)}</div>
</section>
<section class="wrap section grid g2">
 <div class="card signal-card fx"><span class="kicker fx">FREE</span><h2>Free Forex Signals</h2><p>Gold, US30, NAS100 and major pairs on Telegram.</p><div class="cta-line"><a class="btn btn-tg" href="{esc(sig_cfg('forex')['channel'])}" target="_blank" rel="noopener">✈ Join free channel</a></div></div>
 <div class="card signal-card cx"><span class="kicker cx">FREE</span><h2>Free Crypto Signals</h2><p>BTC, ETH and altcoin futures setups on Telegram.</p><div class="cta-line"><a class="btn btn-tg" href="{esc(sig_cfg('crypto')['channel'])}" target="_blank" rel="noopener">✈ Join free channel</a></div></div>
</section>"""
    blog_ld = {"@context": "https://schema.org", "@type": "Blog", "name": BLOG_TITLE, "url": f"{SITE_URL}/blog/",
               "blogPost": [{"@type": "BlogPosting", "headline": x["title"], "url": f"{SITE_URL}/guides/{x['slug']}/", "datePublished": x.get("date", TODAY)} for x in ARTICLES[:30]]}
    page("blog/", f"Forex & Crypto Trading Blog {YEAR} – Guides, Market Reports & Broker Tips | {SITE}",
         f"The {SITE} blog: monthly gold, forex and crypto market reports, how-to guides, broker tips and trading education for {YEAR}.",
         body, d, keywords="forex blog, crypto blog, trading blog, forex trading guides, crypto market report, gold market report, broker guides",
         ld=[blog_ld, breadcrumb_ld([("Home", ""), ("Blog", "blog/")])], priority="0.9")
    # The old /guides/ list stays online (no broken links) but tells Google the main page is now /blog/
    body = f"""<section class="pagehead"><div class="wrap">{crumbs_html([("Home", ""), ("Blog", "blog/")], d)}
<h1>Forex &amp; Crypto Trading Guides</h1><p class="lead">All our guides now live on the <a href="../blog/">{esc(BLOG_TITLE)}</a>.</p></div></section>
<section class="wrap section">{article_cards(ARTICLES, d)}</section>"""
    page("guides/", f"Forex & Crypto Trading Guides | {SITE}", "Learn forex and crypto trading: guides, market reports and broker tips.",
         body, d, canonical="blog/", in_sitemap=False)
    for a in ARTICLES:
        path = f"guides/{a['slug']}/"
        d2 = 2
        html_body, toc = md_to_html(a["body"], d2)
        toc_html = "".join(f'<a href="#{h}">{esc(t)}</a>' for h, t in toc)
        related = ([x for x in ARTICLES if x["slug"] != a["slug"] and x.get("category") == a.get("category")] + [x for x in ARTICLES if x["slug"] != a["slug"] and x.get("category") != a.get("category")])[:3]
        hero = f'<figure class="art-hero"><img src="{rel(d2)}{a["image"]}" alt="{esc(a["title"])}" width="2400" height="1260" fetchpriority="high"></figure>' if a["image"] else ""
        cat = a.get("category", "Guide")
        crypto_cat = cat in ("Crypto", "Signals") or "crypto" in a["slug"]
        promo_items = [x for x in (EXCHANGES if crypto_cat else BROKERS) if x.get("top_pick")] or (EXCHANGES if crypto_cat else BROKERS)[:3]
        promo = "".join(f'<div class="mini">{logo(p, "sm")}<a href="{link(review_path(p), d2)}">{esc(p["name"])}</a>{visit_buttons(p, small=True, first_only=True)}</div>' for p in promo_items)
        body = f"""<section class="pagehead"><div class="wrap narrow">{crumbs_html([("Home", ""), ("Blog", "blog/"), (a["title"], path)], d2)}
<span class="tag">{esc(cat)}</span><h1>{esc(a['title'])}</h1><p class="lead">{esc(a['description'])}</p>
<p class="byline">By {esc(CFG['author'])} · Published <time datetime="{esc(a.get('date', TODAY))}">{esc(nice_date(a.get('date', TODAY)))}</time></p></div></section>
<div class="wrap narrow">{hero}</div>
<section class="wrap section two-col"><article class="prose">{html_body}{disclosure_box(d2)}</article>
<aside class="side"><div class="card sticky"><h3>On this page</h3><nav class="toc">{toc_html}</nav><h3 class="mt">Top picks</h3>{promo}</div></aside></section>
<section class="wrap section"><div class="sec-head"><h2>Related articles</h2><a href="{link('blog/', d2)}">All blog articles →</a></div>{article_cards(related, d2)}</section>"""
        art_ld = {"@context": "https://schema.org", "@type": "BlogPosting", "headline": a["title"], "description": a["description"],
                  "datePublished": a.get("date", TODAY), "dateModified": a.get("date", TODAY),
                  "author": {"@type": "Organization", "name": CFG["author"]},
                  "publisher": {"@type": "Organization", "name": SITE, "logo": {"@type": "ImageObject", "url": SITE_URL + "/assets/og-image.png"}},
                  "mainEntityOfPage": f"{SITE_URL}/{path}", "image": f"{SITE_URL}/{a['image']}" if a["image"] else SITE_URL + "/assets/og-image.png"}
        page(path, f"{a['title']} | {SITE}", a["description"], body, d2, keywords=a.get("keywords", ""),
             ld=[art_ld, breadcrumb_ld([("Home", ""), ("Blog", "blog/"), (a["title"], path)])], priority="0.7", og_type="article", image=a["image"])


# --------------------------------------------------------------------------
# Static pages
# --------------------------------------------------------------------------
def build_static_pages():
    d = 1
    email = esc(CFG["contact_email"])
    partners = ", ".join(b["name"] for b in ALL)
    pages = {
        "about/": ("About Us & Methodology", f"""
<p>{esc(SITE)} helps traders around the world find forex brokers and crypto exchanges that actually accept clients from their country. We publish comparisons, reviews, licence checks, country guides, free trading signals and educational articles.</p>
<h2>How we rate providers</h2>
<p>Each provider gets an editorial score out of 10 based on:</p>
<ul><li><strong>Regulation & safety (30%)</strong> — licences and their tier, client-fund segregation, negative balance protection, track record.</li>
<li><strong>Costs (25%)</strong> — spreads, commissions and trading fees, deposit and withdrawal fees.</li>
<li><strong>Accessibility (20%)</strong> — minimum deposit, number of countries served, local payment methods, KYC process.</li>
<li><strong>Platforms & features (15%)</strong> — MT4/MT5, cTrader, TradingView, copy trading, mobile apps.</li>
<li><strong>Support & reputation (10%)</strong> — customer service and user feedback.</li></ul>
<p>Scores are our editorial opinion and are reviewed regularly.</p>
<h2>How we check licences and country availability</h2>
<p>We collect licence details from providers' official legal pages, regulator registers and reputable industry sources, and list licence numbers where they are publicly confirmed. Country availability comes from each provider's published restricted-country list. A country is marked <em>Available*</em> when it is not on that list; providers make the final decision when you register.</p>
<h2>Corrections</h2><p>Spotted outdated information? Email <a href="mailto:{email}">{email}</a>.</p>"""),
        "contact/": ("Contact Us", f"""<p>Questions, corrections or partnership enquiries:</p>
<ul><li>Email: <a href="mailto:{email}">{email}</a></li><li>Telegram: <a href="{esc(CFG['telegram_url'])}" target="_blank" rel="noopener">{esc(CFG['telegram_url'])}</a></li></ul>
<p>We cannot help with account problems at a broker or exchange — please contact that provider's support team directly through its official website.</p>"""),
        "risk-disclaimer/": ("Risk Disclaimer", """<p>Trading foreign exchange (forex), contracts for difference (CFDs), cryptocurrencies and crypto derivatives on margin carries a high level of risk and may not be suitable for everyone. Leverage can work against you as well as for you. Most retail investor accounts lose money when trading CFDs.</p>
<p>Before trading, consider your objectives, experience and risk appetite. Never invest money you cannot afford to lose. Seek advice from an independent, licensed financial adviser if you have any doubts.</p>
<p>Signals, analysis and opinions on this website are general information and education only — not personal financial advice. Past performance is not a reliable indicator of future results.</p>
<p>Offshore brokers and crypto exchanges may not be authorised in your country, and you may have limited or no protection if they fail. It is your responsibility to make sure that using any provider is legal where you live.</p>"""),
        "privacy-policy/": ("Privacy Policy", f"""<p>Last updated: {esc(LAST_REVIEWED)}.</p>
<p>This website does not require an account and does not collect personal information through forms. If Google Analytics is enabled, it uses cookies to collect anonymous usage data (pages visited, device type, approximate country). You can block these cookies in your browser.</p>
<p>Company icons are loaded from Google's public favicon service, which may receive your IP address when the images load.</p>
<p>When you click a link to a broker or exchange you leave our website and that provider's privacy policy applies.</p>
<p>This site is hosted on GitHub Pages, which may log visitors' IP addresses for security purposes.</p>
<p>Contact: <a href="mailto:{email}">{email}</a></p>"""),
        "terms/": ("Terms of Use", f"""<p>By using {esc(SITE)} you agree to these terms. All content is provided for general information and education, without warranties. Information about brokers and exchanges — fees, minimum deposits, leverage, licences and country availability — can change at any time; always verify it on the provider's official website and the regulator's register.</p>
<p>We are not a broker, exchange or financial adviser and do not hold client funds. We are not responsible for losses arising from the use of this website or any third-party service.</p>"""),
    }
    for path, (title, content) in pages.items():
        body = f"""<section class="pagehead"><div class="wrap narrow">{crumbs_html([("Home", ""), (title, path)], d)}<h1>{esc(title)}</h1></div></section>
<section class="wrap narrow section prose">{content}</section>"""
        page(path, f"{title} | {SITE}", f"{title} — {SITE}. {CFG['site_tagline']}.", body, d, priority="0.3")

    body = f"""<section class="pagehead"><div class="wrap narrow"><h1>Page not found</h1><p class="lead">The page you are looking for has moved or does not exist.</p>
<p><a class="btn btn-gold" href="">Go to homepage</a> <a class="btn btn-ghost" href="countries/">Find your country</a></p></div></section>"""
    page("404.html", f"Page not found | {SITE}", "Page not found.", body, 0, noindex=True)
    p404 = OUT / "404.html"
    t = p404.read_text(encoding="utf-8")
    t = re.sub(r'(href|src)="(?!https?:|#|mailto:)([^"]*)"', lambda m: f'{m.group(1)}="{SITE_URL}/{m.group(2)}"', t)
    p404.write_text(t, encoding="utf-8")


def build_sitemap_robots():
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    urls = "".join(f"<url><loc>{SITE_URL}/{p}</loc><lastmod>{now}</lastmod><priority>{pr}</priority></url>" for p, pr in PAGES)
    (OUT / "sitemap.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>\n', encoding="utf-8")
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {SITE_URL}/sitemap.xml\n", encoding="utf-8")
    (OUT / ".nojekyll").write_text("", encoding="utf-8")


def available_count(b):
    return sum(1 for c in COUNTRIES if status_for(b, c["code"]) != "no")


def reg_summary(b, n=3):
    return ", ".join(short_reg(l) for l in b["licences"][:n])


def directory_block(kind, depth):
    base = "forex-brokers/" if kind == "forex" else "crypto-exchanges/"
    phrase = "Best forex broker in" if kind == "forex" else "Best crypto exchange in"
    regions = {}
    for c in COUNTRIES:
        regions.setdefault(c["region"], []).append(c)
    return "".join(
        f'<div class="region"><h3>{phrase} {esc(r)}</h3><div class="dir">' +
        "".join(f'<a href="{link(base + c["slug"] + "/", depth)}">{c["flag"]} {phrase} {esc(c["in_name"])}</a>' for c in cs) + "</div></div>"
        for r, cs in sorted(regions.items()))


def pillar_entry(b, rank, depth):
    rp = review_path(b)
    facts = ([("Minimum deposit", b["min_deposit"]), ("Max leverage", b["max_leverage"]), ("Spreads", b["spreads"]), ("Platforms", b["platforms"]), ("Copy trading", b["copy_trading"]), ("Regulation", reg_summary(b, 5))]
             if is_fx(b) else
             [("Minimum deposit", b["min_deposit"]), ("Max leverage", b["max_leverage"]), ("Fees", b["fees"]), ("Markets", b["coins"]), ("Copy trading", b["copy_trading"]), ("Licences", reg_summary(b, 5))])
    rows = "".join(f"<tr><th>{esc(k)}</th><td>{esc(v)}</td></tr>" for k, v in facts)
    label = BEST_FOR.get(b["slug"], "Top pick")
    hid = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")
    return f"""<section class="pillar-entry card {'fx' if is_fx(b) else 'cx'}" id="{hid}">
 <div class="pe-head"><span class="rank-big">#{rank}</span>{logo(b, 'lg')}<div><h2>{esc(label)}: {esc(b['name'])}</h2><p class="muted">{esc(b['tagline'])} · Score {b['score']:.1f}/10</p></div></div>
 <p>{esc(b['summary'])}</p>
 <div class="grid g2"><div class="table-wrap"><table class="facts-table">{rows}</table></div>
 <div><h3>Why {esc(b['name'])} is the {esc(label.lower())}</h3><ul class="ticks">{''.join(f'<li>{esc(p)}</li>' for p in b['pros'])}</ul>
 <p><strong>Best for:</strong> {esc(b['best_for'])}</p>
 <div class="bc-cta">{visit_buttons(b)}<a class="btn btn-ghost" href="{link(rp, depth)}">{esc(b['name'])} review</a><a class="btn btn-ghost" href="{link(rp + 'sign-up/', depth)}">How to sign up</a></div></div></div>
</section>"""


def build_pillar(kind):
    fx = kind == "forex"
    items = BROKERS if fx else EXCHANGES
    d = 1
    path = "best-forex-broker/" if fx else "best-crypto-exchange/"
    kw1 = "best forex broker" if fx else "best crypto exchange"
    K = kw1.title()
    n = len(items)
    img = f"assets/img/{path.strip('/')}-ranking.jpg"
    hero = f'<figure class="art-hero"><img src="../{img}" alt="{K} {YEAR}" width="2400" height="1260" fetchpriority="high"></figure>' if (ROOT / img).exists() else ""
    toc = [(re.sub(r"[^a-z0-9]+", "-", BEST_FOR[b["slug"]].lower()).strip("-"), f"{BEST_FOR[b['slug']]}: {b['name']}") for b in items]
    toc_html = "".join(f'<li><a href="#{h}">{esc(t)}</a></li>' for h, t in toc)
    entries = "".join(pillar_entry(b, i, d) for i, b in enumerate(items, 1))
    low = sorted(items, key=lambda b: float(re.sub(r"[^0-9.]", "", b["min_deposit"].split("(")[0]) or 0))
    lev_num = lambda b: float((re.findall(r"1:(\d+)", b["max_leverage"]) or re.findall(r"(\d+)x", b["max_leverage"]) or ["0"])[0])
    top_tier = [b for b in items if has_top(b)]
    if fx:
        fca = [b for b in items if any("Financial Conduct Authority" in l["regulator"] for l in b["licences"])]
        asic = [b for b in items if any("ASIC" in l["regulator"] for l in b["licences"])]
        cysec = [b for b in items if any("CySEC" in l["regulator"] for l in b["licences"])]
        mt5 = [b for b in items if "MT5" in b["platforms"]]
        extra = f"""
<h2 id="best-fca-regulated-forex-broker">Best FCA Regulated Forex Broker</h2>
<p>If UK regulation matters to you, the best FCA regulated forex broker choices are {', '.join(f'<a href="{link(review_path(b), d)}">{esc(b["name"])}</a>' for b in fca)}. Each runs a UK entity authorised by the Financial Conduct Authority: {'; '.join(esc(b['name'] + ' — ' + next(l['number'] for l in b['licences'] if 'Financial Conduct Authority' in l['regulator'])) for b in fca)}.</p>
<h2 id="best-asic-and-cysec-regulated-forex-broker">Best ASIC and CySEC Regulated Forex Broker</h2>
<p>For Australian oversight, the best ASIC regulated forex broker options are {', '.join(esc(b['name']) for b in asic)}. In the EU, the best CySEC regulated forex broker options are {', '.join(esc(b['name']) for b in cysec)}.</p>
<h2 id="best-forex-broker-with-low-minimum-deposit">Best Forex Broker with Low Minimum Deposit</h2>
<ol>{''.join(f'<li><a href="{link(review_path(b), d)}"><strong>{esc(b["name"])}</strong></a> — {esc(b["min_deposit"])}: {esc(b["min_deposit_note"])}</li>' for b in low)}</ol>
<h2 id="best-forex-broker-with-high-leverage">Best Forex Broker with High Leverage</h2>
<p>For maximum flexibility, the best forex broker for high leverage choices are {', '.join(f'{esc(b["name"])} ({esc(b["max_leverage"])})' for b in sorted(items, key=lev_num, reverse=True)[:4])}. Use high leverage carefully and size every trade by risk.</p>
<h2 id="best-mt5-forex-broker">Best MT5 Forex Broker</h2>
<p>All {len(mt5)} brokers in this ranking support MetaTrader 5. The best MT5 forex broker for raw spreads is IC Markets; for $0–$10 accounts choose HFM, Exness or RoboForex; and for commission-free trading choose Octa.</p>
<h2 id="best-forex-broker-for-gold-trading">Best Forex Broker for Gold (XAUUSD) Trading</h2>
<p>Gold traders look for tight XAUUSD spreads, fast execution and flexible leverage. Exness is widely considered the best forex broker for gold trading, with HFM and Vantage close behind. Read our <a href="../guides/how-to-trade-gold-xauusd/">gold trading guide</a>.</p>
<h2 id="how-to-choose-the-best-forex-broker">How to Choose the Best Forex Broker for You</h2>
<ol><li><strong>Check the licence.</strong> The best forex broker is regulated — look for FCA, ASIC, CySEC, DFSA or FSCA licences in our <a href="../licences/">licence table</a>.</li>
<li><strong>Match the minimum deposit to your budget.</strong> Start from $1 at InstaForex, $0 at HFM or $10 at Exness.</li>
<li><strong>Compare spreads and commissions.</strong> Raw/ECN accounts suit active traders; commission-free accounts suit beginners.</li>
<li><strong>Pick your platform.</strong> MT4, MT5, cTrader or TradingView.</li>
<li><strong>Check availability in your country</strong> — see the best forex broker by country below.</li>
<li><strong>Test with a demo account</strong> before trading live.</li></ol>"""
        faqs = [(f"What is the best forex broker in {YEAR}?", f"Exness is our best forex broker overall for {YEAR}, thanks to its $10 minimum deposit, instant withdrawals and nine licences including the FCA. IC Markets is the best forex broker for scalping, HFM for copy trading and AvaTrade for regulation."),
                ("What is the best forex broker for beginners?", "Exness, Octa and InstaForex are the best forex broker choices for beginners: low minimum deposits ($1–$25), simple accounts and copy trading."),
                ("Which is the best forex broker with the lowest minimum deposit?", "InstaForex ($1), HFM ($0 on Cent/Premium/Zero), Exness ($10) and RoboForex ($10)."),
                ("What is the best regulated forex broker?", "AvaTrade is one of the most regulated brokers in the world (Central Bank of Ireland, ASIC, CySEC, JFSA, FSRA, ISA). Exness, HFM and Vantage hold FCA authorisation."),
                ("What is the best forex broker in my country?", "Use the best forex broker by country list on this page — every country page shows which brokers accept local traders, the local regulator and the best pick for that country."),
                ("Which is the best forex broker for copy trading?", "HFM with HFCOPY, plus Octa, AvaTrade, RoboForex (CopyFX) and InstaForex (ForexCopy).")]
        title = f"Best Forex Broker {YEAR}: Top {n} Best Forex Brokers in the World (Ranked) | {SITE}"
        desc = f"The best forex broker for {YEAR}: our ranking of the top {n} best forex brokers — Exness, IC Markets, HFM, Vantage, AvaTrade and more — by licences, minimum deposit, spreads, leverage and country."
        keywords = f"best forex broker, best forex broker {YEAR}, best forex brokers, best forex broker in the world, best forex broker for beginners, best regulated forex broker, best FCA regulated forex broker, best forex broker low minimum deposit, best MT5 forex broker, best forex broker for gold, best forex broker by country, top forex brokers"
    else:
        lowfee = sorted(items, key=lambda b: ("0% maker" not in b["fees"], b["fees"]))
        extra = f"""
<h2 id="best-crypto-exchange-for-futures">Best Crypto Exchange for Futures Trading</h2>
<p>For leverage and liquidity, the best crypto exchange for futures trading choices are {', '.join(f'{esc(b["name"])} ({esc(b["max_leverage"])})' for b in sorted(items, key=lev_num, reverse=True)[:5])}. Bitunix is our best crypto exchange for futures overall thanks to 0.02%/0.06% fees, copy trading and TradingView charts.</p>
<h2 id="best-crypto-exchange-with-lowest-fees">Best Crypto Exchange with the Lowest Fees</h2>
<ul>{''.join(f'<li><a href="{link(review_path(b), d)}"><strong>{esc(b["name"])}</strong></a> — {esc(b["fees"])}</li>' for b in lowfee)}</ul>
<h2 id="best-licensed-crypto-exchange">Best Licensed and Regulated Crypto Exchange</h2>
<p>The best regulated crypto exchange choices hold top-tier licences: {', '.join(f'<a href="{link(review_path(b), d)}">{esc(b["name"])}</a> ({esc(reg_summary(b, 3))})' for b in top_tier)}. See every licence on our <a href="../licences/">licence page</a>.</p>
<h2 id="best-crypto-exchange-wallet">Best Crypto Exchange Wallet</h2>
<p>Every exchange in this ranking gives you a built-in <strong>crypto exchange wallet</strong> — your spot, funding and futures accounts — so you can deposit, store and trade in one place. The best crypto exchange wallet options are:</p>
<ul><li><strong>Binance</strong> — the best crypto exchange wallet for most people: a spot/funding wallet plus the self-custody <em>Binance Web3 Wallet</em> inside the same app.</li>
<li><strong>Bybit</strong> — a unified trading account plus the <em>Bybit Web3 wallet</em> and the Bybit Card for spending crypto.</li>
<li><strong>Bitunix</strong> — the best crypto exchange wallet for futures traders: move USDT between spot and futures instantly.</li>
<li><strong>BingX, MEXC, BloFin and KuCoin</strong> — fast multi-network deposits (TRC20, BEP20, ERC20, Solana and more) for thousands of coins.</li></ul>
<p><strong>Wallet safety tips:</strong> turn on app-based 2FA, set an anti-phishing code and a withdrawal whitelist, and always select the same network when sending crypto. For long-term holdings, many traders also keep a hardware wallet. Read our <a href="../guides/crypto-exchange-safety/">crypto security guide</a>.</p>
<h2 id="best-crypto-exchange-for-beginners">Best Crypto Exchange for Beginners</h2>
<p>Binance and Bybit are the best crypto exchange choices for beginners: simple apps, P2P and card purchases, Earn products and copy trading. BingX is the best crypto exchange for beginners who want to copy experienced traders.</p>
<h2 id="how-to-choose-the-best-crypto-exchange">How to Choose the Best Crypto Exchange</h2>
<ol><li><strong>Licences and security</strong> — VARA, MiCA, AFSA licences, proof of reserves, 2FA.</li>
<li><strong>Fees</strong> — compare maker/taker fees for spot and futures.</li>
<li><strong>Coins and leverage</strong> — altcoin selection and maximum leverage.</li>
<li><strong>Wallet and deposits</strong> — supported networks, P2P and card options in your currency.</li>
<li><strong>Copy trading and bots</strong> — if you want automated strategies.</li>
<li><strong>Availability</strong> — check the best crypto exchange by country below.</li></ol>"""
        faqs = [(f"What is the best crypto exchange in {YEAR}?", f"Bitunix is our best crypto exchange overall for {YEAR}, with up to 200x leverage, low 0.02%/0.06% futures fees and copy trading. Bybit is the best licensed crypto exchange, Binance the best for beginners and BingX the best for copy trading."),
                ("What is the best crypto exchange wallet?", "Binance and Bybit offer the best crypto exchange wallet experience — an exchange wallet plus a built-in Web3 wallet in one app. Bitunix is best for moving funds quickly between spot and futures."),
                ("Which is the best crypto exchange for futures?", "Bitunix (200x), MEXC (200x), BloFin and BitBase (150x), Binance, BingX and KuCoin (125x) and Bybit (100x)."),
                ("What is the best crypto exchange with low fees?", "MEXC has 0% maker fees on spot and futures. Bitunix, Bybit, Binance, BingX, BloFin and KuCoin all charge 0.02% maker on futures."),
                ("What is the best crypto exchange in my country?", "Use the best crypto exchange by country list on this page — each country page shows which exchanges accept local users and our top pick."),
                ("Which is the best regulated crypto exchange?", "Bybit (VARA, MiCA, AFSA), Binance (VARA, FSRA, CBB, AFSA), BingX and KuCoin (MiCA).")]
        title = f"Best Crypto Exchange {YEAR}: Top {n} Best Crypto Exchanges & Wallets (Ranked) | {SITE}"
        desc = f"The best crypto exchange for {YEAR}: top {n} best crypto exchanges and exchange wallets — Bitunix, Bybit, Binance, BingX, MEXC and more — ranked by fees, leverage, licences and country."
        keywords = f"best crypto exchange, best crypto exchange {YEAR}, best crypto exchanges, best crypto exchange wallet, best crypto wallet, best crypto exchange for beginners, best crypto exchange for futures, best crypto exchange low fees, best regulated crypto exchange, best crypto exchange by country, top crypto exchanges"
    body = f"""<section class="pagehead {'fx' if fx else 'cx'}-head"><div class="wrap">
 {crumbs_html([("Home", ""), (K, path)], d)}
 <span class="kicker">{'FOREX RANKING' if fx else 'CRYPTO RANKING'} · UPDATED {esc(LAST_REVIEWED).upper()}</span>
 <h1>{K} {YEAR} – Top {n} Best {'Forex Brokers' if fx else 'Crypto Exchanges'} {'in the World' if fx else '&amp; Wallets'}</h1>
 <p class="lead">Looking for the {kw1}? We compared {n} {'regulated forex brokers' if fx else 'crypto exchanges'} on licences, {'spreads' if fx else 'fees'}, leverage, minimum deposit and availability in {len(COUNTRIES)} countries. Our {kw1} overall is <strong>{esc(items[0]['name'])}</strong>.</p>
 {country_search(d, 'forex-brokers' if fx else 'crypto-exchanges', 'Find the ' + kw1 + ' in your country…')}
</div></section>
<div class="wrap narrow">{hero}</div>
<section class="wrap section two-col">
 <div class="prose">
  <h2 id="quick-picks">{K} {YEAR}: Quick Picks</h2>
  <ol class="quick">{''.join(f'<li><a href="#{h}">{esc(t)}</a></li>' for h, t in toc)}</ol>
  <h2>{K} Comparison Table</h2>
  {compare_table(items, d)}
 </div>
 <aside class="side"><div class="card sticky"><h3>On this page</h3><ol class="toc-list">{toc_html}</ol>
 <p><a href="#{'best-forex-broker-by-country' if fx else 'best-crypto-exchange-by-country'}"><strong>{K} by country →</strong></a></p></div></aside>
</section>
<div class="wrap section">{entries}</div>
<section class="wrap section prose narrow-wide">{extra}</section>
<section class="wrap section" id="{'best-forex-broker-by-country' if fx else 'best-crypto-exchange-by-country'}">
 <h2>{K} by Country</h2>
 <p>Click your country to see the {kw1} for traders there, with local regulation notes and the providers that accept local traders.</p>
 {directory_block(kind, d)}
</section>
<section class="wrap section">{faq_html(faqs, f"{K} – Frequently Asked Questions")}</section>"""
    art_ld = {"@context": "https://schema.org", "@type": "Article", "headline": f"{K} {YEAR}", "description": desc,
              "datePublished": TODAY, "dateModified": TODAY, "author": {"@type": "Organization", "name": CFG["author"]},
              "publisher": {"@type": "Organization", "name": SITE}, "mainEntityOfPage": f"{SITE_URL}/{path}",
              "image": f"{SITE_URL}/{img}"}
    page(path, title, desc, body, d, keywords=keywords,
         ld=[art_ld, itemlist_ld(f"{K} {YEAR}", items), breadcrumb_ld([("Home", ""), (K, path)]), faq_ld(faqs)],
         priority="0.95", og_type="article", theme="fx" if fx else "cx", image=img if (ROOT / img).exists() else None)


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    shutil.copytree(ROOT / "assets", OUT / "assets")
    if (ROOT / "CNAME").exists():
        shutil.copy(ROOT / "CNAME", OUT / "CNAME")
    build_home()
    build_hub("forex")
    build_hub("crypto")
    build_pillar("forex")
    build_pillar("crypto")
    for b in ALL:
        build_review(b)
        build_signup(b)
        build_legit(b)
    for items in (BROKERS, EXCHANGES):
        for a, b in itertools.combinations(items, 2):
            build_vs(a, b)
    build_compare_index()
    build_licences()
    build_countries_index()
    for c in COUNTRIES:
        build_country(c, "forex")
        build_country(c, "crypto")
        build_country_overview(c)
    build_signals("forex")
    build_signals("crypto")
    build_signals_hub()
    build_guides()
    build_static_pages()
    build_sitemap_robots()
    print(f"Built {len(PAGES)} pages into {OUT} for {SITE_URL}")


if __name__ == "__main__":
    sys.exit(main())
