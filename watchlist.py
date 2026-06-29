"""
NSE/BSE Watchlist — Nifty 50 + Nifty Next 50 + Active F&O
All symbols use .NS suffix (NSE via yfinance)
For BSE, swap .NS → .BO
"""

NIFTY_50 = [
    "ADANIENT.NS",   "ADANIPORTS.NS", "APOLLOHOSP.NS", "ASIANPAINT.NS",
    "AXISBANK.NS",   "BAJAJ-AUTO.NS", "BAJAJFINSV.NS", "BAJFINANCE.NS",
    "BHARTIARTL.NS", "BPCL.NS",       "BRITANNIA.NS",  "CIPLA.NS",
    "COALINDIA.NS",  "DIVISLAB.NS",   "DRREDDY.NS",    "EICHERMOT.NS",
    "GRASIM.NS",     "HCLTECH.NS",    "HDFCBANK.NS",   "HDFCLIFE.NS",
    "HEROMOTOCO.NS", "HINDALCO.NS",   "HINDUNILVR.NS", "ICICIBANK.NS",
    "INDUSINDBK.NS", "INFY.NS",       "ITC.NS",        "JSWSTEEL.NS",
    "KOTAKBANK.NS",  "LT.NS",         "M&M.NS",        "MARUTI.NS",
    "NESTLEIND.NS",  "NTPC.NS",       "ONGC.NS",       "POWERGRID.NS",
    "RELIANCE.NS",   "SBILIFE.NS",    "SBIN.NS",       "SUNPHARMA.NS",
    "TATACONSUM.NS", "TATAMOTORS.NS", "TATASTEEL.NS",  "TCS.NS",
    "TECHM.NS",      "TITAN.NS",      "TRENT.NS",      "ULTRACEMCO.NS",
    "WIPRO.NS",      "ZOMATO.NS",
]

NIFTY_NEXT_50 = [
    "ABB.NS",        "AMBUJACEM.NS",  "AUROPHARMA.NS", "BANDHANBNK.NS",
    "BERGEPAINT.NS", "BOSCHLTD.NS",   "CANBK.NS",      "CHOLAFIN.NS",
    "COLPAL.NS",     "DABUR.NS",      "DLF.NS",        "GAIL.NS",
    "GODREJCP.NS",   "HAVELLS.NS",    "ICICIPRULI.NS", "IDFCFIRSTB.NS",
    "IGL.NS",        "INDHOTEL.NS",   "INDUSTOWER.NS", "IOC.NS",
    "IRCTC.NS",      "JINDALSTEL.NS", "LUPIN.NS",      "MARICO.NS",
    "MCDOWELL-N.NS", "MUTHOOTFIN.NS", "NAUKRI.NS",     "NMDC.NS",
    "OBEROIRLTY.NS", "OFSS.NS",       "PAGEIND.NS",    "PIDILITIND.NS",
    "PNB.NS",        "RECLTD.NS",     "SAIL.NS",       "SRF.NS",
    "TORNTPHARM.NS", "TVSMOTOR.NS",   "UBL.NS",        "VEDL.NS",
    "VOLTAS.NS",     "PERSISTENT.NS", "MPHASIS.NS",    "LTIM.NS",
    "POLYCAB.NS",    "ASHOKLEY.NS",   "ZEEL.NS",       "YESBANK.NS",
    "WHIRLPOOL.NS",  "IDEA.NS",
]

ACTIVE_FNO = [
    # Banking & Finance
    "FEDERALBNK.NS", "RBLBANK.NS",    "BANKBARODA.NS", "UNIONBANK.NS",
    "MANAPPURAM.NS", "BAJAJHLDNG.NS", "HDFCAMC.NS",    "ICICIGI.NS",
    # IT
    "COFORGE.NS",    "LTTS.NS",       "KPITTECH.NS",   "TATAELXSI.NS",
    "CYIENT.NS",     "HEXAWARE.NS",
    # Auto & Ancillary
    "MOTHERSON.NS",  "BALKRISIND.NS", "EXIDEIND.NS",   "MRF.NS",
    "APOLLOTYRE.NS", "BHARATFORG.NS",
    # Pharma & Healthcare
    "ALKEM.NS",      "BIOCON.NS",     "GLENMARK.NS",   "IPCALAB.NS",
    "NATCOPHARM.NS", "LAURUSLABS.NS",
    # Metals & Mining
    "NATIONALUM.NS", "HINDCOPPER.NS", "MOIL.NS",       "WELCORP.NS",
    "RATNAMANI.NS",
    # Energy & Power
    "ADANIGREEN.NS", "ADANIPOWER.NS", "TATAPOWER.NS",  "CESC.NS",
    "NLCINDIA.NS",   "SJVN.NS",
    # Consumer & New-age
    "DMART.NS",      "NYKAA.NS",      "POLICYBZR.NS",  "PAYTM.NS",
    "INDIAMART.NS",  "JUBLFOOD.NS",   "DEVYANI.NS",
    # Infra & Real Estate
    "GODREJPROP.NS", "PRESTIGE.NS",   "BRIGADE.NS",    "PHOENIXLTD.NS",
    "GMRINFRA.NS",   "IRB.NS",
    # Chemicals
    "AARTIIND.NS",   "DEEPAKNTR.NS",  "NAVINFLUOR.NS", "VINATIORGA.NS",
]

# Deduplicated master list
_seen = set()
FULL_WATCHLIST = []
for s in NIFTY_50 + NIFTY_NEXT_50 + ACTIVE_FNO:
    if s not in _seen:
        _seen.add(s)
        FULL_WATCHLIST.append(s)

# Index labels for badge display
WATCHLIST_LABELS = {}
for s in NIFTY_50:
    WATCHLIST_LABELS[s] = "Nifty 50"
for s in NIFTY_NEXT_50:
    if s not in WATCHLIST_LABELS:
        WATCHLIST_LABELS[s] = "Nifty Next 50"
for s in ACTIVE_FNO:
    if s not in WATCHLIST_LABELS:
        WATCHLIST_LABELS[s] = "F&O"
