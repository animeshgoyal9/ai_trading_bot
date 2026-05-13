"""
Generate a rich HTML backtest report from the CSV produced by backtesting.py
Usage:  python3 generate_backtest_report.py [path/to/backtest_*.csv]
        If no path is given, uses the most-recently-modified CSV in logs/
"""

import sys, os, glob
import pandas as pd
import numpy as np
from datetime import datetime

# ── Locate CSV ────────────────────────────────────────────────────────────────
if len(sys.argv) > 1:
    csv_path = sys.argv[1]
else:
    files = sorted(glob.glob('logs/backtest_*.csv'), key=os.path.getmtime)
    if not files:
        print("No backtest CSV found in logs/"); sys.exit(1)
    csv_path = files[-1]

print(f"Loading {csv_path}...")
df = pd.read_csv(csv_path)
df['entry_date'] = pd.to_datetime(df['entry_date'])
df['exit_date']  = pd.to_datetime(df['exit_date'])

CAPITAL = 10_000   # matches backtesting.py default

# ── Per-symbol stats ──────────────────────────────────────────────────────────
rows = []
for sym, g in df.groupby('symbol'):
    wins     = g[g['pnl'] > 0]
    losses   = g[g['pnl'] <= 0]
    total_pnl = g['pnl'].sum()
    gp = wins['pnl'].sum()
    gl = abs(losses['pnl'].sum())
    pf = (gp / gl) if gl > 0 else float('inf')
    rows.append({
        'symbol':       sym,
        'trades':       len(g),
        'wins':         len(wins),
        'losses':       len(losses),
        'win_rate':     len(wins) / len(g) * 100,
        'total_pnl':    total_pnl,
        'return_pct':   (total_pnl / CAPITAL) * 100,
        'profit_factor': min(pf, 99.9),
        'avg_hold':     g['hold_days'].mean(),
        'avg_win':      wins['pnl'].mean() if len(wins) else 0,
        'avg_loss':     losses['pnl'].mean() if len(losses) else 0,
        'best_trade':   g['pnl'].max(),
        'worst_trade':  g['pnl'].min(),
    })

sym_df = pd.DataFrame(rows).sort_values('total_pnl', ascending=False).reset_index(drop=True)

# ── Overall stats ─────────────────────────────────────────────────────────────
total_pnl     = df['pnl'].sum()
total_return  = (total_pnl / CAPITAL) * 100
win_rate      = (df['pnl'] > 0).mean() * 100
total_trades  = len(df)
winning       = df[df['pnl'] > 0]
losing        = df[df['pnl'] <= 0]
gross_profit  = winning['pnl'].sum()
gross_loss    = abs(losing['pnl'].sum())
profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
avg_hold      = df['hold_days'].mean()
stop_loss_ct  = (df['reason'] == 'stop_loss').sum()
take_profit_ct = (df['reason'] == 'take_profit').sum()
signal_ct     = (df['reason'] == 'signal').sum()
eop_ct        = (df['reason'] == 'end_of_period').sum()

# ── Helpers for HTML coloring ─────────────────────────────────────────────────
def pnl_class(v):
    if v > 0:   return 'pos'
    if v < 0:   return 'neg'
    return 'neutral'

def pf_class(v):
    if v >= 1.5: return 'pos'
    if v >= 1.0: return 'neutral'
    return 'neg'

def wr_class(v):
    if v >= 55: return 'pos'
    if v >= 40: return 'neutral'
    return 'neg'

def fmt_pnl(v):
    return f'${v:+,.2f}'

def fmt_pct(v):
    return f'{v:+.1f}%'

def fmt_pf(v):
    return f'{v:.2f}' if v < 99 else '∞'

# ── Trade log (sorted by entry date) ─────────────────────────────────────────
trade_rows_html = ''
for _, t in df.sort_values('entry_date').iterrows():
    cls = 'win-row' if t['pnl'] > 0 else 'loss-row'
    trade_rows_html += f"""
      <tr class="{cls}">
        <td>{t['symbol']}</td>
        <td>{str(t['entry_date'])[:10]}</td>
        <td>{str(t['exit_date'])[:10]}</td>
        <td>${t['entry_price']:.2f}</td>
        <td>${t['exit_price']:.2f}</td>
        <td>{int(t['shares'])}</td>
        <td class="{pnl_class(t['pnl'])}">{fmt_pnl(t['pnl'])}</td>
        <td class="{pnl_class(t['pnl_pct'])}">{fmt_pct(t['pnl_pct'])}</td>
        <td>{int(t['hold_days'])}d</td>
        <td>{t['reason']}</td>
      </tr>"""

