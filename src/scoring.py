"""
scoring.py
----------
Turns raw OHLCV DataFrames into a single composite "scout score" per symbol.

Factors (weights configured in config.yaml -> scoring.weights):
  - momentum:              EMA(fast) vs EMA(slow) crossover strength
  - volume_surge:          latest volume vs trailing average volume
  - volatility_adj_return: recent return normalized by ATR (risk-adjusted move)
  - drawdown_penalty:      peak-to-trough pullback over the lookback window (subtracted)

Each factor is computed independently, then z-score normalized across the
universe (so factors on different scales combine fairly), then blended by
the configured weights. Symbols with insufficient data are excluded, not
silently zero-filled — a missing factor should never masquerade as a bad one.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd
from ta.trend import EMAIndicator
from ta.volatility import AverageTrueRange

logger = logging.getLogger("nifty_scout.scoring")


class InsufficientDataError(Exception):
    """Raised when a symbol's history is too short for a given indicator."""


@dataclass
class SymbolScore:
    symbol: str
    momentum: float
    volume_surge: float
    volatility_adj_return: float
    drawdown_penalty: float
    composite: float = 0.0  # filled in after cross-universe normalization


def _require_columns(df: pd.DataFrame, symbol: str, cols: list[str]) -> None:
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise InsufficientDataError(f"{symbol} missing columns: {missing}")


def compute_momentum(df: pd.DataFrame, fast: int, slow: int) -> float:
    """
    Momentum = normalized gap between fast and slow EMA.
    Positive => fast EMA above slow EMA => uptrend; scaled by slow EMA
    so it's comparable across stocks priced at very different levels.
    """
    if len(df) < slow:
        raise InsufficientDataError(f"Need >= {slow} rows for EMA({slow})")

    close = df["Close"]
    ema_fast = EMAIndicator(close, window=fast).ema_indicator().iloc[-1]
    ema_slow = EMAIndicator(close, window=slow).ema_indicator().iloc[-1]

    if ema_slow == 0 or pd.isna(ema_slow) or pd.isna(ema_fast):
        raise InsufficientDataError("EMA computation returned NaN/zero")

    return float((ema_fast - ema_slow) / ema_slow)


def compute_volume_surge(df: pd.DataFrame, trailing_window: int = 20) -> float:
    """
    Volume surge = latest volume / trailing average volume, expressed as a
    ratio minus 1 (0 = normal volume, 1.0 = double the average).
    """
    if len(df) < trailing_window + 1:
        raise InsufficientDataError(f"Need >= {trailing_window + 1} rows for volume avg")

    volume = df["Volume"]
    trailing_avg = volume.iloc[-(trailing_window + 1):-1].mean()
    latest = volume.iloc[-1]

    if trailing_avg == 0 or pd.isna(trailing_avg):
        raise InsufficientDataError("Trailing average volume is zero/NaN")

    return float((latest / trailing_avg) - 1.0)


def compute_volatility_adj_return(df: pd.DataFrame, atr_period: int) -> float:
    """
    Risk-adjusted return = recent price change / ATR.
    Rewards moves that are large relative to the stock's own typical range,
    rather than just large in absolute terms.
    """
    if len(df) < atr_period + 1:
        raise InsufficientDataError(f"Need >= {atr_period + 1} rows for ATR({atr_period})")

    atr = AverageTrueRange(
        high=df["High"], low=df["Low"], close=df["Close"], window=atr_period
    ).average_true_range().iloc[-1]

    if atr == 0 or pd.isna(atr):
        raise InsufficientDataError("ATR is zero/NaN — likely illiquid or flat series")

    price_change = df["Close"].iloc[-1] - df["Close"].iloc[-atr_period]
    return float(price_change / atr)


def compute_drawdown_penalty(df: pd.DataFrame) -> float:
    """
    Max peak-to-trough drawdown over the available window, as a positive
    fraction (0.15 = 15% drawdown). This is *subtracted* in the composite,
    so larger drawdowns reduce the score.
    """
    close = df["Close"]
    running_max = close.cummax()
    drawdown = (running_max - close) / running_max
    return float(drawdown.max())


def score_symbol(symbol: str, df: pd.DataFrame, scoring_cfg: dict) -> SymbolScore | None:
    """
    Compute all raw factors for one symbol. Returns None (and logs) if any
    factor can't be computed — we exclude rather than impute, since a
    fabricated factor value would distort ranking silently.
    """
    try:
        _require_columns(df, symbol, ["Close", "High", "Low", "Volume"])
        df = df.dropna(subset=["Close", "High", "Low", "Volume"])

        momentum = compute_momentum(
            df,
            fast=scoring_cfg["momentum"]["fast_ema"],
            slow=scoring_cfg["momentum"]["slow_ema"],
        )
        volume_surge = compute_volume_surge(df)
        vol_adj_return = compute_volatility_adj_return(
            df, atr_period=scoring_cfg["volatility"]["atr_period"]
        )
        drawdown_penalty = compute_drawdown_penalty(df)

        return SymbolScore(
            symbol=symbol,
            momentum=momentum,
            volume_surge=volume_surge,
            volatility_adj_return=vol_adj_return,
            drawdown_penalty=drawdown_penalty,
        )
    except InsufficientDataError as e:
        logger.info("Excluding %s from scoring: %s", symbol, e)
        return None
    except Exception as e:  # never let one weird symbol crash the batch
        logger.warning("Unexpected scoring error for %s: %s", symbol, e)
        return None


def _zscore(values: np.ndarray) -> np.ndarray:
    std = values.std()
    if std == 0 or np.isnan(std):
        # Every symbol identical on this factor — contributes nothing, not NaN.
        return np.zeros_like(values)
    return (values - values.mean()) / std


def normalize_and_blend(scores: list[SymbolScore], weights: dict) -> list[SymbolScore]:
    """
    Z-score normalize each factor across the whole batch, then combine with
    configured weights into a single composite score. Mutates and returns
    the same SymbolScore objects with `composite` populated.
    """
    if not scores:
        return scores

    momentum_arr = _zscore(np.array([s.momentum for s in scores]))
    volume_arr = _zscore(np.array([s.volume_surge for s in scores]))
    vol_adj_arr = _zscore(np.array([s.volatility_adj_return for s in scores]))
    drawdown_arr = _zscore(np.array([s.drawdown_penalty for s in scores]))

    for i, s in enumerate(scores):
        s.composite = (
            weights["momentum"] * momentum_arr[i]
            + weights["volume_surge"] * volume_arr[i]
            + weights["volatility_adj_return"] * vol_adj_arr[i]
            - weights["drawdown_penalty"] * drawdown_arr[i]
        )

    return scores


def score_universe(
    ohlcv_by_symbol: dict[str, pd.DataFrame], scoring_cfg: dict
) -> list[SymbolScore]:
    """
    Entry point: score every fetched symbol, drop ones with insufficient
    data, normalize across the surviving batch, and return sorted by
    composite score (descending).
    """
    raw_scores = []
    for symbol, df in ohlcv_by_symbol.items():
        s = score_symbol(symbol, df, scoring_cfg)
        if s is not None:
            raw_scores.append(s)

    logger.info(
        "Scored %d/%d symbols (excluded %d for insufficient/bad data)",
        len(raw_scores),
        len(ohlcv_by_symbol),
        len(ohlcv_by_symbol) - len(raw_scores),
    )

    weights = scoring_cfg["weights"]
    blended = normalize_and_blend(raw_scores, weights)
    return sorted(blended, key=lambda s: s.composite, reverse=True)
