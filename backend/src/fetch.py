"""
fetch.py
--------
[FIX-MARKER: fetch-v3-plain-session-serialized]

Pulls OHLCV history for the configured NSE ticker universe via yfinance.

Design goals:
  - Never let one bad symbol crash the whole run (isolate + log + continue).
  - Avoid re-hitting Yahoo for data we already fetched today (disk cache with TTL).
  - Bounded parallelism + exponential backoff to stay polite to the free API.
  - Pure function boundary: returns a dict[symbol -> DataFrame] plus a report
    of what failed, so callers (scoring.py) can decide how to handle gaps.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd
import requests
import yfinance as yf
import yaml
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

logger = logging.getLogger("nifty_scout.fetch")

# A plain requests.Session with a realistic browser User-Agent. Earlier we
# tried a curl_cffi impersonated session here — that caused a *different*
# crash ('str' object has no attribute 'name') due to a known incompatibility
# between yfinance's internal cookie/crumb handling and curl_cffi's Session
# shape. A plain requests.Session avoids that crash; the real defense
# against rate-limiting is the full serialization + throttle below, not the
# session type.
_session = requests.Session()
_session.headers.update(
    {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
    }
)

# Global lock ensures requests are fully serialized end-to-end (not just
# spaced at start) — only one HTTP request to Yahoo is ever in flight at a
# time, system-wide, with a minimum gap enforced *after* each one completes.
# This matters more on shared/datacenter IPs (GitHub Actions) than on a
# residential IP, where Yahoo's rate limiter is noticeably stricter.
_request_lock = threading.Lock()
_last_request_time = [0.0]


def _throttled_call(min_interval_sec: float, fn, *args, **kwargs):
    with _request_lock:
        now = time.monotonic()
        wait = _last_request_time[0] + min_interval_sec - now
        if wait > 0:
            time.sleep(wait)
        try:
            return fn(*args, **kwargs)
        finally:
            _last_request_time[0] = time.monotonic()


class FetchError(Exception):
    """Raised when a symbol fails to fetch after all retries are exhausted."""


@dataclass
class FetchResult:
    ok: dict[str, pd.DataFrame] = field(default_factory=dict)
    failed: dict[str, str] = field(default_factory=dict)  # symbol -> reason

    @property
    def success_rate(self) -> float:
        total = len(self.ok) + len(self.failed)
        return (len(self.ok) / total) if total else 0.0


def load_config(config_path: str = "config.yaml") -> dict:
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def load_universe(tickers_path: str) -> list[dict]:
    with open(tickers_path, "r") as f:
        payload = json.load(f)
    universe = payload.get("universe", [])
    if not universe:
        raise ValueError(f"No tickers found in {tickers_path}")
    return universe


def _cache_path(cache_dir: Path, symbol: str) -> Path:
    safe_symbol = symbol.replace("/", "_")
    return cache_dir / f"{safe_symbol}.parquet"


def _is_cache_fresh(path: Path, ttl_hours: int) -> bool:
    if not path.exists():
        return False
    age = datetime.now() - datetime.fromtimestamp(path.stat().st_mtime)
    return age < timedelta(hours=ttl_hours)


def _read_cache(path: Path) -> Optional[pd.DataFrame]:
    try:
        return pd.read_parquet(path)
    except Exception as e:  # corrupted cache file — treat as miss, don't crash
        logger.warning("Cache read failed for %s (%s); refetching", path, e)
        return None


def _write_cache(path: Path, df: pd.DataFrame) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(path)
    except Exception as e:
        # Cache write failure should never break the pipeline, just log it.
        logger.warning("Cache write failed for %s (%s)", path, e)


def _make_retrying_download(max_retries: int, backoff_base: float, min_request_interval_sec: float):
    """Wrap the actual Yahoo call with tenacity retry, parameterized from config."""

    @retry(
        stop=stop_after_attempt(max_retries),
        wait=wait_exponential(multiplier=backoff_base, min=backoff_base, max=30),
        retry=retry_if_exception_type((FetchError, ConnectionError, TimeoutError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    def _download(symbol: str, period_days: int, timeout: int) -> pd.DataFrame:
        def _do_request():
            return yf.download(
                symbol,
                period=f"{period_days}d",
                interval="1d",
                auto_adjust=True,
                progress=False,
                timeout=timeout,
                session=_session,
            )

        df = _throttled_call(min_request_interval_sec, _do_request)
        if df is None or df.empty:
            raise FetchError(f"Empty response for {symbol}")
        return df

    return _download


def fetch_symbol(
    symbol: str,
    cache_dir: Path,
    lookback_days: int,
    cache_ttl_hours: int,
    request_timeout_sec: int,
    downloader,
    min_rows_required: int,
) -> tuple[str, Optional[pd.DataFrame], Optional[str]]:
    """
    Fetch a single symbol, using cache when fresh.
    Returns (symbol, dataframe_or_None, error_reason_or_None).
    """
    path = _cache_path(cache_dir, symbol)

    if _is_cache_fresh(path, cache_ttl_hours):
        cached = _read_cache(path)
        if cached is not None and len(cached) >= min_rows_required:
            logger.debug("Cache hit for %s", symbol)
            return symbol, cached, None

    try:
        df = downloader(symbol, lookback_days, request_timeout_sec)
    except Exception as e:
        return symbol, None, f"{type(e).__name__}: {e}"

    if len(df) < min_rows_required:
        return symbol, None, f"Insufficient rows ({len(df)} < {min_rows_required})"

    # Flatten yfinance's MultiIndex columns if present (happens for single-symbol
    # calls in some yfinance versions when group_by defaults change).
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    _write_cache(path, df)
    return symbol, df, None


def fetch_universe(config: dict) -> FetchResult:
    """
    Fetch OHLCV for every symbol in the configured universe, in parallel,
    with caching and retry. Isolates per-symbol failures.
    """
    data_cfg = config["data"]
    fetch_cfg = config["fetch"]

    cache_dir = Path(data_cfg["cache_dir"])
    cache_dir.mkdir(parents=True, exist_ok=True)

    universe = load_universe(data_cfg["tickers_file"])
    symbols = [entry["symbol"] for entry in universe]

    downloader = _make_retrying_download(
        max_retries=fetch_cfg["max_retries"],
        backoff_base=fetch_cfg["retry_backoff_base_sec"],
        min_request_interval_sec=fetch_cfg.get("min_request_interval_sec", 1.5),
    )

    result = FetchResult()
    start = time.monotonic()

    with ThreadPoolExecutor(max_workers=data_cfg["max_workers"]) as pool:
        futures = {
            pool.submit(
                fetch_symbol,
                symbol=symbol,
                cache_dir=cache_dir,
                lookback_days=data_cfg["lookback_days"],
                cache_ttl_hours=data_cfg["cache_ttl_hours"],
                request_timeout_sec=data_cfg["request_timeout_sec"],
                downloader=downloader,
                min_rows_required=fetch_cfg["min_rows_required"],
            ): symbol
            for symbol in symbols
        }

        for future in as_completed(futures):
            symbol = futures[future]
            try:
                sym, df, err = future.result()
            except Exception as e:  # belt-and-suspenders: thread itself blew up
                sym, df, err = symbol, None, f"Unhandled: {e}"

            if err is not None:
                result.failed[sym] = err
                logger.warning("FAILED %s: %s", sym, err)
            else:
                result.ok[sym] = df

    elapsed = time.monotonic() - start
    logger.info(
        "Fetch complete: %d ok, %d failed (%.1f%% success) in %.1fs",
        len(result.ok),
        len(result.failed),
        result.success_rate * 100,
        elapsed,
    )

    if not result.ok:
        raise RuntimeError(
            "All symbols failed to fetch — aborting run. "
            f"Sample failures: {dict(list(result.failed.items())[:5])}"
        )

    return result


def main() -> FetchResult:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    config = load_config()
    return fetch_universe(config)


if __name__ == "__main__":
    main()