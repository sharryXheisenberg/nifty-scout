"""
publish.py
----------
Final pipeline stage: takes the rendered PNG + team JSON for the run and
"publishes" them:
  1. Copies dated output to a stable `latest.png` / `latest.json` (for
     embeds/badges that always point at today's result).
  2. Optionally commits the new output files to the git repo (so GitHub
     Actions can push the daily artifact back to the repo).
  3. Optionally posts to X/Twitter if credentials are configured.

Each side effect is independently toggleable via config so this can run
safely in local dev without accidentally committing or tweeting.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger("nifty_scout.publish")


class PublishError(Exception):
    pass


def update_latest_pointers(
    dated_png_path: str,
    dated_json_path: str,
    output_dir: str,
    latest_png_name: str,
    latest_json_name: str,
) -> None:
    latest_png = Path(output_dir) / latest_png_name
    latest_json = Path(output_dir) / latest_json_name

    shutil.copyfile(dated_png_path, latest_png)
    shutil.copyfile(dated_json_path, latest_json)
    logger.info("Updated latest pointers: %s, %s", latest_png, latest_json)


def git_commit_outputs(output_dir: str, commit_message: str) -> None:
    """
    Stages and commits the output directory. Designed to run inside GitHub
    Actions where git user identity is configured by the workflow step
    before this runs (see .github/workflows/daily_scout.yml). No-ops
    gracefully (logs + returns) if there's nothing new to commit, instead
    of treating "nothing changed" as a failure.
    """
    try:
        subprocess.run(["git", "add", output_dir], check=True)

        diff_check = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
        )
        if diff_check.returncode == 0:
            logger.info("No changes to commit — output identical to last run")
            return

        subprocess.run(["git", "commit", "-m", commit_message], check=True)
        subprocess.run(["git", "push"], check=True)
        logger.info("Committed and pushed: %s", commit_message)
    except subprocess.CalledProcessError as e:
        raise PublishError(f"Git commit/push failed: {e}") from e


def post_to_twitter(image_path: str, status_text: str) -> None:
    """
    Optional auto-post. Requires TWITTER_API_KEY, TWITTER_API_SECRET,
    TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET in the environment
    (set as GitHub Actions secrets, never committed to the repo).
    """
    import tweepy  # local import: only needed when auto-post is enabled

    required_env = [
        "TWITTER_API_KEY",
        "TWITTER_API_SECRET",
        "TWITTER_ACCESS_TOKEN",
        "TWITTER_ACCESS_SECRET",
    ]
    missing = [v for v in required_env if not os.environ.get(v)]
    if missing:
        raise PublishError(f"Missing Twitter credentials in env: {missing}")

    auth = tweepy.OAuth1UserHandler(
        os.environ["TWITTER_API_KEY"],
        os.environ["TWITTER_API_SECRET"],
        os.environ["TWITTER_ACCESS_TOKEN"],
        os.environ["TWITTER_ACCESS_SECRET"],
    )
    api = tweepy.API(auth)
    client = tweepy.Client(
        consumer_key=os.environ["TWITTER_API_KEY"],
        consumer_secret=os.environ["TWITTER_API_SECRET"],
        access_token=os.environ["TWITTER_ACCESS_TOKEN"],
        access_token_secret=os.environ["TWITTER_ACCESS_SECRET"],
    )

    media = api.media_upload(image_path)
    client.create_tweet(text=status_text, media_ids=[media.media_id])
    logger.info("Posted to Twitter/X with media %s", image_path)


def publish_run(
    dated_png_path: str,
    dated_json_path: str,
    publish_cfg: dict,
    output_dir: str,
    run_date: str,
) -> None:
    update_latest_pointers(
        dated_png_path,
        dated_json_path,
        output_dir,
        publish_cfg["latest_filename"],
        publish_cfg["latest_json_filename"],
    )

    if publish_cfg.get("git_commit", False):
        commit_message = run_date.join(
            publish_cfg["git_commit_message_pattern"].split("%Y-%m-%d")
        ) if "%Y-%m-%d" in publish_cfg["git_commit_message_pattern"] else (
            f"{publish_cfg['git_commit_message_pattern']} {run_date}"
        )
        git_commit_outputs(output_dir, commit_message)

    if publish_cfg.get("auto_post_enabled", False):
        status_text = f"📊 Nifty Scout Report — {run_date}\nToday's Team of the Week is out."
        try:
            post_to_twitter(dated_png_path, status_text)
        except PublishError as e:
            # Auto-post failure should never fail the whole pipeline run —
            # the data/image artifacts are already safely published.
            logger.error("Auto-post failed (non-fatal): %s", e)
