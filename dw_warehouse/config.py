from pathlib import Path


DEFAULT_DATA_DIR = Path("data") / "warehouse"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_API_PORT = 8000

COLLECTIONS = {
    "instruments": "financial_instruments",
    "sources": "data_sources",
    "series": "time_series",
    "points": "time_series_points",
    "portfolios": "portfolios",
    "portfolio_assets": "portfolio_assets",
}
