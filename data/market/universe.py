from __future__ import annotations

import os
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class SymbolMeta:
    symbol: str
    exchange: str
    sector: str
    priority: int
    is_active: bool = True


_VN30_SYMBOLS: tuple[SymbolMeta, ...] = (
    SymbolMeta("ACB", "HOSE", "Banking", 1),
    SymbolMeta("BCM", "HOSE", "Real Estate", 2),
    SymbolMeta("BID", "HOSE", "Banking", 1),
    SymbolMeta("BVH", "HOSE", "Insurance", 2),
    SymbolMeta("CTG", "HOSE", "Banking", 1),
    SymbolMeta("FPT", "HOSE", "Technology", 1),
    SymbolMeta("GAS", "HOSE", "Energy", 1),
    SymbolMeta("GVR", "HOSE", "Materials", 2),
    SymbolMeta("HDB", "HOSE", "Banking", 2),
    SymbolMeta("HPG", "HOSE", "Materials", 1),
    SymbolMeta("LPB", "HOSE", "Banking", 2),
    SymbolMeta("MBB", "HOSE", "Banking", 1),
    SymbolMeta("MSN", "HOSE", "Consumer", 1),
    SymbolMeta("MWG", "HOSE", "Retail", 1),
    SymbolMeta("PLX", "HOSE", "Energy", 2),
    SymbolMeta("POW", "HOSE", "Utilities", 2),
    SymbolMeta("SAB", "HOSE", "Consumer", 2),
    SymbolMeta("SHB", "HOSE", "Banking", 2),
    SymbolMeta("SSB", "HOSE", "Banking", 2),
    SymbolMeta("SSI", "HOSE", "Securities", 1),
    SymbolMeta("STB", "HOSE", "Banking", 1),
    SymbolMeta("TCB", "HOSE", "Banking", 1),
    SymbolMeta("TPB", "HOSE", "Banking", 2),
    SymbolMeta("VCB", "HOSE", "Banking", 1),
    SymbolMeta("VHM", "HOSE", "Real Estate", 1),
    SymbolMeta("VIB", "HOSE", "Banking", 2),
    SymbolMeta("VIC", "HOSE", "Conglomerate", 1),
    SymbolMeta("VJC", "HOSE", "Airlines", 2),
    SymbolMeta("VNM", "HOSE", "Consumer", 1),
    SymbolMeta("VPB", "HOSE", "Banking", 1),
    SymbolMeta("VRE", "HOSE", "Retail", 2),
)

_VN80_ADDITIONAL_SYMBOLS: tuple[SymbolMeta, ...] = (
    SymbolMeta("ANV", "HOSE", "Seafood", 3),
    SymbolMeta("BAF", "HOSE", "Agriculture", 3),
    SymbolMeta("BMP", "HOSE", "Materials", 3),
    SymbolMeta("BSI", "HOSE", "Securities", 3),
    SymbolMeta("CMG", "HOSE", "Technology", 3),
    SymbolMeta("CTR", "HOSE", "Telecom", 2),
    SymbolMeta("DBC", "HOSE", "Agriculture", 3),
    SymbolMeta("DCM", "HOSE", "Chemicals", 3),
    SymbolMeta("DGW", "HOSE", "Technology", 2),
    SymbolMeta("DHC", "HOSE", "Materials", 3),
    SymbolMeta("DPM", "HOSE", "Chemicals", 3),
    SymbolMeta("DXG", "HOSE", "Real Estate", 3),
    SymbolMeta("EIB", "HOSE", "Banking", 3),
    SymbolMeta("EVF", "HOSE", "Financial Services", 3),
    SymbolMeta("FTS", "HOSE", "Securities", 3),
    SymbolMeta("GEX", "HOSE", "Industrials", 2),
    SymbolMeta("HAG", "HOSE", "Agriculture", 3),
    SymbolMeta("HAH", "HOSE", "Logistics", 3),
    SymbolMeta("HCM", "HOSE", "Securities", 2),
    SymbolMeta("HDG", "HOSE", "Real Estate", 3),
    SymbolMeta("HHV", "HOSE", "Infrastructure", 3),
    SymbolMeta("KBC", "HOSE", "Real Estate", 2),
    SymbolMeta("KDH", "HOSE", "Real Estate", 2),
    SymbolMeta("NKG", "HOSE", "Materials", 3),
    SymbolMeta("OCB", "HOSE", "Banking", 3),
    SymbolMeta("PAN", "HOSE", "Agriculture", 3),
    SymbolMeta("PC1", "HOSE", "Industrials", 3),
    SymbolMeta("PDR", "HOSE", "Real Estate", 3),
    SymbolMeta("PET", "HOSE", "Distribution", 3),
    SymbolMeta("PNJ", "HOSE", "Retail", 2),
    SymbolMeta("PTB", "HOSE", "Industrials", 3),
    SymbolMeta("REE", "HOSE", "Utilities", 2),
    SymbolMeta("SCS", "HOSE", "Logistics", 3),
    SymbolMeta("SZC", "HOSE", "Real Estate", 3),
    SymbolMeta("VCG", "HOSE", "Construction", 3),
    SymbolMeta("VGC", "HOSE", "Materials", 3),
    SymbolMeta("VHC", "HOSE", "Seafood", 2),
    SymbolMeta("VIX", "HOSE", "Securities", 3),
    SymbolMeta("VPI", "HOSE", "Real Estate", 3),
    SymbolMeta("YEG", "HOSE", "Media", 3),
    SymbolMeta("DIG", "HOSE", "Real Estate", 3),
    SymbolMeta("DGC", "HOSE", "Chemicals", 2),
    SymbolMeta("NLG", "HOSE", "Real Estate", 2),
    SymbolMeta("PVT", "HOSE", "Logistics", 2),
    SymbolMeta("VND", "HOSE", "Securities", 2),
    SymbolMeta("KOS", "HOSE", "Real Estate", 3),
    SymbolMeta("SCR", "HOSE", "Real Estate", 3),
    SymbolMeta("ASM", "HOSE", "Agriculture", 3),
    SymbolMeta("IDI", "HOSE", "Seafood", 3),
)

