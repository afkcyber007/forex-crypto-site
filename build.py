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
    "IN": "The Reserve Bank of India (RBI) only allows residents to trade forex in INR-based pairs (and some permitted crosses) on SEBI-recognised Indian exchanges, and publishes an Alert List of unauthorised online forex platforms. Crypto is legal to hold but heavily taxed (30% on gains plus 1% TDS), and offshore exchanges serving Indians must register with FIU-IND.",
    "PK": "The State Bank of Pakistan and SECP do not license offshore forex CFD brokers for retail clients, so traders who use international brokers are protected only by the broker's foreign regulator. Pakistan created the Pakistan Virtual Assets Regulatory Authority (PVARA) in 2025 to license crypto service providers, so rules are changing — check the latest guidance.",
    "US": "US residents may only trade forex with dealers registered with the CFTC and NFA, and CFDs are not available to US retail traders. None of the offshore brokers or global exchanges compared here accept US residents (Binance.US is a separate company).",
    "GB": "UK brokers must be authorised by the FCA. Retail forex leverage is capped at 1:30 on major pairs, and the FCA bans the sale of crypto derivatives (futures, options and CFDs) to retail consumers. MEXC, BingX, PU Prime and Elev8 do not accept UK residents.",
    "AU": "ASIC caps retail forex leverage at 1:30 on major pairs and bans binary options. Crypto exchanges must register with AUSTRAC — Bitunix, BingX and KuCoin hold AUSTRAC registrations.",
    "CA": "Forex and CFD dealers must be registered with CIRO and provincial securities regulators. Most offshore brokers and exchanges — including IC Markets, Vantage, Elev8, Bitunix, Binance, BingX and MEXC — do not accept Canadian residents.",
    "SG": "The Monetary Authority of Singapore licenses brokers and crypto service providers. Vantage, PU Prime, Bitunix, Binance, BingX, MEXC and KuCoin do not accept Singapore residents.",
    "AE": "Forex brokers are licensed by the Capital Market Authority (onshore), the DFSA (DIFC) or the FSRA (ADGM), and crypto firms in Dubai by VARA. Binance holds VARA and ADGM licences; Bitunix lists the UAE as restricted.",
    "CN": "Mainland China restricts capital outflows and has banned crypto trading since 2021. Most international brokers and exchanges do not accept mainland Chinese residents.",
    "JP": "Japan's FSA caps retail forex leverage at 1:25, and crypto exchanges must register with the FSA. Vantage and Elev8 do not accept Japanese residents.",
    "HK": "The SFC licenses forex dealers and virtual-asset trading platforms. Bitunix, BingX, MEXC and KuCoin do not serve Hong Kong residents.",
    "FR": "As an EU country, France applies ESMA's 1:30 leverage cap, and crypto platforms need MiCA authorisation. Bitunix and KuCoin list France as restricted; Binance holds an AMF registration.",
    "NL": "The AFM supervises brokers and crypto platforms under MiCA. Binance, BingX and KuCoin do not accept Dutch residents.",
    "ZA": "The FSCA licenses forex brokers — Exness, Vantage and PU Prime all hold FSCA licences for local entities. Crypto assets are classed as financial products, so crypto platforms also need FSCA authorisation.",
    "NG": "Nigeria's Investments and Securities Act 2025 classes digital assets as securities under SEC Nigeria. Check the regulator's list of registered platforms before funding an account.",
    "KE": "The Capital Markets Authority licenses online forex brokers. Exness holds CMA licence 162 for its Kenyan entity.",
    "MY": "The Securities Commission Malaysia has repeatedly warned about unlicensed foreign forex and crypto platforms. Only SC-registered exchanges may legally serve Malaysians; KuCoin lists Malaysia as restricted.",
    "ID": "Forex and commodity futures fall under Bappebti and OJK. Only locally registered crypto exchanges may legally serve Indonesian residents.",
    "TR": "Turkey's Capital Markets Board (SPK) restricts foreign forex brokers, and a 2024 law requires crypto platforms serving Turkish users to be licensed by the SPK.",
    "PH": "The SEC Philippines and BSP regulate brokers and virtual asset service providers, and the SEC has blocked several unregistered offshore exchanges. PU Prime does not accept Philippine residents.",
    "IL": "The Israel Securities Authority licenses forex dealers. IC Markets and Elev8 do not accept Israeli residents.",
    "NZ": "The FMA licenses derivatives issuers. IC Markets and Elev8 do not accept New Zealand residents.",
    "RU": "International sanctions limit payments to and from Russia, and PU Prime does not accept Russian residents.",
    "BD": "Bangladesh Bank restricts outward remittances for speculative trading and has warned against crypto trading. Understand the foreign-exchange rules before funding an overseas account.",
    "SA": "The Capital Market Authority licenses securities firms. Saudi traders using international brokers usually choose swap-free (Islamic) accounts.",
    "EG": "The Central Bank of Egypt restricts crypto activity without a licence, and foreign-currency transfers are tightly controlled.",
    "BH": "The Central Bank of Bahrain licenses crypto-asset firms — Binance holds a CBB licence through Binance Bahrain.",
    "KZ": "The Astana International Financial Centre (AIFC) regulates crypto exchanges through the AFSA; Binance holds an AFSA licence.",
}
EU_NOTE = "As an EU member state, {name} applies ESMA rules: retail forex leverage is capped at 1:30 on major pairs, and crypto-asset service providers need MiCA authorisation. Offshore brokers often onboard EU residents on different terms, or not at all."


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
    cls = {"Top-tier": "t1", "Mid-tier": "t2", "Offshore": "t3", "Licence": "t2", "Registration": "t2",
           "AML registration": "t3", "Company registration": "t4"}.get(t, "t3")
    return f'<span class="tier {cls}">{esc(t)}</span>'


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
       ("Free Signals", "free-signals/", ""), ("Guides", "guides/", "")]


