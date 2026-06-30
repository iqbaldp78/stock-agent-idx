"""
Commodity Mapper — Map komoditi global ke ticker IDX terkait.
Misal: Gold -> ANTM, Coal -> PTBA/ADRO/ITMG, dll.
"""

# Mapping komoditi → ticker IDX (many-to-many)
COMMODITY_TO_TICKERS = {
    # Precious Metals
    "gold": {
        "tickers": ["ANTM"],  # Antam = major gold producer
        "exposure": "high",
        "currency": "USD/Oz",
        "symbol": "GC=F",  # Yahoo Finance
        "name": "Gold Futures"
    },

    # Coal
    "coal": {
        "tickers": ["PTBA", "ADRO", "ITMG", "TOBA"],  # Coal producers
        "exposure": "high",
        "currency": "USD/ton",
        "symbol": "^BCOM",  # Bloomberg Commodity Index proxy
        "name": "Thermal Coal"
    },

    # Oil & Gas
    "oil": {
        "tickers": ["BRPT", "ADRO", "ENRG"],  # Oil/energy producers
        "exposure": "high",
        "currency": "USD/bbl",
        "symbol": "CL=F",  # WTI Crude Oil
        "name": "Crude Oil"
    },

    "natural_gas": {
        "tickers": ["PGAS"],  # Perusahaan Gas Negara
        "exposure": "medium",
        "currency": "USD/MMBtu",
        "symbol": "NG=F",  # Natural Gas Futures
        "name": "Natural Gas"
    },

    # Base Metals
    "copper": {
        "tickers": ["INCO", "TBIG"],  # Copper producers (TBIG = Tycoon Group, diversified)
        "exposure": "medium",
        "currency": "USD/lb",
        "symbol": "HG=F",  # Copper Futures
        "name": "Copper"
    },

    "nickel": {
        "tickers": ["INCO"],  # Inco = nickel producer
        "exposure": "high",
        "currency": "USD/ton",
        "symbol": "^NICKEL",  # Nickel proxy
        "name": "Nickel"
    },

    "tin": {
        "tickers": ["TINS"],  # Timah (Tin producer)
        "exposure": "high",
        "currency": "USD/ton",
        "symbol": "^LMEX",  # LME Tin proxy
        "name": "Tin"
    },

    # Agriculture
    "palm_oil": {
        "tickers": ["AALI", "LSIP", "SMAR"],  # Palm oil producers
        "exposure": "high",
        "currency": "USD/ton",
        "symbol": "^PALM",  # Palm Oil Index proxy
        "name": "Palm Oil"
    },

    "rubber": {
        "tickers": ["GGRM"],  # Rubber producer
        "exposure": "medium",
        "currency": "USD/ton",
        "symbol": "^RUBBER",  # Rubber Index proxy
        "name": "Rubber"
    },

    # Building Materials
    "cement": {
        "tickers": ["SMGR", "INTP", "WTON"],  # Cement producers
        "exposure": "medium",
        "currency": "USD/ton",
        "symbol": "^CEMENT",  # Cement proxy
        "name": "Cement"
    },

    # Food
    "cocoa": {
        "tickers": ["ASGR"],  # Agro-industry
        "exposure": "low",
        "currency": "USD/ton",
        "symbol": "CC=F",  # Cocoa Futures
        "name": "Cocoa"
    },
}

# Reverse mapping: ticker → komoditi
TICKER_TO_COMMODITIES = {}
for commodity, data in COMMODITY_TO_TICKERS.items():
    for ticker in data["tickers"]:
        if ticker not in TICKER_TO_COMMODITIES:
            TICKER_TO_COMMODITIES[ticker] = []
        TICKER_TO_COMMODITIES[ticker].append(commodity)


def get_commodities_for_ticker(ticker: str) -> list[dict]:
    """Get semua komoditi yang terkait dengan ticker."""
    if ticker not in TICKER_TO_COMMODITIES:
        return []

    commodities = []
    for commodity in TICKER_TO_COMMODITIES[ticker]:
        commodities.append({
            "commodity": commodity,
            **COMMODITY_TO_TICKERS[commodity]
        })
    return commodities


def get_tickers_for_commodity(commodity: str) -> list[str]:
    """Get semua ticker IDX yang terkait dengan komoditi."""
    if commodity not in COMMODITY_TO_TICKERS:
        return []
    return COMMODITY_TO_TICKERS[commodity]["tickers"]


def get_commodity_info(commodity: str) -> dict | None:
    """Get info lengkap tentang 1 komoditi."""
    return COMMODITY_TO_TICKERS.get(commodity)


def get_all_commodities() -> list[str]:
    """Get daftar semua komoditi yang di-track."""
    return list(COMMODITY_TO_TICKERS.keys())
