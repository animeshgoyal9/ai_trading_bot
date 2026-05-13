#!/usr/bin/env python3
"""
update_stock_data.py
─────────────────────────────────────────────────────────────────────────────
Fetches live prices, P/E, growth, margins, short interest, earnings dates
from yfinance for every stock in stock_analysis_v6.html, recalculates scores,
and rewrites the HTML's JavaScript data array in place.

Usage (from ai_trading_bot directory):
    source trading/bin/activate
    python3 update_stock_data.py

Time: ~10-15 min  (throttled at 0.7 s/stock to avoid Yahoo 429s)
─────────────────────────────────────────────────────────────────────────────
"""

import yfinance as yf
import json, re, time, math, sys, os
from datetime import datetime
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
HTML_FILE   = Path(__file__).parent / "stock_analysis_v6.html"
DELAY       = 0.7          # seconds between yfinance calls
RETRY_DELAY = 8            # seconds to wait after a 429

# ── Full ticker list ──────────────────────────────────────────────────────────
TICKERS = [
    # Core AI Compute + Semis
    "NVDA","TSM","AVGO","AMD","MU","INTC","TXN","MRVL","NXPI","ADI","MCHP",
    "KLAC","LRCX","ASML","TER","KEYS","MKSI","GFS","TSEM","VECO","IFNNY",
    "CRDO","AMKR","PLAB","AXTI","AOSL","AEHR","POET","SKYT","CAMT","DRAM",
    # Connectivity / Networking
    "ALAB","ANET","SMH","SOXX",
    # Photonics
    "LITE","LASR","COHR","AAOI","FN","LPTH",
    # EDA Software
    "CDNS","SNPS",
    # AI / Data Infrastructure
    "PLTR","APP","NBIS","CRWV","DELL","ORCL","HPE","VRT","DOCN","GLW","CIEN","APH",
    # Quantum
    "QTUM","IONQ","QBTS","ARQQ",
    # Space / Drones / Robotics
    "RKLB","ASTS","IRDM","BKSY","SERV","RCAT","OUST","VWAV",
    # AI Power Generation (BE-similar)
    "BE","CEG","VST","NRG","FCEL","PLUG","CLNE","GEV","FLNC","EOSE","BW",
    # Uranium / Nuclear
    "CCJ","UUUU","NXE","UEC","LEU",
    # Precious Metals / Commodities
    "AG","GLD","COPX","ABX","AEM","KGC","MP","TMC","WCP",
    # Crypto Mining / AI Data Center pivot
    "APLD","CORZ","RIOT","HUT","CIFR","WULF","IREN",
    # Defense / Speculative Small Cap
    "ONDS","BBAI","RXRX","LAES","CRML","USAR","WWR","OKLL","NUAI",
    # Infrastructure / Industrials
    "STRL","EME","ETN","PWR","JBL","FIX","CAT",
    # Electronics Manufacturing / PCB
    "FLEX","SANM","TTMI","BELFA","OSS",
    # Telecom Equipment (NOK-similar)
    "NOK","ERIC","INFN","CALX","ADTN","COMM",
    # Asia Tech
    "GRAB","ASX","SONY",
    # Storage / Memory
    "SNDK","STX","WDC","MRAM",
    # Broad ETFs
    "QQQ","SPY",
    # Special / Alpaca-listed
    "XNDU","INFQ","ALMU","XE","WYFI",
    # Large cap / Mega cap
    "AAPL","MSFT","GOOGL","ARM","QCOM","IBM",
    # Others from original HTML
    "VIAV","NVT","ONTO","ENTG","LUMN","FRSH","ASYS","TMCR",
    "NBIS","NXE","APLD",
]
TICKERS = list(dict.fromkeys(TICKERS))   # deduplicate, preserve order

