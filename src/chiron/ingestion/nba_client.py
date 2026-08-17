import logging
from datetime import date, datetime

from nba_api.stats.endpoints import (
    commonplayerinfo,
    playergamelog,
    shotchartdetail,
)
from nba_api.stats.static import players as nba_players
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from chiron.db.models import Game, Player, PlayerGameStat, ShotEvent
from chiron.ingestion.nba_http import with_retry
from chiron.ingestion.schemas import FantasyScoringRules, PlayerGameStatSchema, ShotEventSchema
from chiron.ingestion.utils import rate_limit

NBA_API_TIMEOUT = 60

logger = logging.getLogger(__name__)


def compute_fantasy_points(
    stat: PlayerGameStatSchema,
    rules: FantasyScoringRules | None = None,
) -> float:
    rules = rules or FantasyScoringRules()
    return (
        (stat.points or 0) * rules.points
        + (stat.rebounds or 0) * rules.rebounds
        + (stat.assists or 0) * rules.assists
        + (stat.steals or 0) * rules.steals
        + (stat.blocks or 0) * rules.blocks
        + (stat.turnovers or 0) * rules.turnovers
        + (stat.fg3_made or 0) * rules.fg3_made
    )


def _safe_float(value) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def fetch_active_players(limit: int | None = None) -> list[dict]:
    all_players = nba_players.get_active_players()
    if limit:
        return all_players[:limit]
    return all_players


def fetch_player_info(player_id: int) -> dict:
    rate_limit()
    info = with_retry(
        lambda: commonplayerinfo.CommonPlayerInfo(
            player_id=player_id,
            timeout=NBA_API_TIMEOUT,
        ).get_normalized_dict()
    )
    rows = info.get("CommonPlayerInfo", [])
    if not rows:
        return {"id": player_id, "full_name": str(player_id), "team_abbrev": None, "position": None}
    row = rows[0]
    return {
        "id": player_id,
        "full_name": row.get("DISPLAY_FIRST_LAST") or row.get("PLAYER_NAME") or str(player_id),
        "team_abbrev": row.get("TEAM_ABBREVIATION"),
        "position": row.get("POSITION"),
    }


