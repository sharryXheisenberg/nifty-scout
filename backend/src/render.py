"""
render.py
---------
Renders the selected PlayerCard lineup into a shareable PNG using a headless
browser (Playwright) against templates/card_template.html. HTML/CSS rendering
gives far more layout control than drawing pixels manually (Pillow), and lets
the visual design evolve without touching Python code.

Template contract:
  {{RUN_DATE}}   -> human-readable date string
  {{FWD_CARDS}}  -> pre-rendered HTML block for forward row
  {{MID_CARDS}}  -> pre-rendered HTML block for midfield row
  {{DEF_CARDS}}  -> pre-rendered HTML block for defender row
"""

from __future__ import annotations

import logging
from pathlib import Path

from playwright.sync_api import sync_playwright

from selector import PlayerCard

logger = logging.getLogger("nifty_scout.render")


def _escape(text: str) -> str:
    """Minimal HTML-escaping for user/data-derived strings dropped into the template."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _render_player_card_html(card: PlayerCard) -> str:
    return f"""
    <div class="player-card">
      <div class="pos-tag">{card.position}</div>
      <div class="symbol">{_escape(card.symbol.replace('.NS', ''))}</div>
      <div class="name">{_escape(card.name)}</div>
      <div class="score">{card.composite_score:+.2f}</div>
      <div class="stats">
        <span>MOM {card.momentum:+.2f}</span>
        <span>VOL {card.volume_surge:+.2f}</span>
      </div>
    </div>
    """.strip()


def build_html(cards: list[PlayerCard], template_path: str, run_date: str) -> str:
    template = Path(template_path).read_text(encoding="utf-8")

    fwd_html = "".join(_render_player_card_html(c) for c in cards if c.position == "FWD")
    mid_html = "".join(_render_player_card_html(c) for c in cards if c.position == "MID")
    def_html = "".join(_render_player_card_html(c) for c in cards if c.position == "DEF")

    html = (
        template.replace("{{RUN_DATE}}", _escape(run_date))
        .replace("{{FWD_CARDS}}", fwd_html)
        .replace("{{MID_CARDS}}", mid_html)
        .replace("{{DEF_CARDS}}", def_html)
    )
    return html


def render_to_png(
    cards: list[PlayerCard],
    template_path: str,
    output_path: str,
    run_date: str,
    width: int = 1200,
    height: int = 1500,
) -> None:
    """
    Renders the filled HTML template to a PNG at output_path using a headless
    Chromium instance. Requires `playwright install chromium` to have been run
    once in the environment (handled in the GitHub Actions workflow / README).
    """
    html = build_html(cards, template_path, run_date)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        try:
            page = browser.new_page(viewport={"width": width, "height": height})
            page.set_content(html, wait_until="networkidle")
            page.screenshot(path=output_path)
        finally:
            browser.close()

    logger.info("Rendered card image to %s", output_path)
