#!/usr/bin/env python3
"""
catalyst_scanner.py
─────────────────────────────────────────────────────────────────────────────
Daily AI catalyst & stock discovery scanner. Three independent engines:

  1. SEC EDGAR   — official 8-K filings with AI / merger / JV keywords
  2. News RSS    — Google News for catalyst headlines, extracts tickers
  3. Gem Screener — S&P 500 + NASDAQ 100 screened for "hidden gem" pattern
                   (near 52W lows · analyst upside >15% · call-heavy options
                    · low analyst count = under the radar)

Output:
  • discoveries.json  — structured results for dashboard
  • stock_analysis_v6.html gets a live "📡 Discoveries" tab injected
  • Optional daily email digest (--email flag)

Usage:
  python3 catalyst_scanner.py              # run all 3 engines
  python3 catalyst_scanner.py --email      # also send email digest
  python3 catalyst_scanner.py --quick      # news + EDGAR only (skip screener)

Schedule (add to crontab):
  0 8 * * 1-5  cd /Users/animeshgoyal/Downloads/ai_trading_bot && \
               source trading/bin/activate && \
               python3 catalyst_scanner.py --email >> logs/scanner.log 2>&1
─────────────────────────────────────────────────────────────────────────────
"""

import json, re, time, os, sys, smtplib, argparse
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, date, timedelta
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ── Config ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).parent
HTML_FILE    = SCRIPT_DIR / "stock_analysis_v6.html"
OUTPUT_FILE  = SCRIPT_DIR / "discoveries.json"
LOG_DIR      = SCRIPT_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

EMAIL_TO     = "animesh.goyal9@gmail.com"

def _load_env():
    """Load .env directly — handles values with spaces (e.g. Gmail app passwords)."""
    env = {}
    env_file = SCRIPT_DIR / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip()
    return env

_env        = _load_env()
EMAIL_FROM  = _env.get("NOTIFY_EMAIL", os.getenv("NOTIFY_EMAIL", ""))
EMAIL_PASS  = _env.get("NOTIFY_APP_PASSWORD", os.getenv("NOTIFY_APP_PASSWORD", ""))

EDGAR_DELAY  = 0.6   # seconds between EDGAR requests
NEWS_DELAY   = 0.5
SCREEN_DELAY = 0.5   # seconds between yfinance calls during screening

# ── Keyword banks ──────────────────────────────────────────────────────────────
AI_KW = [
    "artificial intelligence", " ai ", "machine learning", "large language model",
    "llm", "generative ai", "gpu cluster", "data center", "neural network",
    "computer vision", "edge ai", "autonomous", "robotics", "inference",
]
CATALYST_KW = [
    "joint venture", "strategic partnership", "memorandum of understanding", "mou",
    "merger", "acquisition", "acquires", "agreement", "contract win", "deal",
    "collaboration", "license agreement", "strategic alliance", "invests in",
    "raises funding", "ipo", "spin-off", "spin off",
]
UPGRADE_KW = [
    "upgrade", "overweight", "outperform", "strong buy", "buy rating",
    "raised price target", "earnings beat", "raised guidance", "record revenue",
    "blowout quarter",
]


# ══════════════════════════════════════════════════════════════════════════════
# ENGINE 1 — SEC EDGAR 8-K Scanner
# ══════════════════════════════════════════════════════════════════════════════
def scan_edgar(days_back=1):
    print(f"\n{'─'*55}")
    print("  📄 ENGINE 1: SEC EDGAR 8-K Scanner")
    print(f"{'─'*55}")

    results = []
    today   = date.today()
    start   = (today - timedelta(days=max(days_back, 3))).isoformat()  # weekends

    search_terms = [
        "artificial intelligence",
        "joint venture",
        "strategic partnership",
        "data center",
        "machine learning",
    ]

    headers = {"User-Agent": f"catalyst-scanner {EMAIL_TO}"}

    for term in search_terms:
        try:
            url = (
                "https://efts.sec.gov/LATEST/search-index?"
                f"q={requests.utils.quote(chr(34)+term+chr(34))}"
                f"&forms=8-K"
                f"&dateRange=custom&startdt={start}&enddt={today.isoformat()}"
            )
            r = requests.get(url, headers=headers, timeout=12)
            if r.status_code != 200:
                print(f"  EDGAR [{term}]: HTTP {r.status_code}")
                continue

            data = r.json()
            hits = data.get("hits", {}).get("hits", [])
            print(f"  EDGAR [{term:28s}]: {len(hits)} filings")

            for hit in hits[:6]:
                src     = hit.get("_source", {})
                ticker  = (src.get("ticker") or "").upper().strip()
                name    = src.get("entity_name", "Unknown")
                filed   = src.get("file_date", "")
                form_url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={src.get('entity_id','')}&type=8-K&dateb=&owner=include&count=5"

                # Score: AI + catalyst together = highest importance
                text_lower = (name + " " + term).lower()
                score = 5  # base for being an 8-K
                if any(k in text_lower for k in AI_KW):      score += 4
                if any(k in text_lower for k in CATALYST_KW): score += 3

                results.append({
                    "source":   "🏛 SEC 8-K",
                    "ticker":   ticker,
                    "name":     name[:40],
                    "headline": f"{name[:45]}: {term} — official 8-K filing",
                    "date":     filed,
                    "url":      form_url,
                    "score":    score,
                    "tag":      term,
                })

            time.sleep(EDGAR_DELAY)

        except Exception as e:
            print(f"  EDGAR error [{term}]: {e}")

    # Deduplicate by ticker+tag
    seen = set()
    deduped = []
    for r in results:
        key = f"{r['ticker']}|{r['tag']}"
        if key not in seen:
            seen.add(key)
            deduped.append(r)

    print(f"  → {len(deduped)} unique EDGAR hits")
    return sorted(deduped, key=lambda x: -x["score"])[:15]


