"""One-time helper that wrote data/countries.json. You do not need to run it again."""
import json, re, unicodedata
from babel import Locale
from babel.numbers import get_territory_currencies

iso = json.load(open('/usr/share/iso-codes/json/iso_3166-1.json'))['3166-1']
en = Locale('en')

REGIONS = {
 "Southern Asia": "AF BD BT IN IR LK MV NP PK",
 "South-Eastern Asia": "BN KH ID LA MY MM PH SG TH TL VN",
 "Eastern Asia": "CN HK JP KP KR MN MO TW",
 "Central Asia": "KZ KG TJ TM UZ",
 "Middle East": "AE AM AZ BH CY GE IL IQ JO KW LB OM PS QA SA SY TR YE",
 "Northern Africa": "DZ EG LY MA SD TN EH",
 "Western Africa": "BJ BF CV CI GM GH GN GW LR ML MR NE NG SH SN SL TG",
 "Eastern Africa": "BI KM DJ ER ET KE MG MW MU YT MZ RE RW SC SO SS TZ UG ZM ZW IO TF",
 "Middle Africa": "AO CM CF TD CG CD GQ GA ST",
 "Southern Africa": "BW SZ LS NA ZA",
 "Western Europe": "AT BE FR DE LI LU MC NL CH",
 "Northern Europe": "AX DK EE FO FI GG IS IE IM JE LV LT NO SJ SE GB",
 "Southern Europe": "AL AD BA HR GI GR VA IT XK MT ME MK PT SM RS SI ES",
 "Eastern Europe": "BY BG CZ HU MD PL RO RU SK UA",
 "Northern America": "BM CA GL PM US",
 "Central America": "BZ CR SV GT HN MX NI PA",
 "Caribbean": "AI AG AW BS BB BQ VG KY CU CW DM DO GD GP HT JM MQ MS PR BL KN LC MF VC SX TT TC VI",
 "South America": "AR BO BV BR CL CO EC FK GF GY PY PE GS SR UY VE",
 "Oceania": "AS AU CK FJ PF GU KI MH FM NR NC NZ NU NF MP PW PG PN WS SB TK TO TV UM VU WF HM CX CC AQ",
}
region_of = {c: r for r, cs in REGIONS.items() for c in cs.split()}

EU = set("AT BE BG HR CY CZ DK EE FI FR DE GR HU IE IT LV LT LU MT NL PL PT RO SK SI ES SE".split())