def page(path, title, description, body, depth, keywords="", ld=None, priority="0.6", og_type="website",
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
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
{f'<meta name="keywords" content="{esc(keywords)}">' if keywords else ''}
<meta name="robots" content="{'noindex, follow' if noindex else 'index, follow, max-image-preview:large'}">
<link rel="canonical" href="{esc(url)}">
<meta property="og:type" content="{og_type}">
<meta property="og:site_name" content="{esc(SITE)}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}">
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
<div class="riskbar">Trading forex, CFDs and crypto with leverage carries a high risk of losing money. <a href="{link('risk-disclaimer/', depth)}">Risk warning</a> · We may earn a commission from partner links. <a href="{link('affiliate-disclosure/', depth)}">Disclosure</a></div>
<header class="top">
 <div class="wrap top-in">
  <a class="brand" href="{link('', depth)}"><img src="{r}assets/favicon.svg" alt="" width="32" height="32"> <span>{esc(SITE)}</span></a>
  <button class="menu-btn" aria-label="Menu" aria-expanded="false" onclick="this.setAttribute('aria-expanded',document.body.classList.toggle('nav-open'))">☰</button>
  <nav class="mainnav" aria-label="Main">{nav_html}</nav>
 </div>
</header>
<main id="main">
{body}
</main>
<footer class="foot">
 <div class="wrap foot-grid">
  <div><p class="brand"><img src="{r}assets/favicon.svg" alt="" width="28" height="28"> {esc(SITE)}</p><p>{esc(CFG['site_tagline'])}. Independent comparisons of forex brokers and crypto exchanges for traders in {len(COUNTRIES)} countries and territories worldwide.</p>
  <p><a class="btn btn-tg" href="{esc(CFG['telegram_url'])}" target="_blank" rel="noopener">Join our Telegram</a></p></div>
  <div><h3>Forex</h3><a href="{link('forex-brokers/', depth)}">Best forex brokers</a><a href="{link('forex-brokers/compare/', depth)}">Forex comparison table</a>{''.join(f'<a href="{link(review_path(b), depth)}">{esc(b["name"])} review</a>' for b in BROKERS)}<a href="{link('free-forex-signals/', depth)}">Free forex signals</a></div>
  <div><h3>Crypto</h3><a href="{link('crypto-exchanges/', depth)}">Best crypto exchanges</a><a href="{link('crypto-exchanges/compare/', depth)}">Crypto comparison table</a>{''.join(f'<a href="{link(review_path(b), depth)}">{esc(b["name"])} review</a>' for b in EXCHANGES)}<a href="{link('free-crypto-signals/', depth)}">Free crypto signals</a></div>
  <div><h3>By country</h3>{''.join(f'<a href="{link("countries/" + BY_CODE[c]["slug"] + "/", depth)}">{esc(BY_CODE[c]["name"])}</a>' for c in pop[:10])}<a href="{link('countries/', depth)}"><strong>All {len(COUNTRIES)} countries →</strong></a></div>
  <div><h3>Company</h3><a href="{link('about/', depth)}">About & methodology</a><a href="{link('licences/', depth)}">Licences & regulation</a><a href="{link('contact/', depth)}">Contact</a><a href="{link('risk-disclaimer/', depth)}">Risk disclaimer</a><a href="{link('affiliate-disclosure/', depth)}">Affiliate disclosure</a><a href="{link('privacy-policy/', depth)}">Privacy policy</a><a href="{link('terms/', depth)}">Terms of use</a></div>
 </div>
 <div class="wrap legal"><p><strong>Risk warning:</strong> CFDs, forex and crypto derivatives are complex instruments with a high risk of losing money rapidly due to leverage. Most retail accounts lose money. Nothing on this site is financial advice. Information is checked as of {esc(CFG['last_reviewed'])} but can change — always confirm terms, regulation and country availability on the provider's official website. Company names and logos belong to their owners and are used only to identify them.</p>
 <p>© {YEAR} {esc(SITE)}. All rights reserved.</p></div>
</footer>
<script src="{r}assets/main.js" defer></script>
</body>
</html>
"""
    out = OUT / "index.html" if path == "" else (OUT / path if path.endswith(".html") else OUT / path / "index.html")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(doc, encoding="utf-8")
    if not noindex:
        PAGES.append((path, priority))


# --------------------------------------------------------------------------
# Reusable blocks
# --------------------------------------------------------------------------
def brand_card(b, rank, depth, country=None):
    review = link(review_path(b), depth)
    badge = ""
    st = status_for(b, country["code"]) if country else "yes"
    if country:
        badge = {"yes": f'<span class="pill ok">✓ Accepts traders from {esc(country["in_name"])}*</span>',
                 "check": f'<span class="pill warn">? Check availability in {esc(country["in_name"])}</span>',
                 "no": f'<span class="pill bad">✕ Not available in {esc(country["in_name"])}</span>'}[st]
    top = '<span class="ribbon">★ Top pick</span>' if rank == 1 and st != "no" else ""
    if is_fx(b):
        facts = [("Min deposit", b["min_deposit"]), ("Max leverage", b["max_leverage"]), ("Spreads", b["spreads"]), ("Platforms", b["platforms"])]
    else:
        facts = [("Min deposit", b["min_deposit"]), ("Max leverage", b["max_leverage"]), ("Fees", b["fees"]), ("Markets", b["coins"])]
    facts_html = "".join(f"<div><dt>{k}</dt><dd>{esc(v)}</dd></div>" for k, v in facts)
    pros = "".join(f"<li>{esc(p)}</li>" for p in b["pros"][:3])
    regs = "".join(f'<span class="regchip" title="{esc(l["regulator"])}">{BY_CODE[l["country"]]["flag"] if l["country"] in BY_CODE else ""} {esc(short_reg(l))}</span>' for l in b["licences"][:6])
    cta = visit_buttons(b) if st != "no" else f'<span class="pill bad">Not open to residents of {esc(country["in_name"])}</span>'
    return f"""<article class="card brand-card {'fx' if is_fx(b) else 'cx'}" id="{b['slug']}">
 {top}
 <div class="bc-head">
  <span class="rank">#{rank}</span>{logo(b)}
  <div class="bc-name"><h3><a href="{review}">{esc(b['name'])}</a></h3><p class="muted">{esc(b['tagline'])}</p></div>
  <div class="score" title="Our editorial score"><b>{b['score']:.1f}</b><small>/10</small></div>
 </div>
 {badge}
 <dl class="facts">{facts_html}</dl>
 <div class="regs"><span class="regs-label">Licensed / registered:</span>{regs}</div>
 <ul class="ticks">{pros}</ul>
 <div class="bc-cta">{cta}<a class="btn btn-ghost" href="{review}">Review</a></div>
</article>"""


def short_reg(l):
    r = l["regulator"]
    if "MiCA" in r:
        return "MiCA (" + (BY_CODE[l["country"]]["name"] if l["country"] in BY_CODE else "EU") + ")"
    if r.startswith("Company registration"):
        return "Company reg. only"
    m = re.findall(r"\(([A-Z][A-Za-z.\- ]{1,14})\)", r)
    if m:
        return m[0].replace("FSC BVI", "FSC")
    return r.split(" – ")[0].split(",")[0].split(" (")[0].strip()[:22]


def compare_table(items, depth, country=None):
    fx = is_fx(items[0])
    head = "<th>" + ("Broker" if fx else "Exchange") + "</th><th>Score</th><th>Min deposit</th><th>Max leverage</th><th>" + ("Spreads" if fx else "Trading fees") + "</th><th>Top-tier licence</th>"
    if country:
        head += f"<th>{esc(country['name'])}</th>"
    head += "<th></th>"
    rows = []
    for b in items:
        st = status_for(b, country["code"]) if country else "yes"
        cell = ""
        if country:
            cell = "<td>" + {"yes": '<span class="pill ok">Available*</span>', "check": '<span class="pill warn">Check</span>', "no": '<span class="pill bad">Not available</span>'}[st] + "</td>"
        top = '<span class="yes">✓ Yes</span>' if has_top(b) else '<span class="no">✕ No</span>'
        btn = "—" if st == "no" else visit_buttons(b, small=True, first_only=True)
        rows.append(f"<tr><td><a class='tname' href='{link(review_path(b), depth)}'>{logo(b, 'sm')} {esc(b['name'])}</a></td><td><b class='sc'>{b['score']:.1f}</b></td>"
                    f"<td>{esc(b['min_deposit'])}</td><td>{esc(b['max_leverage'])}</td><td>{esc(b['spreads'] if fx else b['fees'])}</td><td>{top}</td>{cell}<td>{btn}</td></tr>")
    return f'<div class="table-wrap"><table class="compare"><thead><tr>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'


def full_matrix(items, depth):
    """Transposed table: one column per provider, one row per quality."""
    fx = is_fx(items[0])
    rows = [("Our score", lambda b: f"<b class='sc'>{b['score']:.1f}</b>/10"),
            ("Founded", lambda b: esc(b["founded"])),
            ("Minimum deposit", lambda b: esc(b["min_deposit"])),
            ("Max leverage", lambda b: esc(b["max_leverage"]))]
    if fx:
        rows += [("Spreads & commission", lambda b: esc(b["spreads"])), ("Platforms", lambda b: esc(b["platforms"]))]
    else:
        rows += [("Trading fees", lambda b: esc(b["fees"])), ("Coins / markets", lambda b: esc(b["coins"])),
                 ("Products", lambda b: esc(b["features"])), ("KYC", lambda b: esc(b["kyc"]))]
    rows += [("Copy trading", lambda b: esc(b["copy_trading"])),
             ("Top-tier licence", lambda b: '<span class="yes">✓ Yes</span>' if has_top(b) else '<span class="no">✕ No</span>'),
             ("Safety level", lambda b: f'<span class="pill {safety_level(b)[1]}">{safety_level(b)[0]}</span>'),
             ("Licences / registrations", lambda b: "<br>".join(f"{BY_CODE[l['country']]['flag'] if l['country'] in BY_CODE else ''} {esc(short_reg(l))} {tier_badge(l['tier'])}" for l in b["licences"])),
             ("Regulated in", lambda b: ", ".join(esc(c["name"]) for c in licence_countries(b))),
             ("Countries not served", lambda b: f"{len(not_served(b))} <a href='{link(review_path(b), depth)}#availability'>see list</a>"),
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
            f'<p class="tiny">Tiers are our own classification. "—" means no public number was confirmed; check the regulator\'s official register before depositing. Only the entity that signs you up protects you.</p>')


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
    return f'<p class="disclose">Rankings are editorial. "Visit Site" buttons are partner links: if you open an account we may earn a commission at no extra cost to you, which can influence which providers we feature. <a href="{link("affiliate-disclosure/", depth)}">How we make money</a>.</p>'


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
    for line in md.splitlines():
        t = line.strip()
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
    flush(); close_list()
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


def article_cards(arts, depth):
    def card(a):
        img = f'<img src="{rel(depth)}{a["image"]}" alt="{esc(a["title"])}" loading="lazy" width="2400" height="1260">' if a["image"] else ""
        return (f'<a class="card art-card" href="{link("guides/" + a["slug"] + "/", depth)}"><div class="thumb">{img}</div><div class="art-body">'
                f'<span class="tag">{esc(a.get("category", "Guide"))}</span><h3>{esc(a["title"])}</h3><p>{esc(a["description"])}</p>'
                f'<span class="more">Read guide →</span></div></a>')
    return '<div class="grid g3">' + "".join(card(a) for a in arts) + "</div>"


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
  <p class="eyebrow"><span class="dot"></span> Updated {esc(CFG['last_reviewed'])} · Worldwide · {len(COUNTRIES)} countries</p>
  <h1>Find the Best <span class="g-fx">Forex Broker</span> &amp; <span class="g-cx">Crypto Exchange</span> for Your Country</h1>
  <p class="lead">Licences, minimum deposits, leverage and fees compared side by side — and instant availability checks for every country in the world.</p>
  {country_search(d)}
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
 <a class="split-card fx" href="forex-brokers/"><span class="kicker">FOREX · CFDs · GOLD</span><h2>Forex Brokers</h2><p>MT4 / MT5 brokers with FCA, ASIC, CySEC &amp; FSCA licences. Minimum deposits from $10.</p><span class="logos">{''.join(logo(b, 'sm') for b in BROKERS)}</span><span class="go">Compare forex brokers →</span></a>
 <a class="split-card cx" href="crypto-exchanges/"><span class="kicker">SPOT · FUTURES · COPY TRADING</span><h2>Crypto Exchanges</h2><p>Bitunix, Binance, BingX and more — fees, leverage up to 200x, KYC and licences.</p><span class="logos">{''.join(logo(b, 'sm') for b in EXCHANGES)}</span><span class="go">Compare crypto exchanges →</span></a>
</section>
<section class="zone cx-zone">
 <div class="wrap section">
  <div class="sec-head"><div><span class="kicker cx">CRYPTO</span><h2>Best crypto exchanges {YEAR}</h2></div><a href="crypto-exchanges/compare/">Full comparison table →</a></div>
  <div class="grid g3">{''.join(brand_card(b, i, d) for i, b in enumerate(EXCHANGES, 1))}</div>
 </div>
</section>
<section class="zone fx-zone">
 <div class="wrap section">
  <div class="sec-head"><div><span class="kicker fx">FOREX</span><h2>Best forex brokers {YEAR}</h2></div><a href="forex-brokers/compare/">Full comparison table →</a></div>
  <div class="grid g3">{''.join(brand_card(b, i, d) for i, b in enumerate(BROKERS, 1))}</div>
  {disclosure_box(d)}
 </div>
</section>
<section class="wrap section">
 <div class="sec-head"><div><span class="kicker">TRUST</span><h2>Who regulates them?</h2></div><a href="licences/">All licences →</a></div>
 <div class="grid g4 lic-grid">{''.join(f'<a class="card lic-card" href="{review_path(b)}real-or-fake/">{logo(b)}<b>{esc(b["name"])}</b><span class="pill {safety_level(b)[1]}">Safety: {safety_level(b)[0]}</span><small>{esc(", ".join(short_reg(l) for l in b["licences"][:4]))}</small></a>' for b in ALL)}</div>
</section>
<section class="band">
 <div class="wrap grid g2">
  <div class="card signal-card fx"><span class="kicker fx">FREE</span><h2>Free Forex Signals</h2><p>XAUUSD gold, EURUSD, GBPUSD and more — entry, stop loss and take profit, shared on Telegram with risk-management tips.</p><a class="btn btn-fx" href="free-forex-signals/">Get free forex signals</a></div>
  <div class="card signal-card cx"><span class="kicker cx">FREE</span><h2>Free Crypto Signals</h2><p>Bitcoin, Ethereum and altcoin futures setups with clear invalidation levels. Learn position sizing before copying any trade.</p><a class="btn btn-cx" href="free-crypto-signals/">Get free crypto signals</a></div>
 </div>
</section>
<section class="wrap section">
 <div class="sec-head"><div><span class="kicker">LEARN</span><h2>Trading guides</h2></div><a href="guides/">All guides →</a></div>
 {article_cards(ARTICLES[:6], d)}
</section>
<section class="wrap section prose">
 <h2>How we compare brokers and exchanges</h2>
 <p>Every provider on {esc(SITE)} is checked against the same criteria: <strong>who licenses it</strong> (with licence numbers), the real minimum deposit, maximum leverage, spreads or trading fees, platforms, copy trading — and <strong>whether it accepts residents of your country</strong>. Our {len(COUNTRIES)} country guides cover every region of the world, from North America and Europe to Africa, the Middle East, Asia and Latin America.</p>
 <p>Restricted-country lists change often, so always confirm on the provider's official website before you deposit. Read our <a href="about/">methodology</a>.</p>
</section>"""
    page("", f"Best Forex Brokers & Crypto Exchanges Worldwide ({YEAR}) – Compared by Country | {SITE}", CFG["site_description"], body, d,
         keywords="best forex broker, best crypto exchange, forex brokers by country, crypto exchanges by country, regulated forex broker, FCA regulated broker, free forex signals, free crypto signals, Bitunix, Binance, BingX, KuCoin, MEXC, Exness, IC Markets, Vantage, PU Prime",
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
    intro = ("Forex brokers give you access to currency pairs, gold (XAUUSD), indices and other CFDs through MetaTrader 4, MetaTrader 5, cTrader and TradingView. We rank them by licences, costs, minimum deposit and platforms."
             if fx else
             "Crypto exchanges let you buy Bitcoin, Ethereum and altcoins and trade perpetual futures with leverage. We rank them by fees, leverage, coin selection, copy trading, licences and where they are available.")
    faqs = ([("Which forex broker has the lowest minimum deposit?", "Exness has the lowest entry point of the brokers we compare, with a $10 minimum on Standard accounts. PU Prime's Cent account starts at $20, Elev8 at about $25 and Vantage at $50."),
             ("Which forex brokers are FCA regulated?", "Exness (FRN 730729) and Vantage (OC376560) both have UK entities authorised by the FCA. IC Markets holds ASIC and CySEC licences. Note that clients outside the UK are usually onboarded through an offshore entity."),
             ("Which forex broker is best for scalping and EAs?", "IC Markets is popular with scalpers and Expert Advisor traders because of raw spreads from 0.0 pips, deep liquidity and cTrader/MT5 support."),
             ("Are offshore forex brokers safe?", "Offshore entities (Seychelles, Mauritius, Comoros) are regulated, but give less investor protection than tier-1 regulators such as the FCA or ASIC. Choose brokers with segregated client funds and negative balance protection, and never deposit more than you can afford to lose.")]
            if fx else
            [("Which crypto exchange is best for futures trading?", "Bitunix is our top pick for crypto futures, with up to 200x leverage, 0.02%/0.06% futures fees and built-in copy trading. Binance has the deepest liquidity, and BingX is the leader in copy trading."),
             ("Which crypto exchanges are licensed?", "Binance holds licences in Dubai (VARA), Abu Dhabi (FSRA), Bahrain and Kazakhstan; BingX and KuCoin have MiCA authorisations in Austria for their EU entities. Bitunix, BingX and KuCoin are registered with AUSTRAC in Australia. MEXC and BitBase have no major licences."),
             ("Do I need KYC?", "Binance and KuCoin require KYC before trading. Bitunix, BingX and MEXC let you start before verifying, but withdrawals are limited or locked until you complete KYC."),
             ("Which exchange has the most coins?", "MEXC lists 2,700+ cryptocurrencies, followed by KuCoin and BingX with 1,000+ each.")])
    body = f"""
<section class="pagehead {'fx' if fx else 'cx'}-head"><div class="wrap">
 {crumbs_html([("Home", ""), (noun, path)], d)}
 <span class="kicker">{'FOREX · CFDs · GOLD' if fx else 'CRYPTO · SPOT · FUTURES'}</span>
 <h1>Best {noun} {YEAR} – Compared &amp; Ranked</h1>
 <p class="lead">{intro}</p>
 {country_search(d, path.strip('/'))}
 <p class="sub-links"><a href="compare/">Full comparison table</a> · <a href="../licences/">Licences &amp; regulation</a> · <a href="../compare/">Head-to-head comparisons</a></p>
</div></section>
<section class="wrap section">
 {compare_table(items, d)}
 {disclosure_box(d)}
 <div class="grid g2">{''.join(brand_card(b, i, d) for i, b in enumerate(items, 1))}</div>
</section>
<section class="wrap section">
 <h2>Best {noun.lower()} by country</h2>
 <p>Pick your country to see which {noun.lower()} accept residents, the local regulator and important legal notes.</p>
 {regions_block(path)}
</section>
<section class="wrap section">{faq_html(faqs)}</section>"""
    kw = ("best forex broker, best forex brokers " + str(YEAR) + ", FCA regulated forex broker, ASIC broker, CySEC broker, low minimum deposit forex broker, ECN broker, MT5 broker, MT4 broker, gold trading broker, XAUUSD broker"
          if fx else
          "best crypto exchange, best crypto exchange " + str(YEAR) + ", crypto futures exchange, low fee crypto exchange, bitcoin exchange, licensed crypto exchange, copy trading crypto, Bitunix, Binance, BingX, MEXC, KuCoin")
    desc = (f"Compare the best forex brokers of {YEAR}: Exness, IC Markets, Vantage, PU Prime and Elev8. FCA/ASIC/CySEC licences, minimum deposits from $10, leverage, spreads and availability worldwide."
            if fx else
            f"Compare the best crypto exchanges of {YEAR}: Bitunix, Binance, BingX, MEXC, KuCoin and BitBase. Fees, futures leverage, licences, KYC and which countries each exchange accepts.")
    page(path, f"Best {noun} {YEAR} – Licences, Fees & Minimum Deposit Compared | {SITE}", desc, body, d, keywords=kw,
         ld=[itemlist_ld(f"Best {noun}", items), breadcrumb_ld([("Home", ""), (noun, path)]), faq_ld(faqs)], priority="0.9", theme="fx" if fx else "cx")

    # full comparison table page
    cpath = path + "compare/"
    d2 = 2
    body = f"""
<section class="pagehead {'fx' if fx else 'cx'}-head"><div class="wrap">
 {crumbs_html([("Home", ""), (noun, path), ("Comparison table", cpath)], d2)}
 <h1>{noun} Comparison Table {YEAR}</h1>
 <p class="lead">Every quality side by side: licences and licence countries, minimum deposit, leverage, {'spreads, platforms' if fx else 'fees, coins, KYC'}, copy trading and how many countries each {'broker' if fx else 'exchange'} refuses. Scroll sideways on mobile.</p>
</div></section>
<section class="wrap section">
 {full_matrix(items, d2)}
 {disclosure_box(d2)}
 <h2>Head-to-head comparisons</h2>
 <div class="clist">{''.join(f'<a href="{link("compare/" + a["slug"] + "-vs-" + b["slug"] + "/", d2)}">{esc(a["name"])} vs {esc(b["name"])}</a>' for a, b in itertools.combinations(items, 2))}</div>
</section>"""
    page(cpath, f"{noun} Comparison Table {YEAR}: Licences, Fees, Leverage & Deposits | {SITE}",
         f"Side-by-side {noun.lower()} comparison table for {YEAR}: {', '.join(b['name'] for b in items)} — licences, minimum deposit, leverage, {'spreads' if fx else 'fees'}, copy trading and country availability.",
         body, d2, keywords=f"{noun.lower()} comparison, compare {noun.lower()}, {noun.lower()} comparison table, " + ", ".join(f"{a['name']} vs {b['name']}" for a, b in itertools.combinations(items, 2)),
         ld=[breadcrumb_ld([("Home", ""), (noun, path), ("Comparison table", cpath)])], priority="0.85", theme="fx" if fx else "cx")


# --------------------------------------------------------------------------
# Brand pages: review, sign-up, real-or-fake
# --------------------------------------------------------------------------
def brand_sidebar(b, d):
    others = [x for x in (BROKERS if is_fx(b) else EXCHANGES) if x["slug"] != b["slug"]]
    rp = review_path(b)
    return f"""<aside class="side">
  <div class="card sticky side-cta {'fx' if is_fx(b) else 'cx'}">{logo(b, 'lg')}<h3>{esc(b['name'])}</h3><p class="muted">{esc(b['tagline'])}</p>
  <p><strong>Min deposit:</strong> {esc(b['min_deposit'])}<br><strong>Score:</strong> {b['score']:.1f}/10</p>{visit_buttons(b)}
  <p class="tiny">Partner link. Capital at risk.</p>
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
        rows += [("Trading fees", b["fees"]), ("Markets", b["coins"]), ("Products", b["features"]), ("KYC", b["kyc"])]
    rows += [("Copy trading", b["copy_trading"]), ("Regulation", b["regulation"]), ("Best for", b["best_for"])]
    if b.get("ref_code"):
        rows.append(("Referral / invite code", b["ref_code"]))
    table = "".join(f"<tr><th>{esc(k)}</th><td>{esc(v)}</td></tr>" for k, v in rows)
    ns = not_served(b)
    avail_count = sum(1 for c in COUNTRIES if status_for(b, c["code"]) != "no")
    lvl, lcls = safety_level(b)
    n = b["name"]
    faqs = [(f"Is {n} real or fake?", f"{n} is a real, operating {'forex broker' if fx else 'crypto exchange'} founded in {b['founded']}. Its safety level in our rating is <strong>{lvl}</strong> based on its licences: {esc(b['regulation'])} Always use the official website ({esc(b['domain'])}) to avoid fake copies."),
            (f"What is the {n} minimum deposit?", f"{b['min_deposit']}. {b['min_deposit_note']}"),
            (f"Is {n} regulated?", b["regulation"]),
            (f"What is the maximum leverage at {n}?", b["max_leverage"] + ". Higher leverage increases both potential profits and losses."),
            (f"Which countries can't use {n}?", f"Based on its published restrictions, {n} does not accept residents of: {', '.join(ns)}."),
            (f"How do I sign up for {n}?", f"Use the Visit Site button, register with email or phone, verify your identity and fund your account. See our step-by-step <a href=\"sign-up/\">{esc(n)} sign-up guide</a>.")]
    body = brand_head(b, d, [("Home", ""), hub, (n + " Review", path)], f"{esc(n)} Review {YEAR}", esc(b["tagline"])) + f"""
<section class="wrap section two-col">
 <div class="prose">
  <div class="verdict card"><span class="pill {lcls}">Safety level: {lvl}</span> <span class="pill">{len(b['licences'])} licence{'s' if len(b['licences']) != 1 else ''} / registrations</span> <span class="pill">Available in ~{avail_count} countries</span><p>{esc(b['summary'])}</p></div>
  <h2>{esc(n)} key facts</h2><div class="table-wrap"><table class="facts-table">{table}</table></div>
  <div class="grid g2 pc"><div class="card"><h3>Pros</h3><ul class="ticks">{''.join(f'<li>{esc(p)}</li>' for p in b['pros'])}</ul></div>
  <div class="card"><h3>Cons</h3><ul class="crosses">{''.join(f'<li>{esc(p)}</li>' for p in b['cons'])}</ul></div></div>
  <h2 id="licences">{esc(n)} licences &amp; regulation</h2>
  {licences_table(b, d)}
  <h2 id="availability">{esc(n)} country availability</h2>
  <p>{esc(n)} is open to traders in about <strong>{avail_count}</strong> of the {len(COUNTRIES)} countries and territories we cover. It does <strong>not</strong> accept residents of: {esc(', '.join(ns))}.</p>
  <p>Check your country in our <a href="{link('countries/', d)}">country guides</a>.</p>
  <h2>Related {esc(n)} guides</h2>
  <div class="grid g2"><a class="card mini-link" href="sign-up/"><b>{esc(n)} sign up</b><span>Step-by-step registration{(' with code ' + esc(b['ref_code'])) if b.get('ref_code') else ''}</span></a><a class="card mini-link" href="real-or-fake/"><b>Is {esc(n)} real or fake?</b><span>Licences, safety checks and scam warnings</span></a></div>
  {faq_html(faqs)}
 </div>
 {brand_sidebar(b, d)}
</section>"""
    kw = f"{n} review, {n} review {YEAR}, is {n} safe, is {n} legit, {n} real or fake, {n} minimum deposit, {n} regulation, {n} licence, {n} leverage, {n} fees, {n} restricted countries"
    desc = f"{n} review {YEAR}: is it safe? Licences ({', '.join(short_reg(l) for l in b['licences'][:4])}), minimum deposit {b['min_deposit']}, leverage, fees, pros & cons and countries accepted."
    review_ld = {"@context": "https://schema.org", "@type": "Review",
                 "itemReviewed": {"@type": "Organization", "name": n, "url": f"https://{b['domain']}"},
                 "author": {"@type": "Organization", "name": SITE},
                 "reviewRating": {"@type": "Rating", "ratingValue": b["score"], "bestRating": 10, "worstRating": 0},
                 "datePublished": TODAY, "reviewBody": b["summary"]}
    page(path, f"{n} Review {YEAR}: Is It Safe? Licences, Minimum Deposit & Fees | {SITE}", desc, body, d, keywords=kw,
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
        steps = [("Open the official website", f"Click <strong>Visit Site</strong> to open the official {esc(n)} registration page ({esc(b['domain'])}). Check the address bar before typing any details."
                  + (" Traders in Asia can use the Asia server link; everyone else should use Worldwide." if len(b["links"]) > 1 else "")),
                 ("Register", "Enter your country of residence, email and a strong password. Your country decides which " + esc(n) + " entity and regulator you sign up with."),
                 ("Verify email and phone", "Confirm the code sent to your email and/or phone number."),
                 ("Complete your profile and KYC", "Upload a passport, national ID card or driving licence, then proof of address (a bank statement or utility bill under 6 months old). Approval is often within minutes to a few hours."),
                 ("Choose an account type", f"Minimum deposit: {esc(b['min_deposit'])}. {esc(b['min_deposit_note'])}"),
                 ("Deposit", "Fund with a local bank transfer, card, e-wallet or USDT, depending on your country. Start small and test a withdrawal early."),
                 ("Download the platform", f"Install {esc(b['platforms'])}, log in with the server and account number from your personal area, and practise on a demo account first.")]
    else:
        steps = [("Open the official website", f"Click <strong>Visit Site</strong> to open the official {esc(n)} sign-up page ({esc(b['domain'])}). Bookmark it so you never land on a fake copy."),
                 ("Create your account", "Register with email or phone and a strong, unique password." + (f" The invite code <strong>{esc(code)}</strong> is filled in automatically." if code else "")),
                 ("Turn on security", "Enable app-based 2FA (Google Authenticator), set an anti-phishing code and add a withdrawal whitelist."),
                 ("Verify your identity (KYC)", esc(b["kyc"])),
                 ("Deposit crypto", "Deposit USDT or another supported coin from a wallet, or buy crypto with P2P or a card partner. Always pick the same network (e.g. TRC20, BEP20) on both sides."),
                 ("Start trading", f"Begin on spot or with low leverage on futures. Max leverage is {esc(b['max_leverage'][0].lower() + b['max_leverage'][1:])}, but beginners should stay at 2x–5x and always use a stop loss.")]
    steps_html = "".join(f'<li><h3>{esc(t)}</h3><p>{c}</p></li>' for t, c in steps)
    faqs = [(f"How do I sign up for {n}?", f"Open the official {n} website, register with your email or phone, verify your identity and deposit. The full process usually takes 10–20 minutes."),
            (f"Is {n} sign up free?", f"Yes. Opening an {n} account is free. You only pay trading costs such as {'spreads and commissions' if fx else 'trading fees'}."),
            (f"What documents do I need for {n}?", "A valid passport, national ID card or driving licence" + (", plus proof of address for forex accounts." if fx else ". Some regions also ask for proof of address or a selfie check.")),
            (f"Can I open {n} from my country?", f"{n} does not accept residents of: {', '.join(not_served(b))}. Check your country page before registering."),
            (f"What is the {n} minimum deposit?", f"{b['min_deposit']}. {b['min_deposit_note']}")]
    if code:
        faqs.insert(1, (f"What is the {n} referral code?", f"Our {n} referral / invite code is <strong>{esc(code)}</strong>. It is applied automatically when you register through our Visit Site link."))
    body = brand_head(b, d, [("Home", ""), hub, (n, rp), ("Sign up", path)], f"{esc(n)} Sign Up {YEAR}: How to Open an Account", f"Step-by-step {esc(n)} registration{(' with invite code ' + esc(code)) if code else ''} — verification, deposit and first trade.") + f"""
<section class="wrap section two-col">
 <div class="prose">
  {code_box}
  <h2>How to sign up for {esc(n)} (step by step)</h2>
  <ol class="steps">{steps_html}</ol>
  <div class="callout"><strong>Only register on the official domain:</strong> {esc(b['domain'])}. {esc(n)} staff will never message you first on Telegram or WhatsApp, or ask for your password or 2FA code.</div>
  <h2>{esc(n)} account at a glance</h2>
  <div class="table-wrap"><table class="facts-table"><tr><th>Minimum deposit</th><td>{esc(b['min_deposit'])}</td></tr><tr><th>Max leverage</th><td>{esc(b['max_leverage'])}</td></tr><tr><th>{'Spreads' if fx else 'Fees'}</th><td>{esc(b['spreads'] if fx else b['fees'])}</td></tr><tr><th>Regulation</th><td>{esc(b['regulation'])}</td></tr></table></div>
  <p class="cta-line">{visit_buttons(b)}</p>
  {faq_html(faqs)}
 </div>
 {brand_sidebar(b, d)}
</section>"""
    kw = f"{n} sign up, {n} register, {n} registration, {n} create account, {n} open account, {n} account opening, {n} login, {n} app download" + (f", {n} referral code, {n} invite code, {n} code {code}" if code else "")
    page(path, f"{n} Sign Up {YEAR}: Register & Open an Account{(' (Code ' + code + ')') if code else ''} | {SITE}",
         f"How to sign up for {n} in {YEAR}: step-by-step registration{(', invite code ' + code) if code else ''}, KYC documents, minimum deposit {b['min_deposit']} and first trade.",
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
    lvl, lcls = safety_level(b)
    tops = [l for l in b["licences"] if l["tier"] == "Top-tier"]
    verdict = (f"<strong>Yes — {esc(n)} is real.</strong> It is an operating {'forex and CFD broker' if fx else 'cryptocurrency exchange'} founded in {esc(b['founded'])}, with "
               f"{len(b['licences'])} licence{'s' if len(b['licences']) != 1 else ''} or registration{'s' if len(b['licences']) != 1 else ''}"
               + (f", including top-tier oversight from {esc(', '.join(short_reg(l) for l in tops))}." if tops else ", but no top-tier licence, so investor protection is limited.")
               + f" Our safety level: <strong>{lvl}</strong>.")
    checks = [("Licensed or registered", bool(b["licences"]) and b["licences"][0]["tier"] != "Company registration"),
              ("Top-tier regulator (FCA, ASIC, CySEC, VARA, MiCA…)", bool(tops)),
              ("Operating for 3+ years", b["founded"][:4].isdigit() and YEAR - int(b["founded"][:4]) >= 3),
              ("Public restricted-country list", True),
              ("Copy trading / social features", b["copy_trading"].startswith("Yes"))]
    if fx:
        checks.insert(3, ("Negative balance protection (retail)", True))
    else:
        checks.insert(3, ("Withdrawals require KYC (anti-fraud)", True))
    checks_html = "".join(f'<li class="{"ok" if v else "no"}"><span>{"✓" if v else "✕"}</span>{esc(k)}</li>' for k, v in checks)
    faqs = [(f"Is {n} legit or a scam?", re.sub("<[^>]+>", "", verdict)),
            (f"Is {n} safe?", f"Safety level: {lvl}. {b['regulation']} Keep only what you trade with on any platform, use 2FA and withdraw profits regularly."),
            (f"Is {n} regulated by the FCA?", "Yes — " + n + " has a UK entity authorised by the FCA (" + next((l['number'] for l in b['licences'] if 'FCA' in l['regulator']), '') + "), but clients outside the UK are usually served by other entities." if any("Financial Conduct Authority" in l["regulator"] for l in b["licences"]) else f"No. {n} is not authorised by the UK FCA. Its licences/registrations are: {', '.join(short_reg(l) for l in b['licences'])}."),
            (f"How do I spot a fake {n} website?", f"The official domain is {b['domain']}. Fake sites use look-alike spellings, extra words or different endings. Never log in from links sent in Telegram, WhatsApp or ads."),
            (f"Can I withdraw money from {n}?", f"Yes. Withdrawals are processed to verified payment methods {'(and usually back to the method you deposited with)' if fx else 'or crypto addresses'} after identity verification. Test a small withdrawal first.")]
    body = brand_head(b, d, [("Home", ""), hub, (n, rp), ("Real or fake?", path)], f"Is {esc(n)} Real or Fake? Legit or Scam Check {YEAR}", f"An evidence-based look at {esc(n)}'s licences, track record and warning signs.") + f"""
<section class="wrap section two-col">
 <div class="prose">
  <div class="verdict card big-verdict {lcls}"><span class="pill {lcls}">Safety level: {lvl}</span><p>{verdict}</p></div>
  <h2>{esc(n)} safety checklist</h2>
  <ul class="checklist">{checks_html}</ul>
  <h2>{esc(n)} licences and licence numbers</h2>
  {licences_table(b, d)}
  <h2>How to verify {esc(n)} yourself</h2>
  <ol><li>Copy a licence number from the table above.</li><li>Search it on the regulator's <strong>official</strong> register (for example the FCA register, ASIC Connect or the FSCA FSP search).</li><li>Check the company name and website listed on the register match {esc(b['domain'])}.</li><li>Read your client agreement to see which entity you are signing up with.</li></ol>
  <h2>Warning signs of fake "{esc(n)}" scams</h2>
  <ul class="crosses"><li>"Account managers" who contact you first on Telegram, WhatsApp or Instagram</li><li>Guaranteed profits or fixed daily returns</li><li>Requests to send money to a personal wallet or bank account</li><li>Look-alike websites (e.g. extra words or hyphens) instead of {esc(b['domain'])}</li><li>Fees demanded before you can withdraw</li></ul>
  <h2>Risks to know</h2>
  <ul class="crosses">{''.join(f'<li>{esc(c)}</li>' for c in b['cons'])}</ul>
  <p class="cta-line">{visit_buttons(b)} <a class="btn btn-ghost" href="../">Read full review</a></p>
  {faq_html(faqs)}
 </div>
 {brand_sidebar(b, d)}
</section>"""
    kw = f"{n} real or fake, is {n} real, is {n} fake, is {n} legit, {n} scam, is {n} a scam, is {n} safe, {n} trusted, {n} licence, {n} regulated, {n} withdrawal problem"
    page(path, f"Is {n} Real or Fake? Legit or Scam? Licences & Safety Check ({YEAR}) | {SITE}",
         f"Is {n} real or fake? We check {n}'s licences ({', '.join(short_reg(l) for l in b['licences'][:3])}), track record since {b['founded']}, withdrawal process and scam warning signs.",
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
    loser = b if winner is a else a
    rows = [("Our score", lambda x: f"<b class='sc'>{x['score']:.1f}</b>/10"), ("Founded", lambda x: esc(x["founded"])),
            ("Minimum deposit", lambda x: esc(x["min_deposit"])), ("Max leverage", lambda x: esc(x["max_leverage"])),
            ("Spreads" if fx else "Fees", lambda x: esc(x["spreads"] if fx else x["fees"])),
            ("Platforms" if fx else "Coins", lambda x: esc(x["platforms"] if fx else x["coins"])),
            ("Copy trading", lambda x: esc(x["copy_trading"])),
            ("Top-tier licence", lambda x: '<span class="yes">✓ Yes</span>' if has_top(x) else '<span class="no">✕ No</span>'),
            ("Licences", lambda x: ", ".join(esc(short_reg(l)) for l in x["licences"])),
            ("Countries not served", lambda x: str(len(not_served(x)))),
            ("Best for", lambda x: esc(x["best_for"])), ("", lambda x: visit_buttons(x, small=True))]
    table = "".join(f"<tr><th>{k}</th><td>{f(a)}</td><td>{f(b)}</td></tr>" for k, f in rows)
    both_no = [BY_CODE[c]["name"] for c in BY_CODE if status_for(a, c) == "no" and status_for(b, c) != "no"][:12]
    faqs = [(f"Which is better, {a['name']} or {b['name']}?", f"{winner['name']} scores higher in our rating ({winner['score']:.1f} vs {loser['score']:.1f}). Choose {a['name']} for: {a['best_for'].lower()}. Choose {b['name']} for: {b['best_for'].lower()}."),
            (f"Which has the lower minimum deposit, {a['name']} or {b['name']}?", f"{a['name']}: {a['min_deposit']}. {b['name']}: {b['min_deposit']}."),
            (f"Which is better regulated, {a['name']} or {b['name']}?", f"{a['name']} has {len(a['licences'])} licences/registrations ({safety_level(a)[0]} safety); {b['name']} has {len(b['licences'])} ({safety_level(b)[0]} safety).")]
    body = f"""<section class="pagehead {'fx' if fx else 'cx'}-head"><div class="wrap">
 {crumbs_html([("Home", ""), ("Compare", "compare/"), (f"{a['name']} vs {b['name']}", path)], d)}
 <div class="vs-head">{logo(a, 'xl')}<span class="vs">VS</span>{logo(b, 'xl')}</div>
 <h1>{esc(a['name'])} vs {esc(b['name'])} ({YEAR}): Which Is Better?</h1>
 <p class="lead">Licences, {'spreads' if fx else 'fees'}, leverage, minimum deposit and country availability compared. Our pick: <strong>{esc(winner['name'])}</strong> ({winner['score']:.1f}/10).</p>
</div></section>
<section class="wrap section narrow-wide">
 <div class="table-wrap"><table class="vs-table"><thead><tr><th></th><th><a class="tname" href="{link(review_path(a), d)}">{logo(a, 'sm')} {esc(a['name'])}</a></th><th><a class="tname" href="{link(review_path(b), d)}">{logo(b, 'sm')} {esc(b['name'])}</a></th></tr></thead><tbody>{table}</tbody></table></div>
 {disclosure_box(d)}
 <div class="grid g2"><div class="card"><h2>Why choose {esc(a['name'])}</h2><ul class="ticks">{''.join(f'<li>{esc(p)}</li>' for p in a['pros'])}</ul></div><div class="card"><h2>Why choose {esc(b['name'])}</h2><ul class="ticks">{''.join(f'<li>{esc(p)}</li>' for p in b['pros'])}</ul></div></div>
 <div class="prose">
 <h2>Verdict</h2>
 <p>{esc(a['summary'])}</p><p>{esc(b['summary'])}</p>
 <p>Overall, <strong>{esc(winner['name'])}</strong> edges ahead in our rating. Many traders open both accounts and use each for what it does best.</p>
 {f"<p>Where {esc(a['name'])} is unavailable but {esc(b['name'])} accepts traders, for example: {esc(', '.join(both_no))}.</p>" if both_no else ""}
 {faq_html(faqs)}
 </div>
</section>"""
    page(path, f"{a['name']} vs {b['name']} ({YEAR}): Fees, Licences & Leverage Compared | {SITE}",
         f"{a['name']} vs {b['name']}: side-by-side comparison of licences, minimum deposit ({a['min_deposit']} vs {b['min_deposit']}), leverage, {'spreads' if fx else 'fees'} and countries. Which is better in {YEAR}?",
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
<p class="lead">Every licence and registration we verified — FCA, ASIC, CySEC, FSCA, VARA, MiCA, AUSTRAC and more — with the entity name, country and licence number.</p></div></section>
<section class="wrap section prose">
 <h2>What the tiers mean</h2>
 <ul><li>{tier_badge('Top-tier')} Strict regulators with strong client protection, e.g. FCA (UK), ASIC (Australia), CySEC (EU), VARA (Dubai), MiCA authorisation (EU).</li>
 <li>{tier_badge('Mid-tier')} Credible national regulators, e.g. FSCA (South Africa), CMA (Kenya), CIMA (Cayman), SCB (Bahamas).</li>
 <li>{tier_badge('Offshore')} Light-touch regulators allowing high leverage, e.g. FSA (Seychelles), FSC (Mauritius, BVI), VFSC (Vanuatu), MISA (Comoros).</li>
 <li>{tier_badge('AML registration')} Anti-money-laundering registrations such as FinCEN MSB, FINTRAC or AUSTRAC — these are <em>not</em> trading licences.</li></ul>
 <div class="callout">Brokers often hold several licences, but you are protected only by the entity that opens your account. Check your client agreement.</div>
</section>
<section class="wrap section"><span class="kicker fx">FOREX</span><h2>Forex broker licences</h2>{block(BROKERS, "Broker")}</section>
<section class="wrap section"><span class="kicker cx">CRYPTO</span><h2>Crypto exchange licences &amp; registrations</h2>{block(EXCHANGES, "Exchange")}</section>"""
    page("licences/", f"Forex Broker & Crypto Exchange Licences: FCA, ASIC, CySEC, VARA, MiCA ({YEAR}) | {SITE}",
         "Verified licence list: FCA, ASIC, CySEC, FSCA, VARA, MiCA, AUSTRAC registrations and licence numbers for Exness, IC Markets, Vantage, PU Prime, Elev8, Bitunix, Binance, BingX, KuCoin, MEXC and BitBase.",
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
    base = "forex-brokers/" if fx else "crypto-exchanges/"
    path = f"{base}{c['slug']}/"
    d = 2
    name, title_name = c["in_name"], c["name"]
    reg = c["regulator"] or "the national central bank or securities regulator"
    note = country_note(c)
    order = {"yes": 0, "check": 1, "no": 2}
    ranked = sorted(items, key=lambda b: order[status_for(b, c["code"])])
    avail = [b for b in ranked if status_for(b, c["code"]) == "yes"]
    unavail = [b for b in ranked if status_for(b, c["code"]) == "no"]
    cur = f"{c['currency_name']} ({c['currency']})" if c["currency"] else "your local currency"
    local_lic = lic_in_country(c, items)
    if c["code"] in SANCTIONED:
        summary = f"Because {name} is subject to comprehensive international sanctions, none of the {noun.lower()} we review can accept residents of {name}."
    elif avail:
        summary = (f"Based on published restricted-country lists, <strong>{len(avail)} of the {len(items)}</strong> {noun.lower()} we review accept traders from {esc(name)}. "
                   f"Our top pick for {esc(name)} is <strong>{esc(avail[0]['name'])}</strong> — {esc(avail[0]['tagline'].lower())}.")
    else:
        summary = f"None of the {noun.lower()} we review currently list {esc(name)} as fully supported. Check the notes below and confirm directly with each provider."
    lic_html = ""
    if local_lic:
        lic_html = (f'<div class="callout good"><strong>Locally licensed / registered in {esc(name)}:</strong> ' +
                    "; ".join(f'{esc(b["name"])} — {esc(l["regulator"])}{(" (" + esc(l["number"]) + ")") if l["number"] != "—" else ""}' for b, l in local_lic) + "</div>")
    same_region = [x for x in COUNTRIES if x["region"] == c["region"] and x["code"] != c["code"]][:24]
    region_links = "".join(f'<a href="../{x["slug"]}/">{x["flag"]} {esc(x["name"])}</a>' for x in same_region)
    other = ("crypto-exchanges/", "Crypto Exchanges") if fx else ("forex-brokers/", "Forex Brokers")
    if fx:
        how = f"""<h2>How to choose a forex broker in {esc(name)}</h2>
<ol><li><strong>Check the licence.</strong> In {esc(name)} the main financial regulator is {esc(reg)}. International brokers are regulated abroad, so check which entity you sign up with — see our <a href="{link('licences/', d)}">licence table</a>.</li>
<li><strong>Compare the real minimum deposit.</strong> Entry points range from $10 at Exness to $200 at IC Markets.</li>
<li><strong>Deposit in {esc(cur)}.</strong> Local bank transfers, cards and e-wallets avoid high conversion fees. Many traders also fund with USDT.</li>
<li><strong>Pick your platform.</strong> MT4 and MT5 are the most common; cTrader and TradingView suit chart-focused traders.</li>
<li><strong>Use sensible leverage.</strong> High leverage magnifies losses as much as gains. Risk no more than 1–2% of your balance per trade.</li></ol>"""
        faqs = [(f"Is forex trading legal in {title_name}?", (note or f"Forex trading rules in {name} are set by {reg}.") + " This is general information, not legal advice."),
                (f"What is the best forex broker in {title_name}?", (f"{avail[0]['name']} is our top-rated forex broker that accepts traders from {name}" + (", followed by " + ", ".join(b['name'] for b in avail[1:]) + "." if len(avail) > 1 else ".")) if avail else f"None of the brokers we review currently accept residents of {name}."),
                (f"Which forex broker has the lowest minimum deposit in {title_name}?", next((f"{b['name']}, with a minimum deposit of {b['min_deposit']}." for b in sorted(avail, key=lambda b: float(re.sub(r'[^0-9.]', '', b['min_deposit']) or 0))), f"None of the brokers we review currently accept residents of {name}.")),
                (f"Which FCA or ASIC regulated brokers accept traders from {title_name}?", ", ".join(b["name"] for b in avail if has_top(b)) + " hold top-tier licences, but international clients are usually onboarded by their offshore entities." if any(has_top(b) for b in avail) else f"None of the brokers we review that accept {name} hold top-tier licences."),
                (f"Is Exness available in {title_name}?", {"yes": f"Yes — Exness does not list {name} as a restricted country.", "no": f"No. Exness does not accept residents of {name}.", "check": f"It is unclear — check the Exness website for {name}."}[status_for(BROKERS[0], c["code"])])]
    else:
        how = f"""<h2>How to choose a crypto exchange in {esc(name)}</h2>
<ol><li><strong>Check local rules.</strong> Crypto rules in {esc(name)} are set by {esc(reg)}. Some countries require exchanges to be locally licensed.</li>
<li><strong>Compare fees.</strong> Futures fees range from 0% maker at MEXC to 0.02%/0.06% at Bitunix and KuCoin.</li>
<li><strong>Funding in {esc(cur)}.</strong> Many traders buy USDT through P2P (Binance, Bitunix, BingX) or a card partner, then trade.</li>
<li><strong>Complete KYC early.</strong> Binance and KuCoin need KYC before trading; others lock withdrawals until you verify.</li>
<li><strong>Secure your account.</strong> Enable 2FA and an anti-phishing code, and never keep long-term savings on an exchange.</li></ol>"""
        mx = next(e for e in EXCHANGES if e["slug"] == "mexc")
        bn = next(e for e in EXCHANGES if e["slug"] == "binance")
        faqs = [(f"Is crypto trading legal in {title_name}?", (note or f"Crypto rules in {name} are overseen by {reg}.") + " This is general information, not legal advice."),
                (f"What is the best crypto exchange in {title_name}?", (f"{avail[0]['name']} is our top-rated crypto exchange that accepts users from {name}." + (" Alternatives: " + ", ".join(b['name'] for b in avail[1:]) + "." if len(avail) > 1 else "")) if avail else f"None of the exchanges we review currently accept residents of {name}."),
                (f"Is Bitunix available in {title_name}?", {"yes": f"Yes — Bitunix does not list {name} as a restricted jurisdiction.", "no": f"No. Bitunix does not accept users from {name}.", "check": f"It is unclear — check the Bitunix website."}[status_for(EXCHANGES[0], c["code"])]),
                (f"Is Binance available in {title_name}?", {"yes": f"Binance does not list {name} as restricted, though some products (like futures) may be limited.", "no": f"No. Binance.com does not accept residents of {name}.", "check": f"Binance's status in {name} is unclear or limited — check Binance's terms for your country."}[status_for(bn, c["code"])]),
                (f"Is MEXC available in {title_name}?", {"yes": f"MEXC does not list {name} as restricted.", "no": f"No. MEXC lists {name} as restricted.", "check": f"MEXC's status in {name} is unclear."}[status_for(mx, c["code"])]),
                (f"How do I buy USDT in {title_name}?", f"Common options are P2P marketplaces (paying in {cur}), card purchases through a payment partner, or a locally licensed exchange. Then transfer USDT to your trading exchange on the correct network.")]
    note_html = f'<div class="callout"><strong>Local rules in {esc(name)}:</strong> {esc(note)}</div>' if note else ""
    unavail_html = f'<p class="muted small">Not available in {esc(name)}: ' + ", ".join(esc(b["name"]) for b in unavail) + ".</p>" if unavail else ""
    facts = f"""<div class="cfacts">
 <div><span>Region</span><b>{esc(c['region'])}</b></div>
 <div><span>Currency</span><b>{esc(cur)}</b></div>
 <div><span>Regulator</span><b>{esc(reg)}</b></div>
 <div><span>{noun} available</span><b>{len(avail)} of {len(items)}</b></div></div>"""
    body = f"""
<section class="pagehead {'fx' if fx else 'cx'}-head"><div class="wrap">
 {crumbs_html([("Home", ""), (noun, base), (title_name, path)], d)}
 <h1>{c['flag']} Best {noun} in {esc(name)} ({YEAR})</h1>
 <p class="lead">{summary}</p>
 {facts}
</div></section>
<section class="wrap section">
 {note_html}{lic_html}
 <h2>Compare {noun.lower()} for {esc(name)}</h2>
 {compare_table(ranked, d, c)}
 <p class="tiny">* "Available" means {esc(name)} is not on the provider's published restricted list as of {esc(CFG['last_reviewed'])}. Final eligibility is decided by the provider when you register.</p>
 {disclosure_box(d)}
 <div class="grid g2">{''.join(brand_card(b, i, d, c) for i, b in enumerate(ranked, 1))}</div>
 {unavail_html}
</section>
<section class="wrap section prose">
 {how}
 {faq_html(faqs)}
 <p>Also see: <a href="{link(other[0] + c['slug'] + '/', d)}">Best {other[1]} in {esc(name)}</a> · <a href="{link('countries/' + c['slug'] + '/', d)}">{esc(title_name)} trading guide</a> · <a href="{link('free-forex-signals/', d)}">Free forex signals</a> · <a href="{link('free-crypto-signals/', d)}">Free crypto signals</a></p>
</section>
<section class="wrap section"><h2>Other countries in {esc(c['region'])}</h2><div class="clist">{region_links}<a href="{link(base, d)}#countries"><strong>All countries →</strong></a></div></section>"""
    if fx:
        title = f"Best Forex Brokers in {name} ({YEAR}) – Regulated, Low Deposit & MT4/MT5 | {SITE}"
        desc = f"Best forex brokers in {name} for {YEAR}: {', '.join(b['name'] for b in avail[:4]) or 'compare brokers'} — licences, minimum deposit, leverage and MT4/MT5, checked for traders in {name}."
        kw = f"best forex broker in {title_name}, forex brokers {title_name}, forex trading {title_name}, regulated forex broker {title_name}, FCA broker {title_name}, low minimum deposit forex broker {title_name}, MT5 broker {title_name}, gold trading {title_name}, Exness {title_name}, forex signals {title_name}"
    else:
        title = f"Best Crypto Exchanges in {name} ({YEAR}) – Fees, Leverage & Licences | {SITE}"
        desc = f"Best crypto exchanges in {name} for {YEAR}: {', '.join(b['name'] for b in avail[:4]) or 'compare exchanges'} — fees, futures leverage, KYC, licences and availability for users in {name}."
        kw = f"best crypto exchange in {title_name}, crypto exchanges {title_name}, buy bitcoin {title_name}, buy USDT {title_name}, crypto trading {title_name}, crypto futures {title_name}, Bitunix {title_name}, Binance {title_name}, BingX {title_name}, crypto signals {title_name}"
    page(path, title, desc, body, d, keywords=kw,
         ld=[itemlist_ld(f"Best {noun} in {title_name}", ranked), breadcrumb_ld([("Home", ""), (noun, base), (title_name, path)]), faq_ld(faqs)], priority="0.7", theme="fx" if fx else "cx")


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
 <p>Signals and education: <a href="{link('free-forex-signals/', d)}">free forex signals</a> · <a href="{link('free-crypto-signals/', d)}">free crypto signals</a> · <a href="{link('guides/', d)}">trading guides</a>.</p>
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
    if fx:
        h1 = f"Free Forex Signals {YEAR} – XAUUSD Gold, EURUSD & More"
        pairs = "XAUUSD (gold), EURUSD, GBPUSD, USDJPY, GBPJPY and US30"
        partners = BROKERS
        ex = ("BUY XAUUSD (example)", "Entry: 2,350.00 – 2,348.00", "Stop loss: 2,340.00", "TP1: 2,358.00 · TP2: 2,366.00")
    else:
        h1 = f"Free Crypto Signals {YEAR} – Bitcoin, Ethereum & Altcoin Futures"
        pairs = "BTCUSDT, ETHUSDT, SOLUSDT and selected altcoin perpetual futures"
        partners = EXCHANGES
        ex = ("LONG BTCUSDT (example)", "Entry: 64,800 – 64,500", "Stop loss: 63,900", "TP1: 65,700 · TP2: 66,600 · Leverage: max 5x")
    faqs = [("Are the signals really free?", "Yes. Our free signals are posted in our public Telegram channel at no charge."),
            ("How accurate are the signals?", "No signal service is right all the time and losses are a normal part of trading. We do not promise any win rate."),
            ("How much should I risk per signal?", "Many professional traders risk 1–2% of their account per trade. Always use the stop loss."),
            ("Which " + ("broker" if fx else "exchange") + " should I use?", f"Any provider that accepts residents of your country. Our top picks are {', '.join(p['name'] for p in partners[:4])}.")]
    body = f"""
<section class="pagehead {'fx' if fx else 'cx'}-head"><div class="wrap">
 {crumbs_html([("Home", ""), ("Free Signals", "free-signals/"), (h1.split(' –')[0], path)], d)}
 <h1>{esc(h1)}</h1>
 <p class="lead">Join our free Telegram channel for {esc(pairs)} trade ideas — each with an entry zone, stop loss and take-profit targets — plus risk-management education.</p>
 <a class="btn btn-tg big" href="{esc(CFG['telegram_signals_url'])}" target="_blank" rel="noopener">Join the free signals channel on Telegram</a>
</div></section>
<section class="wrap section two-col">
 <div class="prose">
  <h2>What a signal looks like</h2>
  <div class="signal-demo {'fx' if fx else 'cx'}"><b>{esc(ex[0])}</b><span>{esc(ex[1])}</span><span>{esc(ex[2])}</span><span>{esc(ex[3])}</span><small>Illustration only — not a live trade recommendation.</small></div>
  <h2>How to use trading signals safely</h2>
  <ol><li><strong>Calculate your position size first</strong> so a stop-loss hit costs no more than 1–2% of your balance.</li>
  <li><strong>Always set the stop loss</strong> as soon as you open the trade.</li>
  <li><strong>Take partial profits</strong> at TP1 and move your stop to break-even if the signal says so.</li>
  <li><strong>Skip late entries</strong> if price has already moved far beyond the entry zone.</li>
  <li><strong>{'Watch news events.' if fx else 'Keep leverage low.'}</strong> {'Spreads widen around NFP, CPI and central bank decisions.' if fx else 'With 100x leverage, a 1% move against you wipes out your margin.'}</li></ol>
  <h2>Our transparency policy</h2>
  <p>We share wins and losses openly and never advertise guaranteed profits or made-up accuracy figures. Signals are educational ideas, not personal financial advice.</p>
  {faq_html(faqs)}
 </div>
 <aside class="side"><div class="card"><h3>Trade signals with</h3>{''.join(f'<div class="mini">{logo(p, "sm")}<b>{esc(p["name"])}</b>{visit_buttons(p, small=True, first_only=True)}</div>' for p in partners)}<p class="tiny">Partner links. Capital at risk.</p></div></aside>
</section>"""
    kw = ("free forex signals, forex signals telegram, gold signals, XAUUSD signals, free gold signals, best forex signals, forex signals today" if fx
          else "free crypto signals, crypto signals telegram, bitcoin signals, crypto futures signals, free bitcoin signals, best crypto signals, BTC signals today")
    page(path, f"{h1} | {SITE}", f"Free {'forex' if fx else 'crypto'} signals on Telegram: {pairs} with entry, stop loss and take profit, plus risk management.",
         body, d, keywords=kw, ld=[breadcrumb_ld([("Home", ""), ("Free Signals", "free-signals/"), (h1.split(' –')[0], path)]), faq_ld(faqs)], priority="0.9", theme="fx" if fx else "cx")


def build_signals_hub():
    d = 1
    body = f"""<section class="pagehead"><div class="wrap">{crumbs_html([("Home", ""), ("Free Signals", "free-signals/")], d)}
<h1>Free Trading Signals – Forex &amp; Crypto</h1><p class="lead">Transparent trade ideas with entry, stop loss and targets — shared free on Telegram.</p></div></section>
<section class="wrap section grid g2">
 <div class="card signal-card fx"><span class="kicker fx">FOREX</span><h2>Free Forex Signals</h2><p>Gold (XAUUSD), EURUSD, GBPUSD, USDJPY and indices.</p><a class="btn btn-fx" href="../free-forex-signals/">Forex signals →</a></div>
 <div class="card signal-card cx"><span class="kicker cx">CRYPTO</span><h2>Free Crypto Signals</h2><p>BTC, ETH and altcoin perpetual futures setups.</p><a class="btn btn-cx" href="../free-crypto-signals/">Crypto signals →</a></div>
</section>"""
    page("free-signals/", f"Free Forex & Crypto Signals ({YEAR}) – Telegram | {SITE}", "Free forex and crypto trading signals on Telegram: gold, forex pairs, Bitcoin and altcoin futures with entry, stop loss and take profit.",
         body, d, keywords="free trading signals, free forex signals, free crypto signals, telegram signals", ld=[breadcrumb_ld([("Home", ""), ("Free Signals", "free-signals/")])], priority="0.8")


# --------------------------------------------------------------------------
# Guides
# --------------------------------------------------------------------------
def build_guides():
    d = 1
    body = f"""<section class="pagehead"><div class="wrap">{crumbs_html([("Home", ""), ("Guides", "guides/")], d)}
<h1>Forex &amp; Crypto Trading Guides</h1><p class="lead">Practical, plain-English guides on choosing a broker, managing risk, trading gold and crypto futures.</p></div></section>
<section class="wrap section">{article_cards(ARTICLES, d)}</section>"""
    page("guides/", f"Forex & Crypto Trading Guides | {SITE}", "Learn forex and crypto trading: choosing a broker, risk management, leverage, gold trading, crypto futures and trading signals.",
         body, d, keywords="forex trading guide, crypto trading guide, learn forex, learn crypto futures, risk management", ld=[breadcrumb_ld([("Home", ""), ("Guides", "guides/")])], priority="0.8")
    for a in ARTICLES:
        path = f"guides/{a['slug']}/"
        d2 = 2
        html_body, toc = md_to_html(a["body"], d2)
        toc_html = "".join(f'<a href="#{h}">{esc(t)}</a>' for h, t in toc)
        related = [x for x in ARTICLES if x["slug"] != a["slug"]][:3]
        hero = f'<figure class="art-hero"><img src="{rel(d2)}{a["image"]}" alt="{esc(a["title"])}" width="2400" height="1260" fetchpriority="high"></figure>' if a["image"] else ""
        cat = a.get("category", "Guide")
        promo_items = EXCHANGES[:3] if cat in ("Crypto", "Signals") else BROKERS[:3]
        promo = "".join(f'<div class="mini">{logo(p, "sm")}<a href="{link(review_path(p), d2)}">{esc(p["name"])}</a>{visit_buttons(p, small=True, first_only=True)}</div>' for p in promo_items)
        body = f"""<section class="pagehead"><div class="wrap narrow">{crumbs_html([("Home", ""), ("Guides", "guides/"), (a["title"], path)], d2)}
<span class="tag">{esc(cat)}</span><h1>{esc(a['title'])}</h1><p class="lead">{esc(a['description'])}</p>
<p class="byline">By {esc(CFG['author'])} · Updated <time datetime="{esc(a.get('date', TODAY))}">{esc(a.get('date', TODAY))}</time></p></div></section>
<div class="wrap narrow">{hero}</div>
<section class="wrap section two-col"><article class="prose">{html_body}{disclosure_box(d2)}</article>
<aside class="side"><div class="card sticky"><h3>On this page</h3><nav class="toc">{toc_html}</nav><h3 class="mt">Top picks</h3>{promo}</div></aside></section>
<section class="wrap section"><h2>Related guides</h2>{article_cards(related, d2)}</section>"""
        art_ld = {"@context": "https://schema.org", "@type": "Article", "headline": a["title"], "description": a["description"],
                  "datePublished": a.get("date", TODAY), "dateModified": a.get("date", TODAY),
                  "author": {"@type": "Organization", "name": CFG["author"]},
                  "publisher": {"@type": "Organization", "name": SITE, "logo": {"@type": "ImageObject", "url": SITE_URL + "/assets/og-image.png"}},
                  "mainEntityOfPage": f"{SITE_URL}/{path}", "image": f"{SITE_URL}/{a['image']}" if a["image"] else SITE_URL + "/assets/og-image.png"}
        page(path, f"{a['title']} | {SITE}", a["description"], body, d2, keywords=a.get("keywords", ""),
             ld=[art_ld, breadcrumb_ld([("Home", ""), ("Guides", "guides/"), (a["title"], path)])], priority="0.7", og_type="article", image=a["image"])


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
<p>Scores are our opinion. Because we earn commissions from partner links, this can influence which providers appear and in what order — see our <a href="../affiliate-disclosure/">affiliate disclosure</a>.</p>
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
        "affiliate-disclosure/": ("Affiliate Disclosure", f"""<p>{esc(SITE)} is free to use. We earn money through partner (affiliate) links: when you open an account through a "Visit Site" button, we may receive a commission or a share of trading fees. This costs you nothing extra.</p>
<p>Our current partners include {esc(partners)}. Commercial relationships can influence which providers we feature and how prominently. We still aim to give accurate facts — including drawbacks, licences and country restrictions — so you can decide for yourself.</p>
<p>All partner links use <code>rel="sponsored"</code> in line with search engine guidelines. Company names and logos are trademarks of their owners and are shown only to identify them.</p>"""),
        "privacy-policy/": ("Privacy Policy", f"""<p>Last updated: {esc(CFG['last_reviewed'])}.</p>
<p>This website does not require an account and does not collect personal information through forms. If Google Analytics is enabled, it uses cookies to collect anonymous usage data (pages visited, device type, approximate country). You can block these cookies in your browser.</p>
<p>Company icons are loaded from Google's public favicon service, which may receive your IP address when the images load.</p>
<p>When you click a partner link you leave our website and the partner's privacy policy applies. Partners may use cookies to record that you arrived from our site.</p>
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