# ── Preserved qualitative notes ───────────────────────────────────────────────
NOTES = {
    "NVDA":  "AI GPU monopoly · H100/B200 · Data center +73% YoY · 71% gross margin · PEG reflects multi-year AI capex supercycle",
    "TSM":   "Q1 2026: Revenue +40.6% YoY · GM 66.2% · Op margin 58.1% · Only fab that can make leading-edge chips",
    "LITE":  "Q3 revenue +90% · Q4 guided $980M vs $917M expected · Sold out through 2027 · AI optical interconnect leader",
    "MU":    "Cheapest AI stock by P/E · HBM sold out 2026 · CEO buying · DRAM +63% Q2 · Jun 25 earnings · PEG near 0.2",
    "LASR":  "85% A&D revenue · $162M backlog · Defense laser systems · ATH momentum · May 7 earnings",
    "ALAB":  "Only profitable AI connectivity · Zero debt · ~78% gross margin · AEC copper moat",
    "AVGO":  "AI revenue doubling · Custom ASIC moat for Google/Amazon/Meta · Jun 4 earnings",
    "ANET":  "AI switching monopoly · Zero debt · $3.25B AI revenue target · Hyper-scaler capex beneficiary",
    "ASML":  "EUV lithography monopoly · Irreplaceable — every advanced node needs ASML · No substitute exists",
    "CCJ":   "$2.6B India nuclear deal · Uranium to $100-125/lb · Westinghouse stake · Nuclear renaissance",
    "VRT":   "S&P 500 · $13.75B guided · AI data center cooling leader · High debt 1.8x watch",
    "CDNS":  "EDA duopoly with SNPS · 90% gross margin · AI chip design essential · Every AI chip needs Cadence",
    "PLTR":  "70% revenue growth · 137% US commercial growth · D/E near zero · ROE 26%",
    "AMD":   "Data center +39% YoY · MI450 upcoming · CPU renaissance beneficiary · NVDA challenger",
    "MRVL":  "Custom AI silicon for AWS/Microsoft · Celestial AI $5.5B · Revenue +63% YoY · Non-GAAP GM 60%",
    "UUUU":  "Only US mine-to-oxide uranium + REE · Apple $500M deal · Zero debt · China export beneficiary",
    "SNPS":  "Chip design software monopoly · NVDA $2.3B holding · EDA duopoly with CDNS",
    "AG":    "Silver deficit year 6 · Non-correlated to AI · Physical silver demand from solar + electronics",
    "INTC":  "CPU renaissance · Apple chip deal catalyst · Data center +22% YoY · New CEO Lip-Bu Tan · 18A node",
    "NOK":   "NVDA invested $1.1B — biggest external validation · Optical +18-20% · Best month in 13 years",
    "SOXX":  "iShares Semiconductor ETF · 30 US-listed semicon companies · Broad AI chip exposure",
    "ONDS":  "820% revenue guided · Palantir AI · $10M border order · Defense drones · May 18 earnings",
    "TER":   "Semiconductor + robotics test equipment · 58% gross margin · Low debt · Steady compounder",
    "AMKR":  "$1.6B CHIPS Act · Intel advanced packaging · Cheap P/E but growth slowing",
    "CRDO":  "AEC copper + optical · 200%+ revenue growth · Zero debt · AI connectivity infrastructure",
    "FN":    "AI optical transceiver manufacturing leader · Beat EPS but flat guidance dragged stock",
    "LPTH":  "Infrared optics for defense thermal cameras, counter-drone systems & autonomous vehicles · Revenue +120% YoY · $700M cap = massive upside if defense IR demand accelerates · PEG 1.54 · Flat 3m = coiling at base",
    "AAPL":  "Sell RSUs systematically · Hold core position · Target max 10% of net worth",
    "GLD":   "Central bank buying · Gold at $3,200+ · Safe haven · Macro hedge vs AI volatility",
    "QTUM":  "87 holdings quantum + AI exposure · 5-star Morningstar · INTC NOK MU top holdings",
    "PLAB":  "Photomask near-duopoly · Zero debt · Undervalued vs photonics peers",
    "KEYS":  "Network & electronics test · 62% gross margin · Solid ROE · Slow revenue growth ~8%",
    "AAOI":  "$1B+ 2026 revenue · Amazon warrant · $500M dilution risk · Reports earnings key catalyst",
    "BKSY":  "$322M backlog · 91% international defense · Satellite imaging · May 14 earnings",
    "GEV":   "Gas turbines for AI data centers · AI power thesis · Low gross margin 12% is concern",
    "AEHR":  "🔴 $7M+ insider selling · $60M dilution · Bookings strong but management selling stock",
    "IONQ":  "SkyWater acquisition adds chip fab · Only vertically integrated quantum · Real commercial revenue",
    "SANM":  "Contract manufacturer · 173% above historical P/E average · Low gross margin 8%",
    "STX":   "HAMR fully allocated 2026 · High debt 2.1x · Insider selling before earnings — caution",
    "TTMI":  "Data center PCBs & aerospace · Low gross margin 18% · Picks & shovels data center play",
    "TSEM":  "436% above historical P/E · Specialty foundry · Intel partnership · Intel 18A synergy",
    "WDC":   "+905% TTM · Flash + HDD for AI storage layer · Heavy options put activity = hedge warning",
    "MRAM":  "Everspin Technologies · Magnetoresistive RAM · Non-volatile + DRAM-speed = ideal for industrial IoT, aerospace & automotive · Small cap $120M · Profitable · Low coverage = asymmetric opportunity",
    "BE":    "CEO sold $34M post-earnings RED FLAG · High debt 3.5x · Wait for $240-250 pullback · Fuel cell AI power",
    "LRCX":  "BofA US 1 list · WFE surge · AI memory equipment leader · +244% TTM",
    "COHR":  "NVDA $2B exclusive contract · Book-to-bill >4x · AI optical transceiver leader",
    "DOCN":  "SMB cloud · High debt · Niche vs AWS/Azure/GCP · No AI infra thesis",
    "CORZ":  "Bitcoin→AI pivot · AMD 50MW deal · High debt $3.3B new notes · Execution risk",
    "SNDK":  "Sold at $879 — DO NOT buy back · At analyst target · +2740% TTM run already priced in",
    "FLNC":  "Battery storage for AI data centers · 36GWh under development · Pre-profitable",
    "RIOT":  "AMD 50MW deal = pivot signal · But -$500M net loss Q1 · Forward P/E extreme",
    "KLAC":  "BofA top 6 pick · Wafer inspection near-monopoly · Benefits from ALL WFE growth · 72% GM",
    "ADI":   "BofA top 6 pick · Analog duopoly with TXN · 68% gross margin · Data center power management",
    "NBIS":  "European AI cloud · NVDA invested $100M · $27B Meta deal · Former Yandex assets",
    "FLEX":  "SPINNING OFF Cloud & Power (SpinCo) by Q1 2027 · Grid-to-chip AI infrastructure · +35% today",
    "HUT":   "Compute segment revenue tripled to $66M · Pivoting Bitcoin mining to AI compute · 64% GM",
    "IRDM":  "66 LEO satellites · Govt/military comms · Steady cash flow · High debt 2.1x · Slow growth",
    "ASTS":  "Direct-to-smartphone satellite broadband · AT&T/Verizon/Google partners · Pre-profitable",
    "CAT":   "Heavy equipment for data center construction · Iran war + tariff headwinds · Dividend aristocrat",
    "BELFA": "Power conversion for AI servers & defense · P/E 14x cheap · $500M cap = room to 5-10x",
    "VECO":  "Advanced packaging equipment · Guidance disappointing · Small cap risk · Wait for stabilization",
    "GRAB":  "SE Asia super-app · Ride, food, finance · Growing profitability · Different theme from portfolio",
    "SONY":  "Image sensor monopoly (~50% global share) · TSMC JV for next-gen AI sensors · PlayStation AI (+$700M revenue) · Sony Music IP moat for AI licensing · Crunchyroll +25% subs · Trading at 52W lows · Underappreciated AI angle",
    "EOSE":  "Zinc battery storage · Pre-profitable · Burning cash · Very high debt · Avoid",
    "MCHP":  "Microcontrollers + analog ICs · 68% gross margin · ROE 42% · Dividend payer · Recovering",
    "MKSI":  "Semiconductor process control equipment · 48% gross margin · High debt 1.8x",
    "STRL":  "Data center site prep & construction · Low debt · ROE 28% · Record backlog",
    "OSS":   "Edge AI computing for defense · Tiny market cap = illiquid · 40% gross margin decent",
    "ASX":   "World's largest chip packaging · P/E 12x · Advanced packaging bottleneck play · Cheap vs AMKR",
    "IFNNY": "German semiconductor · Power semiconductors + automotive AI · European diversification",
    "OUST":  "LiDAR for defense drones · DOD certified · Earnings miss risk — wait for stabilization",
    "POET":  "🔴 Marvell order CANCELLED · SELL REMAINING into any strength · Score 35",
    "SMH":   "VanEck Semi ETF · 25 largest US-listed semiconductor companies · NVDA TSMC AVGO top holdings",
    "NXPI":  "Automotive + IoT + industrial semis · Car AI silicon growing · Tariff headwind from auto",
    "GFS":   "Specialty foundry for automotive/defense/IoT · CHIPS Act beneficiary · Low gross margin",
    "AXTI":  "Compound semiconductor substrates · InP for AI optical transceivers · Micro-cap risk",
    "AOSL":  "Power management ICs for computing/storage · Cheap P/E · Small cap · Slow growth",
    "SKYT":  "US-based specialty foundry · DoD trusted fab · CHIPS Act beneficiary · Pre-profitable",
    "CAMT":  "Israeli inspection/metrology · HBM + CoWoS demand driver · Low debt · PEG undervalued",
    "APP":   "PEG ~0.55 · 73% revenue growth · 72% gross margin · ROE 80% · Mobile AI monetization → e-commerce",
    "CRWV":  "AI cloud GPU rental · NVDA-backed · Microsoft $10B contract · IPO Mar 2025 · High debt build-out",
    "DELL":  "AI server revenue surging ISG +35% YoY · Low gross margin · Very high debt from Vivint/EMC",
    "ORCL":  "OCI cloud +48% YoY · AI GPU cluster · 72% gross margin · Very high debt 8.5x",
    "HPE":   "AI server + networking + storage · GreenLake growing · P/E 10x cheap · Slow 7% growth",
    "GLW":   "Optical fiber for AI data center interconnects · Springboard plan targets $4B+ earnings",
    "CIEN":  "Optical networking for AI backbone · WaveLogic 6 competitive · Lumpy order cadence",
    "APH":   "Connectors for AI data centers + defense · Berkshire holding · Steady 20% growth",
    "QBTS":  "Quantum annealing · Real government/enterprise revenue · Pre-profitable · High cash burn",
    "ARQQ":  "Quantum-safe encryption SaaS · SPAC origin · Execution risk · Very small cap",
    "SERV":  "Sidewalk delivery robots · NVDA strategic investment · Pre-revenue scale · High burn",
    "RCAT":  "Military drones · DoD Black Widow procurement · +120% revenue · Defense drone demand",
    "RKLB":  "Small satellite launch + spacecraft · Neutron rocket · NRO classified contracts · Real execution",
    "VWAV":  "Defense logistics + base operations · US DoD contractor · Very low gross margin",
    "NXE":   "Athabasca Basin uranium · Rook I = highest-grade deposit globally · Under construction",
    "UEC":   "US uranium producer · Wyoming/Texas ISR · Zero debt · Leveraged to uranium price",
    "LEU":   "Only US HALEU enricher for advanced reactors · National security asset · $850M cap · PEG ~0.55",
    "COPX":  "Global copper miner exposure · AI data center wiring + EV battery demand · China stimulus",
    "ABX":   "World's 2nd largest gold miner · Low debt · Operational issues in Africa/Pakistan",
    "AEM":   "Best-in-class gold miner · Canada/Finland/Australia = lowest geopolitical risk · Growing dividend",
    "KGC":   "Mid-tier gold miner · Americas/West Africa · Cheapest P/E in gold majors",
    "MP":    "Only US rare earth miner · Apple $500M magnet supply deal · China export ban = strategic asset",
    "TMC":   "Deep sea polymetallic nodule mining · ISA license pending · High environmental opposition",
    "WCP":   "Canadian oil & gas · High dividend yield ~8% · Oil price dependent · CAD currency exposure",
    "APLD":  "Pivoting from crypto to AI HPC data centers · Samsung deal · High debt · High short interest",
    "CIFR":  "Pure Bitcoin miner · No AI pivot unlike peers · High short interest · BTC price speculation",
    "WULF":  "Nuclear-powered Bitcoin mining · Lake Mariner AI HPC pivot · Green energy thesis",
    "IREN":  "Bitcoin mining + AI HPC · NVDA H100 cluster · Cleanest energy footprint · 180%+ rev growth",
    "CRML":  "Critical metals royalty · Micro-cap · Speculative early-stage · African assets · Avoid",
    "USAR":  "Micro-cap real estate · Very illiquid · No clear AI/tech thesis · Verify relevance",
    "WWR":   "Battery-grade graphite · Kellyton Alabama plant · Pre-revenue · High dilution risk",
    "OKLL":  "⚠️ Verify ticker — may be incorrectly listed · Very low liquidity · Cannot confirm business",
    "NUAI":  "Micro-cap AI · Unverified revenue · Very illiquid · OTC market · No institutional coverage",
    "BBAI":  "AI analytics for defense/intelligence · DoD contracts · Pre-profitable · SPAC origin",
    "RXRX":  "NVDA invested $50M · AI drug discovery · 65% gross margin · Long payoff horizon",
    "LAES":  "Semiconductor security chips · Post-quantum cryptography · WISeKey spinoff · Micro-cap",
    "EME":   "Electrical/mechanical construction for data centers · Record backlog · Low debt 0.2x · ROE 32%",
    "ETN":   "Power management for AI data centers · $10B+ order backlog · BofA favorite · Demand > supply",
    "PWR":   "Electric grid + data center site construction · Record backlog $30B+ · AI grid expansion",
    "JBL":   "Electronics manufacturing services · Apple + AI server supply chain · P/E 12x cheap",
    "FIX":   "HVAC/mechanical for data centers · AI cooling demand · Low debt · ROE 30% solid",
    "BW":    "Nuclear/energy technology · High debt 3.5x = financial stress · SMR exposure but early",
    "QQQ":   "Top 100 non-financial NASDAQ · NVDA MSFT AAPL AMZN META top holdings · Benchmark",
    "SPY":   "500 largest US companies · Market benchmark · Portfolio hedge / cash parking",
    "TXN":   "Analog duopoly with ADI · 65% gross margin · Dividend aristocrat · Free cash flow machine",
    "CEG":   "Only pure-play nuclear stock · Microsoft 20-year PPA · Three Mile Island restarted · Score 85",
    "VST":   "Nuclear + gas power · Energy Harbor acquisition adds 4 nuclear plants · PEG ~0.72 undervalued",
    "NRG":   "Power generation + retail electricity · AI data center supply contracts · P/E 12x cheap",
    "FCEL":  "Direct BE competitor · Revenue declining · Massive cash burn · High dilution risk · AVOID",
    "PLUG":  "Hydrogen fuel cells · Going concern warning 2023 · DOE loan conditional · AVOID",
    "CLNE":  "Natural gas + renewable fueling stations · Amazon/BP backed · Pre-profitability transition",
    "ERIC":  "Direct Nokia competitor · 5G RAN equipment · US DoD contracts · No NVDA catalyst",
    "INFN":  "⚠️ Nokia acquiring Infinera at ~$6.65/share · Arbitrage play only if deal still open",
    "CALX":  "Cloud + software for broadband providers · 60% gross margin SaaS-like · Revenue growth stalled",
    "ADTN":  "Access networking equipment · Revenue declining · No clear AI catalyst · AVOID",
    "COMM":  "Network infrastructure · $9B+ debt = near-bankruptcy risk · Revenue declining · AVOID",
    "VIAV":  "Q3 Revenue +42.8% · Op margin 21% · Q4 guided $0.29-0.31 vs $0.23 expected · Already beat",
    "NVT":   "Electrical enclosures for data centers · +21-23% organic growth guided · Cheaper VRT alternative",
    "ARM":   "96% gross margin = highest in list · Every AI chip pays ARM royalties · Royalty model scales infinitely",
    "QCOM":  "Cheapest quality semi by P/E · PEG ~0.72 undervalued · AI PC Snapdragon X · Auto AI +35%",
    "IBM":   "$12.5B generative AI book of business · Watson x winning regulated enterprises · IBM Z revenue +67%",
    "MSFT":  "$94B AI CapEx 2026 · Azure AI +35% YoY · OpenAI exclusive · Copilot in 400M Office users",
    "ONTO":  "Oppenheimer top recovery play · Advanced packaging metrology · PEG ~0.49 · Zero debt",
    "ENTG":  "Specialty chemicals for every semiconductor fab · TSMC Arizona direct beneficiary",
    "GOOGL": "$175-185B CapEx 2026 · Gemini 3 leading LLM · TPU competitive with NVDA · P/E 22x cheapest hyperscaler",
    "LUMN":  "$13B AI contracts · Debt paid down · 5.2x debt ratio still high · 2-year story",
    "FRSH":  "SMB CRM/helpdesk · 82% gross margin · Revenue growth slowing · No AI infra thesis",
    "ASYS":  "Revenue declining FY26 · New CFO · Very small cap $270M · Avoid",
    "TMCR":  "Critical metals royalty streaming · 85% royalty margin · Zero debt · Tiny market cap",
    "DRAM":  "Memory sector ETF · Direct HBM/DRAM exposure · Micron/Samsung/SK Hynix exposure",
    "XNDU":  "Alpaca-listed ETF · Verify full name/strategy before sizing",
    "INFQ":  "Alpaca-listed ETF · Verify full name/strategy before sizing",
    "ALMU":  "Alpaca-listed ETF · Verify full name/strategy before sizing",
    "XE":    "Alpaca-listed ETF · Verify full name/strategy before sizing",
    "WYFI":  "Alpaca-listed ETF · Verify full name/strategy before sizing",
}

