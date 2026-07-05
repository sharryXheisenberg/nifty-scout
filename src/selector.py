"""
selector.py
-----------
Takes ranked SymbolScore objects (from scoring.py) plus raw OHLCV data and
metadata, and picks the final "Team of the Week": a formation-based lineup
(e.g. 4-3-3) with sector diversification and liquidity filters applied.

Position assignment logic:
  - DEF (defenders):   most stable large-caps -> lowest volatility_adj_return
                        magnitude + lowest drawdown, picked from the top
                        overall scorers (not weakest scorers — stable AND good).
  - MID (midfielders):  balanced composite score, no strong tilt.
  - FWD (forwards):     highest momentum + volume_surge.

This isn't a strict quant claim — it's a presentation layer that maps scout
metaphor to real factors, done deterministically so the same day's data
always produces the same lineup (no randomness).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, asdict
from pathlib import Path

import pandas as pd

from scoring import SymbolScore

logger = logging.getLogger("nifty_scout.selector")


@dataclass
class PlayerCard:
    symbol: str
    name: str
    sector: str
    position: str  # DEF | MID | FWD
    composite_score: float
    momentum: float
    volume_surge: float
    volatility_adj_return: float
    drawdown_penalty: float
    latest_close: float
    latest_volume: int


def load_metadata(tickers_path: str) -> dict[str, dict]:
    with open(tickers_path, "r") as f:
        payload = json.load(f)
    return {entry["symbol"]: entry for entry in payload["universe"]}


def apply_liquidity_filters(
    scores: list[SymbolScore],
    ohlcv_by_symbol: dict[str, pd.DataFrame],
    min_price: float,
    min_avg_volume: float,
) -> list[SymbolScore]:
    """Drop illiquid / penny-stock symbols before selection, not scoring —
    they should still be visible in scoring logs, just ineligible for the XI."""
    filtered = []
    for s in scores:
        df = ohlcv_by_symbol.get(s.symbol)
        if df is None or df.empty:
            continue
        latest_close = float(df["Close"].iloc[-1])
        avg_volume = float(df["Volume"].tail(20).mean())

        if latest_close < min_price:
            logger.debug("Excluding %s: price %.2f below min %.2f", s.symbol, latest_close, min_price)
            continue
        if avg_volume < min_avg_volume:
            logger.debug("Excluding %s: avg volume %.0f below min %.0f", s.symbol, avg_volume, min_avg_volume)
            continue

        filtered.append(s)
    return filtered


def _sector_cap_ok(sector: str, chosen_sectors: list[str], cap: int) -> bool:
    return chosen_sectors.count(sector) < cap


def _pick_for_position(
    candidates: list[SymbolScore],
    count: int,
    metadata: dict[str, dict],
    already_picked: set[str],
    sector_cap: int,
    sort_key,
    reverse: bool = True,
) -> list[SymbolScore]:
    ranked = sorted(candidates, key=sort_key, reverse=reverse)
    picked: list[SymbolScore] = []
    chosen_sectors: list[str] = []

    for s in ranked:
        if len(picked) >= count:
            break
        if s.symbol in already_picked:
            continue
        sector = metadata.get(s.symbol, {}).get("sector", "Unknown")
        if not _sector_cap_ok(sector, chosen_sectors, sector_cap):
            continue
        picked.append(s)
        chosen_sectors.append(sector)

    if len(picked) < count:
        logger.warning(
            "Could only fill %d/%d slots for this position (sector cap or pool exhaustion)",
            len(picked), count,
        )
    return picked


def select_team(
    scores: list[SymbolScore],
    ohlcv_by_symbol: dict[str, pd.DataFrame],
    metadata: dict[str, dict],
    selector_cfg: dict,
) -> list[PlayerCard]:
    """
    Applies liquidity filters, then greedily fills DEF/MID/FWD slots from
    the ranked pool with sector-cap diversification, avoiding duplicate picks.
    """
    eligible = apply_liquidity_filters(
        scores,
        ohlcv_by_symbol,
        min_price=selector_cfg["universe_min_price_inr"],
        min_avg_volume=selector_cfg["universe_min_avg_volume"],
    )

    if not eligible:
        raise RuntimeError("No symbols passed liquidity filters — check thresholds/data quality")

    slots = selector_cfg["slots"]
    sector_cap = selector_cfg["sector_cap_per_position"]
    already_picked: set[str] = set()
    final: list[SymbolScore] = []

    # FWD: highest momentum + volume surge (most "attacking" signal)
    fwd = _pick_for_position(
        eligible, slots["FWD"], metadata, already_picked, sector_cap,
        sort_key=lambda s: s.momentum + s.volume_surge,
    )
    already_picked.update(s.symbol for s in fwd)
    final.extend(fwd)

    # DEF: strong composite score but lowest drawdown (stability-first)
    def_candidates = [s for s in eligible if s.symbol not in already_picked]
    defs = _pick_for_position(
        def_candidates, slots["DEF"], metadata, already_picked, sector_cap,
        sort_key=lambda s: s.composite - s.drawdown_penalty,
    )
    already_picked.update(s.symbol for s in defs)
    final.extend(defs)

    # MID: best remaining composite score (balanced)
    mid_candidates = [s for s in eligible if s.symbol not in already_picked]
    mids = _pick_for_position(
        mid_candidates, slots["MID"], metadata, already_picked, sector_cap,
        sort_key=lambda s: s.composite,
    )
    already_picked.update(s.symbol for s in mids)
    final.extend(mids)

    total_needed = slots["DEF"] + slots["MID"] + slots["FWD"]
    if len(final) < total_needed:
        logger.warning(
            "Final lineup has %d/%d players — insufficient eligible universe today",
            len(final), total_needed,
        )

    cards = []
    for s, position in (
        [(p, "FWD") for p in fwd] + [(p, "DEF") for p in defs] + [(p, "MID") for p in mids]
    ):
        meta = metadata.get(s.symbol, {})
        df = ohlcv_by_symbol[s.symbol]
        cards.append(
            PlayerCard(
                symbol=s.symbol,
                name=meta.get("name", s.symbol),
                sector=meta.get("sector", "Unknown"),
                position=position,
                composite_score=round(s.composite, 4),
                momentum=round(s.momentum, 4),
                volume_surge=round(s.volume_surge, 4),
                volatility_adj_return=round(s.volatility_adj_return, 4),
                drawdown_penalty=round(s.drawdown_penalty, 4),
                latest_close=round(float(df["Close"].iloc[-1]), 2),
                latest_volume=int(df["Volume"].iloc[-1]),
            )
        )
    return cards


def write_team_json(cards: list[PlayerCard], output_path: str, run_date: str) -> None:
    payload = {
        "date": run_date,
        "formation": "4-3-3",
        "players": [asdict(c) for c in cards],
    }
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(payload, f, indent=2)
    logger.info("Wrote team JSON to %s (%d players)", output_path, len(cards))
