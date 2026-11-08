# Forex & Crypto Broker Comparison Website

A fast, SEO-ready website that compares forex brokers and crypto exchanges for **243 countries and territories worldwide**. It runs **free on GitHub Pages**, and you don't need to know how to code to use it.

**Design:** the base is deep navy. Forex sections use **MT4 blue** with blue "Visit Site" buttons; crypto sections use **profit green** with green "Visit Site" buttons. Each company shows its real icon, loaded from its official website.

**What's inside (about 810 pages):**
- Home page with a country search box and boxed broker and exchange cards with "Open Account" buttons
- `/forex-brokers/` and `/crypto-exchanges/` comparison pages with ranking tables
- **Forex brokers:** Exness, IC Markets, Vantage, PU Prime, Elev8
- **Crypto exchanges:** Bitunix (ranked #1), Binance, BingX, MEXC, KuCoin, BitBase
- **3 brand-search pages for every company**, so people searching the company name can find your site:
  - Review: `/exchanges/bitunix/` ("bitunix review", "is bitunix safe")
  - Sign up: `/exchanges/bitunix/sign-up/` ("bitunix sign up", "bitunix referral code")
  - Real or fake: `/exchanges/bitunix/real-or-fake/` ("bitunix real or fake", "is bitunix legit", "bitunix scam")
- **Licences:** every company shows a licence table with regulator, country, entity and licence number (FCA, ASIC, CySEC, FSCA, VARA, MiCA, AUSTRAC and more). There's also a full `/licences/` page.
- **Comparison tables:**
  - `/forex-brokers/compare/` and `/crypto-exchanges/compare/` compare every quality side by side
  - `/compare/` has 25 head-to-head pages, e.g. `/compare/bitunix-vs-binance/`
- **Country pages for all 243 countries.** Each country gets three pages:
  - `/forex-brokers/pakistan/` – best forex brokers in Pakistan
  - `/crypto-exchanges/pakistan/` – best crypto exchanges in Pakistan
  - `/countries/pakistan/` – Pakistan trading overview

  Each page shows which brokers **accept** or **don't accept** that country, the local regulator, the currency, legal notes and an FAQ.
- Free Forex Signals and Free Crypto Signals pages that link to your Telegram channel
- 9 trading guides (gold trading, leverage, crypto futures, risk management and more). Each guide has its own original high-resolution picture in `assets/img/`.
- About, Contact, Risk Disclaimer, Affiliate Disclosure, Privacy and Terms pages
- Built-in SEO on every page:
  - title, description and keywords tags
  - canonical URL and Open Graph share image
  - Schema.org structured data (FAQ, breadcrumbs, reviews, articles, item lists)
  - `sitemap.xml`, `robots.txt` and a 404 page
  - `rel="sponsored"` on all affiliate links, as Google requires

---

## Put it online in 10 minutes (no coding)

1. **Create a GitHub account** at https://github.com (free).
2. Click **+ → New repository**.
   - Name it, for example `forex-crypto-site`.
   - Choose **Public**, then click **Create repository**.
3. On the new repository page, click **"uploading an existing file"**.
   - Unzip the zip file on your computer.
   - Drag **everything inside the folder** into the browser. The `.github` folder must be included. If it doesn't upload, see the tip below.
   - Click **Commit changes**.
4. Go to **Settings → Pages**.
   - Under **Build and deployment → Source**, choose **GitHub Actions**.
5. Go to the **Actions** tab. You'll see "Build and deploy website" running.
   - After about a minute it turns green ✅.
   - Your site is now live at `https://YOUR-USERNAME.github.io/forex-crypto-site/`.

> **Tip: the `.github` folder didn't upload?** Hidden folders sometimes don't drag in. On GitHub, click **Add file → Create new file** and type the name `.github/workflows/deploy.yml`. Then paste in the contents of that file from the zip and commit.

The site address is detected automatically, so canonical links and the sitemap are always correct.

---

## Make it yours: edit `config.json`

On GitHub, open `config.json`, click the ✏️ pencil, change the values, then click **Commit changes**. The site rebuilds by itself in about a minute.

| Setting | What to put |
|---|---|
| `site_name` | Your brand name |
| `contact_email` | Your public contact email |
| `telegram_url` | Your main Telegram channel link |
| `telegram_signals_url` | Your free-signals Telegram channel link |
| `google_analytics_id` | Your GA4 ID, e.g. `G-XXXXXXX` (optional) |
| `google_site_verification` | The code from Google Search Console's "HTML tag" method (optional) |
| `last_reviewed` | The month you last checked broker details |

## Change brokers, links or rankings

- **Forex brokers** are in `data/brokers.json`. **Crypto exchanges** are in `data/exchanges.json`.
- The **order in the file is the ranking order** (Bitunix is first among exchanges).
- To change an affiliate link, edit the `"url"` inside `"links"`. The `"label"` is the button text ("Visit Site").
- `"licences"` is the licence table. Each entry has a country code, regulator, entity, licence number and tier.
- `"domain"` is the company's official website, which is used to show its icon.
- `"ref_code"` is your referral code, shown on the sign-up page.
- To add a new exchange, copy one whole `{ ... }` block. Paste it after a comma, give it a new `slug` and `name`, and fill in the details.
- `"restricted"` holds two-letter country codes that the provider **does not** accept, e.g. `"US"`, `"CA"`. `"unclear"` holds codes where availability isn't certain.

## Add a new article

Create a new file in `data/articles/`, for example `bitcoin-halving-explained.md`, in this format:

```
---
title: Your Article Title
description: One-sentence summary shown in Google (about 150 characters).
keywords: keyword one, keyword two
category: Crypto
date: 2026-11-20
---
Intro paragraph...

## A heading
Text, **bold**, [a link](/crypto-exchanges/), and lists:
- point one
- point two
```

Commit the file and it appears on the Guides page automatically.

**Picture for a new article:** add a photo as `assets/img/your-article-file-name.jpg`, using the same name as the `.md` file. A wide 2400×1260 image works best. You can also run `python tools/make_images.py` (needs `pip install pillow`) to create an original chart picture automatically.

## Use your own domain (optional)

1. Buy a domain, e.g. `yourbrand.com`.
2. Add a file named `CNAME` (no extension) to the repository. Its only content is your domain, e.g. `yourbrand.com`.
3. In **Settings → Pages**, enter the domain and turn on **Enforce HTTPS**.
4. At your domain registrar, point DNS to GitHub Pages. GitHub shows the exact records.

## After going live: get indexed by Google

1. Open **Google Search Console** at https://search.google.com/search-console and add your site.
2. Verify it with the HTML tag: paste the code into `google_site_verification` in `config.json`.
3. Go to **Sitemaps** and submit `sitemap.xml`.
4. Publish new, original guides regularly and share them on your Telegram and social channels.
   - Backlinks and fresh content matter much more than keywords.

## Preview on your computer (optional)

With Python 3 installed, run `python build.py`, then open `_site/index.html`.

---

### Important notes

- **Broker facts were checked in November 2026.** Brokers change minimum deposits, leverage and restricted-country lists often, so re-check every couple of months and update the JSON files.
- **Keep the risk warning and affiliate disclosure.** Search engines and regulators expect them on financial affiliate sites, and they protect you legally.
- **Free signals pages don't contain made-up results.** Post real signals in your Telegram channel, including losses. Never advertise guaranteed profits or win rates.