# ══════════════════════════════════════════════════════════════════════════════
# ENGINE 2 — News RSS Scanner
# ══════════════════════════════════════════════════════════════════════════════
def scan_news():
    print(f"\n{'─'*55}")
    print("  📰 ENGINE 2: News RSS Scanner")
    print(f"{'─'*55}")

    results = []

    queries = [
        "AI joint venture stock deal 2026",
        "artificial intelligence acquisition merger stock",
        "AI partnership contract semiconductor",
        "data center AI contract announcement",
        "AI stock catalyst upgrade 2026",
        "machine learning deal agreement stock",
        "AI chip partnership NVIDIA AMD Intel",
        "autonomous vehicle AI contract 2026",
    ]

    # Ticker pattern: "Company Name (TICK)" or standalone $TICK
    ticker_re  = re.compile(r'\(([A-Z]{2,5})\)')
    dollar_re  = re.compile(r'\$([A-Z]{2,5})\b')

    for query in queries:
        try:
            url  = f"https://news.google.com/rss/search?q={requests.utils.quote(query)}&hl=en-US&gl=US&ceid=US:en"
            resp = requests.get(url, timeout=12, headers={"User-Agent": "Mozilla/5.0"})
            if resp.status_code != 200:
                continue

            root  = ET.fromstring(resp.content)
            items = root.findall(".//item")
            print(f"  News [{query[:38]:38s}]: {len(items)} articles")

            for item in items[:20]:
                title = item.findtext("title", "") or ""
                desc  = item.findtext("description", "") or ""
                link  = item.findtext("link", "") or ""
                pub   = item.findtext("pubDate", "") or ""

                combined = (title + " " + desc).lower()

                # Score
                score = 0
                tags  = []
                for kw in AI_KW:
                    if kw in combined: score += 2; tags.append(kw.strip())
                for kw in CATALYST_KW:
                    if kw in combined: score += 3; tags.append(kw.strip())
                for kw in UPGRADE_KW:
                    if kw in combined: score += 1; tags.append(kw.strip())

                if score < 4:
                    continue

                # Extract ticker
                m = ticker_re.search(title) or dollar_re.search(title)
                ticker = m.group(1) if m else ""

                # Parse date — skip articles older than 48 hours
                try:
                    dt  = datetime.strptime(pub[:25], "%a, %d %b %Y %H:%M:%S")
                    age = (datetime.utcnow() - dt).total_seconds() / 3600
                    if age > 48:
                        continue
                    day = dt.strftime("%b %d")
                except:
                    day = pub[:10]

                results.append({
                    "source":   "📰 News",
                    "ticker":   ticker,
                    "name":     "",
                    "headline": title[:120],
                    "date":     day,
                    "url":      link,
                    "score":    score,
                    "tag":      ", ".join(dict.fromkeys(tags))[:60],
                })

            time.sleep(NEWS_DELAY)

        except Exception as e:
            print(f"  News error [{query[:30]}]: {e}")

    # Deduplicate
    seen = set()
    deduped = []
    for r in results:
        key = r["headline"][:50]
        if key not in seen:
            seen.add(key)
            deduped.append(r)

    print(f"  → {len(deduped)} unique news hits")
    return sorted(deduped, key=lambda x: -x["score"])[:20]


