"""
NSE/BSE Stock Scanner Dashboard
Run: streamlit run dashboard.py
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
from datetime import datetime, timedelta
import pytz
import time
import sqlite3
import os
import threading

from watchlist import NIFTY_50, NIFTY_NEXT_50, ACTIVE_FNO, FULL_WATCHLIST, WATCHLIST_LABELS

# ── Page config ───────────────────────────────────────────────
IST = pytz.timezone("Asia/Kolkata")
DB_PATH = "scanner_hits.db"
TELEGRAM_TOKEN  = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

st.set_page_config(page_title="NSE/BSE Scanner", page_icon="📈",
                   layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
.green  { color: #16a34a; }
.red    { color: #dc2626; }
.badge-n50  { background:#dbeafe;color:#1e40af;padding:2px 8px;border-radius:12px;font-size:11px; }
.badge-nn50 { background:#dcfce7;color:#166534;padding:2px 8px;border-radius:12px;font-size:11px; }
.badge-fno  { background:#fef9c3;color:#854d0e;padding:2px 8px;border-radius:12px;font-size:11px; }
.chip-on  { display:inline-block;background:#ede9fe;color:#4c1d95;padding:2px 7px;border-radius:8px;font-size:11px;margin:1px; }
.chip-off { display:inline-block;background:#f1f5f9;color:#cbd5e1;padding:2px 7px;border-radius:8px;font-size:11px;margin:1px; }
</style>
""", unsafe_allow_html=True)

# ── Helpers ───────────────────────────────────────────────────
def is_market_open() -> bool:
    now = datetime.now(IST)
    if now.weekday() >= 5:
        return False
    o = now.replace(hour=9,  minute=15, second=0, microsecond=0)
    c = now.replace(hour=15, minute=30, second=0, microsecond=0)
    return o <= now <= c

def next_open() -> str:
    now = datetime.now(IST)
    for i in range(1, 8):
        d = now + timedelta(days=i)
        if d.weekday() < 5:
            return d.replace(hour=9, minute=15).strftime("%a %d %b, 9:15 AM IST")
    return "Next weekday"

# ── Database ──────────────────────────────────────────────────
def init_db():
    con = sqlite3.connect(DB_PATH)
    con.execute("""CREATE TABLE IF NOT EXISTS hits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT, price REAL, rsi REAL, vol_ratio REAL,
        signals TEXT, index_label TEXT, scanned_at TEXT)""")
    con.commit(); con.close()

def save_hit(row: dict):
    con = sqlite3.connect(DB_PATH)
    con.execute("INSERT INTO hits (symbol,price,rsi,vol_ratio,signals,index_label,scanned_at) VALUES (?,?,?,?,?,?,?)",
        (row["symbol"], row["price"], row["rsi"], row["vol_ratio"],
         row["signals"], row["index_label"], datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")))
    con.commit(); con.close()

def was_alerted(symbol: str, minutes=5) -> bool:
    con = sqlite3.connect(DB_PATH)
    cutoff = (datetime.now(IST) - timedelta(minutes=minutes)).strftime("%Y-%m-%d %H:%M:%S")
    cur = con.execute("SELECT 1 FROM hits WHERE symbol=? AND scanned_at>=? LIMIT 1", (symbol, cutoff))
    found = cur.fetchone() is not None
    con.close()
    return found

def load_today() -> pd.DataFrame:
    today = datetime.now(IST).strftime("%Y-%m-%d")
    con = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM hits WHERE scanned_at LIKE ? ORDER BY scanned_at DESC",
                           con, params=(f"{today}%",))
    con.close()
    return df

# ── Telegram ──────────────────────────────────────────────────
def send_telegram(hit: dict):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        import telegram
        bot = telegram.Bot(token=TELEGRAM_TOKEN)
        msg = (f"BREAKOUT: {hit['display']}\n"
               f"Price : Rs {hit['price']:,.2f} ({hit['change_pct']:+.2f}%)\n"
               f"RSI   : {hit['rsi']}\nVol   : {hit['vol_ratio']}x avg\n"
               f"Signals: {hit['signals'].upper()}\n"
               f"Time  : {datetime.now(IST).strftime('%H:%M IST')}")
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg)
    except Exception:
        pass

