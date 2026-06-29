from jugaad_trader.nse import NSELive
import yfinance as yf
import pytz
from datetime import datetime

IST = pytz.timezone("Asia/Kolkata")
_nse = None

def _get_nse():
    global _nse
    if _nse is None:
        _nse = NSELive()
    return _nse

def get_live_quote(symbol: str) -> dict | None:
    try:
        nse  = _get_nse()
        data = nse.stock_quote(symbol)

        price_info = data.get("priceInfo", {})
        trade_info = data.get("tradeInfo", {})
        intra      = price_info.get("intraDayHighLow", {})

        ltp        = float(price_info.get("lastPrice", 0))
        prev_close = float(price_info.get("previousClose", ltp))
        change_pct = round((ltp - prev_close) / prev_close * 100, 2) if prev_close else 0

        return {
            "symbol":     symbol,
            "ltp":        ltp,
            "open":       float(price_info.get("open", ltp)),
            "high":       float(intra.get("max", ltp)),
            "low":        float(intra.get("min", ltp)),
            "prev_close": prev_close,
            "change_pct": change_pct,
            "volume":     int(trade_info.get("totalTradedVolume", 0)),
            "vwap":       float(price_info.get("vwap", ltp)),
            "time":       datetime.now(IST).strftime("%H:%M:%S"),
        }
    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
        return None

def scan_with_live_price(symbol: str) -> dict | None:
    try:
        df = yf.download(symbol + ".NS", period="5d", interval="1m",
                         progress=False, auto_adjust=True)
        if df.empty or len(df) < 26:
            return None
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]

        live = get_live_quote(symbol)
        if live and live["ltp"] > 0:
            df.iloc[-1, df.columns.get_loc("Close")]  = live["ltp"]
            df.iloc[-1, df.columns.get_loc("High")]   = live["high"]
            df.iloc[-1, df.columns.get_loc("Low")]    = live["low"]
            df.iloc[-1, df.columns.get_loc("Volume")] = live["volume"]

        import pandas_ta as ta
        df.ta.ema(length=20, append=True)
        df.ta.rsi(length=14, append=True)
        df.ta.vwap(append=True)

        last    = df.iloc[-1]
        avg_vol = float(df["Volume"].rolling(20).mean().iloc[-1])
        close   = float(last["Close"])
        ema20   = float(last.get("EMA_20", close))
        rsi     = float(last.get("RSI_14", 50))
        vwap    = float(last.get("VWAP_D", close))
        volume  = float(last["Volume"])

        signals = {
            "ema":  close > ema20,
            "rsi":  rsi > 60,
            "vol":  avg_vol > 0 and volume > 2 * avg_vol,
            "vwap": close > vwap,
        }
        return {
            "symbol":     symbol,
            "price":      round(close, 2),
            "change_pct": live["change_pct"] if live else 0,
            "rsi":        round(rsi, 1),
            "ema20":      round(ema20, 2),
            "volume":     int(volume),
            "avg_volume": int(avg_vol),
            "vol_ratio":  round(volume / avg_vol, 1) if avg_vol else 0,
            "vwap":       round(vwap, 2),
            "signals":    ",".join(k for k, v in signals.items() if v),
            "all_pass":   all(signals.values()),
            "source":     "NSE live" if live else "yfinance delayed",
        }
    except Exception as e:
        print(f"Scan error {symbol}: {e}")
        return None

if __name__ == "__main__":
    print("Testing live quote...")
    q = get_live_quote("RELIANCE")
    if q:
        print(f"{q['symbol']}: Rs {q['ltp']} ({q['change_pct']:+.2f}%) | Vol: {q['volume']:,}")
    else:
        print("Quote failed.")

    print("\nTesting full scan...")
    r = scan_with_live_price("HDFCBANK")
    if r:
        print(f"Price: {r['price']} | RSI: {r['rsi']} | Vol: {r['vol_ratio']}x | Source: {r['source']}")