# ══════════════════════════════════════════════════════════════════════════════
# ENGINE 3 — Broad Universe "Hidden Gem" Screener
# ══════════════════════════════════════════════════════════════════════════════
def screen_universe():
    print(f"\n{'─'*55}")
    print("  🔭 ENGINE 3: Hidden Gem Screener (S&P 500 + NASDAQ 100)")
    print(f"{'─'*55}")

    import yfinance as yf
    import pandas as pd

    # ── Build universe (multiple sources with fallbacks) ──────────────────
    tickers = []

    def _try_wikipedia():
        """Try Wikipedia S&P 500 list."""
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
            r = requests.get("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies",
                             headers=headers, timeout=15)
            tables = pd.read_html(r.text)
            sp = tables[0]
            col = [c for c in sp.columns if "symbol" in c.lower() or "ticker" in c.lower()]
            if col:
                t = [x.replace(".", "-") for x in sp[col[0]].dropna().tolist()]
                print(f"  ✅ Wikipedia S&P 500: {len(t)} tickers")
                return t
        except Exception as e:
            print(f"  Wikipedia failed: {e}")
        return []

    def _try_slickcharts():
        """Try slickcharts.com S&P 500 list."""
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
            r = requests.get("https://slickcharts.com/sp500", headers=headers, timeout=15)
            tables = pd.read_html(r.text)
            for tbl in tables:
                col = [c for c in tbl.columns if "symbol" in str(c).lower()]
                if col:
                    t = [x.replace(".", "-") for x in tbl[col[0]].dropna().tolist() if isinstance(x, str)]
                    if len(t) > 400:
                        print(f"  ✅ Slickcharts S&P 500: {len(t)} tickers")
                        return t
        except Exception as e:
            print(f"  Slickcharts failed: {e}")
        return []

    def _try_ishares_etf():
        """Download SPY holdings CSV from iShares."""
        try:
            # iShares IVV (S&P 500 ETF) holdings
            url = "https://www.ishares.com/us/products/239726/ishares-core-sp-500-etf/1467271812596.ajax?fileType=csv&fileName=IVV_holdings&dataType=fund"
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
            lines = r.text.splitlines()
            # Skip header rows, find ticker column
            data_lines = [l for l in lines if l.count(",") >= 3]
            t = []
            for line in data_lines[2:]:
                parts = line.split(",")
                if len(parts) >= 2:
                    tkr = parts[0].strip().strip('"')
                    if tkr and tkr.isupper() and 1 <= len(tkr) <= 5 and tkr.isalpha():
                        t.append(tkr)
            if len(t) > 400:
                print(f"  ✅ iShares IVV holdings: {len(t)} tickers")
                return t
        except Exception as e:
            print(f"  iShares failed: {e}")
        return []

    def _comprehensive_hardcoded():
        """Comprehensive hardcoded universe ~500 stocks across all sectors."""
        return [
            # Mega cap tech
            "AAPL","MSFT","NVDA","GOOGL","GOOG","AMZN","META","TSLA","AVGO","ORCL",
            # Large cap tech
            "AMD","INTC","QCOM","TXN","ADI","MCHP","AMAT","LRCX","KLAC","ASML",
            "MU","STX","WDC","SNPS","CDNS","CRM","NOW","ADBE","INTU","PANW",
            "CRWD","FTNT","ZS","OKTA","DDOG","NET","SNOW","PLTR","COIN","MSTR",
            "IBM","HPE","DELL","HPQ","JNPR","CSCO","ANET","FFIV","NTAP","PSTG",
            # Semis
            "MRVL","NXPI","ON","MPWR","WOLF","SWKS","QRVO","CRUS","SLAB","DIOD",
            "RMBS","ACLS","UCTT","FORM","ICHR","ONTO","ENTG","MKSI","NOVT","CAMT",
            "AMKR","ASX","SPWR","AXTI","AOSL","CRDO","ALAB","PLAB","TSEM","GFS",
            # AI / Cloud
            "MSFT","GOOGL","AMZN","META","ORCL","CRM","NOW","WDAY","VEEV","HUBS",
            "BILL","ZI","BRZE","APP","APPLOVIN","TTD","IAS","MGNI","PUBM",
            "GTLB","MDB","ESTC","CFLT","DDOG","SPLK","SUMO","FIVN","NICE","NICE",
            # Networking / Infra
            "CIEN","GLW","VIAV","LITE","COHR","II-VI","FN","AAOI","FNSR","NPTN",
            "INFN","CALX","ADTN","COMM","NOK","ERIC","CSCO","ANET","JNPR","CIEN",
            # Semicon equipment
            "AMAT","LRCX","KLAC","TER","COHU","ONTO","ENTG","MKSI","ICHR","UCTT",
            "ACLS","FORM","NOVT","CAMT","VECO","AXTI","AEHR","SKYT","POET",
            # AI Power / Energy
            "NEE","DUK","SO","AEP","EXC","PCG","ED","FE","ETR","PPL",
            "CEG","VST","NRG","GEV","VRT","ETN","EMR","ROK","PH","IR",
            "BE","FCEL","PLUG","CLNE","FLNC","EOSE","BW","BLDP","BLOOM",
            # Defense
            "LMT","RTX","NOC","GD","L3H","LDOS","BAH","CACI","SAIC","HII",
            "KTOS","RKLB","ASTS","BKSY","ONDS","BBAI","LASR","LPTH","OUST","RCAT",
            # Healthcare / Biotech
            "LLY","JNJ","ABBV","MRK","PFE","BMY","GILD","AMGN","REGN","VRTX",
            "MRNA","BNTX","NVAX","OCGN","SGEN","ALNY","INCY","EXEL","RARE","ARWR",
            "RXRX","SDGR","SCHD","ILMN","A","TMO","DHR","BIO","IDXX","HOLX",
            # Financials
            "JPM","BAC","WFC","GS","MS","C","BLK","SCHW","AXP","COF",
            "V","MA","PYPL","SQ","AFRM","UPST","LC","SOFI","NU","HOOD",
            # Consumer
            "AMZN","WMT","TGT","COST","HD","LOW","NKE","LULU","PTON","DASH",
            "UBER","LYFT","ABNB","BKNG","EXPE","TRIP","YELP","SNAP","PINS","RDDT",
            # Industrials
            "CAT","DE","MMM","HON","GE","BA","LMT","UPS","FDX","XPO",
            "STRL","EME","PWR","FIX","MTZ","WLDN","TTEK","J","ACM","KBR",
            "ETN","ROK","PH","IR","AME","GNRC","XYL","ROP","IDEX","IEX",
            # Materials / Commodities
            "FCX","NEM","GOLD","AEM","KGC","AG","MP","CCJ","UUUU","NXE",
            "CLF","STLD","NUE","RS","CMC","WOR","ATI","TIE","HAYN","KALU",
            # Real Estate / REITs
            "AMT","CCI","EQIX","DLR","CONE","QTS","SBAC","IRM","VTR","WELL",
            # ETFs with options
            "SPY","QQQ","IWM","SMH","SOXX","XLK","XLF","XLE","XBI","ARK",
            "ARKK","ARKQ","ARKG","ARKF","ARKX","TQQQ","SQQQ","UVXY","VIX",
            # Asia Tech ADRs
            "TSM","SONY","BABA","JD","PDD","BIDU","NIO","LI","XPEV","TCEHY",
            "GRAB","SEA","COUR","TIGR","FUTU","UP","LMND","OPEN","OPRT",
            # Storage / Memory
            "SNDK","MU","STX","WDC","MRAM","NTAP","PSTG","NTNX","PURE",
            # Telecom
            "T","VZ","TMUS","DISH","LUMN","SATS","VSAT","IRDM","GSAT",
        ]

    # Try sources in order
    print("  Loading universe...")
    tickers = _try_wikipedia()
    if len(tickers) < 400:
        tickers = _try_slickcharts()
    if len(tickers) < 400:
        tickers = _try_ishares_etf()
    if len(tickers) < 400:
        print("  ⚠️  Using comprehensive hardcoded universe")
        tickers = _comprehensive_hardcoded()

    # Always add NASDAQ 100 on top
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
        r = requests.get("https://en.wikipedia.org/wiki/Nasdaq-100", headers=headers, timeout=15)
        tables = pd.read_html(r.text)
        for tbl in tables:
            col = [c for c in tbl.columns if "ticker" in str(c).lower() or "symbol" in str(c).lower()]
            if col and len(tbl) > 90:
                extra = tbl[col[0]].dropna().tolist()
                tickers += [str(x) for x in extra if isinstance(x, str) and x.isupper()]
                print(f"  + NASDAQ 100 appended: total = {len(set(tickers))} tickers")
                break
    except:
        pass

    tickers = list(dict.fromkeys(tickers))  # deduplicate
    print(f"  Final universe: {len(tickers)} tickers\n")

    # ── Theme filter: AI / Semiconductor / Defense only ───────────────────
    # Sectors yfinance returns for qualifying companies
    FOCUS_SECTORS = {
        "technology", "communication services", "industrials",
        "basic materials",  # for uranium, rare earth, critical minerals
    }
    # Keywords in company name or description that qualify ANY sector
    FOCUS_NAME_KW = [
        "semiconductor","semicon","chip","wafer","photon","optic","laser","lidar",
        "sensor","imaging","radar","sonar","infrared","defense","defence","aerospace",
        "drone","autonomous","robot","artificial intelligence"," ai ","machine learning",
        "data center","datacenter","cloud","quantum","nuclear","uranium","satellite",
        "cyber","security","intelligence","military","navy","army","dod","darpa",
        "gpu","cpu","fpga","asic","networking","fiber","wireless","5g","6g",
        "power","energy storage","battery","fuel cell","solar","grid",
    ]

    # Pre-filter by known ticker lists for guaranteed coverage
    # (catches niche semis/defense that may report under non-tech sector)
    ALWAYS_INCLUDE = set([
        # Semis & equipment
        "NVDA","AMD","INTC","AVGO","QCOM","TXN","ADI","MCHP","NXPI","MRVL",
        "AMAT","LRCX","KLAC","ASML","TER","KLAC","ONTO","ENTG","MKSI","VECO",
        "MU","STX","WDC","SNDK","MRAM","CRDO","ALAB","ANET","PLAB","CAMT",
        "AMKR","TSM","ASX","TSEM","GFS","AXTI","AOSL","SKYT","AEHR","DRAM",
        # Photonics / optics
        "LITE","LASR","COHR","AAOI","FN","LPTH","GLW","CIEN","VIAV","INFN",
        # AI software / cloud
        "PLTR","APP","SNOW","DDOG","NET","CRWD","PANW","ZS","OKTA","MSFT",
        "GOOGL","META","AMZN","ORCL","NOW","CRM","ADBE","IBM","NBIS","CRWV",
        # Defense
        "LMT","RTX","NOC","GD","KTOS","RKLB","ASTS","BKSY","ONDS","BBAI",
        "LASR","LPTH","OUST","RCAT","SERV","VWAV","IRDM","BAH","CACI","SAIC",
        # AI infra / power
        "VRT","ETN","APH","GLW","PWR","EME","STRL","FIX","NVT","JBL","FLEX",
        "CEG","VST","NRG","GEV","BE","CCJ","UUUU","LEU","NXE","UEC",
        # Connectivity / networking
        "NOK","ERIC","CALX","COMM","ADTN","KEYS","TTMI","BELFA","OSS","SANM",
        # AI compute
        "DELL","HPE","SMCI","NTAP","PSTG","NTNX",
        # Crypto / AI data center
        "APLD","CORZ","RIOT","HUT","IREN","WULF","CIFR",
        # Quantum
        "IONQ","QBTS","ARQQ","QTUM",
        # Critical minerals (defense supply chain)
        "MP","TMC","UUUU","CCJ","NXE","UEC","LEU","COPX",
        # Asia tech with AI angle
        "TSM","SONY","IFNNY",
        # Broad ETFs with AI theme
        "SMH","SOXX","ARKQ","ARKX",
    ])

    def _qualifies(tkr, inf):
        """Return True if stock fits AI / semiconductor / defense theme."""
        if tkr in ALWAYS_INCLUDE:
            return True
        sector = (inf.get("sector") or "").lower()
        if sector not in FOCUS_SECTORS:
            return False
        # Check name + description for theme keywords
        name = (inf.get("shortName") or inf.get("longName") or "").lower()
        desc = (inf.get("longBusinessSummary") or "")[:300].lower()
        combined = name + " " + desc
        return any(kw in combined for kw in FOCUS_NAME_KW)

    gems = []
    n    = len(tickers)
    print(f"  Screening {n} stocks — AI / Semiconductor / Defense filter active...\n")

    for i, tkr in enumerate(tickers, 1):
        try:
            t   = yf.Ticker(tkr)
            inf = t.info

            price = inf.get("currentPrice") or inf.get("regularMarketPrice")
            pt    = inf.get("targetMeanPrice")
            nana  = int(inf.get("numberOfAnalystOpinions") or 0)
            revG  = inf.get("revenueGrowth")
            fpe   = inf.get("forwardPE")
            peg   = inf.get("pegRatio")
            mc    = inf.get("marketCap") or 0
            gm    = inf.get("grossMargins")
            opM   = inf.get("operatingMargins")
            de_r  = inf.get("debtToEquity")
            de    = de_r / 100 if de_r else None
            beta  = inf.get("beta")

            # ── Theme filter: skip non-AI/semi/defense companies ──────────
            if not _qualifies(tkr, inf):            continue

            # ── Hard filters ──────────────────────────────────────────────
            if not price or price <= 0:             continue
            if mc < 300e6:                          continue  # min $300M cap
            if not pt or pt <= 0:                   continue
            upside = (pt - price) / price * 100
            if upside < 15:                         continue  # analyst upside floor
            if revG is None or revG < 0.08:        continue  # >8% revenue growth
            if fpe and fpe > 100:                   continue  # not crazy expensive

            # ── 52-week position (lower half only) ────────────────────────
            hist = t.history(period="1y", auto_adjust=True)
            if len(hist) < 20:                      continue
            lo52  = float(hist["Low"].min())
            hi52  = float(hist["High"].max())
            pos52 = (price - lo52) / (hi52 - lo52) * 100 if hi52 > lo52 else 100
            if pos52 > 55:                          continue  # must be in lower 55% of range

            # ── Options flow (quick: first expiry only) ───────────────────
            pc_vol = None
            try:
                exps = t.options
                if exps:
                    ch    = t.option_chain(exps[0])
                    c_vol = float(ch.calls["volume"].fillna(0).sum())
                    p_vol = float(ch.puts["volume"].fillna(0).sum())
                    if c_vol > 50:
                        pc_vol = round(p_vol / c_vol, 2)
            except:
                pass

            # ── Composite gem score ───────────────────────────────────────
            gs = 0
            gs += min(35, upside * 0.8)              # analyst upside (max 35)
            gs += (55 - pos52) * 0.4                 # lower in range = better (max 22)
            if peg  and 0 < peg  < 1.0:  gs += 15
            elif peg and 0 < peg < 1.5:  gs += 8
            if pc_vol and pc_vol < 0.4:  gs += 12
            elif pc_vol and pc_vol < 0.7: gs += 6
            if nana < 8:   gs += 8   # under the radar
            elif nana < 15: gs += 4
            if revG and revG > 0.30: gs += 10
            elif revG and revG > 0.15: gs += 5
            if gm  and gm  > 0.50:  gs += 6
            if opM and opM > 0.15:  gs += 4
            if de  and de  < 0.3:   gs += 5
            if beta and beta < 1.2:  gs += 3  # lower vol bonus

            sector = inf.get("sector", "")
            name   = (inf.get("shortName") or tkr)[:35]

            gems.append({
                "ticker":     tkr,
                "name":       name,
                "price":      round(price, 2),
                "mc_b":       round(mc / 1e9, 1),
                "upside":     round(upside, 1),
                "revG":       round(revG * 100, 1) if revG else None,
                "fpe":        round(fpe, 1) if fpe else None,
                "peg":        round(peg, 2) if peg else None,
                "pos52":      round(pos52, 0),
                "pc_vol":     pc_vol,
                "n_analysts": nana,
                "gm":         round(gm * 100, 1) if gm else None,
                "beta":       round(beta, 2) if beta else None,
                "sector":     sector,
                "gem_score":  round(gs, 1),
            })

            if i % 50 == 0 or (gems and i % 20 == 0):
                print(f"  [{i:3}/{n}] scanned  ·  {len(gems)} gems so far  ·  last hit: {tkr}")

            time.sleep(SCREEN_DELAY)

        except Exception:
            time.sleep(0.3)
            continue

    ranked = sorted(gems, key=lambda x: -x["gem_score"])[:20]
    print(f"\n  → {len(ranked)} hidden gems found (top 20 of {len(gems)} that passed filters)")
    return ranked