# ── Per-symbol table rows ─────────────────────────────────────────────────────
sym_rows_html = ''
for rank, r in sym_df.iterrows():
    medal = ['🥇','🥈','🥉'][rank] if rank < 3 else f'#{rank+1}'
    sym_rows_html += f"""
      <tr>
        <td class="rank-cell">{medal}</td>
        <td><strong>{r['symbol']}</strong></td>
        <td>{int(r['trades'])}</td>
        <td class="{wr_class(r['win_rate'])}">{r['win_rate']:.0f}%</td>
        <td class="{pnl_class(r['total_pnl'])}">{fmt_pnl(r['total_pnl'])}</td>
        <td class="{pnl_class(r['return_pct'])}">{fmt_pct(r['return_pct'])}</td>
        <td class="{pf_class(r['profit_factor'])}">{fmt_pf(r['profit_factor'])}</td>
        <td>{r['avg_hold']:.1f}d</td>
        <td class="pos">{fmt_pnl(r['avg_win'])}</td>
        <td class="neg">{fmt_pnl(r['avg_loss'])}</td>
        <td class="pos">{fmt_pnl(r['best_trade'])}</td>
        <td class="neg">{fmt_pnl(r['worst_trade'])}</td>
      </tr>"""

# ── Exit reason breakdown for chart ──────────────────────────────────────────
reason_data = df['reason'].value_counts()

# ── CSV date range ────────────────────────────────────────────────────────────
date_from = df['entry_date'].min().strftime('%Y-%m-%d')
date_to   = df['exit_date'].max().strftime('%Y-%m-%d')
now_str   = datetime.now().strftime('%Y-%m-%d %H:%M')

# ── Top 5 winners / losers ────────────────────────────────────────────────────
top5_winners = sym_df.head(5)
top5_losers  = sym_df.tail(5).iloc[::-1]

winner_cards = ''
for _, r in top5_winners.iterrows():
    winner_cards += f"""
      <div class="mini-card win-card">
        <div class="mc-symbol">{r['symbol']}</div>
        <div class="mc-pnl pos">{fmt_pnl(r['total_pnl'])}</div>
        <div class="mc-detail">{int(r['trades'])} trades · {r['win_rate']:.0f}% WR</div>
      </div>"""

loser_cards = ''
for _, r in top5_losers.iterrows():
    loser_cards += f"""
      <div class="mini-card loss-card">
        <div class="mc-symbol">{r['symbol']}</div>
        <div class="mc-pnl neg">{fmt_pnl(r['total_pnl'])}</div>
        <div class="mc-detail">{int(r['trades'])} trades · {r['win_rate']:.0f}% WR</div>
      </div>"""