# ── Sector mapping ─────────────────────────────────────────────────────────────
SECTOR_MAP = {
    "NVDA":"AI Compute","TSM":"AI Foundry","LITE":"AI Optics","MU":"Memory",
    "LASR":"Defense","ALAB":"AI Connectivity","AVGO":"AI Chips","ANET":"Networking",
    "ASML":"Semicon Equip","CCJ":"Uranium","VRT":"AI Infra","CDNS":"EDA Software",
    "PLTR":"AI Software","AMD":"AI Compute","MRVL":"AI Chips","UUUU":"Uranium+REE",
    "SNPS":"EDA Software","AG":"Precious Metals","INTC":"AI CPU","NOK":"Networking",
    "SOXX":"ETF","ONDS":"Defense Drones","TER":"Semicon Equip","AMKR":"Chip Packaging",
    "CRDO":"Networking","FN":"Optical Mfg","LPTH":"Defense Optics","AAPL":"Consumer Tech","DRAM":"ETF",
    "GLD":"ETF/Macro","QTUM":"ETF","PLAB":"Chip Mfg","KEYS":"Test & Measure",
    "AAOI":"AI Optics","BKSY":"Defense Space","GEV":"Power","AEHR":"Chip Testing",
    "IONQ":"Quantum","SANM":"EMS","STX":"Storage","TTMI":"PCB Substrates",
    "TSEM":"Foundry","WDC":"Storage","BE":"AI Power Gen","LRCX":"Semicon Equip",
    "MRAM":"Memory",
    "COHR":"AI Optics","DOCN":"Cloud","CORZ":"AI Data Center","SNDK":"Storage",
    "FLNC":"Energy Storage","RIOT":"Bitcoin Mining","KLAC":"Semicon Equip",
    "ADI":"AI Chips","NBIS":"AI Cloud","FLEX":"AI Infra","HUT":"Bitcoin Mining",
    "IRDM":"Defense Space","ASTS":"Defense Space","CAT":"AI Infra","BELFA":"AI Infra",
    "VECO":"Semicon Equip","GRAB":"Consumer Tech","SONY":"Asia Tech","EOSE":"Energy Storage",
    "MCHP":"AI Chips","MKSI":"Semicon Equip","STRL":"AI Infra","OSS":"Defense",
    "ASX":"Chip Packaging","IFNNY":"AI Chips","OUST":"Defense","POET":"AI Optics",
    "SMH":"ETF","NXPI":"AI Chips","GFS":"Semicon Equip","AXTI":"Semicon Equip",
    "AOSL":"AI Chips","SKYT":"Semicon Equip","CAMT":"Semicon Equip","APP":"AI Software",
    "CRWV":"AI Cloud","DELL":"AI Infra","ORCL":"AI Software","HPE":"AI Infra",
    "GLW":"AI Infra","CIEN":"Networking","APH":"AI Infra","QBTS":"Quantum",
    "ARQQ":"Quantum","SERV":"Defense","RCAT":"Defense","RKLB":"Defense Space",
    "VWAV":"Defense","NXE":"Uranium+REE","UEC":"Uranium+REE","LEU":"Uranium+REE",
    "COPX":"ETF","ABX":"Precious Metals","AEM":"Precious Metals","KGC":"Precious Metals",
    "MP":"Critical Minerals","TMC":"Critical Minerals","WCP":"Energy","APLD":"AI Data Center",
    "CIFR":"Bitcoin Mining","WULF":"Bitcoin Mining","IREN":"AI Data Center",
    "CRML":"Critical Minerals","USAR":"Defense","WWR":"Critical Minerals","OKLL":"Defense",
    "NUAI":"AI Software","BBAI":"AI Software","RXRX":"AI Software","LAES":"Defense",
    "EME":"AI Infra","ETN":"AI Infra","PWR":"AI Infra","JBL":"AI Infra","FIX":"AI Infra",
    "BW":"Energy","QQQ":"ETF","SPY":"ETF","XNDU":"ETF","INFQ":"ETF","ALMU":"ETF",
    "XE":"ETF","WYFI":"ETF","TXN":"AI Chips","CEG":"AI Power Gen","VST":"AI Power Gen",
    "NRG":"AI Power Gen","FCEL":"AI Power Gen","PLUG":"AI Power Gen","CLNE":"AI Power Gen",
    "ERIC":"Telecom Equip","INFN":"Telecom Equip","CALX":"Telecom Equip",
    "ADTN":"Telecom Equip","COMM":"Telecom Equip","VIAV":"Test & Measure","NVT":"AI Infra",
    "ARM":"Chip Design","QCOM":"AI Chips","IBM":"AI Software","MSFT":"AI Software",
    "ONTO":"Semicon Equip","ENTG":"Semicon Equip","GOOGL":"AI Software","LUMN":"Fiber",
    "FRSH":"SaaS","ASYS":"Semicon Equip","TMCR":"Critical Minerals",
}

