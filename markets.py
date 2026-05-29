import logging
import time

import requests

logger = logging.getLogger(__name__)

YAHOO_HEADERS = {"User-Agent": "Mozilla/5.0"}


def _yahoo_index(symbol_encoded: str):
    """Return (last_value, percent_change, is_closed) for a Yahoo index, or None.

    Uses a 5-day range and a cache-busting timestamp so morning and evening
    briefs get fresh data. ``is_closed`` is True on weekends/holidays when the
    market is not in its regular session.
    """
    try:
        url = (
            f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol_encoded}"
            f"?interval=1d&range=5d&t={int(time.time())}"
        )
        r = requests.get(url, headers=YAHOO_HEADERS, timeout=10)
        r.raise_for_status()
        result = r.json()["chart"]["result"][0]
        meta = result.get("meta", {})
        closes = [c for c in result["indicators"]["quote"][0]["close"] if c is not None]
        if not closes:
            return None

        # Prefer the live regular-market price from meta when present; fall back
        # to the most recent close.
        last = meta.get("regularMarketPrice") or closes[-1]
        prev = meta.get("chartPreviousClose")
        if prev is None:
            prev = closes[-2] if len(closes) >= 2 else last

        is_closed = meta.get("marketState", "").upper() not in ("REGULAR", "PRE", "POST")
        pct = ((last - prev) / prev * 100) if prev else 0.0
        return last, pct, is_closed
    except Exception as e:
        logger.warning("Yahoo fetch failed for %s: %s", symbol_encoded, e)
        return None


def _format_index(name: str, data):
    if not data:
        return f"{name}: N/A"
    val, pct, is_closed = data
    if is_closed:
        return f"{name}: {val:,.0f} (closed)"
    arrow = "▲" if pct >= 0 else "▼"
    return f"{name}: {val:,.0f} {arrow}{abs(pct):.1f}%"


def _usd_inr():
    try:
        r = requests.get("https://open.er-api.com/v6/latest/USD", timeout=10)
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