# ── Scanner ───────────────────────────────────────────────────
def scan_ticker(symbol: str) -> dict | None:
    try:
        df = yf.download(symbol, period="5d", interval="1m",
                         progress=False, auto_adjust=True)
        if df.empty or len(df) < 26:
            return None

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]

        needed = ["Open", "High", "Low", "Close", "Volume"]
        if not all(c in df.columns for c in needed):
            return None

        df = df[needed].copy().dropna()
        if len(df) < 26:
            return None

        df.ta.ema(length=20, append=True)
        df.ta.rsi(length=14, append=True)
        df.ta.vwap(append=True)

        last    = df.iloc[-1]
        avg_vol = float(df["Volume"].rolling(20).mean().iloc[-1])
        close   = float(last["Close"])
        ema20   = float(last["EMA_20"]) if "EMA_20" in df.columns else close
        rsi     = float(last["RSI_14"]) if "RSI_14" in df.columns else 50.0
        vwap    = float(last["VWAP_D"]) if "VWAP_D" in df.columns else close
        volume  = float(last["Volume"])
        prev    = float(df["Close"].iloc[-2]) if len(df) >= 2 else close
        chg     = round((close - prev) / prev * 100, 2) if prev else 0

        s = {
            "ema":  close > ema20,
            "vol":  avg_vol > 0 and volume > 2 * avg_vol,
            "rsi":  rsi > 60,
            "vwap": close > vwap,
        }
        return {
            "symbol":      symbol,
            "display":     symbol.replace(".NS","").replace(".BO",""),
            "price":       round(close, 2),
            "change_pct":  chg,
            "rsi":         round(rsi, 1),
            "ema20":       round(ema20, 2),
            "volume":      int(volume),
            "avg_volume":  int(avg_vol),
            "vol_ratio":   round(volume / avg_vol, 1) if avg_vol else 0,
            "vwap":        round(vwap, 2),
            "signals":     ",".join(k for k, v in s.items() if v),
            "all_pass":    all(s.values()),
            "index_label": WATCHLIST_LABELS.get(symbol, "Other"),
            "sig_ema":     s["ema"],
            "sig_vol":     s["vol"],
            "sig_rsi":     s["rsi"],
            "sig_vwap":    s["vwap"],
        }
    except Exception:
        return None

@st.cache_data(ttl=55, show_spinner=False)
def run_full_scan(symbols: tuple) -> list:
    results = []
    for sym in symbols:
        r = scan_ticker(sym)
        if r and isinstance(r, dict) and "price" in r:
            results.append(r)
    return results

# ── UI helpers ────────────────────────────────────────────────
def badge(label):
    cls = {"Nifty 50":"badge-n50","Nifty Next 50":"badge-nn50"}.get(label,"badge-fno")
    return f"<span class='{cls}'>{label}</span>"

def chips(sig_str):
    hits = set(sig_str.split(",")) if sig_str else set()
    labels = {"ema":"EMA20","rsi":"RSI>60","vol":"Vol 2x","vwap":"VWAP"}
    return "".join(f"<span class='{'chip-on' if k in hits else 'chip-off'}'>{v}</span>"
                   for k,v in labels.items())

