import logging

import requests

logger = logging.getLogger(__name__)

YAHOO_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; DailyDigestBot/1.0)"}


def _yahoo_index(symbol_encoded: str):
    """Return (last_close, percent_change) for a Yahoo Finance index, or None."""
    try:
        r = requests.get(
            f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol_encoded}",
            params={"interval": "1d", "range": "5d"},
            headers=YAHOO_HEADERS,
            timeout=10,
        )
        r.raise_for_status()
        result = r.json()["chart"]["result"][0]
        closes = result["indicators"]["quote"][0]["close"]
        closes = [c for c in closes if c is not None]
        if len(closes) < 2:
            return None
        prev, last = closes[-2], closes[-1]
        pct = (last - prev) / prev * 100
        return last, pct
    except Exception as e:
        logger.warning("Yahoo fetch failed for %s: %s", symbol_encoded, e)
        return None


def _format_index(name: str, data):
    if not data:
        return f"{name}: N/A"
    val, pct = data
    arrow = "▲" if pct >= 0 else "▼"
    return f"{name}: {val:,.0f} {arrow}{abs(pct):.1f}%"


def _usd_inr():
    try:
        r = requests.get(
            "https://api.exchangerate-api.com/v4/latest/USD",
            timeout=10,
        )
        r.raise_for_status()
        return float(r.json()["rates"]["INR"])
    except Exception as e:
        logger.warning("USD/INR fetch failed: %s", e)
        return None


def _btc_usd():
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": "bitcoin", "vs_currencies": "usd"},
            timeout=10,
        )
        r.raise_for_status()
        return float(r.json()["bitcoin"]["usd"])
    except Exception as e:
        logger.warning("BTC fetch failed: %s", e)
        return None


def get_market_snapshot():
    """Return a one-line market snapshot string, or None if everything failed."""
    try:
        nifty_part = _format_index("Nifty", _yahoo_index("%5ENSEI"))
        sensex_part = _format_index("Sensex", _yahoo_index("%5EBSESN"))
        inr = _usd_inr()
        btc = _btc_usd()
        inr_part = f"₹/$ {inr:.1f}" if inr is not None else "₹/$ N/A"
        btc_part = f"BTC ${btc:,.0f}" if btc is not None else "BTC N/A"
        line = f"📊 {nifty_part} · {sensex_part} · {inr_part} · {btc_part}"
        # If every single piece failed, treat as failure.
        if "N/A" in nifty_part and "N/A" in sensex_part and inr is None and btc is None:
            return None
        return line
    except Exception as e:
        logger.warning("Market snapshot failed entirely: %s", e)
        return None
