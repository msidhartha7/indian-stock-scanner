from __future__ import annotations

import json
from pathlib import Path

from .storage import StoragePaths


DEFAULT_NIFTY_50 = [
    {"ticker": "ADANIENT", "company_name": "Adani Enterprises", "sector": "Industrials"},
    {"ticker": "ADANIPORTS", "company_name": "Adani Ports", "sector": "Logistics"},
    {"ticker": "APOLLOHOSP", "company_name": "Apollo Hospitals", "sector": "Healthcare"},
    {"ticker": "ASIANPAINT", "company_name": "Asian Paints", "sector": "Consumer"},
    {"ticker": "RELIANCE", "company_name": "Reliance Industries", "sector": "Energy"},
    {"ticker": "TCS", "company_name": "Tata Consultancy Services", "sector": "IT"},
    {"ticker": "HDFCBANK", "company_name": "HDFC Bank", "sector": "Financials"},
    {"ticker": "ICICIBANK", "company_name": "ICICI Bank", "sector": "Financials"},
    {"ticker": "INFY", "company_name": "Infosys", "sector": "IT"},
    {"ticker": "HCLTECH", "company_name": "HCL Technologies", "sector": "IT"},
    {"ticker": "TECHM", "company_name": "Tech Mahindra", "sector": "IT"},
    {"ticker": "WIPRO", "company_name": "Wipro", "sector": "IT"},
    {"ticker": "BHARTIARTL", "company_name": "Bharti Airtel", "sector": "Telecom"},
    {"ticker": "LT", "company_name": "Larsen & Toubro", "sector": "Industrials"},
    {"ticker": "SBIN", "company_name": "State Bank of India", "sector": "Financials"},
    {"ticker": "ITC", "company_name": "ITC", "sector": "Consumer"},
    {"ticker": "HINDUNILVR", "company_name": "Hindustan Unilever", "sector": "Consumer"},
    {"ticker": "KOTAKBANK", "company_name": "Kotak Mahindra Bank", "sector": "Financials"},
    {"ticker": "AXISBANK", "company_name": "Axis Bank", "sector": "Financials"},
    {"ticker": "BAJFINANCE", "company_name": "Bajaj Finance", "sector": "Financials"},
    {"ticker": "BAJAJFINSV", "company_name": "Bajaj Finserv", "sector": "Financials"},
    {"ticker": "SBILIFE", "company_name": "SBI Life Insurance", "sector": "Financials"},
    {"ticker": "HDFCLIFE", "company_name": "HDFC Life Insurance", "sector": "Financials"},
    {"ticker": "SHRIRAMFIN", "company_name": "Shriram Finance", "sector": "Financials"},
    {"ticker": "MARUTI", "company_name": "Maruti Suzuki", "sector": "Auto"},
    {"ticker": "M&M", "company_name": "Mahindra & Mahindra", "sector": "Auto"},
    {"ticker": "TATAMOTORS", "company_name": "Tata Motors", "sector": "Auto"},
    {"ticker": "BAJAJ-AUTO", "company_name": "Bajaj Auto", "sector": "Auto"},
    {"ticker": "HEROMOTOCO", "company_name": "Hero MotoCorp", "sector": "Auto"},
    {"ticker": "EICHERMOT", "company_name": "Eicher Motors", "sector": "Auto"},
    {"ticker": "SUNPHARMA", "company_name": "Sun Pharma", "sector": "Pharma"},
    {"ticker": "CIPLA", "company_name": "Cipla", "sector": "Pharma"},
    {"ticker": "DRREDDY", "company_name": "Dr Reddy's Laboratories", "sector": "Pharma"},
    {"ticker": "DIVISLAB", "company_name": "Divi's Laboratories", "sector": "Pharma"},
    {"ticker": "NESTLEIND", "company_name": "Nestle India", "sector": "Consumer"},
    {"ticker": "TITAN", "company_name": "Titan Company", "sector": "Consumer"},
    {"ticker": "BRITANNIA", "company_name": "Britannia Industries", "sector": "Consumer"},
    {"ticker": "ULTRACEMCO", "company_name": "UltraTech Cement", "sector": "Materials"},
    {"ticker": "GRASIM", "company_name": "Grasim Industries", "sector": "Materials"},
    {"ticker": "JSWSTEEL", "company_name": "JSW Steel", "sector": "Materials"},
    {"ticker": "TATASTEEL", "company_name": "Tata Steel", "sector": "Materials"},
    {"ticker": "POWERGRID", "company_name": "Power Grid", "sector": "Utilities"},
    {"ticker": "NTPC", "company_name": "NTPC", "sector": "Utilities"},
    {"ticker": "ONGC", "company_name": "ONGC", "sector": "Energy"},
    {"ticker": "COALINDIA", "company_name": "Coal India", "sector": "Materials"},
    {"ticker": "BPCL", "company_name": "BPCL", "sector": "Energy"},
    {"ticker": "INDUSINDBK", "company_name": "IndusInd Bank", "sector": "Financials"},
]


def load_universe(paths: StoragePaths) -> list[dict]:
    if not paths.universe_path.exists():
        refresh_universe(paths)
    return json.loads(paths.universe_path.read_text(encoding="utf-8"))


def refresh_universe(paths: StoragePaths, symbols: list[dict] | None = None) -> Path:
    universe = symbols or DEFAULT_NIFTY_50
    paths.universe_path.write_text(json.dumps(universe, indent=2), encoding="utf-8")
    return paths.universe_path