# ── Hard verdict overrides ─────────────────────────────────────────────────────
VERDICT_OVERRIDES = {
    "POET":"SELL","SNDK":"AVOID","FCEL":"AVOID","PLUG":"AVOID",
    "COMM":"AVOID","ADTN":"AVOID","EOSE":"AVOID","TMC":"AVOID",
    "USAR":"AVOID","WWR":"AVOID","OKLL":"AVOID","NUAI":"AVOID",
    "CRML":"AVOID","CIFR":"AVOID","ASYS":"AVOID","ARQQ":"AVOID",
    "BE":"WAIT","WDC":"WATCH","STX":"WATCH","AEHR":"CAUTION",
}

# ── Helpers ────────────────────────────────────────────────────────────────────
def _clean(v):
    if v is None: return None
    try:
        f = float(v)
        return None if (math.isnan(f) or math.isinf(f)) else f
    except: return None

def _pct(v):
    c = _clean(v)
    return round(c * 100, 1) if c is not None else None

def _fmt_price(p):
    if p is None: return "N/A"
    if p >= 1000: return f"~${p:,.0f}"
    if p >= 100:  return f"~${p:.2f}"
    return f"~${p:.2f}"

def _fmt_mc(mc):
    if mc is None: return "N/A"
    if mc >= 1e12: return f"${mc/1e12:.2f}T"
    if mc >= 1e9:  return f"${mc/1e9:.0f}B"
    if mc >= 1e6:  return f"${mc/1e6:.0f}M"
    return f"${mc:,.0f}"

def _val_trend_bonus(fpe_hist, peg_hist):
    """
    Returns a score bonus in [-8, +8] based on valuation compression/expansion
    over the last ~4 quarters.

    fpe_hist / peg_hist: lists of floats (or None), ordered oldest → newest.
    Compression (fwd P/E shrinking while price holds / rises) = bullish signal.
    """
    bonus = 0

    # ── Forward P/E compression ──────────────────────────────────────────────
    valid_fpe = [v for v in fpe_hist if v is not None and 0 < v < 300]
    if len(valid_fpe) >= 3:
        oldest = valid_fpe[0]
        newest = valid_fpe[-1]
        compression = (oldest - newest) / oldest   # positive = fwd P/E dropped
        if   compression >  0.45: bonus += 8   # fwd P/E crushed >45% — earnings exploding
        elif compression >  0.30: bonus += 5
        elif compression >  0.15: bonus += 2
        elif compression < -0.35: bonus -= 6   # P/E ballooned — getting very expensive
        elif compression < -0.15: bonus -= 3

    # ── PEG trend ────────────────────────────────────────────────────────────
    valid_peg = [v for v in peg_hist if v is not None and 0 < v < 20]
    if len(valid_peg) >= 3:
        hist_avg  = sum(valid_peg[:-1]) / len(valid_peg[:-1])
        curr_peg  = valid_peg[-1]
        if   curr_peg < hist_avg * 0.55: bonus += 3   # PEG well below own history
        elif curr_peg < hist_avg * 0.80: bonus += 1
        elif curr_peg > hist_avg * 1.60: bonus -= 3   # PEG expanding vs own history

    return max(-8, min(8, bonus))


def _score(pe, fpe, revG, gm, roe, de, si, fcfM, peg, val_bonus=0, extras=None):
    """
    Score 10–99.  extras dict carries new signals without bloating the signature.
    extras keys: upside_pct, rec_key, num_analysts, opM, netM, rev_accel,
                 insider_pct, inst_pct, net_cash_pct, earn_growth
    """
    s = 50

    # ── Revenue growth (highest weight) ──────────────────────────────────────
    if revG is not None:
        if revG > 60:   s += 22
        elif revG > 40: s += 16
        elif revG > 20: s += 10
        elif revG > 8:  s += 4
        elif revG < 0:  s -= 12

    # ── Gross margin ─────────────────────────────────────────────────────────
    if gm is not None:
        if gm > 70:   s += 18
        elif gm > 55: s += 12
        elif gm > 35: s += 5
        elif gm > 20: s += 2
        elif gm < 0:  s -= 12

    # ── Valuation: PEG preferred, fallback fwd P/E ───────────────────────────
    if peg is not None and peg > 0:
        if peg < 0.5:   s += 16
        elif peg < 1.0: s += 11
        elif peg < 1.5: s += 7
        elif peg < 2.5: s += 3
        elif peg > 5:   s -= 10
    elif fpe is not None and fpe > 0:
        if fpe < 15:   s += 11
        elif fpe < 25: s += 7
        elif fpe < 40: s += 2
        elif fpe > 80: s -= 8

    # ── ROE ──────────────────────────────────────────────────────────────────
    if roe is not None:
        if roe > 50:   s += 10
        elif roe > 25: s += 7
        elif roe > 10: s += 3
        elif roe < 0:  s -= 8

    # ── Debt/Equity ──────────────────────────────────────────────────────────
    if de is not None:
        if de < 0.2:   s += 8
        elif de < 0.5: s += 5
        elif de < 1.0: s += 2
        elif de > 3:   s -= 10
        elif de > 6:   s -= 18

    # ── Short interest penalty ───────────────────────────────────────────────
    if si is not None:
        if si > 20:   s -= 12
        elif si > 15: s -= 7
        elif si > 10: s -= 3
        elif si < 3:  s += 3

    # ── FCF quality ──────────────────────────────────────────────────────────
    if fcfM is not None:
        if fcfM > 30:    s += 8
        elif fcfM > 15:  s += 5
        elif fcfM > 0:   s += 2
        elif fcfM < -30: s -= 10
        elif fcfM < 0:   s -= 5

    # ── Historical valuation trend ───────────────────────────────────────────
    s += val_bonus

    # ── Extended signals (extras) ────────────────────────────────────────────
    if extras:
        # Analyst price target upside vs current price
        upside = extras.get("upside_pct")
        n_ana  = extras.get("num_analysts", 0) or 0
        if upside is not None and n_ana >= 3:
            if upside > 40:   s += 8
            elif upside > 25: s += 5
            elif upside > 10: s += 2
            elif upside < -15: s -= 6
            elif upside < -5:  s -= 3

        # Analyst consensus (Strong Buy / Buy / Hold / Sell)
        rec = (extras.get("rec_key") or "").lower()
        if rec in ("strong_buy",):  s += 4
        elif rec in ("buy",):       s += 2
        elif rec in ("sell", "underperform", "strong_sell"): s -= 4

        # Operating margin (business efficiency beyond gross margin)
        opM = extras.get("opM")
        if opM is not None:
            if opM > 35:   s += 5
            elif opM > 20: s += 3
            elif opM > 5:  s += 1
            elif opM < 0:  s -= 5

        # Revenue acceleration (quarterly trend: positive = accelerating growth)
        rev_accel = extras.get("rev_accel")
        if rev_accel is not None:
            if rev_accel > 15:   s += 5
            elif rev_accel > 5:  s += 2
            elif rev_accel < -15: s -= 5
            elif rev_accel < -5:  s -= 2

        # Earnings growth (YoY)
        eg = extras.get("earn_growth")
        if eg is not None:
            if eg > 60:   s += 5
            elif eg > 30: s += 3
            elif eg > 10: s += 1
            elif eg < -20: s -= 5
            elif eg < 0:   s -= 2

        # Insider ownership: skin in the game
        ins = extras.get("insider_pct")
        if ins is not None:
            if ins > 20: s += 4
            elif ins > 10: s += 2
            elif ins > 3:  s += 1

        # Net cash as % of market cap (de-risked balance sheet)
        nc = extras.get("net_cash_pct")
        if nc is not None:
            if nc > 25:   s += 4
            elif nc > 10: s += 2
            elif nc < -50: s -= 5
            elif nc < -25: s -= 3

        # Options market signal (put/call ratio + unusual activity)
        s += extras.get("opt_bonus", 0)

    return max(10, min(99, round(s)))

def _verdict(score):
    if score >= 88: return "STRONG BUY"
    if score >= 78: return "BUY"
    if score >= 65: return "HOLD"
    if score >= 50: return "WATCH"
    return "AVOID"

