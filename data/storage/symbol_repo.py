from __future__ import annotations

from .base import BaseRepository
from .models import Symbol


class SymbolRepository(BaseRepository):
    def upsert_symbol_metadata(self, symbol: str, metadata: dict[str, object]) -> None:
        self.upsert(Symbol, {"symbol": symbol.upper().strip()}, metadata)

    def get_symbol(self, symbol: str) -> Symbol | None:
        try:
            normalized_symbol = symbol.upper().strip()
            return self.db.query(Symbol).filter(Symbol.symbol == normalized_symbol).first()
        except Exception:
            return None

    def resolve_sector_bucket(self, symbol: str) -> str:
        symbol_row = self.get_symbol(symbol)
        if symbol_row is None:
            return "other"

        labels = [
            str(value).strip().lower()
            for value in [symbol_row.industry, symbol_row.icb_name2, symbol_row.icb_name3, symbol_row.icb_name4]
            if value
        ]
        text_value = " | ".join(labels)
        if any(keyword in text_value for keyword in ["ngan hang", "bank"]):
            return "banking"
        if any(keyword in text_value for keyword in ["bat dong san", "real estate", "real_estate"]):
            return "real_estate"
        if any(keyword in text_value for keyword in ["cong nghe", "phan mem", "technology", "software"]):
            return "technology"
        if any(keyword in text_value for keyword in ["tai nguyen", "vat lieu", "materials", "steel", "chemical"]):
            return "materials"
        if any(keyword in text_value for keyword in ["dau khi", "energy", "oil", "gas", "utility"]):
            return "energy"
        if any(keyword in text_value for keyword in ["ban le", "thuc pham", "consumer", "retail", "beverage"]):
            return "consumer"
        if any(keyword in text_value for keyword in ["van tai", "aviation", "airline", "transport"]):
            return "transport"
        if any(keyword in text_value for keyword in ["bao hiem", "insurance"]):
            return "insurance"
        if any(keyword in text_value for keyword in ["chung khoan", "securities", "brokerage"]):
            return "securities"
        return "other"