# ══════════════════════════════════════════════════════════════════════════════
# HTML Injection
# ══════════════════════════════════════════════════════════════════════════════
def inject_html(edgar_hits, news_hits, gems, run_time):
    """Write a Discoveries section into stock_analysis_v6.html."""
    if not HTML_FILE.exists():
        print("  ⚠️  HTML file not found — skipping injection")
        return

    # Build discoveries tab HTML
    ts = run_time.strftime("%b %d, %Y %H:%M")

    def score_badge(score):
        if score >= 10: return f'<span style="background:#dcfce7;color:#15803d;padding:1px 6px;border-radius:8px;font-size:10px;font-weight:700">⭐⭐⭐ High</span>'
        if score >= 6:  return f'<span style="background:#fef9c3;color:#854d0e;padding:1px 6px;border-radius:8px;font-size:10px;font-weight:700">⭐⭐ Medium</span>'
        return              f'<span style="background:#f1f5f9;color:#475569;padding:1px 6px;border-radius:8px;font-size:10px;font-weight:700">⭐ Watch</span>'

    # EDGAR section
    edgar_rows = ""
    for h in edgar_hits[:10]:
        ticker_tag = f'<span style="font-weight:800;color:#1d4ed8;margin-right:6px">{h["ticker"]}</span>' if h["ticker"] else ""
        edgar_rows += f"""
        <div style="padding:8px 0;border-bottom:1px solid #f1f5f9;display:flex;align-items:flex-start;gap:10px">
          <div style="min-width:60px;font-size:10px;color:#94a3b8;margin-top:2px">{h.get("date","")[:10]}</div>
          <div style="flex:1">
            {ticker_tag}
            <a href="{h['url']}" target="_blank" style="color:#0f172a;text-decoration:none;font-size:12px">{h['headline'][:100]}</a>
            <div style="font-size:10px;color:#64748b;margin-top:2px">🏷 {h.get('tag','')}</div>
          </div>
          <div>{score_badge(h['score'])}</div>
        </div>"""

    # News section
    news_rows = ""
    for h in news_hits[:12]:
        ticker_tag = f'<span style="font-weight:800;color:#1d4ed8;margin-right:6px">{h["ticker"]}</span>' if h["ticker"] else ""
        news_rows += f"""
        <div style="padding:8px 0;border-bottom:1px solid #f1f5f9;display:flex;align-items:flex-start;gap:10px">
          <div style="min-width:60px;font-size:10px;color:#94a3b8;margin-top:2px">{h.get("date","")}</div>
          <div style="flex:1">
            {ticker_tag}
            <a href="{h['url']}" target="_blank" style="color:#0f172a;text-decoration:none;font-size:12px">{h['headline'][:110]}</a>
            <div style="font-size:10px;color:#64748b;margin-top:2px">🏷 {h.get('tag','')[:60]}</div>
          </div>
          <div>{score_badge(h['score'])}</div>
        </div>"""

    # Gems section
    gem_rows = ""
    for g in gems[:15]:
        pc_color = "#15803d" if (g["pc_vol"] or 1) < 0.6 else "#d97706" if (g["pc_vol"] or 1) < 1.0 else "#dc2626"
        peg_color = "#15803d" if g["peg"] and g["peg"] < 1.0 else "#1d4ed8" if g["peg"] and g["peg"] < 1.5 else "#475569"
        gem_rows += f"""
        <div style="padding:8px 12px;border:1px solid #e2e8f0;border-radius:8px;margin-bottom:6px;background:#fafbff">
          <div style="display:flex;justify-content:space-between;align-items:center">
            <div>
              <span style="font-weight:800;font-size:13px;color:#0f172a">{g['ticker']}</span>
              <span style="font-size:11px;color:#475569;margin-left:6px">{g['name']}</span>
              <span style="font-size:10px;color:#94a3b8;margin-left:6px">{g['sector']}</span>
            </div>
            <div style="font-size:11px;font-weight:700;color:#15803d">GEM SCORE {g['gem_score']:.0f}</div>
          </div>
          <div style="display:flex;gap:12px;margin-top:6px;flex-wrap:wrap">
            <span style="font-size:11px"><b style="color:#0f172a">${g['price']}</b> · ${g['mc_b']}B cap</span>
            <span style="font-size:11px;color:#15803d">▲ {g['upside']}% analyst upside</span>
            <span style="font-size:11px">Rev +{g['revG']}%</span>
            {f'<span style="font-size:11px">fPE {g["fpe"]}x</span>' if g['fpe'] else ''}
            {f'<span style="font-size:11px;color:{peg_color}">PEG {g["peg"]}</span>' if g['peg'] else ''}
            <span style="font-size:11px">52W pos: {g['pos52']:.0f}%</span>
            {f'<span style="font-size:11px;color:{pc_color}">P/C {g["pc_vol"]}</span>' if g['pc_vol'] is not None else ''}
            {f'<span style="font-size:11px;color:#64748b">{g["n_analysts"]} analysts</span>' if g['n_analysts'] else ''}
          </div>
        </div>"""

    disc_html = f"""
<!-- DISCOVERIES SECTION — auto-generated by catalyst_scanner.py -->
<div id="discoveries-section" style="max-width:1400px;margin:0 auto;padding:20px 24px">
  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px">
    <h2 style="font-size:16px;font-weight:800;color:#0f172a;margin:0">📡 Daily Catalyst & Discovery Feed</h2>
    <span style="font-size:11px;color:#94a3b8">Last run: {ts}</span>
  </div>

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">

    <!-- SEC EDGAR -->
    <div style="background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:16px">
      <div style="font-size:12px;font-weight:800;color:#475569;text-transform:uppercase;letter-spacing:.5px;margin-bottom:10px">
        🏛 SEC 8-K Filings · AI / Merger / JV
      </div>
      {edgar_rows if edgar_rows else '<div style="color:#94a3b8;font-size:12px;padding:8px 0">No hits today</div>'}
    </div>

    <!-- News -->
    <div style="background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:16px">
      <div style="font-size:12px;font-weight:800;color:#475569;text-transform:uppercase;letter-spacing:.5px;margin-bottom:10px">
        📰 News Catalysts · AI / Deals / Upgrades
      </div>
      {news_rows if news_rows else '<div style="color:#94a3b8;font-size:12px;padding:8px 0">No hits today</div>'}
    </div>

  </div>

  <!-- Hidden Gems -->
  <div style="background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:16px;margin-top:20px">
    <div style="font-size:12px;font-weight:800;color:#475569;text-transform:uppercase;letter-spacing:.5px;margin-bottom:10px">
      💎 Hidden Gems — S&P 500 + NASDAQ 100 Screen
      <span style="font-size:10px;font-weight:400;color:#94a3b8;margin-left:8px">
        Near 52W lows · Analyst upside >15% · Call-heavy · Under the radar
      </span>
    </div>
    {gem_rows if gem_rows else '<div style="color:#94a3b8;font-size:12px;padding:8px 0">Screener not run (use --full to include)</div>'}
  </div>
</div>
<!-- END DISCOVERIES SECTION -->"""

    html = HTML_FILE.read_text(encoding="utf-8")

    # Replace existing discoveries section or inject before </body>
    if "<!-- DISCOVERIES SECTION" in html:
        html = re.sub(
            r"<!-- DISCOVERIES SECTION.*?<!-- END DISCOVERIES SECTION -->",
            disc_html.strip(),
            html,
            flags=re.DOTALL,
        )
    else:
        html = html.replace("</body>", disc_html + "\n</body>")

    HTML_FILE.write_text(html, encoding="utf-8")
    print(f"  ✅ HTML updated → {HTML_FILE.name}")