# ── Main fetch function ────────────────────────────────────────────────────────
def fetch(ticker_str):
    for attempt in range(3):
        try:
            t   = yf.Ticker(ticker_str)
            inf = t.info

            # ── Core pricing / valuation from info ───────────────────────────
            price   = _clean(inf.get("currentPrice") or inf.get("regularMarketPrice") or inf.get("navPrice"))
            pe      = _clean(inf.get("trailingPE"))
            fpe     = _clean(inf.get("forwardPE"))
            peg     = _clean(inf.get("pegRatio"))
            revG    = _pct(inf.get("revenueGrowth"))
            gm      = _pct(inf.get("grossMargins"))
            roe     = _pct(inf.get("returnOnEquity"))
            de_raw  = _clean(inf.get("debtToEquity"))
            de      = round(de_raw / 100, 2) if de_raw is not None else None
            si      = _pct(inf.get("shortPercentOfFloat"))
            mc_raw  = _clean(inf.get("marketCap"))
            mc      = _fmt_mc(mc_raw)

            # FCF margin
            fcf = _clean(inf.get("freeCashflow"))
            rev = _clean(inf.get("totalRevenue"))
            fcfM = round(fcf / rev * 100, 1) if fcf and rev and rev > 0 else None

            # ── Extended fundamentals from info ──────────────────────────────
            opM         = _pct(inf.get("operatingMargins"))
            netM        = _pct(inf.get("profitMargins"))
            ebitdaM     = _pct(inf.get("ebitdaMargins"))
            earn_growth = _pct(inf.get("earningsGrowth"))
            insider_pct = _pct(inf.get("heldPercentInsiders"))
            inst_pct    = _pct(inf.get("heldPercentInstitutions"))
            curr_ratio  = _clean(inf.get("currentRatio"))
            quick_ratio = _clean(inf.get("quickRatio"))
            book_val    = _clean(inf.get("bookValue"))
            ps_ratio    = _clean(inf.get("priceToSalesTrailing12Months"))
            pb_ratio    = _clean(inf.get("priceToBook"))
            ev_rev      = _clean(inf.get("enterpriseToRevenue"))
            ev_ebitda   = _clean(inf.get("enterpriseToEbitda"))
            beta        = _clean(inf.get("beta"))
            shares_out  = _clean(inf.get("sharesOutstanding"))
            description = (inf.get("longBusinessSummary") or "")[:500]

            # Net cash % of market cap
            total_cash  = _clean(inf.get("totalCash"))
            total_debt  = _clean(inf.get("totalDebt"))
            net_cash_pct = None
            if total_cash is not None and mc_raw and mc_raw > 0:
                net_cash = (total_cash or 0) - (total_debt or 0)
                net_cash_pct = round(net_cash / mc_raw * 100, 1)

            # ── Analyst targets from info ─────────────────────────────────────
            pt_mean   = _clean(inf.get("targetMeanPrice"))
            pt_high   = _clean(inf.get("targetHighPrice"))
            pt_low    = _clean(inf.get("targetLowPrice"))
            pt_median = _clean(inf.get("targetMedianPrice"))
            num_ana   = int(inf.get("numberOfAnalystOpinions") or 0)
            rec_key   = inf.get("recommendationKey") or ""
            upside_pct = None
            if pt_mean and price and price > 0:
                upside_pct = round((pt_mean - price) / price * 100, 1)

            # ── 1-year price return ───────────────────────────────────────────
            ret1y = "N/A"
            try:
                hist = t.history(period="1y", auto_adjust=True)
                if len(hist) >= 20:
                    r = (hist["Close"].iloc[-1] / hist["Close"].iloc[0] - 1) * 100
                    ret1y = ("+" if r >= 0 else "") + f"{r:.0f}%"
            except: pass

            # ── Next earnings date ────────────────────────────────────────────
            earn = "N/A"
            try:
                cal = t.calendar
                if cal is not None and "Earnings Date" in cal:
                    dates = cal["Earnings Date"]
                    if dates and len(dates) > 0:
                        d = dates[0]
                        if hasattr(d, "strftime"):
                            earn = d.strftime("%b %d")
            except: pass

            # ── EPS beat/miss from last quarter ──────────────────────────────
            beat = "—"
            try:
                eh = t.earnings_history
                if eh is not None and len(eh) > 0:
                    row  = eh.iloc[-1]
                    surp = _clean(row.get("surprisePercent"))
                    if surp is not None:
                        pct_s = surp * 100
                        if pct_s > 5:    beat = f"✅ Beat +{pct_s:.0f}%"
                        elif pct_s > 0:  beat = f"✅ Beat +{pct_s:.1f}%"
                        elif pct_s < -5: beat = f"❌ Missed {pct_s:.0f}%"
                        else:            beat = "~In line"
            except: pass

            # ── Quarterly revenue trend (last 4 quarters) ────────────────────
            q_rev_labels = []   # e.g. ["Q1 25","Q2 25","Q3 25","Q4 25"]
            q_rev_vals   = []   # revenue in $B
            q_rev_growth = []   # YoY % for each quarter
            rev_accel    = None # acceleration: latest QoQ growth delta
            try:
                qi = t.quarterly_income_stmt
                if qi is not None and not qi.empty:
                    rev_row = next(
                        (qi.loc[k] for k in qi.index
                         if "revenue" in str(k).lower() and "cost" not in str(k).lower()),
                        None
                    )
                    if rev_row is not None:
                        cols = sorted(rev_row.index, reverse=False)  # oldest first
                        for c in cols[-8:]:  # take up to 8 quarters
                            v = rev_row[c]
                            if v == v and v is not None:  # not NaN
                                try:
                                    lbl = f"Q{(c.month-1)//3+1} '{c.strftime('%y')}" if hasattr(c, "strftime") else str(c)[:7]
                                except: lbl = str(c)[:7]
                                q_rev_labels.append(lbl)
                                q_rev_vals.append(round(float(v) / 1e9, 2))  # in $B
                        # YoY growth per quarter (compare to 4 quarters ago)
                        for i in range(len(q_rev_vals)):
                            if i >= 4 and q_rev_vals[i-4] > 0:
                                g = round((q_rev_vals[i] / q_rev_vals[i-4] - 1) * 100, 1)
                                q_rev_growth.append(g)
                            else:
                                q_rev_growth.append(None)
                        # Revenue acceleration: latest YoY growth vs prior YoY growth
                        valid_g = [(i, g) for i, g in enumerate(q_rev_growth) if g is not None]
                        if len(valid_g) >= 2:
                            rev_accel = round(valid_g[-1][1] - valid_g[-2][1], 1)
            except Exception:
                pass

            # ── Quarterly EPS trend ───────────────────────────────────────────
            q_eps_labels = []
            q_eps_vals   = []
            try:
                qi = t.quarterly_income_stmt
                if qi is not None and not qi.empty:
                    eps_row = next(
                        (qi.loc[k] for k in qi.index
                         if "diluted" in str(k).lower() and "eps" in str(k).lower()),
                        None
                    )
                    if eps_row is None:
                        eps_row = next(
                            (qi.loc[k] for k in qi.index
                             if "net income" in str(k).lower()),
                            None
                        )
                    if eps_row is not None:
                        cols = sorted(eps_row.index, reverse=False)
                        for c in cols[-6:]:
                            v = eps_row[c]
                            if v == v and v is not None:
                                try:
                                    lbl = f"Q{(c.month-1)//3+1} '{c.strftime('%y')}" if hasattr(c, "strftime") else str(c)[:7]
                                except: lbl = str(c)[:7]
                                q_eps_labels.append(lbl)
                                q_eps_vals.append(round(float(v) / 1e6, 1))  # in $M (net income)
            except Exception:
                pass

            # ── Analyst upgrades/downgrades (last 5) ─────────────────────────
            upgrades = []
            try:
                ud = t.upgrades_downgrades
                if ud is not None and not ud.empty:
                    ud = ud.sort_index(ascending=False).head(5)
                    for idx, row in ud.iterrows():
                        try:
                            date_s = idx.strftime("%b %d") if hasattr(idx, "strftime") else str(idx)[:10]
                        except: date_s = str(idx)[:10]
                        firm  = str(row.get("Firm", ""))
                        grade = str(row.get("ToGrade", row.get("Action", "")))
                        upgrades.append({"d": date_s, "f": firm[:20], "g": grade[:20]})
            except Exception:
                pass

            # ── Institutional holders (top 5) ─────────────────────────────────
            inst_holders = []
            try:
                ih = t.institutional_holders
                if ih is not None and not ih.empty:
                    for _, row in ih.head(5).iterrows():
                        holder = str(row.get("Holder", row.iloc[0] if len(row) > 0 else ""))
                        pct    = _clean(row.get("pctHeld") or row.get("% Out"))
                        inst_holders.append({
                            "h": holder[:30],
                            "p": round(pct * 100, 1) if pct else None
                        })
            except Exception:
                pass

            # ── Historical valuation measures (quarterly snapshots) ───────────
            fpe_hist   = []
            peg_hist   = []
            val_labels = []
            val_bonus  = 0
            try:
                vm = t.get_valuation_measures()
                if vm is not None and not vm.empty:
                    vm = vm.sort_index()
                    col_fpe = next((c for c in vm.columns if "ForwardPE" in c or "forwardPE" in c), None)
                    col_peg = next((c for c in vm.columns if "PegRatio"  in c or "pegRatio"  in c), None)
                    for idx, row in vm.iterrows():
                        try:
                            label = idx.strftime("%b %y") if hasattr(idx, "strftime") else str(idx)[:7]
                        except: label = str(idx)[:7]
                        val_labels.append(label)
                        fpe_v = float(row[col_fpe]) if col_fpe and row[col_fpe] == row[col_fpe] else None
                        peg_v = float(row[col_peg]) if col_peg and row[col_peg] == row[col_peg] else None
                        fpe_hist.append(round(fpe_v, 2) if fpe_v else None)
                        peg_hist.append(round(peg_v, 2) if peg_v else None)
                    val_bonus = _val_trend_bonus(fpe_hist, peg_hist)
            except Exception:
                pass

            # ── Options data: put/call ratio, IV, unusual activity ───────────
            pc_oi      = None   # put/call open-interest ratio (when OI available)
            pc_vol_r   = None   # put/call volume ratio (primary signal — always available)
            atm_iv     = None   # ATM implied volatility % (annualized)
            opt_signal = ""     # "🔥 Unusual calls" | "⚠️ Unusual puts" | ""
            opt_bonus  = 0
            inst_conf  = 0      # 0-100 institutional flow confidence score
            inst_buyer = ""     # "🏛 Institutional" | "🔀 Mixed" | "👤 Retail" | ""
            try:
                from datetime import date as _date
                exps = t.options
                if exps:
                    # Use two expiries: nearest ≥7 days and next one out for OI
                    today = _date.today()
                    valid = [e for e in exps if (_date.fromisoformat(e) - today).days >= 7]
                    targets = valid[:2] if len(valid) >= 2 else (valid or [exps[0]])

                    all_calls = []
                    all_puts  = []
                    for exp in targets:
                        ch = t.option_chain(exp)
                        all_calls.append(ch.calls)
                        all_puts.append(ch.puts)

                    import pandas as _pd
                    calls_df = _pd.concat(all_calls, ignore_index=True)
                    puts_df  = _pd.concat(all_puts,  ignore_index=True)

                    # ── Put/call OI ratio (may be null if OI hasn't settled yet) ──
                    c_oi = float(calls_df["openInterest"].fillna(0).sum())
                    p_oi = float(puts_df["openInterest"].fillna(0).sum())
                    if c_oi > 100:   # only trust OI when there's meaningful data
                        pc_oi = round(p_oi / c_oi, 2)

                    # ── Put/call VOLUME ratio (primary — always populated same day) ──
                    c_vol = float(calls_df["volume"].fillna(0).sum())
                    p_vol = float(puts_df["volume"].fillna(0).sum())
                    if c_vol > 100:
                        pc_vol_r = round(p_vol / c_vol, 2)

                    # ── ATM implied volatility (annualized %) ──────────────────────
                    # yfinance returns IV as decimal (0.45 = 45%) — multiply by 100
                    if price and price > 0:
                        band = price * 0.05          # within 5% of spot
                        atm_c = calls_df[abs(calls_df["strike"] - price) < band]
                        atm_p = puts_df [abs(puts_df ["strike"] - price) < band]
                        ivs   = _pd.concat([
                            atm_c["impliedVolatility"],
                            atm_p["impliedVolatility"]
                        ]).dropna()
                        ivs = ivs[ivs > 0.15]   # only trust IV >15% annualized (filters near-expiry artefacts)
                        if len(ivs) > 0:
                            atm_iv = round(float(ivs.mean()) * 100, 1)

                    # ── Unusual activity: top-strike volume concentration ──────────
                    # A single strike capturing >15% of total call/put volume = unusual
                    if c_vol > 500:
                        top_call_pct = float(calls_df["volume"].fillna(0).max()) / c_vol
                        if top_call_pct > 0.15:
                            unc = float(calls_df["volume"].fillna(0).max())
                        else:
                            unc = 0
                    else:
                        unc = 0
                    if p_vol > 500:
                        top_put_pct  = float(puts_df["volume"].fillna(0).max()) / p_vol
                        if top_put_pct > 0.15:
                            unp = float(puts_df["volume"].fillna(0).max())
                        else:
                            unp = 0
                    else:
                        unp = 0
                    if unc > unp * 2 and unc > 2000:
                        opt_signal = "🔥 Unusual call buying"
                    elif unp > unc * 2 and unp > 2000:
                        opt_signal = "⚠️ Unusual put buying"

                    # ── Institutional flow analysis ──────────────────────────────────
                    # Heuristics: concentrated block trades → institutional
                    if c_vol > 200:
                        _inst_signals = []

                        # Signal 1: HHI on call volume by strike
                        # High HHI = volume concentrated in few strikes = institutions
                        _vol_by_strike = calls_df.groupby("strike")["volume"].sum().fillna(0)
                        _total_c = float(_vol_by_strike.sum())
                        if _total_c > 0:
                            _hhi = float(((_vol_by_strike / _total_c) ** 2).sum())
                            _inst_signals.append(min(100, _hhi * 200))  # 0.5 HHI → 100

                        # Signal 2: Deep ITM call % (strike < 80% of spot = synthetic long)
                        if price and price > 0:
                            _deep_mask = calls_df["strike"] < price * 0.80
                            _deep_vol  = float(calls_df.loc[_deep_mask, "volume"].fillna(0).sum())
                            _deep_pct  = _deep_vol / c_vol if c_vol > 0 else 0
                            _inst_signals.append(min(100, _deep_pct * 300))  # 33% → 100

                        # Signal 3: Largest single-strike block (>500 = institutional)
                        _max_block = float(calls_df["volume"].fillna(0).max())
                        _inst_signals.append(min(100, _max_block / 20))  # 2000 contracts → 100

                        # Signal 4: Top-5 strike volume concentration (>60% = concentrated)
                        if _total_c > 0:
                            _top5_pct = float(_vol_by_strike.nlargest(5).sum()) / _total_c
                            _inst_signals.append(min(100, max(0, (_top5_pct - 0.35) * 250)))

                        if _inst_signals:
                            inst_conf = round(sum(_inst_signals) / len(_inst_signals))
                            if inst_conf >= 55:
                                inst_buyer = "🏛 Institutional"
                            elif inst_conf >= 30:
                                inst_buyer = "🔀 Mixed"
                            else:
                                inst_buyer = "👤 Retail"

                    # ── Score bonus: use volume ratio as primary, OI as confirmation ─
                    # Primary signal: today's volume flow
                    pc_primary = pc_vol_r if pc_vol_r is not None else pc_oi
                    if pc_primary is not None:
                        if   pc_primary < 0.4:  opt_bonus += 4
                        elif pc_primary < 0.7:  opt_bonus += 2
                        elif pc_primary < 1.0:  opt_bonus += 1
                        elif pc_primary > 2.5:  opt_bonus -= 5
                        elif pc_primary > 1.5:  opt_bonus -= 3
                        elif pc_primary > 1.0:  opt_bonus -= 1
                    if opt_signal == "🔥 Unusual call buying": opt_bonus += 3
                    if opt_signal == "⚠️ Unusual put buying":  opt_bonus -= 3
                    # Institutional accumulation in calls = additional bullish signal
                    if inst_buyer == "🏛 Institutional" and (pc_primary or 1) < 1.0:
                        opt_bonus += 2
                    elif inst_buyer == "🔀 Mixed" and (pc_primary or 1) < 1.0:
                        opt_bonus += 1
                    opt_bonus = max(-6, min(6, opt_bonus))
            except Exception:
                pass   # options are optional — never block the fetch

            # ── Round display values ──────────────────────────────────────────
            if pe  is not None: pe  = round(pe,  1)
            if fpe is not None: fpe = round(fpe, 1)
            if peg is not None: peg = round(peg, 2)
            if gm  is not None: gm  = round(gm,  1)
            if roe is not None: roe = round(roe, 1)
            if si  is not None: si  = round(si,  1)
            if opM is not None: opM = round(opM, 1)
            if netM is not None: netM = round(netM, 1)
            if ebitdaM is not None: ebitdaM = round(ebitdaM, 1)
            if earn_growth is not None: earn_growth = round(earn_growth, 1)
            if insider_pct is not None: insider_pct = round(insider_pct, 1)
            if inst_pct    is not None: inst_pct    = round(inst_pct,    1)
            if curr_ratio  is not None: curr_ratio  = round(curr_ratio,  2)
            if quick_ratio is not None: quick_ratio = round(quick_ratio, 2)
            if beta        is not None: beta        = round(beta,        2)
            if ps_ratio    is not None: ps_ratio    = round(ps_ratio,    2)
            if pb_ratio    is not None: pb_ratio    = round(pb_ratio,    2)
            if ev_rev      is not None: ev_rev      = round(ev_rev,      2)
            if ev_ebitda   is not None: ev_ebitda   = round(ev_ebitda,   2)

            extras = {
                "upside_pct":   upside_pct,
                "rec_key":      rec_key,
                "num_analysts": num_ana,
                "opM":          opM,
                "netM":         netM,
                "rev_accel":    rev_accel,
                "earn_growth":  earn_growth,
                "insider_pct":  insider_pct,
                "net_cash_pct": net_cash_pct,
                "opt_bonus":    opt_bonus,
            }

            score   = _score(pe, fpe, revG, gm, roe, de, si, fcfM, peg, val_bonus, extras)
            verdict = VERDICT_OVERRIDES.get(ticker_str) or _verdict(score)
            name    = inf.get("shortName") or inf.get("longName") or ticker_str
            sector  = SECTOR_MAP.get(ticker_str, inf.get("sector", "Other"))
            note    = NOTES.get(ticker_str, "")

            return {
                # Core
                "t": ticker_str, "n": name, "s": sector,
                "p": _fmt_price(price), "mc": mc,
                "pe": pe, "fpe": fpe, "peg": peg,
                "revG": revG, "gm": gm, "roe": roe, "de": de,
                "si": si, "fcfM": fcfM,
                "ret1y": ret1y, "earn": earn, "beat": beat,
                "score": score, "v": verdict, "note": note,
                # Extended fundamentals
                "opM": opM, "netM": netM, "ebitdaM": ebitdaM,
                "earnG": earn_growth,
                "insiderPct": insider_pct, "instPct": inst_pct,
                "currRatio": curr_ratio, "quickRatio": quick_ratio,
                "beta": beta, "ps": ps_ratio, "pb": pb_ratio,
                "evRev": ev_rev, "evEbitda": ev_ebitda,
                "netCashPct": net_cash_pct,
                "desc": description,
                # Analyst
                "ptMean": round(pt_mean, 2) if pt_mean else None,
                "ptHigh": round(pt_high, 2) if pt_high else None,
                "ptLow":  round(pt_low,  2) if pt_low  else None,
                "upside": upside_pct,
                "numAna": num_ana,
                "recKey": rec_key,
                "upgrades": upgrades,
                # Quarterly trends
                "qRevL": q_rev_labels, "qRevV": q_rev_vals, "qRevG": q_rev_growth,
                "qEpsL": q_eps_labels, "qEpsV": q_eps_vals,
                "revAccel": rev_accel,
                # Institutional
                "instHolders": inst_holders,
                # Historical valuation
                "val_labels": val_labels, "fpe_hist": fpe_hist,
                "peg_hist": peg_hist, "val_bonus": val_bonus,
                # Options
                "pcOI": pc_oi, "pcVol": pc_vol_r,
                "atmIV": atm_iv, "optSignal": opt_signal,
                "optBonus": opt_bonus,
                "instConf": inst_conf, "instBuyer": inst_buyer,
            }

        except Exception as e:
            err = str(e)
            if "429" in err or "Too Many Requests" in err:
                print(f" ⏳ 429 — waiting {RETRY_DELAY}s...", end="", flush=True)
                time.sleep(RETRY_DELAY)
            else:
                print(f" ⚠️  {e}", end="")
                break
    return None

