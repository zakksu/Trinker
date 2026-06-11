"""
TRINKER - aoe2.gg / ladder match import
Fetches recent ranked matches by Steam ID with graceful fallbacks.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

try:
    import requests as _requests
except ImportError:
    _requests = None

from ..core.config import AOE2GG_BASE, AOE2NET_BASE, REQUEST_HEADERS, settings
from ..core.database import db_conn, now_iso
from ..core.logger import logger

COMPANION_BASE = "https://data.aoe2companion.com/api"


@dataclass
class OnlineMatch:
    match_id: str
    played_at: str
    map_name: str
    civ: str
    result: str
    rating: Optional[int]
    opponent: str
    source: str
    profile_url: str


@dataclass
class MatchImportResult:
    matches: list[OnlineMatch]
    profile_url: str
    source: str
    error: str = ""


def profile_url_for(steam_id: str) -> str:
    return f"{AOE2GG_BASE}/player/{steam_id.strip()}"


def _parse_aoe2net_matches(data: list, steam_id: str) -> list[OnlineMatch]:
    out: list[OnlineMatch] = []
    for m in data[:20]:
        mid = str(m.get("matchId") or m.get("match_id") or "")
        if not mid:
            continue
        teams = m.get("teams") or []
        player_civ = "Unknown"
        result = "unknown"
        opponent = "—"
        rating = None
        for team in teams:
            for p in team.get("players") or []:
                if str(p.get("profileId") or p.get("steam_id") or "") == steam_id:
                    player_civ = p.get("civ") or p.get("civName") or "Unknown"
                    rating = p.get("rating")
                    won = p.get("winner")
                    if won is True:
                        result = "win"
                    elif won is False:
                        result = "loss"
                else:
                    opponent = p.get("name") or opponent
        started = m.get("started") or m.get("started_time")
        if isinstance(started, (int, float)):
            played = datetime.fromtimestamp(started, tz=timezone.utc).isoformat()
        else:
            played = str(started or now_iso())
        out.append(OnlineMatch(
            match_id=mid,
            played_at=played,
            map_name=m.get("mapName") or m.get("map") or "—",
            civ=str(player_civ),
            result=result,
            rating=int(rating) if rating is not None else None,
            opponent=opponent,
            source="aoe2.net",
            profile_url=profile_url_for(steam_id),
        ))
    return out


def _parse_companion_matches(data: list, steam_id: str) -> list[OnlineMatch]:
    out: list[OnlineMatch] = []
    for m in data[:20]:
        mid = str(m.get("matchId") or m.get("id") or "")
        if not mid:
            continue
        teams = m.get("teams") or []
        player_civ = "Unknown"
        result = "unknown"
        opponent = "—"
        rating = None
        for team in teams:
            for p in team.get("players") or []:
                pid = str(p.get("profileId") or p.get("steamId") or "")
                if pid == steam_id or pid.endswith(steam_id[-8:]):
                    player_civ = p.get("civName") or p.get("civ") or "Unknown"
                    rating = p.get("rating")
                    wr = p.get("won")
                    if wr is True:
                        result = "win"
                    elif wr is False:
                        result = "loss"
                else:
                    opponent = p.get("name") or opponent
        started = m.get("started")
        played = str(started) if started else now_iso()
        out.append(OnlineMatch(
            match_id=mid,
            played_at=played,
            map_name=m.get("mapName") or "—",
            civ=str(player_civ),
            result=result,
            rating=int(rating) if rating is not None else None,
            opponent=opponent,
            source="aoe2companion",
            profile_url=profile_url_for(steam_id),
        ))
    return out


def fetch_recent_matches(steam_id: str, count: int = 10) -> MatchImportResult:
    """
    Fetch recent ladder matches for a Steam ID.
    Tries aoe2.net then AoE2 Companion; returns empty list with error if all fail.
    """
    steam_id = (steam_id or settings.steam_id or "").strip()
    url = profile_url_for(steam_id)
    if not steam_id:
        return MatchImportResult([], url, "", error="Set your Steam ID in Settings first.")

    if not _requests:
        return MatchImportResult([], url, "", error="requests library not available.")

    headers = dict(REQUEST_HEADERS)
    headers["User-Agent"] = "TRINKER/2.0 (https://github.com/zakksu/Trinker)"

    # Legacy aoe2.net API (may be sunset)
    try:
        resp = _requests.get(
            f"{AOE2NET_BASE}/player/matches",
            params={"game": "aoe2de", "steam_id": steam_id, "count": count},
            headers=headers,
            timeout=12,
        )
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list) and data:
                matches = _parse_aoe2net_matches(data, steam_id)
                return MatchImportResult(matches, url, "aoe2.net")
    except Exception as exc:
        logger.debug("aoe2.net fetch failed: %s", exc)

    # AoE2 Companion API
    try:
        resp = _requests.get(
            f"{COMPANION_BASE}/matches",
            params={"profile_ids": steam_id, "page": 1, "language": "en", "count": count},
            headers=headers,
            timeout=12,
        )
        if resp.status_code == 200:
            payload = resp.json()
            data = payload if isinstance(payload, list) else payload.get("matches") or []
            if data:
                matches = _parse_companion_matches(data, steam_id)
                return MatchImportResult(matches, url, "aoe2companion")
    except Exception as exc:
        logger.debug("companion fetch failed: %s", exc)

    return MatchImportResult(
        [],
        url,
        "",
        error=(
            "Online match APIs are temporarily unavailable. "
            f"View your profile at {url} — local replays still auto-import."
        ),
    )


def save_online_matches(matches: list[OnlineMatch], steam_id: str) -> int:
    """Upsert imported matches; returns count saved."""
    if not matches:
        return 0
    saved = 0
    with db_conn() as conn:
        for m in matches:
            conn.execute(
                """INSERT INTO online_matches
                   (match_id, steam_id, played_at, map_name, civ, result,
                    rating, opponent, source, profile_url, imported_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(match_id) DO UPDATE SET
                     result=excluded.result,
                     rating=excluded.rating,
                     imported_at=excluded.imported_at""",
                (
                    m.match_id,
                    steam_id,
                    m.played_at,
                    m.map_name,
                    m.civ,
                    m.result,
                    m.rating,
                    m.opponent,
                    m.source,
                    m.profile_url,
                    now_iso(),
                ),
            )
            saved += 1
    logger.info("Saved %d online match(es) for steam_id=%s", saved, steam_id)
    return saved


def get_stored_matches(steam_id: str = "", limit: int = 10) -> list[OnlineMatch]:
    steam_id = (steam_id or settings.steam_id or "").strip()
    query = "SELECT * FROM online_matches"
    params: list = []
    if steam_id:
        query += " WHERE steam_id = ?"
        params.append(steam_id)
    query += " ORDER BY played_at DESC LIMIT ?"
    params.append(limit)

    with db_conn() as conn:
        rows = conn.execute(query, params).fetchall()
    return [
        OnlineMatch(
            match_id=row["match_id"],
            played_at=row["played_at"],
            map_name=row["map_name"] or "—",
            civ=row["civ"] or "Unknown",
            result=row["result"] or "unknown",
            rating=row["rating"],
            opponent=row["opponent"] or "—",
            source=row["source"] or "",
            profile_url=row["profile_url"] or profile_url_for(steam_id),
        )
        for row in rows
    ]


def import_recent_matches(steam_id: str = "", count: int = 10) -> MatchImportResult:
    """Fetch and persist recent matches."""
    steam_id = (steam_id or settings.steam_id or "").strip()
    result = fetch_recent_matches(steam_id, count)
    if result.matches:
        save_online_matches(result.matches, steam_id)
    return result