def render_table(df_view, sort_col="change_pct", ascending=False, max_rows=30):
    if df_view.empty:
        st.info("No stocks match this filter right now.")
        return
    rows = ""
    for _, r in df_view.sort_values(sort_col, ascending=ascending).head(max_rows).iterrows():
        cls = "green" if r["change_pct"] >= 0 else "red"
        arrow = "▲" if r["change_pct"] >= 0 else "▼"
        rows += f"""<tr>
          <td><b>{r['display']}</b> {badge(r['index_label'])}</td>
          <td>Rs {r['price']:,.2f}</td>
          <td class='{cls}'>{arrow} {abs(r['change_pct']):.2f}%</td>
          <td>{r['rsi']}</td>
          <td>{r['vol_ratio']}x</td>
          <td>Rs {r['vwap']:,.2f}</td>
          <td>{chips(r['signals'])}</td>
        </tr>"""
    st.markdown(f"""
    <table style="width:100%;border-collapse:collapse;font-size:13px;">
      <thead><tr style="border-bottom:2px solid #e5e7eb;color:#6b7280;font-size:12px;">
        <th style="padding:8px 4px">Symbol</th><th style="padding:8px 4px">Price</th>
        <th style="padding:8px 4px">Change</th><th style="padding:8px 4px">RSI</th>
        <th style="padding:8px 4px">Vol</th><th style="padding:8px 4px">VWAP</th>
        <th style="padding:8px 4px">Signals</th>
      </tr></thead>
      <tbody>{rows}</tbody>
    </table>""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════
init_db()

with st.sidebar:
    st.markdown("## NSE/BSE Scanner")
    st.markdown("---")
    universe = st.multiselect("Watchlist universe",
        ["Nifty 50","Nifty Next 50","F&O"], default=["Nifty 50","F&O"])
    rsi_min  = st.slider("Min RSI", 50, 80, 60)
    vol_min  = st.slider("Min Volume multiplier", 1.0, 5.0, 2.0, step=0.5)
    req_all  = st.checkbox("Require ALL 4 signals", value=True)
    st.markdown("---")
    st.markdown("### Telegram alerts")
    tg_tok  = st.text_input("Bot token",  value=TELEGRAM_TOKEN,   type="password")
    tg_chat = st.text_input("Chat ID",    value=TELEGRAM_CHAT_ID)
    if tg_tok:  TELEGRAM_TOKEN   = tg_tok
    if tg_chat: TELEGRAM_CHAT_ID = tg_chat
    st.markdown("---")
    auto_refresh = st.checkbox("Auto-refresh (60s)", value=False)
    manual_scan  = st.button("Scan now", use_container_width=True, type="primary")
    st.markdown("---")
    st.caption("Market: 9:15–15:30 IST · Mon–Fri")

# ── Symbol list ───────────────────────────────────────────────
selected = []
if "Nifty 50"      in universe: selected += NIFTY_50
if "Nifty Next 50" in universe: selected += NIFTY_NEXT_50
if "F&O"           in universe: selected += ACTIVE_FNO
selected = list(dict.fromkeys(selected))

# ═══════════════════════════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════════════════════════
c1, c2 = st.columns([3, 1])
with c1:
    st.title("NSE/BSE Scanner Dashboard")
    st.caption(f"Scanning {len(selected)} stocks · Last refreshed: {datetime.now(IST).strftime('%H:%M:%S IST')}")
with c2:
    if is_market_open():
        st.success("Market OPEN")
    else:
        st.warning(f"Market CLOSED\nNext: {next_open()}")

st.markdown("---")

# ═══════════════════════════════════════════════════════════════
# SCAN
# ═══════════════════════════════════════════════════════════════
if manual_scan or auto_refresh:
    run_full_scan.clear()

with st.spinner(f"Scanning {len(selected)} stocks — please wait..."):
    # pass as tuple so st.cache_data can hash it
    raw = run_full_scan(tuple(selected))

if not raw:
    st.warning("No data returned. Check internet connection.")
    st.stop()

df_all = pd.DataFrame(raw)

# Apply filters
df_all["rsi_pass"] = df_all["rsi"]       > rsi_min
df_all["vol_pass"] = df_all["vol_ratio"] >= vol_min
df_all["all_pass"] = (df_all["sig_ema"] & df_all["rsi_pass"] &
                      df_all["vol_pass"] & df_all["sig_vwap"])

# ═══════════════════════════════════════════════════════════════
# METRICS
# ═══════════════════════════════════════════════════════════════
total     = len(df_all)
gainers   = int((df_all["change_pct"] > 0).sum())
losers    = int((df_all["change_pct"] < 0).sum())
breakouts = int(df_all["all_pass"].sum())
rsi_hot   = int(df_all["rsi_pass"].sum())
vol_spk   = int(df_all["vol_pass"].sum())

m1,m2,m3,m4,m5,m6 = st.columns(6)
m1.metric("Scanned",   total)
m2.metric("Gainers",   gainers,   delta=f"{round(gainers/total*100)}%" if total else "0%")
m3.metric("Losers",    losers,    delta=f"-{round(losers/total*100)}%" if total else "0%", delta_color="inverse")
m4.metric("Breakouts", breakouts, help="All 4 signals hit")
m5.metric(f"RSI>{rsi_min}", rsi_hot)
m6.metric(f"Vol≥{vol_min}x", vol_spk)

st.markdown("---")

# ═══════════════════════════════════════════════════════════════
# TABS
# ═══════════════════════════════════════════════════════════════
tab1,tab2,tab3,tab4,tab5,tab6 = st.tabs([
    f"🚨 Breakouts ({breakouts})",
    "📈 Top Gainers",
    "📉 Top Losers",
    "🔊 Volume Spikes",
    f"⚡ RSI Hot ({rsi_hot})",
    "📊 EMA Crossovers",
])

# ── Breakouts ─────────────────────────────────────────────────
with tab1:
    st.subheader(f"Breakout signals — all 4 conditions hit")
    df_bo = df_all[df_all["all_pass"]].copy()
    for _, row in df_bo.iterrows():
        if not was_alerted(row["symbol"]):
            save_hit(row.to_dict())
            threading.Thread(target=send_telegram, args=(row.to_dict(),), daemon=True).start()
    render_table(df_bo, sort_col="vol_ratio")
    st.caption("Price > EMA20 · RSI > threshold · Volume ≥ multiplier · Price > VWAP")

# ── Gainers ───────────────────────────────────────────────────
with tab2:
    st.subheader("Top gainers today")
    n = st.slider("Show top N", 5, 50, 20, key="gn")
    render_table(df_all[df_all["change_pct"] > 0], sort_col="change_pct", max_rows=n)

# ── Losers ────────────────────────────────────────────────────
with tab3:
    st.subheader("Top losers today")
    n = st.slider("Show top N", 5, 50, 20, key="ln")
    render_table(df_all[df_all["change_pct"] < 0], sort_col="change_pct",
                 ascending=True, max_rows=n)

# ── Volume spikes ─────────────────────────────────────────────
with tab4:
    st.subheader(f"Volume spikes ≥ {vol_min}x average")
    render_table(df_all[df_all["vol_pass"]], sort_col="vol_ratio", max_rows=40)

# ── RSI hot ───────────────────────────────────────────────────
with tab5:
    st.subheader(f"RSI > {rsi_min} — momentum building")
    df_rsi = df_all[df_all["rsi_pass"]].sort_values("rsi", ascending=False)
    if not df_rsi.empty:
        st.bar_chart(df_rsi.head(25).set_index("display")[["rsi"]], height=260)
    render_table(df_rsi, sort_col="rsi", max_rows=40)

# ── EMA crossovers ────────────────────────────────────────────
with tab6:
    st.subheader("Price above EMA20")
    df_ema = df_all[df_all["sig_ema"]].copy()
    ca, cb = st.columns(2)
    with ca:
        st.markdown("##### Gaining above EMA20")
        render_table(df_ema[df_ema["change_pct"] > 0], sort_col="change_pct", max_rows=20)
    with cb:
        st.markdown("##### Losing above EMA20 (watch for reversal)")
        render_table(df_ema[df_ema["change_pct"] <= 0], sort_col="change_pct",
                     ascending=True, max_rows=20)

# ── History ───────────────────────────────────────────────────
st.markdown("---")
with st.expander("Today's alert history"):
    hist = load_today()
    if hist.empty:
        st.info("No breakout alerts fired today yet.")
    else:
        st.dataframe(hist[["symbol","price","rsi","vol_ratio","signals","scanned_at"]],
                     use_container_width=True)
        st.caption(f"{len(hist)} alerts fired today.")

# ── Auto refresh ──────────────────────────────────────────────
if auto_refresh:
    time.sleep(60)
    st.rerun()