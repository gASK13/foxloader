from __future__ import annotations

from guessit import guessit

from app.models import ParsedMedia


def detect_media(link_or_name: str) -> ParsedMedia:
    result = guessit(link_or_name or "")
    season = result.get("season")
    episode = result.get("episode")
    is_episode = result.get("type") == "episode" or season is not None or episode is not None
    if not is_episode:
        return ParsedMedia(is_series=False, season_number=None)
    if season is None:
        season = 1
    return ParsedMedia(is_series=True, season_number=int(season))