# ══════════════════════════════════════════════════════════════════════════════
# Email Digest
# ══════════════════════════════════════════════════════════════════════════════
def send_email(edgar_hits, news_hits, gems, run_time):
    if not EMAIL_FROM or not EMAIL_PASS:
        print("\n  ⚠️  Email not configured. Set SCANNER_EMAIL_FROM and SCANNER_EMAIL_PASS env vars.")
        print("      See README section: 'Setting up email alerts'")
        return

    ts = run_time.strftime("%B %d, %Y")

    def row(item, kind="catalyst"):
        ticker = f"<b style='color:#1d4ed8'>{item['ticker']}</b> — " if item.get("ticker") else ""
        stars  = "⭐⭐⭐" if item["score"]>=10 else "⭐⭐" if item["score"]>=6 else "⭐"
        return f"<tr><td style='padding:6px 8px;font-size:12px;border-bottom:1px solid #f1f5f9'>{stars} {ticker}{item['headline'][:100]}</td><td style='padding:6px 8px;font-size:11px;color:#64748b;white-space:nowrap'>{item.get('date','')[:10]}</td></tr>"

    def gem_row(g):
        return (f"<tr>"
                f"<td style='padding:6px 8px;font-weight:800;color:#1d4ed8'>{g['ticker']}</td>"
                f"<td style='padding:6px 8px;font-size:12px'>{g['name']}</td>"
                f"<td style='padding:6px 8px;font-size:12px;color:#15803d'>▲ {g['upside']}%</td>"
                f"<td style='padding:6px 8px;font-size:12px'>+{g['revG']}% rev</td>"
                f"<td style='padding:6px 8px;font-size:12px'>{g['pos52']:.0f}% of 52W</td>"
                f"<td style='padding:6px 8px;font-size:11px;color:#94a3b8'>{g['n_analysts']} analysts</td>"
                f"</tr>")

    html_body = f"""
<html><body style="font-family:system-ui,-apple-system,sans-serif;max-width:800px;margin:0 auto;padding:20px;color:#0f172a">
<h1 style="font-size:20px;border-bottom:2px solid #e2e8f0;padding-bottom:10px">
  📡 AI Catalyst & Discovery Digest — {ts}
</h1>

<h2 style="font-size:14px;color:#475569;text-transform:uppercase;letter-spacing:.5px">🏛 SEC 8-K Filings</h2>
<table style="width:100%;border-collapse:collapse;margin-bottom:20px">
  {''.join(row(h) for h in edgar_hits[:8]) if edgar_hits else '<tr><td style="color:#94a3b8;font-size:12px;padding:8px">No filings today</td></tr>'}
</table>

<h2 style="font-size:14px;color:#475569;text-transform:uppercase;letter-spacing:.5px">📰 News Catalysts</h2>
<table style="width:100%;border-collapse:collapse;margin-bottom:20px">
  {''.join(row(h) for h in news_hits[:10]) if news_hits else '<tr><td style="color:#94a3b8;font-size:12px;padding:8px">No news hits today</td></tr>'}
</table>

<h2 style="font-size:14px;color:#475569;text-transform:uppercase;letter-spacing:.5px">💎 Hidden Gems</h2>
<table style="width:100%;border-collapse:collapse;margin-bottom:20px">
  <tr style="font-size:10px;color:#94a3b8;text-transform:uppercase">
    <th style="padding:4px 8px;text-align:left">Ticker</th>
    <th style="padding:4px 8px;text-align:left">Name</th>
    <th style="padding:4px 8px;text-align:left">Upside</th>
    <th style="padding:4px 8px;text-align:left">Growth</th>
    <th style="padding:4px 8px;text-align:left">52W Pos</th>
    <th style="padding:4px 8px;text-align:left">Coverage</th>
  </tr>
  {''.join(gem_row(g) for g in gems[:12]) if gems else '<tr><td colspan="6" style="color:#94a3b8;font-size:12px;padding:8px">Run with --full to include screener</td></tr>'}
</table>

<div style="font-size:11px;color:#94a3b8;border-top:1px solid #e2e8f0;padding-top:10px;margin-top:20px">
  Generated by catalyst_scanner.py · {run_time.strftime("%H:%M")} ·
  <a href="file://{HTML_FILE}" style="color:#1d4ed8">Open Dashboard</a>
</div>
</body></html>"""

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"📡 AI Catalyst Digest — {ts}"
        msg["From"]    = EMAIL_FROM
        msg["To"]      = EMAIL_TO
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(EMAIL_FROM, EMAIL_PASS)
            smtp.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())

        print(f"  ✅ Email sent → {EMAIL_TO}")
    except Exception as e:
        print(f"  ❌ Email failed: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(description="Daily AI catalyst & stock discovery scanner")
    parser.add_argument("--email",      action="store_true", help="Send email digest")
    parser.add_argument("--quick",      action="store_true", help="Skip universe screener (news + EDGAR only)")
    parser.add_argument("--screen-only",action="store_true", help="Run screener only")
    parser.add_argument("--days",       type=int, default=1,  help="Days back for EDGAR/news (default 1)")
    args = parser.parse_args()

    run_time = datetime.now()
    ts       = run_time.strftime("%B %d, %Y %H:%M")

    print(f"\n{'═'*55}")
    print(f"  📡 Catalyst Scanner  ·  {ts}")
    print(f"{'═'*55}")

    edgar_hits, news_hits, gems = [], [], []

    if not args.screen_only:
        edgar_hits = scan_edgar(days_back=args.days)
        news_hits  = scan_news()

    if not args.quick:
        gems = screen_universe()

    # ── Save raw JSON ──────────────────────────────────────────────────────
    output = {
        "run_time":   ts,
        "edgar_hits": edgar_hits,
        "news_hits":  news_hits,
        "gems":       gems,
    }
    OUTPUT_FILE.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"\n  💾 Results saved → {OUTPUT_FILE.name}")

    # ── Inject into HTML ───────────────────────────────────────────────────
    inject_html(edgar_hits, news_hits, gems, run_time)

    # ── Email digest ───────────────────────────────────────────────────────
    if args.email:
        print("\n  📧 Sending email digest...")
        send_email(edgar_hits, news_hits, gems, run_time)

    # ── Summary ───────────────────────────────────────────────────────────
    print(f"\n{'═'*55}")
    print(f"  ✅ Done")
    print(f"  📄 EDGAR hits : {len(edgar_hits)}")
    print(f"  📰 News hits  : {len(news_hits)}")
    print(f"  💎 Gems found : {len(gems)}")
    print(f"{'═'*55}\n")

    if gems:
        print("  TOP 5 HIDDEN GEMS:")
        for g in gems[:5]:
            pc = f"P/C={g['pc_vol']}" if g["pc_vol"] else ""
            print(f"    {g['ticker']:<6} {g['name']:<30} upside={g['upside']:+.0f}%  "
                  f"pos52={g['pos52']:.0f}%  {pc}  score={g['gem_score']:.0f}")
    print()


if __name__ == "__main__":
    main()