# ── News fetcher ───────────────────────────────────────────────────────────────
def fetch_news(ticker_str, max_headlines=4):
    """Fetch recent news headlines for a ticker via yfinance."""
    try:
        items = yf.Ticker(ticker_str).news or []
        headlines = []
        for item in items[:max_headlines]:
            # yfinance ≥ 0.2.x nests title under content dict
            title = (item.get("title")
                     or item.get("content", {}).get("title")
                     or "")
            if title:
                headlines.append(title.strip())
        return headlines
    except Exception:
        return []


# ── Mistral batch enrichment ───────────────────────────────────────────────────
MISTRAL_BATCH = 6   # stocks per Mistral call

def mistral_enrich(results):
    """
    Calls Mistral in batches of MISTRAL_BATCH stocks.
    For each stock it sends: base metrics + top-3 news headlines.
    Returns dict  { ticker: {"adj": int, "insight": str} }
    where adj is in [-15, +15] and gets added to the base score.
    """
    api_key = os.getenv("MISTRAL_API_KEY", "")
    if not api_key:
        print("  ⚠️  MISTRAL_API_KEY not set — skipping AI enrichment")
        return {}

    try:
        from mistralai import Mistral
    except ImportError:
        print("  ⚠️  mistralai package not installed — skipping AI enrichment")
        return {}

    client = Mistral(api_key=api_key)
    model  = os.getenv("MISTRAL_MODEL", "mistral-small-latest")

    # Only enrich stocks that have real fundamentals (skip bare ETFs, sub-30 scores)
    to_enrich = [r for r in results
                 if r["score"] >= 30
                 and r["gm"] is not None          # ETFs have no gross margin
                 and r["v"] not in ("SELL",)]     # no point enriching sells

    print(f"\n{'─'*60}")
    print(f"  🤖  Mistral AI enrichment  ({model})")
    print(f"  Enriching {len(to_enrich)} stocks in batches of {MISTRAL_BATCH}")
    print(f"{'─'*60}")

    # ── Step 1: fetch news headlines for every stock ──────────────────────────
    print("  📰  Fetching news headlines ...", flush=True)
    news_map = {}
    for r in to_enrich:
        news_map[r["t"]] = fetch_news(r["t"])
        time.sleep(0.25)
    print(f"  Done — {sum(bool(v) for v in news_map.values())} tickers had headlines\n")

    enrichment = {}
    batches = [to_enrich[i:i+MISTRAL_BATCH]
               for i in range(0, len(to_enrich), MISTRAL_BATCH)]

    system_prompt = (
        "You are a quantitative equity analyst. "
        "Analyse the provided news headlines and fundamentals for each stock "
        "and return ONLY a valid JSON object — no markdown, no extra text."
    )

    for idx, batch in enumerate(batches):
        tickers_str = ", ".join(r["t"] for r in batch)
        print(f"  [{idx+1:2}/{len(batches)}] {tickers_str}", end=" ... ", flush=True)

        # Build the per-stock block
        blocks = []
        for r in batch:
            headlines = news_map.get(r["t"], [])
            news_str  = (" | ".join(f'"{h}"' for h in headlines[:3])
                         if headlines else "No recent news available")
            meta = (f"score={r['score']} rev_growth={r['revG']}% "
                    f"gross_margin={r['gm']}% roe={r['roe']}% "
                    f"peg={r['peg']} verdict={r['v']}")
            blocks.append(
                f"{r['t']} — {r['n'][:35]}\n"
                f"  Fundamentals : {meta}\n"
                f"  Recent news  : {news_str}"
            )

        user_prompt = f"""For each stock below, evaluate the news and fundamentals and provide:
  score_adj  — integer from -15 to +15
               +10 to +15 : major earnings beat, raised guidance, big contract win, M&A premium offer
               +5  to +9  : analyst upgrade, positive product launch, strong sector tailwind
               +1  to +4  : mildly positive news, in-line results
               0           : neutral / no meaningful news
               -1  to -4  : minor caution, soft guidance, analyst downgrade
               -5  to -9  : earnings miss, revenue cut, significant insider selling
               -10 to -15 : going concern, major contract loss, regulatory action, fraud

  insight    — one sentence ≤ 120 chars: the single most important news catalyst or risk right now

Respond ONLY with this JSON structure (replace TICKER with actual ticker symbols):
{{"TICKER": {{"score_adj": 0, "insight": "..."}}, ...}}

Stocks:
{'=' * 55}
{chr(10).join(blocks)}
"""

        try:
            from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

            def _call():
                return client.chat.complete(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user",   "content": user_prompt},
                    ],
                    temperature=0.1,
                    max_tokens=900,
                )

            with ThreadPoolExecutor(max_workers=1) as ex:
                future   = ex.submit(_call)
                response = future.result(timeout=45)

            raw = response.choices[0].message.content.strip()
            # Strip markdown fences if Mistral wraps in ```json ... ```
            raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
            raw = re.sub(r"\s*```$",          "", raw, flags=re.MULTILINE)

            batch_result = json.loads(raw)

            count = 0
            for ticker, data in batch_result.items():
                adj     = max(-15, min(15, int(data.get("score_adj", 0))))
                insight = str(data.get("insight", "")).strip()[:150]
                enrichment[ticker] = {"adj": adj, "insight": insight}
                count += 1

            print(f"✅  ({count} parsed)")

        except json.JSONDecodeError as e:
            print(f"⚠️  JSON error: {e}")
        except FuturesTimeout:
            print(f"⏱️  Timeout (45s)")
        except Exception as e:
            print(f"❌  {e}")

        time.sleep(1.0)   # rate-limit between Mistral calls

    enriched = sum(1 for v in enrichment.values() if v["adj"] != 0)
    print(f"\n  🤖 AI enrichment done — {len(enrichment)} stocks processed, "
          f"{enriched} scores adjusted\n")
    return enrichment