# ── HTML ──────────────────────────────────────────────────────────────────────
html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>Backtest Report — 1 Year</title>
<style>
  :root {{
    --bg:     #0d1117;
    --card:   #161b22;
    --border: #30363d;
    --text:   #e6edf3;
    --muted:  #8b949e;
    --green:  #3fb950;
    --red:    #f85149;
    --yellow: #d29922;
    --blue:   #58a6ff;
    --purple: #bc8cff;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', monospace; font-size: 14px; }}

  header {{ background: linear-gradient(135deg, #161b22 0%, #1c2b3a 100%); border-bottom: 1px solid var(--border); padding: 24px 32px; }}
  header h1 {{ font-size: 22px; font-weight: 700; letter-spacing: 1px; color: var(--blue); }}
  header p  {{ color: var(--muted); margin-top: 4px; font-size: 12px; }}

  .container {{ max-width: 1400px; margin: 0 auto; padding: 24px 32px; }}

  /* KPI cards */
  .kpi-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 16px; margin-bottom: 32px; }}
  .kpi {{ background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 16px 18px; }}
  .kpi-label {{ color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: .8px; margin-bottom: 6px; }}
  .kpi-value {{ font-size: 22px; font-weight: 700; font-family: monospace; }}
  .kpi-sub   {{ color: var(--muted); font-size: 11px; margin-top: 4px; }}

  .pos     {{ color: var(--green) !important; }}
  .neg     {{ color: var(--red)   !important; }}
  .neutral {{ color: var(--yellow)!important; }}

  /* Section headers */
  .section-title {{ font-size: 14px; font-weight: 600; text-transform: uppercase;
                    letter-spacing: 1px; color: var(--blue); border-bottom: 1px solid var(--border);
                    padding-bottom: 8px; margin-bottom: 16px; margin-top: 32px; }}

  /* Mini cards */
  .card-row {{ display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 32px; }}
  .mini-card {{ background: var(--card); border: 1px solid var(--border); border-radius: 8px;
                padding: 12px 16px; min-width: 130px; }}
  .win-card  {{ border-color: #238636; }}
  .loss-card {{ border-color: #da3633; }}
  .mc-symbol {{ font-weight: 700; font-size: 16px; color: var(--text); }}
  .mc-pnl    {{ font-size: 14px; font-weight: 700; font-family: monospace; margin: 4px 0; }}
  .mc-detail {{ color: var(--muted); font-size: 11px; }}

  /* Exit reasons */
  .reasons-grid {{ display: grid; grid-template-columns: repeat(4,1fr); gap: 12px; margin-bottom: 32px; }}
  .reason-card  {{ background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 12px; text-align: center; }}
  .reason-count {{ font-size: 24px; font-weight: 700; }}
  .reason-label {{ color: var(--muted); font-size: 11px; margin-top: 4px; }}

  /* Tables */
  .table-wrap {{ overflow-x: auto; margin-bottom: 32px; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th {{ background: #1c2128; color: var(--muted); font-size: 11px; text-transform: uppercase;
        letter-spacing: .6px; padding: 10px 12px; border-bottom: 2px solid var(--border);
        text-align: right; white-space: nowrap; }}
  th:first-child, th:nth-child(2) {{ text-align: left; }}
  td {{ padding: 9px 12px; border-bottom: 1px solid #21262d; text-align: right;
        font-family: monospace; font-size: 13px; white-space: nowrap; }}
  td:first-child, td:nth-child(2) {{ text-align: left; font-family: -apple-system, sans-serif; }}
  tr:hover td {{ background: #1c2128; }}
  .win-row  {{ background: rgba(63,185,80,.04); }}
  .loss-row {{ background: rgba(248,81,73,.04); }}
  .rank-cell {{ text-align: center !important; font-size: 16px; }}

  /* Filter bar */
  .filter-bar {{ display: flex; gap: 12px; align-items: center; margin-bottom: 16px; flex-wrap: wrap; }}
  .filter-bar input {{ background: var(--card); border: 1px solid var(--border); color: var(--text);
                       padding: 8px 12px; border-radius: 6px; font-size: 13px; }}
  .filter-bar input:focus {{ outline: none; border-color: var(--blue); }}
  .btn {{ background: var(--card); border: 1px solid var(--border); color: var(--text);
          padding: 7px 14px; border-radius: 6px; cursor: pointer; font-size: 12px; }}
  .btn:hover {{ background: #1c2128; }}
  .btn.active {{ border-color: var(--blue); color: var(--blue); }}

  footer {{ text-align: center; color: var(--muted); font-size: 11px; padding: 32px; }}
</style>
</head>
<body>

<header>
  <h1>Trading Bot — 1-Year Backtest Report</h1>
  <p>Period: {date_from} → {date_to} &nbsp;|&nbsp; Strategy: Conservative (200MA filter, SMA crossover, RSI, MACD, ADX)
     &nbsp;|&nbsp; Capital per symbol: ${CAPITAL:,} &nbsp;|&nbsp; Generated: {now_str}</p>
</header>

<div class="container">

  <!-- ── KPI Row ── -->
  <div class="kpi-grid">
    <div class="kpi">
      <div class="kpi-label">Total P&amp;L</div>
      <div class="kpi-value {'pos' if total_pnl>=0 else 'neg'}">{fmt_pnl(total_pnl)}</div>
      <div class="kpi-sub">across all symbols</div>
    </div>
    <div class="kpi">
      <div class="kpi-label">Total Return</div>
      <div class="kpi-value {'pos' if total_return>=0 else 'neg'}">{fmt_pct(total_return)}</div>
      <div class="kpi-sub">on ${CAPITAL:,}/symbol</div>
    </div>
    <div class="kpi">
      <div class="kpi-label">Win Rate</div>
      <div class="kpi-value {wr_class(win_rate)}">{win_rate:.1f}%</div>
      <div class="kpi-sub">{int((df['pnl']>0).sum())} wins / {int((df['pnl']<=0).sum())} losses</div>
    </div>
    <div class="kpi">
      <div class="kpi-label">Total Trades</div>
      <div class="kpi-value">{total_trades}</div>
      <div class="kpi-sub">across {len(sym_df)} symbols</div>
    </div>
    <div class="kpi">
      <div class="kpi-label">Profit Factor</div>
      <div class="kpi-value {pf_class(profit_factor)}">{fmt_pf(profit_factor)}</div>
      <div class="kpi-sub">gross profit / gross loss</div>
    </div>
    <div class="kpi">
      <div class="kpi-label">Avg Hold Time</div>
      <div class="kpi-value">{avg_hold:.1f}d</div>
      <div class="kpi-sub">per trade</div>
    </div>
    <div class="kpi">
      <div class="kpi-label">Avg Win</div>
      <div class="kpi-value pos">{fmt_pnl(winning['pnl'].mean() if len(winning) else 0)}</div>
      <div class="kpi-sub">per winning trade</div>
    </div>
    <div class="kpi">
      <div class="kpi-label">Avg Loss</div>
      <div class="kpi-value neg">{fmt_pnl(losing['pnl'].mean() if len(losing) else 0)}</div>
      <div class="kpi-sub">per losing trade</div>
    </div>
  </div>

  <!-- ── Exit Reasons ── -->
  <div class="section-title">Exit Reasons</div>
  <div class="reasons-grid">
    <div class="reason-card">
      <div class="reason-count neg">{stop_loss_ct}</div>
      <div class="reason-label">Stop Loss (-5%)</div>
    </div>
    <div class="reason-card">
      <div class="reason-count pos">{take_profit_ct}</div>
      <div class="reason-label">Take Profit (+10%)</div>
    </div>
    <div class="reason-card">
      <div class="reason-count neutral">{signal_ct}</div>
      <div class="reason-label">Sell Signal</div>
    </div>
    <div class="reason-card">
      <div class="reason-count" style="color:var(--blue)">{eop_ct}</div>
      <div class="reason-label">End of Period</div>
    </div>
  </div>

  <!-- ── Top Winners / Losers ── -->
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:24px;margin-bottom:8px;">
    <div>
      <div class="section-title" style="margin-top:0">Top 5 Winners</div>
      <div class="card-row">{winner_cards}</div>
    </div>
    <div>
      <div class="section-title" style="margin-top:0">Top 5 Losers</div>
      <div class="card-row">{loser_cards}</div>
    </div>
  </div>

  <!-- ── Per-Symbol Table ── -->
  <div class="section-title">Per-Symbol Results ({len(sym_df)} symbols with trades)</div>
  <div class="filter-bar">
    <input type="text" id="symFilter" placeholder="Filter symbol..." oninput="filterSymTable()" style="width:160px"/>
    <button class="btn" onclick="sortSymTable('total_pnl')">Sort by P&amp;L</button>
    <button class="btn" onclick="sortSymTable('win_rate')">Sort by Win%</button>
    <button class="btn" onclick="sortSymTable('trades')">Sort by Trades</button>
    <button class="btn active" id="showAllBtn" onclick="toggleFilter('all')">All</button>
    <button class="btn" id="showWinBtn"  onclick="toggleFilter('win')">Winners only</button>
    <button class="btn" id="showLossBtn" onclick="toggleFilter('loss')">Losers only</button>
  </div>
  <div class="table-wrap">
    <table id="symTable">
      <thead>
        <tr>
          <th>#</th><th>Symbol</th><th>Trades</th><th>Win%</th>
          <th>Total P&amp;L</th><th>Return%</th><th>Profit Factor</th>
          <th>Avg Hold</th><th>Avg Win</th><th>Avg Loss</th>
          <th>Best Trade</th><th>Worst Trade</th>
        </tr>
      </thead>
      <tbody id="symBody">
        {sym_rows_html}
      </tbody>
    </table>
  </div>

  <!-- ── Full Trade Log ── -->
  <div class="section-title">Full Trade Log ({total_trades} trades)</div>
  <div class="filter-bar">
    <input type="text" id="tradeFilter" placeholder="Filter symbol..." oninput="filterTradeTable()" style="width:160px"/>
  </div>
  <div class="table-wrap">
    <table id="tradeTable">
      <thead>
        <tr>
          <th>Symbol</th><th>Entry</th><th>Exit</th>
          <th>Entry $</th><th>Exit $</th><th>Shares</th>
          <th>P&amp;L</th><th>P&amp;L%</th><th>Hold</th><th>Reason</th>
        </tr>
      </thead>
      <tbody id="tradeBody">
        {trade_rows_html}
      </tbody>
    </table>
  </div>

</div>

<footer>Generated by generate_backtest_report.py &nbsp;·&nbsp; {now_str}</footer>

<script>
function filterSymTable() {{
  const q = document.getElementById('symFilter').value.toLowerCase();
  document.querySelectorAll('#symBody tr').forEach(r => {{
    r.style.display = r.children[1].textContent.toLowerCase().includes(q) ? '' : 'none';
  }});
}}

function filterTradeTable() {{
  const q = document.getElementById('tradeFilter').value.toLowerCase();
  document.querySelectorAll('#tradeBody tr').forEach(r => {{
    r.style.display = r.children[0].textContent.toLowerCase().includes(q) ? '' : 'none';
  }});
}}

let _filterMode = 'all';
function toggleFilter(mode) {{
  _filterMode = mode;
  ['showAllBtn','showWinBtn','showLossBtn'].forEach(id => document.getElementById(id).classList.remove('active'));
  document.getElementById('show' + mode.charAt(0).toUpperCase() + mode.slice(1) + 'Btn')?.classList.add('active');
  if (mode === 'all') document.getElementById('showAllBtn').classList.add('active');
  document.querySelectorAll('#symBody tr').forEach(r => {{
    const pnl = parseFloat(r.children[4].textContent.replace(/[$,+]/g,''));
    if (mode === 'win')  r.style.display = pnl > 0 ? '' : 'none';
    else if (mode === 'loss') r.style.display = pnl <= 0 ? '' : 'none';
    else r.style.display = '';
  }});
}}

let _sortAsc = false;
function sortSymTable(col) {{
  const colMap = {{ total_pnl: 4, win_rate: 3, trades: 2 }};
  const colIdx = colMap[col];
  const body   = document.getElementById('symBody');
  const rows   = Array.from(body.querySelectorAll('tr'));
  _sortAsc = !_sortAsc;
  rows.sort((a, b) => {{
    const av = parseFloat(a.children[colIdx].textContent.replace(/[$,%+]/g,'')) || 0;
    const bv = parseFloat(b.children[colIdx].textContent.replace(/[$,%+]/g,'')) || 0;
    return _sortAsc ? av - bv : bv - av;
  }});
  rows.forEach(r => body.appendChild(r));
}}
</script>
</body>
</html>"""

# ── Write output ──────────────────────────────────────────────────────────────
out_path = csv_path.replace('.csv', '_report.html').replace('logs/', '')
with open(out_path, 'w') as f:
    f.write(html)

print(f"HTML report written to: {out_path}")
print(f"\nSummary:")
print(f"  Period      : {date_from} → {date_to}")
print(f"  Symbols     : {len(sym_df)} with trades")
print(f"  Total Trades: {total_trades}")
print(f"  Win Rate    : {win_rate:.1f}%")
print(f"  Total P&L   : {fmt_pnl(total_pnl)}")
print(f"  Profit Factor: {fmt_pf(profit_factor)}")
