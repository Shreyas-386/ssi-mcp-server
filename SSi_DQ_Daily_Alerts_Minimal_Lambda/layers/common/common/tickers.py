"""
Centralized Ticker Configuration
Single source of truth for all stock tickers used across Lambda functions.

To add a new stock:
1. Add the ticker to the appropriate sector in STOCKS_WITH_SECTORS
2. Add the ticker and company name to TICKER_TO_NAME

The STOCK_LIST is auto-generated from STOCKS_WITH_SECTORS.
"""

STOCKS_WITH_SECTORS = [
    {
        "sector": "Communication Services",
        "tickers": ["META", "DIS", "GOOGL", "NFLX", "ASTS", "RBLX", "RDDT", "SPOT"]
    },
    {
        "sector": "Consumer Discretionary",
        "tickers": ["F", "TSLA", "UBER", "MAR", "AMZN", "GME", "DKNG", "LCID", "LULU", "NKE", "RIVN", "GM", "SBUX", "MCD", "CMG", "DPZ", "DASH", "TTM", "MMYT", "BABA"]
    },
    {
        "sector": "Consumer Staples",
        "tickers": ["PG", "WMT", "COST", "KO", "PEP", "PM", "CELH", "TGT"]
    },
    {
        "sector": "Energy",
        "tickers": ["XOM", "CVX", "SHEL", "NFE", "COP"]
    },
    {
        "sector": "Financials",
        "tickers": ["BAC", "JPM", "V", "PYPL", "XYZ", "GS", "COIN", "HOOD", "MA", "NU", "SOFI", "C", "BK", "IBN", "HDB"]
    },
    {
        "sector": "Healthcare",
        "tickers": ["PFE", "NVAX", "JNJ", "CVS", "MRNA", "UNH", "VKTX", "LLY", "SNDX", "RDY"]
    },
    {
        "sector": "Industrials",
        "tickers": ["BA", "CAT", "FDX", "MMM", "HON", "ETN", "UNP", "RTX", "GE"]
    },
    {
        "sector": "Technology",
        "tickers": ["MSFT", "INTC", "AAPL", "AMD", "NVDA", "AVGO", "CRM", "CRWD", "MSTR", "PLTR", "SNOW", "APP", "MU", "SMCI", "ZETA", "U", "DELL", "ORCL", "ADBE", "ZS", "SHOP", "TSM", "INTU", "DDOG", "DOCU", "ENPH", "MRVL", "INFY", "WIT"]
    },
    {
        "sector": "Materials",
        "tickers": ["LIN"]
    },
    {
        "sector": "Real Estate",
        "tickers": ["O"]
    },
    {
        "sector": "Utilities",
        "tickers": ["NEE", "DUK"]
    }
]

