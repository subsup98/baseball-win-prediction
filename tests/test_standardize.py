import math

from mlb_winprob.standardize import _parse_weather, baseball_innings_to_float


def test_baseball_innings_to_float_uses_thirds():
    assert baseball_innings_to_float("6.0") == 6.0
    assert baseball_innings_to_float("5.1") == 5 + 1 / 3
    assert baseball_innings_to_float("0.2") == 2 / 3


def test_parse_weather_marks_closed_roof_and_condition():
    parsed = _parse_weather({"Weather": "68 degrees, Roof Closed.", "Wind": "0 mph, None."})

    assert parsed["temperature"] == 68
    assert parsed["wind_speed"] == 0
    assert math.isnan(parsed["wind_direction"])
    assert parsed["is_dome"] == 1
    assert parsed["weather_condition"] == "Roof Closed"
    assert parsed["weather_source"] == "mlb_stats_api_boxscore"


def test_parse_weather_extracts_humidity_when_source_provides_it():
    parsed = _parse_weather({"Weather": "82 degrees, Clear, humidity 57%.", "Wind": "8 mph, Out To RF."})

    assert parsed["humidity"] == 57.0
