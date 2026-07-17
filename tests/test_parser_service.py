from app.services.parser_service import detect_media


def test_detect_series_with_explicit_season() -> None:
    parsed = detect_media("Futurama.S03E05.1080p.WEB-DL.mkv")
    assert parsed.is_series is True
    assert parsed.season_number == 3


def test_detect_series_defaults_to_season_one_when_missing() -> None:
    parsed = detect_media("Some.Show.E05.1080p.WEB-DL.mkv")
    assert parsed.is_series is True
    assert parsed.season_number == 1


def test_detect_movie_returns_non_series() -> None:
    parsed = detect_media("Dune.Part.Two.2024.2160p.mkv")
    assert parsed.is_series is False
    assert parsed.season_number is None