# ── JS array serialiser ────────────────────────────────────────────────────────
def to_js(stocks):
    def jv(v):
        if v is None:                    return "null"
        if isinstance(v, bool):          return "true" if v else "false"
        if isinstance(v, str):           return json.dumps(v)
        if isinstance(v, (list, dict)):  return json.dumps(v)   # handles None→null inside arrays
        return str(v)

    lines = ["const stocks = ["]
    for s in stocks:
        lines.append(
            f'  {{t:{jv(s["t"])},n:{jv(s["n"])},s:{jv(s["s"])},'
            f'pe:{jv(s["pe"])},fpe:{jv(s["fpe"])},revG:{jv(s["revG"])},'
            f'gm:{jv(s["gm"])},roe:{jv(s["roe"])},de:{jv(s["de"])},'
            f'beat:{jv(s["beat"])},score:{jv(s["score"])},v:{jv(s["v"])},'
            f'p:{jv(s["p"])},mc:{jv(s["mc"])},ret1y:{jv(s["ret1y"])},'
            f'peg:{jv(s["peg"])},fcfM:{jv(s["fcfM"])},si:{jv(s["si"])},'
            f'earn:{jv(s["earn"])},note:{jv(s["note"])},'
            f'ai_adj:{jv(s.get("ai_adj",0))},ai_note:{jv(s.get("ai_note",""))},'
            # Extended fundamentals
            f'opM:{jv(s.get("opM"))},netM:{jv(s.get("netM"))},ebitdaM:{jv(s.get("ebitdaM"))},'
            f'earnG:{jv(s.get("earnG"))},insiderPct:{jv(s.get("insiderPct"))},'
            f'instPct:{jv(s.get("instPct"))},currRatio:{jv(s.get("currRatio"))},'
            f'quickRatio:{jv(s.get("quickRatio"))},beta:{jv(s.get("beta"))},'
            f'ps:{jv(s.get("ps"))},pb:{jv(s.get("pb"))},'
            f'evRev:{jv(s.get("evRev"))},evEbitda:{jv(s.get("evEbitda"))},'
            f'netCashPct:{jv(s.get("netCashPct"))},desc:{jv(s.get("desc",""))},'
            # Analyst
            f'ptMean:{jv(s.get("ptMean"))},ptHigh:{jv(s.get("ptHigh"))},'
            f'ptLow:{jv(s.get("ptLow"))},upside:{jv(s.get("upside"))},'
            f'numAna:{jv(s.get("numAna",0))},recKey:{jv(s.get("recKey",""))},'
            f'upgrades:{jv(s.get("upgrades",[]))},'
            # Quarterly trends
            f'qRevL:{jv(s.get("qRevL",[]))},qRevV:{jv(s.get("qRevV",[]))},'
            f'qRevG:{jv(s.get("qRevG",[]))},qEpsL:{jv(s.get("qEpsL",[]))},'
            f'qEpsV:{jv(s.get("qEpsV",[]))},revAccel:{jv(s.get("revAccel"))},'
            f'instHolders:{jv(s.get("instHolders",[]))},'
            # Historical valuation
            f'val_labels:{jv(s.get("val_labels",[]))},fpe_hist:{jv(s.get("fpe_hist",[]))},'
            f'peg_hist:{jv(s.get("peg_hist",[]))},val_bonus:{jv(s.get("val_bonus",0))},'
            f'pcOI:{jv(s.get("pcOI"))},pcVol:{jv(s.get("pcVol"))},'
            f'atmIV:{jv(s.get("atmIV"))},optSignal:{jv(s.get("optSignal",""))},'
            f'optBonus:{jv(s.get("optBonus",0))},'
            f'instConf:{jv(s.get("instConf",0))},instBuyer:{jv(s.get("instBuyer",""))}}},',
        )
    lines.append("];")
    return "\n".join(lines)