# Main financial regulators (forex/securities) and crypto notes for larger markets.
REG = {
 "US": "CFTC & NFA (forex), SEC (securities)", "GB": "Financial Conduct Authority (FCA)",
 "AU": "Australian Securities & Investments Commission (ASIC)", "CA": "Canadian Investment Regulatory Organization (CIRO) & provincial securities regulators",
 "NZ": "Financial Markets Authority (FMA)", "IN": "Securities and Exchange Board of India (SEBI) & Reserve Bank of India (RBI)",
 "PK": "Securities & Exchange Commission of Pakistan (SECP) & State Bank of Pakistan (SBP)", "BD": "Bangladesh Securities and Exchange Commission (BSEC) & Bangladesh Bank",
 "LK": "Securities and Exchange Commission of Sri Lanka & Central Bank of Sri Lanka", "NP": "Securities Board of Nepal (SEBON) & Nepal Rastra Bank",
 "CY": "Cyprus Securities and Exchange Commission (CySEC)", "DE": "BaFin", "FR": "Autorité des marchés financiers (AMF)",
 "IT": "CONSOB", "ES": "CNMV", "NL": "Autoriteit Financiële Markten (AFM)", "IE": "Central Bank of Ireland", "BE": "FSMA",
 "AT": "FMA Austria", "PL": "KNF (Polish Financial Supervision Authority)", "SE": "Finansinspektionen", "DK": "Finanstilsynet",
 "FI": "FIN-FSA", "PT": "CMVM", "GR": "Hellenic Capital Market Commission", "CZ": "Czech National Bank", "HU": "Magyar Nemzeti Bank",
 "RO": "ASF Romania", "CH": "FINMA", "NO": "Finanstilsynet Norway", "LU": "CSSF", "MT": "Malta Financial Services Authority (MFSA)",
 "SG": "Monetary Authority of Singapore (MAS)", "HK": "Securities and Futures Commission (SFC)", "JP": "Financial Services Agency (JFSA)",
 "KR": "Financial Services Commission (FSC) & FSS", "CN": "China Securities Regulatory Commission (CSRC)", "TW": "Financial Supervisory Commission (FSC)",
 "MY": "Securities Commission Malaysia (SC)", "ID": "OJK & Bappebti", "TH": "Securities and Exchange Commission Thailand", "PH": "Securities and Exchange Commission Philippines & BSP",
 "VN": "State Securities Commission of Vietnam", "AE": "SCA, DFSA (DIFC), FSRA (ADGM) & VARA (Dubai virtual assets)", "SA": "Capital Market Authority (CMA)",
 "QA": "Qatar Financial Markets Authority & QFCRA", "KW": "Capital Markets Authority Kuwait", "BH": "Central Bank of Bahrain", "OM": "Financial Services Authority Oman",
 "JO": "Jordan Securities Commission", "TR": "Capital Markets Board (SPK)", "IL": "Israel Securities Authority (ISA)", "EG": "Financial Regulatory Authority (FRA)",
 "MA": "AMMC", "ZA": "Financial Sector Conduct Authority (FSCA)", "NG": "Securities and Exchange Commission Nigeria", "KE": "Capital Markets Authority (CMA)",
 "GH": "Securities and Exchange Commission Ghana", "UG": "Capital Markets Authority Uganda", "TZ": "Capital Markets and Securities Authority", "MU": "Financial Services Commission (FSC)",
 "SC": "Financial Services Authority Seychelles (FSA)", "BR": "Comissão de Valores Mobiliários (CVM)", "MX": "CNBV", "AR": "CNV", "CL": "CMF Chile", "CO": "Superintendencia Financiera",
 "PE": "SMV", "RU": "Bank of Russia", "UA": "NSSMC", "KZ": "AFSA (AIFC) & ARDFM", "UZ": "National Agency of Perspective Projects (crypto)", "AZ": "Central Bank of Azerbaijan",
 "BS": "Securities Commission of The Bahamas (SCB)", "KY": "Cayman Islands Monetary Authority (CIMA)", "VU": "Vanuatu Financial Services Commission (VFSC)",
 "BZ": "Financial Services Commission Belize", "SV": "CNAD & Central Reserve Bank (BCR)",
}

def slugify(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')

rows = []
codes = [c['alpha_2'] for c in iso] + ['XK']
flags = {c['alpha_2']: c.get('flag', '') for c in iso}; flags['XK'] = '🇽🇰'
for code in codes:
    name = en.territories.get(code) or next(c['name'] for c in iso if c['alpha_2'] == code)
    name = name.replace(' SAR China', '').replace(' SAR', '')
    if code == 'PS': name = 'Palestine'
    cur = (get_territory_currencies(code) or [''])[0]
    rows.append({
        "code": code, "name": name, "slug": slugify(name), "flag": flags.get(code, ''),
        "region": region_of.get(code, 'Other'), "eu": code in EU,
        "currency": cur, "currency_name": en.currencies.get(cur, cur) if cur else "",
        "regulator": REG.get(code, ""),
    })
missing = [r['code'] for r in rows if r['region'] == 'Other']
assert not missing, missing
assert len({r['slug'] for r in rows}) == len(rows)
rows.sort(key=lambda r: r['name'])
json.dump(rows, open('data/countries.json', 'w'), ensure_ascii=False, indent=1)
print(len(rows), 'countries written')
