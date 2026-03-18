from __future__ import annotations

DEFAULT_STOCK_FUTURES_SYMBOLS: tuple[str, ...] = (
    "RELIANCE-FUT",
    "TCS-FUT",
    "INFY-FUT",
    "HDFCBANK-FUT",
    "ICICIBANK-FUT",
    "SBIN-FUT",
    "LT-FUT",
    "ITC-FUT",
    "HINDUNILVR-FUT",
    "KOTAKBANK-FUT",
    "AXISBANK-FUT",
    "BHARTIARTL-FUT",
    "MARUTI-FUT",
    "SUNPHARMA-FUT",
    "ULTRACEMCO-FUT",
    "NTPC-FUT",
    "POWERGRID-FUT",
    "BAJFINANCE-FUT",
    "TITAN-FUT",
    "WIPRO-FUT",
)

SECTOR_BY_ROOT: dict[str, str] = {
    "RELIANCE": "energy",
    "TCS": "it",
    "INFY": "it",
    "HDFCBANK": "financials",
    "ICICIBANK": "financials",
    "SBIN": "financials",
    "LT": "industrials",
    "ITC": "consumer_staples",
    "HINDUNILVR": "consumer_staples",
    "KOTAKBANK": "financials",
    "AXISBANK": "financials",
    "BHARTIARTL": "telecom",
    "MARUTI": "consumer_discretionary",
    "SUNPHARMA": "healthcare",
    "ULTRACEMCO": "materials",
    "NTPC": "utilities",
    "POWERGRID": "utilities",
    "BAJFINANCE": "financials",
    "TITAN": "consumer_discretionary",
    "WIPRO": "it",
}


def normalize_symbol(symbol: str) -> str:
    return symbol.strip().upper()


def symbol_root(symbol: str) -> str:
    normalized = normalize_symbol(symbol)
    return normalized.replace("-FUT", "")


def infer_sector(symbol: str) -> str | None:
    root = symbol_root(symbol)
    return SECTOR_BY_ROOT.get(root)


def merged_symbol_universe(dynamic_symbols: list[str]) -> list[str]:
    merged: set[str] = {normalize_symbol(item) for item in DEFAULT_STOCK_FUTURES_SYMBOLS}
    merged.update(normalize_symbol(item) for item in dynamic_symbols if item and str(item).strip())
    return sorted(symbol for symbol in merged if symbol.endswith("-FUT"))