# ── Entry point ────────────────────────────────────────────────────────────────
def main():
    import argparse
    parser = argparse.ArgumentParser(description="Update stock_analysis_v6.html with live data")
    parser.add_argument("--ai", action="store_true",
                        help="Enrich scores with Mistral news-sentiment analysis (adds ~5 min)")
    args = parser.parse_args()

    n   = len(TICKERS)
    eta = n * (DELAY + 0.5) / 60 + (5 if args.ai else 0)
    ts  = datetime.now().strftime("%B %d, %Y %H:%M")

    print(f"\n{'─'*60}")
    print(f"  Live Stock Data Updater{'  +  Mistral AI' if args.ai else ''}")
    print(f"  {n} tickers  ·  ETA ~{eta:.0f} min  ·  {ts}")
    print(f"{'─'*60}\n")

    results, failed = [], []

    for i, ticker in enumerate(TICKERS, 1):
        print(f"  [{i:3}/{n}] {ticker:<8}", end=" ", flush=True)
        data = fetch(ticker)
        if data:
            # Seed AI fields so they always exist in the JS even without --ai
            data["ai_adj"]  = 0
            data["ai_note"] = ""
            # Seed all optional fields so to_js() never KeyErrors
            for _k, _v in [
                ("val_labels",[]),("fpe_hist",[]),("peg_hist",[]),("val_bonus",0),
                ("opM",None),("netM",None),("ebitdaM",None),("earnG",None),
                ("insiderPct",None),("instPct",None),("currRatio",None),
                ("quickRatio",None),("beta",None),("ps",None),("pb",None),
                ("evRev",None),("evEbitda",None),("netCashPct",None),("desc",""),
                ("ptMean",None),("ptHigh",None),("ptLow",None),("upside",None),
                ("numAna",0),("recKey",""),("upgrades",[]),
                ("qRevL",[]),("qRevV",[]),("qRevG",[]),
                ("qEpsL",[]),("qEpsV",[]),("revAccel",None),("instHolders",[]),
                ("pcOI",None),("pcVol",None),("atmIV",None),
                ("optSignal",""),("optBonus",0),
                ("instConf",0),("instBuyer",""),
            ]:
                data.setdefault(_k, _v)
            results.append(data)
            print(f"✅  {data['p']:<14} score={data['score']:<3}  {data['v']}")
        else:
            failed.append(ticker)
            print(f"❌  skipped")
        time.sleep(DELAY)

    print(f"\n{'─'*60}")
    print(f"  ✅ Fetched : {len(results)}")
    print(f"  ❌ Failed  : {len(failed)}{(' → ' + ', '.join(failed)) if failed else ''}")
    print(f"{'─'*60}\n")

    if not results:
        print("No data fetched — aborting.")
        sys.exit(1)

    # ── Mistral AI enrichment (optional) ──────────────────────────────────────
    if args.ai:
        enrichment = mistral_enrich(results)

        adjusted = 0
        for r in results:
            if r["t"] in enrichment:
                e       = enrichment[r["t"]]
                adj     = e["adj"]
                insight = e["insight"]
                r["ai_adj"]  = adj
                r["ai_note"] = insight

                if adj != 0:
                    old_score  = r["score"]
                    r["score"] = max(10, min(99, old_score + adj))
                    # Re-derive verdict unless it was manually overridden
                    if r["t"] not in VERDICT_OVERRIDES:
                        r["v"] = _verdict(r["score"])
                    direction = "▲" if adj > 0 else "▼"
                    print(f"  {direction} {r['t']:<6} score {old_score:>2} → {r['score']:>2} "
                          f"({adj:+d})  {insight[:55]}")
                    adjusted += 1

        print(f"\n  Scores adjusted by AI: {adjusted} / {len(results)}\n")

    # ── Write HTML ─────────────────────────────────────────────────────────────
    html = HTML_FILE.read_text(encoding="utf-8")

    new_js = to_js(results)
    html = re.sub(
        r"const stocks = \[.*?\];",
        lambda _: new_js,
        html,
        flags=re.DOTALL,
    )

    ai_badge = "  🤖 AI" if args.ai else ""
    html = re.sub(
        r"COMPREHENSIVE STOCK ANALYSIS · \d+ SYMBOLS[^<]*",
        f"COMPREHENSIVE STOCK ANALYSIS · {len(results)} SYMBOLS · LIVE {ts}{ai_badge}",
        html,
    )
    html = re.sub(
        r"\d+ Stocks · Multi-Metric Scorecard",
        f"{len(results)} Stocks · Multi-Metric Scorecard",
        html,
    )

    HTML_FILE.write_text(html, encoding="utf-8")
    print(f"  HTML written → {HTML_FILE.name}")
    print(f"  Open with:   open \"{HTML_FILE}\"\n")


if __name__ == "__main__":
    main()