_BASE_UNIVERSES: dict[str, tuple[SymbolMeta, ...]] = {
    "vn30": _VN30_SYMBOLS,
    "vn50": _VN30_SYMBOLS + _VN80_ADDITIONAL_SYMBOLS[:20],
    "vn80": _VN30_SYMBOLS + _VN80_ADDITIONAL_SYMBOLS,
}


def _parse_symbol_list(raw: str | None) -> list[str]:
    if not raw:
        return []
    items = [item.strip().upper() for item in raw.split(",")]
    return [item for item in items if item]


def _catalog_by_symbol() -> dict[str, SymbolMeta]:
    catalog: dict[str, SymbolMeta] = {}
    for entries in _BASE_UNIVERSES.values():
        for entry in entries:
            catalog[entry.symbol] = entry
    return catalog


def load_symbols_from_config() -> list[dict[str, object]]:
    symbols = _parse_symbol_list(
        os.getenv("MARKET_SYMBOLS")
        or os.getenv("MARKET_UNIVERSE_SYMBOLS")
        or os.getenv("CUSTOM_WATCHLIST")
    )
    if not symbols:
        return []

    catalog = _catalog_by_symbol()
    items: list[dict[str, object]] = []
    for symbol in symbols:
        meta = catalog.get(symbol)
        if meta is None:
            items.append(asdict(SymbolMeta(symbol, "HOSE", "Unknown", 3, True)))
            continue
        items.append(asdict(meta))
    return items


def load_universe(name: str) -> list[dict[str, object]]:
    normalized = name.strip().lower()
    if normalized == "custom_watchlist":
        configured = load_symbols_from_config()
        if configured:
            return configured
        return [asdict(item) for item in _BASE_UNIVERSES["vn30"]]

    if normalized not in _BASE_UNIVERSES:
        raise ValueError(f"unknown universe: {name}")

    return [asdict(item) for item in _BASE_UNIVERSES[normalized]]


def split_symbols_into_shards(
    symbols: list[dict[str, object]] | list[str],
    shard_size: int,
) -> list[list[dict[str, object]] | list[str]]:
    if shard_size <= 0:
        raise ValueError("shard_size must be positive")

    return [symbols[index:index + shard_size] for index in range(0, len(symbols), shard_size)]


def get_priority_symbols() -> list[str]:
    configured = _parse_symbol_list(os.getenv("MARKET_PRIORITY_SYMBOLS"))
    if configured:
        return configured

    universe_name = os.getenv("MARKET_PRIORITY_UNIVERSE", "vn80")
    items = load_universe(universe_name)
    return [
        item["symbol"]
        for item in sorted(items, key=lambda item: (int(item["priority"]), str(item["symbol"])))
        if bool(item["is_active"]) and int(item["priority"]) == 1
    ]