TICKER_TO_NAME = {
    "F": "Ford",
    "BAC": "Bank of America",
    "BA": "Boeing",
    "MSFT": "Microsoft",
    "XOM": "Exxon Mobil",
    "AAPL": "Apple",
    "UBER": "Uber",
    "META": "Meta Platforms",
    "INTC": "Intel",
    "DIS": "Walt Disney",
    "TSLA": "Tesla",
    "PFE": "Pfizer",
    "JPM": "JPMorgan Chase",
    "V": "Visa",
    "MAR": "Marriott",
    "PG": "Procter & Gamble",
    "CAT": "Caterpillar",
    "AMZN": "Amazon",
    "GOOGL": "Alphabet (Class A)",
    "GME": "GameStop",
    "PYPL": "PayPal",
    "JNJ": "Johnson & Johnson",
    "NVAX": "Novavax",
    "XYZ": "Block",
    "WMT": "Walmart",
    "GS": "Goldman Sachs",
    "AMD": "AMD",
    "NVDA": "Nvidia",
    "NFLX": "Netflix",
    "COIN": "Coinbase",
    "AVGO": "Broadcom",
    "COST": "Costco",
    "CRM": "Salesforce",
    "CRWD": "CrowdStrike",
    "CVS": "CVS Health",
    "HOOD": "Robinhood",
    "MA": "Mastercard",
    "MRNA": "Moderna",
    "MSTR": "MicroStrategy",
    "NKE": "Nike",
    "PLTR": "Palantir",
    "SNOW": "Snowflake",
    "SOFI": "SoFi",
    "TGT": "Target",
    "UNH": "UnitedHealth",
    "APP": "AppLovin",
    "ASTS": "AST SpaceMobile",
    "CELH": "Celsius Holdings",
    "DKNG": "DraftKings",
    "LCID": "Lucid",
    "LULU": "Lululemon",
    "MU": "Micron",
    "NU": "Nu Holdings",
    "RBLX": "Roblox",
    "RDDT": "Reddit",
    "RIVN": "Rivian",
    "SMCI": "Super Micro Computer",
    "VKTX": "Viking Therapeutics",
    "ZETA": "Zeta Global",
    "U": "Unity Software",
    "DELL": "Dell Technologies",
    "C": "Citigroup",
    "GM": "General Motors",
    "FDX": "FedEx",
    "SBUX": "Starbucks",
    "KO": "Coca-Cola",
    "MCD": "McDonald's",
    "MMM": "3M",
    "PM": "Philip Morris",
    "BK": "Bank of New York Mellon",
    "ORCL": "Oracle",
    "CVX": "Chevron",
    "SHEL": "Shell",
    "NEE": "NextEra Energy",
    "GE": "GE Aerospace",
    "HON": "Honeywell",
    "ETN": "Eaton",
    "ADBE": "Adobe",
    "LLY": "Eli Lilly",
    "ZS": "Zscaler",
    "SHOP": "Shopify",
    "TSM": "TSMC",
    "PEP": "PepsiCo",
    "CMG": "Chipotle",
    "DPZ": "Domino's Pizza",
    "INTU": "Intuit",
    "DDOG": "Datadog",
    "SPOT": "Spotify",
    "NFE": "New Fortress Energy",
    "DASH": "DoorDash",
    "SNDX": "Syndax Pharma",
    "DOCU": "DocuSign",
    "ENPH": "Enphase Energy",
    "MRVL": "Marvell Tech",
    "UNP": "Union Pacific",
    "LIN": "Linde",
    "O": "Realty Income",
    "DUK": "Duke Energy",
    "RTX": "RTX Corp",
    "COP": "ConocoPhillips",
    "TTM": "Tata Motors",
    "IBN": "ICICI Bank",
    "HDB": "HDFC Bank",
    "RDY": "Dr. Reddy's Laboratories",
    "MMYT": "MakeMyTrip",
    "BABA": "Alibaba",
    "INFY": "Infosys",
    "WIT": "Wipro"
}

# Auto-generate flat stock list from sectors
STOCK_LIST = [ticker for sector in STOCKS_WITH_SECTORS for ticker in sector["tickers"]]

# Get all unique sectors
SECTORS = [s["sector"] for s in STOCKS_WITH_SECTORS]

# Pre-compute excluded terms for wordcloud (lowercase)
WORDCLOUD_EXCLUDED_TERMS = set()
for sym, name in TICKER_TO_NAME.items():
    WORDCLOUD_EXCLUDED_TERMS.add(sym.lower())
    if name:
        WORDCLOUD_EXCLUDED_TERMS.add(str(name).lower())


def get_company_name(ticker):
    """Get company name for a ticker"""
    return TICKER_TO_NAME.get(ticker, ticker)


def get_sector_for_ticker(ticker):
    """Get sector for a ticker"""
    for sector_data in STOCKS_WITH_SECTORS:
        if ticker in sector_data["tickers"]:
            return sector_data["sector"]
    return None


def get_tickers_for_sector(sector):
    """Get all tickers for a sector"""
    for sector_data in STOCKS_WITH_SECTORS:
        if sector_data["sector"] == sector:
            return sector_data["tickers"]
    return []