def _parse_game_date(value: str | None) -> date:
    if not value:
        return date.today()
    for fmt in ("%b %d, %Y", "%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return date.today()


def fetch_player_game_logs(player_id: int, season: str) -> list[tuple[PlayerGameStatSchema, date]]:
    rate_limit()
    data = with_retry(
        lambda: playergamelog.PlayerGameLog(
            player_id=player_id,
            season=season,
            timeout=NBA_API_TIMEOUT,
        ).get_normalized_dict()
    )
    rows = data.get("PlayerGameLog", [])
    stats: list[tuple[PlayerGameStatSchema, date]] = []
    for row in rows:
        game_id = row.get("Game_ID")
        if not game_id:
            continue
        game_date = _parse_game_date(row.get("GAME_DATE"))
        fg_made = _safe_int(row.get("FGM"))
        fg_attempted = _safe_int(row.get("FGA"))
        fg3_made = _safe_int(row.get("FG3M"))
        fg3_attempted = _safe_int(row.get("FG3A"))
        ft_made = _safe_int(row.get("FTM"))
        ft_attempted = _safe_int(row.get("FTA"))
        efg = None
        if fg_attempted:
            if fg_made is not None and fg3_made is not None:
                efg = (fg_made + 0.5 * fg3_made) / fg_attempted
            else:
                efg = None
        ts = None
        if fg_attempted and ft_attempted is not None:
            ts_denom = 2 * (fg_attempted + 0.44 * ft_attempted)
            if ts_denom:
                pts = _safe_float(row.get("PTS")) or 0
                ts = pts / ts_denom
        stat = PlayerGameStatSchema(
            player_id=player_id,
            game_id=str(game_id),
            minutes=_safe_float(row.get("MIN")),
            points=_safe_int(row.get("PTS")),
            rebounds=_safe_int(row.get("REB")),
            assists=_safe_int(row.get("AST")),
            steals=_safe_int(row.get("STL")),
            blocks=_safe_int(row.get("BLK")),
            turnovers=_safe_int(row.get("TOV")),
            fg_made=fg_made,
            fg_attempted=fg_attempted,
            fg3_made=fg3_made,
            fg3_attempted=fg3_attempted,
            ft_made=ft_made,
            ft_attempted=ft_attempted,
            efg_pct=efg,
            ts_pct=ts,
        )
        stat.fantasy_points = compute_fantasy_points(stat)
        stats.append((stat, game_date))
    return stats


def fetch_shot_events(player_id: int, season: str) -> list[ShotEventSchema]:
    rate_limit()
    data = with_retry(
        lambda: shotchartdetail.ShotChartDetail(
            player_id=player_id,
            team_id=0,
            season_nullable=season,
            context_measure_simple="FGA",
            timeout=NBA_API_TIMEOUT,
        ).get_normalized_dict()
    )
    rows = data.get("Shot_Chart_Detail", [])
    events: list[ShotEventSchema] = []
    for idx, row in enumerate(rows):
        game_id = row.get("GAME_ID")
        if not game_id:
            continue
        events.append(
            ShotEventSchema(
                player_id=player_id,
                game_id=str(game_id),
                event_num=idx,
                period=_safe_int(row.get("PERIOD")),
                minutes_remaining=_safe_int(row.get("MINUTES_REMAINING")),
                seconds_remaining=_safe_int(row.get("SECONDS_REMAINING")),
                x=_safe_float(row.get("LOC_X")),
                y=_safe_float(row.get("LOC_Y")),
                shot_distance=_safe_float(row.get("SHOT_DISTANCE")),
                shot_made=(row.get("SHOT_MADE_FLAG") or "0") == "1",
                shot_zone=row.get("SHOT_ZONE_BASIC") or row.get("SHOT_ZONE_AREA"),
            )
        )
    return events


def upsert_player(session: Session, player_data: dict) -> None:
    stmt = insert(Player).values(**player_data)
    stmt = stmt.on_conflict_do_update(
        index_elements=[Player.id],
        set_={
            "full_name": stmt.excluded.full_name,
            "team_abbrev": stmt.excluded.team_abbrev,
            "position": stmt.excluded.position,
            "is_active": True,
        },
    )
    session.execute(stmt)


def upsert_game(session: Session, game_id: str, game_date: date, season: str) -> None:
    stmt = insert(Game).values(
        id=game_id,
        game_date=game_date,
        season=season,
    )
    stmt = stmt.on_conflict_do_nothing(index_elements=[Game.id])
    session.execute(stmt)


def upsert_player_game_stat(session: Session, stat: PlayerGameStatSchema) -> None:
    values = stat.model_dump()
    stmt = insert(PlayerGameStat).values(**values)
    skip_keys = ("player_id", "game_id")
    update_cols = {k: getattr(stmt.excluded, k) for k in values if k not in skip_keys}
    stmt = stmt.on_conflict_do_update(
        constraint="uq_player_game",
        set_=update_cols,
    )
    session.execute(stmt)


def upsert_shot_event(session: Session, event: ShotEventSchema) -> None:
    values = event.model_dump()
    stmt = insert(ShotEvent).values(**values)
    update_cols = {
        k: getattr(stmt.excluded, k)
        for k in values
        if k not in ("player_id", "game_id", "event_num")
    }
    stmt = stmt.on_conflict_do_update(
        constraint="uq_shot_event",
        set_=update_cols,
    )
    session.execute(stmt)


def ingest_player(session: Session, player_id: int, season: str) -> dict[str, int]:
    counts = {"games": 0, "stats": 0, "shots": 0}
    player_data = fetch_player_info(player_id)
    upsert_player(session, player_data)

    stats = fetch_player_game_logs(player_id, season)
    for stat, game_date in stats:
        upsert_game(session, stat.game_id, game_date, season)
        upsert_player_game_stat(session, stat)
        counts["stats"] += 1

    shots = fetch_shot_events(player_id, season)
    for shot in shots:
        upsert_shot_event(session, shot)
        counts["shots"] += 1

    counts["games"] = len({s.game_id for s, _ in stats})
    session.commit()
    logger.info("Ingested player %s: %s", player_id, counts)
    return counts
