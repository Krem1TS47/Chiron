import logging
import re

import httpx

from chiron.config import get_settings
from chiron.ingestion.schemas import FantasyScoringRules

logger = logging.getLogger(__name__)

ESPN_FANTASY_BASE = "https://lm-api-reads.fantasy.espn.com/apis/v3/games/fba/seasons"


def _build_headers(settings) -> dict[str, str]:
    headers = {"Accept": "application/json"}
    if settings.espn_swid and settings.espn_s2:
        headers["Cookie"] = f"SWID={settings.espn_swid}; espn_s2={settings.espn_s2};"
    return headers


def fetch_league_settings(league_id: str | None = None, season: int | None = None) -> dict:
    settings = get_settings()
    league_id = league_id or settings.espn_league_id
    season = season or settings.espn_season
    if not league_id:
        logger.warning("ESPN_LEAGUE_ID not configured; skipping ESPN fetch")
        return {}

    url = f"{ESPN_FANTASY_BASE}/{season}/segments/0/leagues/{league_id}"
    params = {"view": "mSettings"}
    try:
        with httpx.Client(timeout=30.0, headers=_build_headers(settings)) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as exc:
        logger.warning("ESPN API request failed: %s", exc)
        return {}


def parse_scoring_rules(league_json: dict) -> FantasyScoringRules:
    scoring_items = (
        league_json.get("settings", {}).get("scoringSettings", {}).get("scoringItems", [])
    )
    rules = FantasyScoringRules()
    mapping = {
        "points": "points",
        "rebounds": "rebounds",
        "assists": "assists",
        "steals": "steals",
        "blocks": "blocks",
        "turnovers": "turnovers",
        "threepointmade": "fg3_made",
    }
    for item in scoring_items:
        stat_id = str(item.get("statId", "")).lower()
        for key, attr in mapping.items():
            if key in stat_id or key in str(item.get("description", "")).lower():
                setattr(rules, attr, float(item.get("points", getattr(rules, attr))))
    return rules


def fetch_league_roster_player_ids(
    league_id: str | None = None,
    season: int | None = None,
) -> list[int]:
    settings = get_settings()
    league_id = league_id or settings.espn_league_id
    season = season or settings.espn_season
    if not league_id:
        return []

    url = f"{ESPN_FANTASY_BASE}/{season}/segments/0/leagues/{league_id}"
    params = {"view": "mRoster"}
    player_ids: list[int] = []
    try:
        with httpx.Client(timeout=30.0, headers=_build_headers(settings)) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError as exc:
        logger.warning("ESPN roster fetch failed: %s", exc)
        return []

    for team in data.get("teams", []):
        for entry in team.get("roster", {}).get("entries", []):
            player = entry.get("playerPoolEntry", {}).get("player", {})
            nba_ref = player.get("fullName")
            espn_id = player.get("id")
            if espn_id:
                player_ids.append(int(espn_id))
            if nba_ref:
                logger.debug("Roster player: %s (%s)", nba_ref, espn_id)
    return player_ids


async def scrape_espn_league_page(league_id: str, season: int) -> str:
    """Playwright fallback when ESPN API is unavailable."""
    from playwright.async_api import async_playwright

    url = f"https://fantasy.espn.com/basketball/team?leagueId={league_id}&seasonId={season}"
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, wait_until="networkidle", timeout=60000)
        content = await page.content()
        await browser.close()
    return content


def extract_league_id_from_html(html: str) -> str | None:
    match = re.search(r"leagueId[\"']?\s*[:=]\s*[\"']?(\d+)", html)
    return match.group(1) if match else None
