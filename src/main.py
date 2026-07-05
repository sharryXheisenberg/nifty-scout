"""
main.py
-------
Entry point for the daily pipeline run. Wires together:

    fetch_universe -> score_universe -> select_team -> render_to_png -> publish_run

Run locally with:  python src/main.py
Run in CI via:      .github/workflows/daily_scout.yml (same command)

Exit codes:
  0 -> success
  1 -> unrecoverable pipeline failure (logged with full context)
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path

import yaml

from fetch import fetch_universe
from scoring import score_universe
from selector import load_metadata, select_team, write_team_json
from render import render_to_png
from publish import publish_run

logger = logging.getLogger("nifty_scout.main")


def load_config(config_path: str = "config.yaml") -> dict:
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def setup_logging(logging_cfg: dict) -> None:
    log_file = logging_cfg.get("file")
    handlers = [logging.StreamHandler(sys.stdout)]
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        level=getattr(logging, logging_cfg.get("level", "INFO")),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers,
    )


def run() -> int:
    config = load_config()
    setup_logging(config["logging"])

    run_date = datetime.now().strftime("%Y-%m-%d")
    logger.info("=== Nifty Scout Report — run started for %s ===", run_date)

    try:
        # 1. Fetch
        fetch_result = fetch_universe(config)
        if fetch_result.success_rate < 0.5:
            logger.warning(
                "Fetch success rate low (%.0f%%) — proceeding with partial universe",
                fetch_result.success_rate * 100,
            )

        # 2. Score
        scores = score_universe(fetch_result.ok, config["scoring"])
        if not scores:
            raise RuntimeError("No symbols survived scoring — cannot select a team")

        # 3. Select
        metadata = load_metadata(config["data"]["tickers_file"])
        cards = select_team(scores, fetch_result.ok, metadata, config["selector"])

        output_dir = config["render"]["output_dir"]
        dated_json_path = str(Path(output_dir) / f"{run_date}.json")
        write_team_json(cards, dated_json_path, run_date)

        # 4. Render
        dated_png_path = str(Path(output_dir) / f"{run_date}.png")
        render_to_png(
            cards,
            template_path=config["render"]["template_path"],
            output_path=dated_png_path,
            run_date=run_date,
            width=config["render"]["image_width"],
            height=config["render"]["image_height"],
        )

        # 5. Publish
        publish_run(
            dated_png_path=dated_png_path,
            dated_json_path=dated_json_path,
            publish_cfg=config["publish"],
            output_dir=output_dir,
            run_date=run_date,
        )

        logger.info("=== Run completed successfully for %s ===", run_date)
        return 0

    except Exception as e:
        logger.exception("Pipeline failed: %s", e)
        return 1


if __name__ == "__main__":
    sys.exit(run())
